# Import necessary libraries
import re, ipaddress
import os
import sys
import json
import glob
import time
import yaml
import serial
import openpyxl
import subprocess
import threading
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from enum import Enum
from openpyxl.drawing.image import Image
import xml.etree.ElementTree as ET
from openpyxl.styles import PatternFill, Border, Side, Alignment, Font
from openpyxl.utils import get_column_letter
from pathlib import Path
from datetime import datetime
from collections import OrderedDict
from typing import Final, Tuple , Dict, OrderedDict
from typing import List, TypedDict
from Shutdown_Time_Scripts.fgs_transfer import FGSTransfer

plot_lock = threading.Lock()

# Global variables for process tracking and stop flag monitoring
running_processes = []
running_threads = []
stop_requested = threading.Event()
script_directory = Path(__file__).parent.parent
stop_flag_path = script_directory / "stop.flag"

def check_stop_flag(py_logger):
    """
    Continuously monitors for the stop.flag file and sets the stop event if found.
    This function runs in a separate thread to provide real-time monitoring.
    """
    while not stop_requested.is_set():
        if stop_flag_path.exists():
            py_logger.warning(f"Stop flag detected at {stop_flag_path}. Initiating graceful shutdown...")
            stop_requested.set()
            break
        time.sleep(0.5)  # Check every 500ms

def register_process(process):
    """
    Register a subprocess for tracking so it can be terminated if stop flag is detected.
    
    Args:
        process: subprocess.Popen object or process ID
    """
    global running_processes
    running_processes.append(process)

def register_thread(thread):
    """
    Register a thread for tracking so it can be terminated if stop flag is detected.
    
    Args:
        thread: threading.Thread object
    """
    global running_threads
    running_threads.append(thread)

def terminate_all_processes(py_logger):
    """
    Terminate all registered processes and threads gracefully.
    This function is called when stop flag is detected.
    """
    global running_processes, running_threads
    
    py_logger.warning("Terminating all running processes and threads...")
    
    # Terminate all registered processes
    for process in running_processes[:]:  # Create a copy to avoid modification during iteration
        try:
            if hasattr(process, 'terminate'):
                py_logger.warning(f"Terminating process PID: {process.pid}")
                process.terminate()
                process.wait(timeout=5)  # Wait up to 5 seconds
            running_processes.remove(process)
        except Exception as e:
            py_logger.error(f"Error terminating process: {e}")
            try:
                if hasattr(process, 'kill'):
                    process.kill()
                running_processes.remove(process)
            except Exception as kill_error:
                py_logger.error(f"Error killing process: {kill_error}")
    
    # Kill any dlt-viewer processes by name using system commands
    try:
        import platform
        if platform.system() == "Windows":
            # Use taskkill on Windows
            subprocess.run(["taskkill", "/F", "/IM", "dlt-viewer.exe"], capture_output=True, check=False)
            py_logger.warning("Terminated dlt-viewer.exe processes on Windows")
        else:
            # Use pkill on Linux/Unix
            subprocess.run(["pkill", "-f", "dlt-viewer"], capture_output=True, check=False)
            py_logger.warning("Terminated dlt-viewer processes on Linux/Unix")
    except Exception as e:
        py_logger.error(f"Error terminating dlt-viewer processes: {e}")
    
    # Set stop event for threads
    for thread in running_threads[:]:
        try:
            if thread.is_alive():
                py_logger.warning(f"Stopping thread: {thread.name}")
                # For threads that check stop_requested, they will stop automatically
            running_threads.remove(thread)
        except Exception as e:
            py_logger.error(f"Error stopping thread: {e}")
    
    py_logger.info("Process and thread termination completed.")

def check_stop_flag_periodically(py_logger):
    """
    Check if stop flag exists and handle graceful shutdown if detected.
    This should be called periodically during long-running operations.
    
    Returns:
        bool: True if stop was requested, False otherwise
    """
    if stop_requested.is_set() or stop_flag_path.exists():
        py_logger.warning("Stop requested. Terminating all processes...")
        terminate_all_processes(py_logger)
        return True
    return False

OFFSET_TIME: Final = 1.5

# Define a custom type for the shutdown timing information
class ShutdownInfo(TypedDict):
    process: str
    shutdown_time: datetime
    difference: float
    difference_ms: float

class ECUType(Enum):
    RCAR = "RCAR"
    PADAS = "PADAS"
    ELITE = "ELITE"
    SoC0 = "SoC0"
    SoC1 = "SoC1"

# Define a custom type for the shutdown summary information
class ShutdownSummaryInfo(TypedDict):
    process: str
    min_time: float
    max_time: float
    values: List[float]
    avg_time: float

class ResultThread(threading.Thread):
   def __init__(self, target, args=(), kwargs=None):
       super().__init__()
       self._target = target
       self._args   = args
       self._kwargs = kwargs or {}
       self.result  = None

   def run(self):
       # run() is what .start() invokes
       self.result = self._target(*self._args, **self._kwargs)

# py_logger = None
local_save_path = None
current_timestamp = None
table_headers = None

# Define the column names for the application shutdown time data
application_shutdown_time_columns = ['Services/Applications', 'Time (HH:MM:SS:MS)', 'Shutdown Time (SS:MS)',
                                    'Shutdown Time (MS)']
# Define the column names for the application shutdown summary data
application_shutdown_summary_columns = ['Services/Applications', 'Minimum (sec)', 'Maximum (sec)',
                                    'Average (sec)']

# Define a border style for cells in the Excel sheet
border_style = Border(left=Side(border_style='thin'), right=Side(border_style='thin'),
                        top=Side(border_style='thin'), bottom=Side(border_style='thin'))

def remove_png_files(py_logger):
    script_dir = Path(__file__).parent
    png_files = list(script_dir.glob('*.png'))
    if png_files:
        py_logger.info(f"Cleaning up {len(png_files)} temporary chart file(s)...")
        for file in png_files:
            try:
                file.unlink()
            except Exception as e:
                py_logger.warning(f"Could not delete file {file.name}: {e}")  


def adjust_column_width(sheet, ecu_type, logger):
    """
    Automatically adjusts column widths in an Excel worksheet based on content length.
   
    This function analyzes the content of each column in the worksheet and sets
    the column width to accommodate the longest content with some padding. It
    intelligently handles various Excel formatting scenarios including merged cells,
    wrapped text, and specific content types.
   
    Args:
        sheet (openpyxl.worksheet.worksheet.Worksheet): The Excel worksheet to adjust
        ecu_type (str): The ECU type identifier used to skip certain log file references
       
    Features:
        - Calculates optimal width based on maximum content length in each column
        - Skips merged cells to avoid width calculation conflicts
        - Ignores cells with text wrapping enabled
        - Filters out log file references containing ECU type
        - Ensures minimum column width of 9 characters
        - Adds 3 characters padding for better readability
       
    Note:
        This function is essential for creating professional-looking Excel reports
        where all content is visible without manual column width adjustments.
    """
    # Iterate through each column in the Excel sheet
    for col in sheet.columns:
        # Initialize a variable to track the maximum content length within the column
        max_length = 0
       
        # Extract the letter representing the label of the current column
        column_letter = get_column_letter(col[0].column)

        # Iterate through each cell in the current column, starting from the start_row
        for cell in col[0:]:
            try:
                # Check if the cell is empty
                if not cell.value:
                    continue
               
                # Skip cells with specific content
                if f'Startup_Time_Logs_{ecu_type}' in str(cell.value)  or str(cell.value) in table_headers:
                    continue

                # Attempt to retrieve the content of the cell and check its length
                cell_content = str(cell.value)
               
                # Check if the cell's alignment has wrap text enabled
                if cell.alignment.wrap_text:
                    lines = cell_content.split('\n')
                    max_length = max(max(len(line) for line in lines), max_length)
                else:
                    # If wrap text is not enabled, use the length of the cell content directly
                    max_length = max(len(cell_content), max_length)

            except (TypeError, AttributeError, ValueError) as e:
                # Handle specific exceptions
                logger.error(f"An error occurred: {e}")

        # Calculate the adjusted width for the column based on the maximum content length with extra space
        adjusted_width = max(max_length + 3, 9)  # Ensure a minimum width of 9

        # Set the column width in the Excel sheet to the calculated adjusted width
        sheet.column_dimensions[column_letter].width = adjusted_width
def format_excel_cells(sheet, start_row):
    # Iterate over each row in the sheet, starting from the specified row
    for row in sheet.iter_rows(min_row=start_row, max_row=sheet.max_row):
       
        # Skip empty rows
        if all(cell.value is None for cell in row):
            continue
       
        # Iterate over each cell in the row
        for cell in row[0:]:  
            # Skip empty cells
            if cell.value is None:
                continue
           
            # Check if the cell value is a column header
            if cell.value in (application_shutdown_time_columns+application_shutdown_summary_columns):
               
                # Apply a green fill color and bold font to column headers
                cell.fill = PatternFill(start_color="B5E6A2", end_color="B5E6A2", fill_type="solid")
                cell.font = Font(bold=True)
                cell.border = border_style
                continue
           
            elif cell.value == "PASS":
                # If the cell value is "PASS", fill it with a light green color.
                cell.fill = PatternFill(start_color = "92D050", end_color = "92D050", fill_type = "solid")

            elif cell.value == "FAIL":
                # If the cell value is "FAIL", fill it with a light red color.
                cell.fill = PatternFill(start_color = "FF0000", end_color = "FF0000", fill_type = "solid")
               
            # Center align the cell contents horizontally and vertically
            cell.alignment = Alignment(horizontal='center', vertical='center')
           
            # Apply the defined border style to the cell
            cell.border = border_style

def plot_shutdown_times(terminated_apps, sheet, start_row, ecu_type):
    with plot_lock:
        # Extract application names and time differences
        app_names = [app['process'] for app in terminated_apps]
        time_diffs = [app['difference_ms'] for app in terminated_apps]
       
        # Create horizontal bar chart
        fig_height = max(6, len(app_names) * 0.2)
        plt.figure(figsize=(12, 8))
       
        # Create horizontal bars
        y_pos = np.arange(len(app_names))
        bars = plt.barh(y_pos, time_diffs, align='center', alpha=0.7, height=0.4)
       
        # Add value labels next to each bar
        for i, bar in enumerate(bars):
            width = bar.get_width()
            plt.text(width + 50,  # Position text slightly to the right of the bar
                    bar.get_y() + bar.get_height()/2,  # Vertical center of the bar
                    f'{time_diffs[i]:.0f} ms',  # Text with value and unit
                    ha='left',  # Horizontal alignment
                    va='center',  # Vertical alignment
                    fontsize=9)  # Font size
           
        # Set labels and title
        plt.yticks(y_pos, app_names)
        plt.xlabel('Time to terminate (ms)')
        plt.ylabel('Applications/Services')
        plt.title(f'{ecu_type} Shutdown Time (MS)')
       
        # # Set x-axis range and ticks
        # plt.xlim(0, 9000)
        # plt.xticks(range(0, 10000, 1000))

        max_time_diff = max(time_diffs)

        if max_time_diff < 10000:
            interval = 1000
        elif max_time_diff < 100000:
            interval = 10000
        else:
            interval = 100000

        plt.xlim(0, max_time_diff + interval)
        plt.xticks(np.arange(0, max_time_diff + interval * 2, interval))
       
        # Add grid lines for better readability
        plt.grid(axis='x', linestyle='--', alpha=0.7)
       
        # Tight layout to ensure everything fits
        plt.tight_layout()
        plt.subplots_adjust(left=0.25)

        # Get the current time
        timestamp = datetime.now().strftime("%M%S%f")
        # plot_image = f'graph_process_shutdown_{timestamp}.png'
        plot_image = Path(__file__).parent.joinpath(f'graph_process_shutdown_{ecu_type}_{timestamp}.png')
       
        # Save the figure
        plt.savefig(plot_image)

        # Close the plot
        plt.close()

        # Add the plot to the Excel sheet
        img = Image(plot_image)
        sheet.add_image(img, f'H{start_row}')

def get_log_file_path(ecu_type, setup_type, index):
    # Construct the log file name based on the ECU type and timestamp
    basename = f'{current_timestamp}_Shutdown_Time_Logs_{setup_type}_{ecu_type}_N{index + 1}'
    # basename = f'20250602_191926_Shutdown_Time_Logs_{ecu_type}_N{index + 1}'
    logfile = basename+'.log'
    dltfile = basename+'.dlt'
    # logfile = f'{index + 1}_Shutdown_Time_Logs_RCAR_ECU_N20_20250404_173249.log'


    # Define the directory for storing logs
    logs_dir = local_save_path / "Logs"

    # Define the full path to the log file
    filename = logs_dir / logfile

    # Check if the logs directory exists, and create it if it doesn't
    if not logs_dir.exists():
        # Create the logs directory
        logs_dir.mkdir()

    # py_logger.info(f"filename : {filename}")
    # Return the log file path and name
    return filename, logfile, dltfile

def get_log_file_paths_for_elite(index, ecu_config_list, setup_type, py_logger):
   
    parent_dir = local_save_path / "Logs"
    ecu_type_list = [ecu['ecu-type'] for ecu in ecu_config_list]
    logs_dir_list = [parent_dir/ecu_type for ecu_type in ecu_type_list]
    filename_list = {}
   
    for logs_dir, ecu_type in zip(logs_dir_list, ecu_type_list):
        basename = f'{current_timestamp}_Shutdown_Time_Logs_{setup_type}_{ecu_type}_N{index + 1}'
        logfile = basename+'.log'
        dltfile = basename+'.dlt'
        filename_list[ecu_type] = tuple((logs_dir / logfile, logfile, dltfile))
        if(not logs_dir.exists()):
            logs_dir.mkdir(parents=True, exist_ok=True)
            py_logger.info(f"Created log directory: {logs_dir}")
    return filename_list

def write_data_to_excel(welcome_timestamp: datetime, differences: List[ShutdownInfo], sheet):
    # Create a data row for the EXM_2001 termination time
    formatted_time = welcome_timestamp.strftime('%H:%M:%S.%f')[:-3]
    data_row = ['MachineFG state Shutdown', formatted_time, '-', '-']
    # Append the data row to the sheet
    sheet.append(data_row)

    # Iterate over the DLTStart timestamps and differences in parallel using zip
    for app in differences:
        # Format shutdown_time to extract only HH:MM:SS.mmm
        formatted_time = app['shutdown_time'].strftime('%H:%M:%S.%f')[:-3]
        data_row = [app['process'], formatted_time, round(app['difference'], 3),round(app['difference_ms'], 0)]
        sheet.append(data_row)

def create_header(sheet, ecu_type, app_columns):
    # Check if the sheet has existing rows and append empty rows if necessary
    if sheet.max_row > 1:
        # Append 5 empty rows to separate the header from existing data
        for _ in range(10):
            sheet.append([])

    header = ""
    columns = []
    # Determine the header text and column names based on the app_columns parameter
    if app_columns == 'shutdown_time_columns':
        # If avg_flag is False, only include Startup Time in the header
        header = f'Shutdown Time of Services/Applications on {ecu_type}'
        columns = application_shutdown_time_columns
    elif app_columns == 'shutdown_summary_columns':
        # If avg_flag is False, only include Startup Time in the header
        header = f'Services/Applications Shutdown Time from QNX Termination on {ecu_type} (Min, Max, Avg)'
        columns = application_shutdown_summary_columns
    table_headers.append(header)

    # Append the header text to the sheet
    sheet.append([header])

    # Get the current row number (which is now the start of the header)
    start_row = sheet.max_row

    # Calculate the last column letter based on the number of columns
    last_column_letter = chr(64 + len(columns))

    # Merge the cells in the header row
    merged_range = f'A{sheet.max_row}:{last_column_letter}{sheet.max_row}'
    sheet.merge_cells(merged_range)

    # Get the merged cell object
    merged_cell = sheet.cell(row=sheet.max_row, column=1)

    # Apply formatting to the merged cell (gray fill, bold text, centered alignment)
    merged_cell.fill = PatternFill(start_color="9EB9DA", end_color="9EB9DA", fill_type="solid")
    merged_cell.alignment = Alignment(horizontal='center', vertical='center')
    merged_cell.font = Font(bold=True)

    # Append the column names for the header
    sheet.append(columns)    

    for col_idx, col_val in enumerate(columns):
        cell = sheet.cell(row=sheet.max_row, column=col_idx + 1)
        if '\n' in col_val:
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)    
        else:    
            cell.alignment = Alignment(horizontal='center', vertical='center')

    # Apply the border style to the entire merged range
    for row in sheet[merged_range]:
        for cell in row:
            cell.border = border_style

    # Return the row number where the header starts
    return start_row

def export_and_plot_average_data_to_excel(sheet, ecu_type: str, shutdown_summary: Dict[str, ShutdownSummaryInfo], workbook, report_file, py_logger):
    try:
        # Check if the workbook creation was successful
        if sheet is None:
            py_logger.error("Error: Unable to create workbook.")
            return False
       
        # Create a header in the Excel sheet for the average data
        start_row = create_header(sheet, ecu_type, 'shutdown_summary_columns')


        # Initialize an empty list to store the data
        data = [app for app in shutdown_summary.values()]

        # Sort the data based on the average time
        data.sort(key=lambda x: x['avg_time'])

        # Append the sorted data to the Excel sheet
        for data_row in data:
            sheet.append([data_row['process'], round(data_row['min_time'], 0),round(data_row['max_time'], 0), round(data_row['avg_time'], 0)])

        # Plot the average data as a graph
        terminated_apps = [{'process': app['process'], 'difference_ms': app['avg_time']} for app in data]
        plot_shutdown_times(terminated_apps, sheet, start_row, ecu_type)

        # Format the Excel cells
        format_excel_cells(sheet, start_row)

        # Adjust the column width of the Excel sheet
        adjust_column_width(sheet, ecu_type, py_logger)
       
        # Save the Excel workbook
        workbook.save(report_file)
    except Exception as e:
        py_logger.error(f"Error exporting and plotting average data to Excel: {e}")
        return False
   
    return True

def add_logfile_hyperlink(report_path, log_path, sheet, ecu_type, setup_type):
    # Get the next available row in the sheet
    row_no = sheet.max_row + 2
 
    # Set the text for the hyperlink
    sheet.cell(row=row_no, column=1).value = "Log File:"  
 
    # Use Excel's =HYPERLINK() formula with the relative path
    if setup_type == ECUType.ELITE.value:
        hyperlink_formula = f'=HYPERLINK(".\Logs\{ecu_type}\{log_path}", "{log_path}")'
    else:
        hyperlink_formula = f'=HYPERLINK(".\Logs\{log_path}", "{log_path}")'
    # Insert the hyperlink formula
    sheet.cell(row=row_no + 1, column=1).value = hyperlink_formula
   
    # Set the font color of the hyperlink to blue
    sheet.cell(row=row_no + 1, column=1).font = Font(color="0000FF")

def generate_apps_shutdown_report_from_QNX_shutdown(ecu_type, sheet, welcome_timestamp, differences, py_logger):
    # Create the header for the Excel sheet
    start_row = create_header(sheet, ecu_type, 'shutdown_time_columns')

    # Write the data to the Excel sheet
    write_data_to_excel(welcome_timestamp, differences, sheet)

    # Plot the differences as a graph
    # plot_process_startup_time_graph(differences, sheet, start_row, ecu_type, config.get('threshold'), False)
    plot_shutdown_times(differences, sheet, start_row, ecu_type)

    # Format the Excel cells
    format_excel_cells(sheet, start_row)

    # Adjust the column width of the Excel sheet
    adjust_column_width(sheet, ecu_type, py_logger)

# Function to calculate the differences between DLTStart timestamps and the welcome timestamp
def calculate_differences(initial_shutdown_timestamp, application_shutdown_timestamps, py_logger) -> Tuple[datetime, List[ShutdownInfo], ]:
    # Initialize an empty dictionary to store differences
    process_shutdown_timing_info = []
    initial_shutdown_datetime = datetime.strptime(initial_shutdown_timestamp, '%Y/%m/%d %H:%M:%S.%f')
    # Iterate over each DLTStart timestamp
    for app_name, app_timestamp in application_shutdown_timestamps.items():
        try:
            # Parse the DLTStart timestamp and welcome timestamp to datetime objects
            app_datetime = datetime.strptime(app_timestamp, '%Y/%m/%d %H:%M:%S.%f')
            # Calculate the difference between the two timestamps
            difference = abs((app_datetime - initial_shutdown_datetime).total_seconds())
           
            # Store the procesed objects in the list
            process_shutdown_timing_info.append({
            'process': app_name,
            'shutdown_time': app_datetime,
            'difference': difference,
            'difference_ms': difference * 1000
            })
           
        except ValueError:
            # Handle any errors parsing the timestamps
            py_logger.error(f"Error parsing timestamp for process {app_name}: {app_timestamp}")
    return initial_shutdown_datetime, process_shutdown_timing_info

def extract_shutdown_timing_data(lines: List[str], py_logger) -> Tuple[str, OrderedDict[str, str]]:
    # Flag to indicate if we've found the shutdown message
    shutdown_initiated = False
    mfg_timestamp=None

    # Using OrderedDict to maintain insertion order while avoiding duplicates
    terminated_apps = OrderedDict()
   
    for line in lines:
        # Check for shutdown message
        if "MachineFG State :: Shutdown" in line:
            timestamp_match = re.search(r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d+)', line)
            if timestamp_match:
                shutdown_initiated = True
                mfg_timestamp=timestamp_match.group(1)
                continue
           
           
        # Check if this line contains "terminated cause:"
        if shutdown_initiated and ("terminated cause:" in line):
            # Extract timestamp
            timestamp_match = re.search(r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d+)', line)
         
            app_match = re.search(r'Process termination based on request:\s*([^\s]+)\s+terminated cause:', line)
           
            if timestamp_match and app_match:
                app_name = app_match.group(1)
               
                # Remove any .0 or version suffix
                app_name = app_name.rstrip('.0')
               
                app_timestamp = timestamp_match.group(1)
               
                # Store in dictionary (will overwrite if app_name already exists)
                # For duplicates, the last occurrence's timestamp will be kept
                terminated_apps[app_name] = app_timestamp

    py_logger.info(f"  MachineFG shutdown timestamp: {mfg_timestamp}")
    py_logger.info(f"  Applications terminated: {len(terminated_apps)}")
       
    return (mfg_timestamp, terminated_apps)

def RCAR_ON_OFF_Relay(power_on_off_delay, py_logger):
    try:
        # Check stop flag before starting
        if check_stop_flag_periodically(py_logger):
            py_logger.info("Stop flag detected. Aborting RCAR relay operation.")
            return False
            
        py_logger.info("  Turning OFF relay...")
        subprocess.run(["usbrelay", "BITFT_1=0"])
        
        # Check stop flag during delay
        delay_time = float(power_on_off_delay)
        py_logger.info(f"  Waiting {delay_time} seconds...")
        start_time = time.time()
        while time.time() - start_time < delay_time:
            if check_stop_flag_periodically(py_logger):
                py_logger.info("Stop flag detected during relay delay. Aborting operation.")
                return False
            time.sleep(min(0.5, delay_time - (time.time() - start_time)))  # Check every 0.5s or remaining time

        # Check stop flag before turning on
        if check_stop_flag_periodically(py_logger):
            py_logger.info("Stop flag detected. Aborting RCAR relay operation.")
            return False

        py_logger.info("  Turning ON relay...")
        subprocess.run(["usbrelay", "BITFT_1=1"])
        time.sleep(0.2)  #  delay

    except Exception as e:
        py_logger.error(f"[Error] Failed to execute usbrelay commands: {e}")
        return False
    return True    

def power_ON_OFF_Relay(serial_port_relay, baudrate_relay, power_on_off_delay, py_logger):
    try:
        #set up your serial port with the desire COM port and baudrate.
        signal = serial.Serial(serial_port_relay, baudrate_relay, bytesize=8, stopbits=1, timeout=1)
        if not signal.is_open:
            py_logger.error(f"[Error] Failed to open serial port: {serial_port_relay}")
            return False
       
        py_logger.info("  Turning OFF relay...")
        signal.write("AT+CH1=0".encode())   # Relay OFF
        py_logger.info(f"  Waiting {float(power_on_off_delay)} seconds...")
        time.sleep(float(power_on_off_delay))  # Delay for power off
       
        py_logger.info("  Turning ON relay...")
        signal.write("AT+CH1=1".encode())   # Relay ON
        py_logger.info("  Waiting 25 seconds for system boot...")
        time.sleep(25)  # 25s delay
    except Exception as e:
        py_logger.error(f"[Error] Serial port operation failed: {e}")
        return False
    return True
    
def power_ON_OFF_Relay1(serial_port_relay, baudrate_relay, power_on_off_delay, py_logger):
    try:
        # Check stop flag before starting
        if check_stop_flag_periodically(py_logger):
            py_logger.info("Stop flag detected. Aborting power relay operation.")
            return False
            
        #set up your serial port with the desire COM port and baudrate.
        signal = serial.Serial(serial_port_relay, baudrate_relay, bytesize=8, stopbits=1, timeout=1)
        if not signal.is_open:
            py_logger.error(f"[Error] Failed to open serial port: {serial_port_relay}")
            return False
       
        py_logger.info("  Turning OFF relay...")
        signal.write("AT+CH1=0".encode())   # Relay OFF
        
        # Check stop flag during power off delay
        delay_time = float(power_on_off_delay)
        py_logger.info(f"  Waiting {delay_time} seconds...")
        start_time = time.time()
        while time.time() - start_time < delay_time:
            if check_stop_flag_periodically(py_logger):
                py_logger.info("Stop flag detected during power off delay. Aborting operation.")
                signal.close()
                return False
            time.sleep(min(0.5, delay_time - (time.time() - start_time)))  # Check every 0.5s
       
        # Check stop flag before turning on
        if check_stop_flag_periodically(py_logger):
            py_logger.info("Stop flag detected. Aborting power relay operation.")
            signal.close()
            return False
            
        py_logger.info("  Turning ON relay...")
        signal.write("AT+CH1=1".encode())   # Relay ON
        
        # Check stop flag during 25s delay
        py_logger.info("  Waiting 25 seconds for system boot...")
        start_time = time.time()
        while time.time() - start_time < 25:
            if check_stop_flag_periodically(py_logger):
                py_logger.info("Stop flag detected during power on delay. Aborting operation.")
                signal.close()
                return False
            time.sleep(0.5)  # Check every 0.5s
            
        signal.close()
    except Exception as e:
        py_logger.error(f"[Error] Serial port operation failed: {e}")
        return False
    return True

def create_workBook(ecu_type, setup_type, iterations, py_logger):
    try:
        # Create the report file name based on the ECU type and current timestamp
        reportName = f"Application_Shutdown_Time_{setup_type}_{ecu_type}_N{iterations}_{current_timestamp}.xlsx"
       
        # Define the directory where the report will be saved
        report_dir = local_save_path
       
        # Define the full path of the report file
        report_file = report_dir / reportName
       
        # Check if the report directory exists
        if not report_dir.exists():
            # If the directory does not exist, create it
            report_dir.mkdir()
       
    except OSError as e:
        # If an error occurs while creating the directory, py_logger. the error message and return None
        py_logger.error(f"Error creating directory: {e}")
        return None, None, None
   
    except Exception as e:
        # If any other exception occurs, py_logger. the error message and return None
        py_logger.error(f"An unexpected error occurred: {e}")
        return None, None, None

    try:
        # Create a new Excel workbook
        workbook = openpyxl.Workbook()

        # Get the active sheet in the workbook
        summary_sheet = workbook.active

        # Set the title of the sheet
        summary_sheet.title = 'Summary'

        # Create a list to store the sheets
        sheets = []

        # Create each sheet and add it to the list
        for i in range(1, iterations + 1):
            sheet_title = f"GEN3_ShutdownTime_{i:02d}"
            sheet = workbook.create_sheet(title=sheet_title)
            sheets.append(sheet)

        # Remove gridlines from all the sheets in the workbook
        for sheet_exl in sheets:
            # Hide the grid lines in the sheet
            sheet_exl.sheet_view.showGridLines = False

        summary_sheet.sheet_view.showGridLines = False      
       
        # Return the report file path, workbook object, and active sheet object
        return report_file, workbook, sheets, summary_sheet
   
    except Exception as e:
        # If any exception occurs while creating the workbook or sheet, py_logger. the error message and return None
        py_logger.error(f"An error occurred while creating the workbook or sheet: {e}")
        return None, None, None, None

def load_config(file_path, py_logger):
    try:
        config_path = Path(__file__).parent.joinpath(file_path)
        root, ext = os.path.splitext(config_path)
        with open(config_path, 'r') as file:
            if ext == '.json':
                config = json.load(file)
            elif ext in ('.yml', '.yaml'):
                config = yaml.safe_load(file)
            else:
                py_logger.error(f"'{file_path}' is not a valid config file")        
                return None

        return config
    except (FileNotFoundError, PermissionError, yaml.YAMLError, IOError) as e:
        py_logger.error(f"An error occurred while reading the file '{file_path}': {e}")
        return None
   
def create_dlp_files(ecu_config_list, setup_type, py_logger):
    output_dir = 'DLP'
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir_path = os.path.join(script_dir, output_dir)
    dlp_files = {}
    # Create output directory if it doesn't exist or clear it if it does
    if os.path.exists(output_dir_path):
        # Clear all files in the directory
        for file in os.listdir(output_dir_path):
            file_path = os.path.join(output_dir_path, file)
            if os.path.isfile(file_path):
                os.unlink(file_path)
        py_logger.info(f"Cleared existing DLP directory")
    else:
        os.makedirs(output_dir_path)
        py_logger.info(f"Created DLP directory: {output_dir_path}")
    
    # Use the script directory to find the proj.dlp file
    proj_path = os.path.join(script_dir, 'proj.dlp')
    tree = ET.parse(proj_path)
    root = tree.getroot()
    for ecu in ecu_config_list:
        project_name = f"{setup_type}_{ecu['ecu-type']}.dlp"
        # Set hostname text to the IP address
        hostname = root.find('ecu/hostname')
        if hostname is not None:
            hostname.text = ecu['ip-address']
        else:
            py_logger.warning(f"[Warning] 'hostname' not found for ECU {ecu['ecu-type']}")
            continue
        # Set description text to the ECU type
        description = root.find('ecu/description')
        if description is not None:
            description.text = ecu['ecu-type']
        else:
            py_logger.warning(f"[Warning] 'description' not found for ECU {ecu['ecu-type']}")
        # Write updated XML to file
        output_path = os.path.join(output_dir_path, project_name)
        dlp_files[ecu['ecu-type']] = output_path
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
        py_logger.info(f"  Created DLP file: {project_name}")
   
    return dlp_files

def update_shutdown_summary(shutdown_summary: Dict[str, ShutdownSummaryInfo], shutdown_app_timings: List[ShutdownInfo]):
    if shutdown_summary is None or len(shutdown_summary) == 0:
        # If the shutdown summary is empty, initialize it with the first set of data
        for app in shutdown_app_timings:
            shutdown_summary[app['process']] = {
                'process': app['process'],
                'min_time': app['difference_ms'],
                'max_time': app['difference_ms'],
                'values': [app['difference_ms']],
                'avg_time': app['difference_ms']
            }
    else:
        # Update the shutdown summary with the new data
        for app in shutdown_app_timings:
            # Check if the process already exists in the summary
            if app['process'] in shutdown_summary:
                # Update the min, max, and running average
                current_summary = shutdown_summary[app['process']]
                current_summary['min_time'] = min(current_summary['min_time'], app['difference_ms'])
                current_summary['max_time'] = max(current_summary['max_time'], app['difference_ms'])
                current_summary['values'].append(app['difference_ms'])
                # Update the average with new value
                current_summary['avg_time'] = sum(current_summary['values']) /len(current_summary['values'])
            else:
                # Add new process to summary
                shutdown_summary[app['process']] = {
                    'process': app['process'],
                    'min_time': app['difference_ms'],
                    'max_time': app['difference_ms'],
                    'values': [app['difference_ms']],
                    'avg_time': app['difference_ms']
                }
def is_valid_ip(ip_string):
   try:
       ipaddress.ip_address(ip_string)
       return True
   except ValueError:
       return False

def validate_ip_address(ecu_config_list, py_logger):
    py_logger.info("Validating IP addresses for all ECUs...")
    for ecu in ecu_config_list:
        if is_valid_ip(ecu['ip-address']):
            py_logger.info(f"  {ecu['ecu-type']}: {ecu['ip-address']} - Valid")
        else:
            py_logger.error(f"[Error] Invalid IP address for {ecu['ecu-type']}: {ecu['ip-address']}")
            return False
    return True

def capture_logs_from_dlt_viewer(log_file_name, dlt_file_name, project_file_name, config, ecu_type, py_logger):
    py_logger.info(f"Starting DLT log capture for {ecu_type}...")
    py_logger.info(f"  Capture timeout: {config['DLT-Viewer Log Capture Time']} seconds")
    
    # Check stop flag before starting
    if check_stop_flag_periodically(py_logger):
        py_logger.info("Stop flag detected. Aborting DLT log capture.")
        return False
        
    timeout = config['DLT-Viewer Log Capture Time']
    script_dir = Path(__file__).parent.joinpath("dlt-viewer.bat")

    try:
        process = None
        if sys.platform.startswith("win"):
            isPathSet = config['windows']['Is Environment Path Set']
            if isPathSet:
                py_logger.info("  Using DLT-Viewer from system PATH")
                process = subprocess.Popen([script_dir, "dlt-viewer.exe", str(timeout), log_file_name, dlt_file_name, project_file_name])
            else:
                dlt_viewer_path = config['windows']['DLT-Viewer Installed Path']
                log_file_name = os.path.join(log_file_name)
                py_logger.info(f"  Using DLT-Viewer from: {dlt_viewer_path}")
                process = subprocess.Popen([script_dir, dlt_viewer_path, str(timeout), log_file_name, dlt_file_name, project_file_name])
        elif sys.platform.startswith("linux"):
            py_logger.info("  Running on Linux platform")
            process = subprocess.Popen("timeout " + str(timeout) + " dlt-viewer -p "+project_file_name+" -l "+dlt_file_name+" -v", shell=True)
        
        # Register the process for tracking
        if process:
            register_process(process)
            
            # Wait for process to complete, checking stop flag periodically
            while process.poll() is None:
                if check_stop_flag_periodically(py_logger):
                    py_logger.info("Stop flag detected during DLT capture. Terminating process.")
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    return False
                time.sleep(0.5)
            
            # Process completed normally
            if sys.platform.startswith("linux"):
                # Check stop flag before conversion
                if check_stop_flag_periodically(py_logger):
                    py_logger.info("Stop flag detected. Aborting DLT conversion.")
                    return False
                    
                py_logger.info("  Converting DLT to text format...")
                convert_process = subprocess.Popen("dlt-viewer -c  "+str(dlt_file_name)+" "+str(log_file_name), shell=True)
                register_process(convert_process)
                
                # Wait for conversion to complete
                while convert_process.poll() is None:
                    if check_stop_flag_periodically(py_logger):
                        py_logger.info("Stop flag detected during DLT conversion. Terminating process.")
                        convert_process.terminate()
                        try:
                            convert_process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            convert_process.kill()
                        return False
                    time.sleep(0.5)
                py_logger.info("  Conversion completed successfully")

        # Check if log file was created successfully
        size = os.path.getsize(log_file_name)
        if size == 0:
            py_logger.error(f"[Error] Generated log file is empty: {os.path.basename(log_file_name)}")
            py_logger.error(f"  Please verify: IP address, ECU status for {ecu_type}")
            return False
        
        py_logger.info(f"  Log file captured successfully: {os.path.basename(log_file_name)} ({size} bytes)")
            
    except Exception as e:
        py_logger.error(f"Error during DLT log capture: {e}")
        return False
        
    return True

def process_log_file(i, ecu_type, setup_type, log_file_details, dlp_file, config, sheet, shutdown_summary, py_logger):
    try:
        py_logger.info(f"Processing log file for {ecu_type} - Iteration {i+1}")
        
        # Check stop flag before processing
        if check_stop_flag_periodically(py_logger):
            py_logger.info("Stop flag detected. Aborting log file processing.")
            return False
            
        # Get the log file path and name for the specified ECU type and timestamp
        filename, logfile, dltfile = log_file_details
        if not capture_logs_from_dlt_viewer(filename, dltfile, dlp_file, config, ecu_type, py_logger):
            py_logger.error(f"[Error] Failed to capture logs for {ecu_type}")
            return False
            
        # Check stop flag after capture
        if check_stop_flag_periodically(py_logger):
            py_logger.info("Stop flag detected after log capture. Aborting processing.")
            return False
            
        # Attempt to open the log file in read mode with error handling for encoding issues
        py_logger.info(f"  Reading log file: {os.path.basename(filename)}")
        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as file:
                lines = file.readlines()
                time.sleep(2)
            py_logger.info(f"  Log file contains {len(lines)} lines")
        except FileNotFoundError:
            py_logger.error(f"[Error] File not found: {filename}")
            return False
        except UnicodeDecodeError as e:
            py_logger.error(f"[Error] Unicode decode error: {e}")
            return False
           
        # Check stop flag before processing log data
        if check_stop_flag_periodically(py_logger):
            py_logger.info("Stop flag detected before processing log data. Aborting.")
            return False
            
        # Extract the shutdown timing data from the log file
        py_logger.info("  Analyzing shutdown timing data...")
        mfg_timestamp, terminated_apps = extract_shutdown_timing_data(lines, py_logger)
        if mfg_timestamp is None:
            py_logger.error("[Error] Unable to extract shutdown timing data from log")
            return False
   
        if (terminated_apps is None) or (len(terminated_apps) == 0):
            py_logger.error("[Error] No terminated applications found in log")
            return False
   
        mfg_datetime, shutdown_app_timings = calculate_differences(mfg_timestamp, terminated_apps, py_logger)
        py_logger.info(f"  Calculated shutdown timings for {len(shutdown_app_timings)} applications")
   
        # Check if the differences were calculated
        if shutdown_app_timings is None or len(shutdown_app_timings) == 0:
            py_logger.error("[Error] Failed to calculate time differences from shutdown to application termination")
            return False
           
        # Check stop flag before updating summary
        if check_stop_flag_periodically(py_logger):
            py_logger.info("Stop flag detected before updating summary. Aborting.")
            return False
            
        update_shutdown_summary(shutdown_summary, shutdown_app_timings)
        py_logger.info("  Updated shutdown summary statistics")

        # Check stop flag before generating report
        if check_stop_flag_periodically(py_logger):
            py_logger.info("Stop flag detected before generating report. Aborting.")
            return False
            
        py_logger.info("  Generating Excel report...")
        generate_apps_shutdown_report_from_QNX_shutdown(ecu_type, sheet, mfg_datetime, shutdown_app_timings, py_logger)
   
        # Add a hyperlink to the log file in the Excel sheet
        add_logfile_hyperlink(filename, logfile, sheet, ecu_type, setup_type)
        py_logger.info(f"Successfully processed log file for {ecu_type} - Iteration {i+1}")

    except Exception as e:
        py_logger.error(f"[Error] Exception during log processing: {e}")
        return False
    return True      

def start_shutdown_time_measurement(py_logger):
    cur_dt_time_obj = datetime.now()
    global local_save_path
    global current_timestamp
    current_timestamp = cur_dt_time_obj.strftime("%Y%m%d_%H%M%S")
    global table_headers
    table_headers  = list()
   
    # Start stop flag monitoring thread
    stop_monitor_thread = threading.Thread(target=check_stop_flag, args=(py_logger,), daemon=True)
    stop_monitor_thread.start()
    register_thread(stop_monitor_thread)
    py_logger.info("Stop flag monitoring started")
   
    script_start_time = time.perf_counter()
    py_logger.info("="*80)
    py_logger.info("SHUTDOWN TIME MEASUREMENT - EXECUTION STARTED")
    py_logger.info("="*80)
    py_logger.info(f"Execution Start Time: {datetime.fromtimestamp(script_start_time).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
    py_logger.info(f"Timestamp: {current_timestamp}")
    try:
        workbook_map = {}
        fgs_map = {}
        # Initialize a dictionary to store the shutdown summary data
        shutdown_summary_map = {}
        setup_type = None
        enabled_ecu_list = set()      
       
        isSuccess = True
        anySheet = []
        
        # Check stop flag before starting
        if check_stop_flag_periodically(py_logger):
            py_logger.info("Stop flag detected at startup. Aborting measurement.")
            return False

        # Load the configuration
        py_logger.info("\n[Configuration Loading]")
        config_file_path = 'shutdown_time_config.json'
        config = load_config(config_file_path, py_logger)

        # Check if the configuration is empty
        if config is None:
            py_logger.error(f"[Error] Configuration file not found: {config_file_path}")
            return False
        
        py_logger.info("Configuration loaded successfully")
        
        local_save_path = Path(__file__).parents[2].joinpath("Reports", "07_Shutdown_Time", config.get('Current_Timestamp', cur_dt_time_obj.strftime("%Y%m%d_%H-%M-%S")))
        local_save_path.mkdir(parents=True, exist_ok=True)
        py_logger.info(f"Report directory: {local_save_path}")
       
        if config['windows']['DLT-Viewer Installed Path'] and not os.path.isfile(os.path.join(config['windows']['DLT-Viewer Installed Path'])):
            py_logger.error("[Error] Configured DLT-Viewer path is not valid")
            return False

        # Retrieve the number of iterations from the configuration
        try:
            iterations = config["Iterations"]
            py_logger.info(f"Number of iterations: {iterations}")
        except KeyError:
            py_logger.error("[Error] 'Iterations' key not found in configuration file")
            return False
       
        try:
            duration = config["DLT-Viewer Log Capture Time"]
            if not isinstance(duration, int):
                py_logger.error("[Error] 'DLT-Viewer Log Capture Time' must be an integer")
                return False
            py_logger.info(f"DLT-Viewer log capture time: {duration} seconds")
        except KeyError:
            py_logger.error("[Error] 'DLT-Viewer Log Capture Time' key not found in configuration file")
            return False        
               
        if config.get('ECU_setting', {}).get('PADAS', {}).get('RCAR', False):
            enabled_ecu_list.add('RCAR')
            setup_type = 'PADAS'
        else:
            for board_type, enabled in config.get('ECU_setting', {}).get('Elite', {}).items():
                if enabled:
                    enabled_ecu_list.add(board_type)
                    setup_type = 'ELITE'
       
        py_logger.info(f"\n[GUI Settings]")
        py_logger.info(f"Setup Type: {setup_type}")
        py_logger.info(f"Enabled ECUs: {', '.join(enabled_ecu_list)}")
        
        if setup_type is None or len(enabled_ecu_list) == 0:
            py_logger.error("[Error] No enabled ECU found in the configuration")
            return False
           
        def get_ecu_setting(config, prop):
            return config['ECU_setting'].get(prop)

        ecu_config_list = [
            {
                'ecu-type': ecu_name,
                'ip-address': get_ecu_setting(config, f'{ecu_name}_IPAddress'),
                'ftp-user': get_ecu_setting(config, f'{ecu_name}_FTP_Username'),
                'ftp-passwd': get_ecu_setting(config, f'{ecu_name}_FTP_Password'),
                'tn-user': get_ecu_setting(config, f'{ecu_name}_Telnet_Username'),
                'tn-passwd': get_ecu_setting(config, f'{ecu_name}_Telnet_Password')
            }
            for ecu_name in enabled_ecu_list
        ]

        py_logger.info("\n[ECU Initialization]")
        for ecu in ecu_config_list:
            py_logger.info(f"Setting up {ecu['ecu-type']}...")
            py_logger.info(f"  IP Address: {ecu['ip-address']}")
            
            fgs_transfer = FGSTransfer(
                config,
                py_logger,
                ecu['ip-address'],
                ecu['tn-user'],
                ecu['tn-passwd'],
                ecu['ftp-user'],
                ecu['ftp-passwd']
            )
            fgs_map[ecu['ecu-type']] = fgs_transfer
            if not fgs_transfer.remote_fgs_transfer():
                py_logger.error(f"[Error] Failed to transfer FGS for {ecu['ecu-type']}")
                return False
            
            py_logger.info(f"  Creating workbook for {ecu['ecu-type']}...")
            workbook_map[ecu['ecu-type']] = tuple(create_workBook(ecu['ecu-type'], setup_type, iterations, py_logger))

            if workbook_map[ecu['ecu-type']][2] is None:
                py_logger.error(f"[Error] Unable to create workbook for {ecu['ecu-type']}")
                return False

            shutdown_summary_map[ecu['ecu-type']] = {}
            py_logger.info(f"  {ecu['ecu-type']} initialized successfully")

        if not validate_ip_address(ecu_config_list, py_logger):
            return False
        
        py_logger.info("\n[DLP File Creation]")
        dlp_files = create_dlp_files(ecu_config_list, setup_type, py_logger)
        if not dlp_files and len(dlp_files)==0:
            py_logger.error("[Error] Failed to create DLP files")
            return False
        py_logger.info(f"Created {len(dlp_files)} DLP file(s)")

        for i in range(iterations):
            py_logger.info(f"\n{'='*80}")
            py_logger.info(f"ITERATION {i+1} of {iterations}")
            py_logger.info(f"{'='*80}")
            
            # Check stop flag before each iteration
            if check_stop_flag_periodically(py_logger):
                py_logger.info(f"Stop flag detected before iteration {i+1}. Aborting measurement.")
                return False
           
            py_logger.info(f"[Power Cycling]")
            if setup_type == ECUType.RCAR.value:
                if not RCAR_ON_OFF_Relay(config.get('power-on-off-delay-in-seconds', 25), py_logger):
                    py_logger.error("[Error] Power cycling failed for RCAR")
                    return False
            else:
                if not power_ON_OFF_Relay(config.get('serial-port-relay'), config.get('baudrate-relay'), config.get('power-on-off-delay-in-seconds', 25), py_logger):
                    py_logger.error("[Error] Power cycling failed")
                    return False
            py_logger.info("Power cycling completed successfully")

            # Check stop flag after power cycling
            if check_stop_flag_periodically(py_logger):
                py_logger.info(f"Stop flag detected after power cycling in iteration {i+1}. Aborting.")
                return False

            threads = []
           
            for ecu_type, (report_file, workbook, sheets, summary_sheet) in workbook_map.items():
                py_logger.info(f"\n[Processing {ecu_type}]")
                # Check stop flag before processing each ECU
                if check_stop_flag_periodically(py_logger):
                    py_logger.info(f"Stop flag detected before processing ECU {ecu_type}. Aborting.")
                    return False
               
                filename_list = {}
                if setup_type == ECUType.ELITE.value:
                    filename_list = get_log_file_paths_for_elite(i, ecu_config_list, setup_type, py_logger)
                else:
                    filename_list[ecu_type] = tuple(get_log_file_path(ecu_type, setup_type, i))
                if any(not filename for (filename, logfile, dltfile) in filename_list.values()):
                    py_logger.error("[Error] Log file path could not be created")
                    return False
                thread = ResultThread(
                    target=process_log_file,
                    args=(
                        i,
                        ecu_type,
                        setup_type,
                        filename_list[ecu_type],
                        dlp_files[ecu_type],
                        config,
                        sheets[i],
                        shutdown_summary_map[ecu_type],
                        py_logger
                     )
                )

                threads.append(thread)
                register_thread(thread)
                thread.start()
               
            # Wait for all threads to complete, checking stop flag periodically
            py_logger.info(f"Waiting for all {len(threads)} ECU processing thread(s) to complete...")
            for thread in threads:
                while thread.is_alive():
                    if check_stop_flag_periodically(py_logger):
                        py_logger.info("Stop flag detected while waiting for threads. Terminating all processes.")
                        return False
                    thread.join(timeout=0.5)  # Check every 0.5 seconds
                anySheet.append(thread.result)
            py_logger.info(f"Iteration {i+1} completed")
                
        py_logger.info(f"\n[Iterations Summary]")
        py_logger.info(f"All {iterations} iteration(s) completed")
        successful_iterations = sum(1 for result in anySheet if result)
        py_logger.info(f"Successful iterations: {successful_iterations}/{len(anySheet)}")
        if not any(anySheet):
            py_logger.warning("No successful data collected from any iteration")
            isSuccess = False

        # Check stop flag before generating final reports
        if check_stop_flag_periodically(py_logger):
            py_logger.info("Stop flag detected before generating final reports. Aborting.")
            return False

        # Save workbooks and generate reports for each ECU type
        py_logger.info(f"\n[Report Generation]")
        for ecu_type, (report_file, workbook, sheets, summary_sheet) in workbook_map.items():
            # Check stop flag before each ECU report generation
            if check_stop_flag_periodically(py_logger):
                py_logger.info(f"Stop flag detected before generating report for {ecu_type}. Aborting.")
                return False
           
            py_logger.info(f"Generating report for {ecu_type}...")
            # Export the average data to the Excel sheet
            if not export_and_plot_average_data_to_excel(summary_sheet, ecu_type, shutdown_summary_map[ecu_type], workbook, report_file, py_logger):
                py_logger.error(f"[Error] Failed to generate report for {ecu_type}")
                isSuccess = False
            else:
                py_logger.info(f"Report created successfully: {report_file.name}")

    except KeyError as e:
        py_logger.error(f"[Error] Missing expected key in ECU input fields: {e}")
        isSuccess = False
    except Exception as e:
        py_logger.error(f"[Error] An unexpected error occurred: {e}")
        isSuccess = False
    finally:
        try:
            py_logger.info("\n[Cleanup Operations]")
            
            # Check if stop was requested for logging purposes
            if stop_requested.is_set():
                py_logger.warning("Measurement stopped due to stop flag detection")
                
            remove_png_files(py_logger)
           
            # Final power cycling
            py_logger.info("Performing final power cycle...")
            if setup_type == ECUType.RCAR.value:
                RCAR_ON_OFF_Relay(config.get('power-on-off-delay-in-seconds', 25), py_logger)
            else:
                power_ON_OFF_Relay(config.get('serial-port-relay'), config.get('baudrate-relay'), config.get('power-on-off-delay-in-seconds', 25), py_logger)

            # FGS cleanup
            py_logger.info("Cleaning up FGS transfers...")
            for ecu_type, fgs_transfer in fgs_map.items():
                if fgs_transfer:
                    py_logger.info(f"  Cleaning up {ecu_type} FGS")
                    fgs_transfer.remote_fgs_cleanup()

            # Final cleanup of any remaining processes
            terminate_all_processes(py_logger)
            
            script_end_time = time.perf_counter()
            execution_time = script_end_time - script_start_time
            
            py_logger.info("\n" + "="*80)
            py_logger.info("SHUTDOWN TIME MEASUREMENT - EXECUTION COMPLETED")
            py_logger.info("="*80)
            py_logger.info(f"Execution End Time: {datetime.fromtimestamp(script_end_time).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
            py_logger.info(f"Total Execution Time: {execution_time:.2f} seconds ({execution_time/60:.2f} minutes)")
            py_logger.info(f"Final Status: {'SUCCESS' if isSuccess else 'FAILURE'}")
            py_logger.info("="*80)
            
            stop_requested.clear()
        except Exception as e:
            py_logger.error(f"[Error] Exception during cleanup: {e}")
    
    return isSuccess