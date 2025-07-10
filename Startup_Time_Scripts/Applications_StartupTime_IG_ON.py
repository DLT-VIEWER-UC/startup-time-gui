# Import necessary libraries
import re
import os
import sys
import json
import glob
import time
import yaml
import serial
import openpyxl
import xml.etree.ElementTree as ET
import subprocess
import matplotlib
import matplotlib.pyplot as plt
import ipaddress
matplotlib.use('Agg')
import numpy as np
from multiprocessing import Process
from openpyxl.drawing.image import Image
from openpyxl.styles import PatternFill, Border, Side, Alignment, Font
from openpyxl.utils import get_column_letter
from pathlib import Path
from datetime import datetime
import logging
from typing import Final
from enum import Enum, auto
import threading
from collections import OrderedDict
import colorlog
import pandas as pd


plot_lock = threading.Lock()

logger = None
cur_dt_time_obj = None
local_save_path = None
workbook_map = None
current_timestamp = None

def setup_logging():
    # Set up colored logging configuration
    LOG_FORMAT = (
        '%(log_color)s%(asctime)s - %(levelname)s - %(funcName)s - %(lineno)d - %(message)s%(reset)s'
    )
    logging.root.setLevel(logging.INFO)  # Set the root logger level to INFO

    # Configure the colorlog formatter
    formatter = colorlog.ColoredFormatter(LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")

    # Create a StreamHandler for console output
    stream = logging.StreamHandler()
    stream.setFormatter(formatter)

    # Add the handlers to the root logger
    logging.root.addHandler(stream)    

    # Return the configured logger
    return logging.getLogger(__name__)


# Define the column names for the application startup time data
application_startup_time_columns = ['No.', 'Services/Applications', 'Application Startup\n Time (sec)',

                                    'IG ON\n to\n QNX Startup (sec)', 'Total Time\n from\n IG ON (sec)',
                                    'Test Case Status','Expected Order', 'StartUp Order Status', 'Reason for FAIL']

# Define the column names for the application startup time data with minimum, maximum, and average values
application_startup_time_min_max_avg_columns = ['Services/Applications', 'Minimum (sec)', 'Maximum (sec)',
                                                'Average (sec)', 'Average\n from\n IG ON (sec)' ]

application_info_columns = ['Services/Applications', 'Init(Up) Time (us)', 'Init(Up) Time (ms)']

application_start_end_time_min_max_avg_columns = ['Services/Applications', 'Minimum (ms)', 'Maximum (ms)',
                                                  'Average (ms)']

applications_overall_status_columns = ['No. of Iterations', 'Total Time\n to Startup\n Last Application\n from IG ON (sec)',
                                        'Test Case Status', 'Startup Order Status']
appendix_columns = ['Column Name', 'Description']
startup_field_descriptions = [
   ("Services/Applications", "Name of the Service/Application being initialized."),
   ("Start Time", "The timestamp (from DLT logs) indicating when the application startup begins.",),
   ("Apps Startup", "Time taken (in seconds) by the application to initialize after the welcome timestamp. \n Apps Startup = Start time of each Application - KSAR start time.)"),
   ("Init(Up) Time", "Time taken for the application to fully start after initialization and that is captured from the DLT logs.",),
   ("IG ON to QNX + KSAR Startup", "This is the offfset time from IG ON to QNX startup and from QNX startup to KSAR start time. \n Offset time = IG ON to QNX startup + QNX startup to KSAR startup."),
   ("Total Time", "This is the Total time taken from IG ON to Application Startup completion. \n Total time = Apps Startup +  InitUp Time/1000000 + offset time (IG ON to QNX + KSAR Startup.")
]

# Define a border style for cells in the Excel sheet
border_style = Border(left=Side(border_style='thin'), right=Side(border_style='thin'),
                        top=Side(border_style='thin'), bottom=Side(border_style='thin'))

OFFSET_TIME: Final = 1.5

class ECUType(Enum):
    RCAR = "RCAR"
    PADAS = "PADAS"
    ELITE = "ELITE"
    SoC0 = "SoC0"
    SoC1 = "SoC1"

class OrderType(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"

class OrderFailureType(Enum):
   ORDER_MISMATCH   = 1
   APPLICATION_NOT_CONFIGURED = 2
   APPLICATION_NOT_FOUND  = 3

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

def is_valid_ip(ip_str):
    try:
        ipaddress.ip_address(ip_str)
        return True
    except ValueError:
        return False

def validate_ip_address(ecu_config_list):
    for ecu in ecu_config_list:
        if is_valid_ip(ecu['ip-address']):
            continue
        else:
            logger.info(f"Entered IP address for {ecu['ecu-type']} is not valid.")
            return False
    return True

def remove_png_files():
    script_dir = Path(__file__).parent
    png_files = list(script_dir.glob('*.png'))
    for file in png_files:
        try:
            # logger.info(f"Deleting {file.name}")
            file.unlink()
        except Exception as e:
            pass
            logger.info(f"Error deleting file {file}: {e}")

def adjust_column_width(sheet, ecu_type):
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
                if f'Startup_Time_Logs_{ecu_type}' in str(cell.value):
                    continue

                # Check if the cell is part of a merged cell
                is_merged = False
                for merged_cell in sheet.merged_cells.ranges:
                    if cell.coordinate in merged_cell:
                        is_merged = True
                        break

                # If the cell is part of a merged cell, skip it
                if is_merged:
                    continue

                # Check if the cell's alignment has wrap text enabled
                if cell.alignment.wrap_text:
                    continue

                # Attempt to retrieve the content of the cell and check its length
                cell_content = str(cell.value)

                # Update max_length if the current cell content is longer
                if len(cell_content) > max_length:
                    max_length = len(cell_content)

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
            if cell.value in (application_startup_time_columns + application_startup_time_min_max_avg_columns
                              + application_info_columns + application_start_end_time_min_max_avg_columns +
                              applications_overall_status_columns):
               
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


def plot_process_individual_apps_avg_graph(differences, sheet, start_row, ecu_type):
    with plot_lock:
        # Determine the height of the graph based on the size of the sheet
        height = (sheet.max_row - start_row + 1) * 0.35 # adjust the multiplier as needed
        width = 10

        # logger.info(f"Sheet size: {sheet.max_row - start_row + 1}, height : {height}")

        if height > 6.5:
            height = 6.5
            width = 12

        # Create a new figure with a specified size
        plt.figure(figsize=(12, max(3, len(differences)*0.2)))

        # Iterate over each process and its difference
        for index, (process, difference) in enumerate(differences.items(), start=1):
            plt.plot([0, difference], [index, index], marker='o')

            # Add a text label at the midpoint of the line with the difference value
            plt.text((0 + difference) / 2, index + 0.1, str(round(difference, 3))+" ms",#"{:.3f} ms".format(difference),
                    verticalalignment='bottom', horizontalalignment='center')

        # Set the y-axis tick labels to the process names and 'Time from IG ON to QNX startup'
        plt.yticks(range(1, len(differences) + 1), list(differences.keys()))

        # Set the x-axis label
        plt.xlabel('Time Interval (milliseconds)')

        # Set the y-axis label

        plt.ylabel('Services or Applications')

        # Set the title of the plot
        plt.title(f'{ecu_type} Timeline Graph: Individual Services/Applications Startup Time Average', pad=20)

        # Enable the grid on both x and y axes with light lines
        plt.grid(True, axis='both', linestyle='--', linewidth=0.5, color='gray')

        # Ensure the plot fits within the figure
        plt.tight_layout()

        # Determine the x-axis limits with some padding
        min_x = 0
        max_x = max(differences.values())
        # padding = (max_x - min_x) * 0.05
        padding = 3
   
        # Create a sequence of milliseconds for the x-axis
        x_ticks = np.arange(0, max_x + 200, 200)  # show ticks every 100ms

        plt.xticks(x_ticks)
        plt.xlim(min_x - padding, max_x + padding)

        # Get the current time
        timestamp = datetime.now().strftime("%M%S%f")
        plot_image = Path(__file__).parent.joinpath(f'graph_process_startup_{ecu_type}_{timestamp}.png')

        # Save the plot to a file
        plt.savefig(plot_image)

        # Close the plot
        plt.close()

        # Add the plot to the Excel sheet
        img = Image(plot_image)
        sheet.add_image(img, f'J{start_row}')


def plot_process_start_end_time_graph(ecu_type, data, sheet, start_row):
    with plot_lock:
        # Determine the height of the graph based on the size of the sheet
        height = (sheet.max_row - start_row + 1) * 0.35 # adjust the multiplier as needed
        width = 10

        # logger.info(f"Sheet size: {sheet.max_row - start_row + 1}, height : {height}")

        if height > 6.5:
            height = 6.5
            width = 12

        # Create a new figure with a specified size
        plt.figure(figsize=(12, max(3, len(data)*0.2)))

        df = pd.DataFrame(data)  
        df['start_time_ms'] = pd.to_numeric(df['start_time_ms'])
        print ("df", df)
 
        for index, row in df.iterrows():
            print ("row",row['start_time_ms'])
            plt.plot([0, row['start_time_ms']], [index, index], marker='o')
            plt.text(row['start_time_ms'] / 2, index + 0.1,
                    str(round(row['start_time_ms'], 3))+" ms", #"{:.3f} ms".format(row['start_time_ms']),
                    verticalalignment='bottom',
                    horizontalalignment='center')    

        plt.yticks(range(len(df)), df["process"])
        plt.xlabel('Time Interval (microseconds)')
        plt.ylabel('Services or Applications')
        plt.title(f'{ecu_type} Timeline Graph:Services/Applications Init(Up) Time', pad=20)
        plt.grid(True)
        plt.tight_layout()
   
        max_x = df['start_time_ms'].max()
        plt.xlim(-10, max_x)    

        # Get the current time
        timestamp = datetime.now().strftime("%M%S%f")

        # Save the plot as an image file
        plot_image = Path(__file__).parent.joinpath(f'process_start_end_graph_{ecu_type}_{timestamp}.png')
        plt.savefig(plot_image)
        plt.close()

        # Add the plot image to the worksheet
        img = Image(plot_image)
        sheet.add_image(img, f'J{start_row}')


def plot_process_startup_time_graph(differences, sheet, start_row, ecu_type, threshold, avg_flag):
    with plot_lock:
        # Determine the height of the graph based on the size of the sheet
        height = (sheet.max_row - start_row + 1) * 0.35 # adjust the multiplier as needed
        width = 10

        if height > 6.5:
            height = 6.5
            width = 12

        # Create a new figure with a specified size
        plt.figure(figsize=(12, max(3, len(differences)*0.2)))  

        plt.plot([0, OFFSET_TIME], [0, 0],  marker='o')
        plt.text((OFFSET_TIME) / 2, 0.1, f"{OFFSET_TIME} sec", verticalalignment='bottom', horizontalalignment='center')

        # Iterate over each process and its difference
        for index, (process, difference) in enumerate(differences.items()):
            index = index + 1
            # Plot a line from (OFFSET_TIME, index) to (difference + OFFSET_TIME, index) with a marker at the end
            plt.plot([OFFSET_TIME, difference + OFFSET_TIME], [index, index], marker='o')

            # Add a text label at the midpoint of the line with the difference value
            plt.text((OFFSET_TIME + difference + OFFSET_TIME) / 2, index + 0.1,
                    str(round(difference, 3))+" sec", #"{:.3f} sec".format(difference),
                    verticalalignment='bottom', horizontalalignment='center')

        # Set the y-axis tick labels to the process names and 'Time from IG ON to QNX startup'
        plt.yticks(range(len(differences) + 1), ['Time from IG ON to QNX startup'] + list(differences.keys()))

        # Set the x-axis label
        plt.xlabel('Time Interval (seconds)')

        # Set the y-axis label
        plt.ylabel('Services or Applications')

        # Set the title of the graph
        if avg_flag:
            plt.title(f'{ecu_type} Timeline Graph: Services/Applications Startup Time Average', pad=20)
        else:
            plt.title(f'{ecu_type} Timeline Graph: Services/Applications Startup Completion Time', pad=20)

        # Enable the grid on both x and y axes with light lines
        plt.grid(True, axis='both', linestyle='--', linewidth=0.5, color='gray')

        # Ensure the plot fits within the figure
        plt.tight_layout()

        # Determine the x-axis limits with some padding
        min_x = 0
        max_x = max(differences.values()) + OFFSET_TIME  # add OFFSET_TIME to max_x
        padding = (max_x - min_x) * 0.015

        # Create a sequence of seconds for the x-axis
        x_ticks = np.arange(0, max_x + 1, 1)  

        plt.xticks(x_ticks)

        plt.xlim(min_x - padding, max_x + padding)
        # plt.xlim(0, max_x + padding)

        # Add QNX Startup Time label exactly below OFFSET_TIME sec on x-axis
        plt.text(OFFSET_TIME, -3.0, "QNX Startup", verticalalignment='top', horizontalalignment='center')
   
        # Add a vertical line at x=threshold seconds
        plt.axvline(x=threshold, color='red', linestyle='--', linewidth=2, label=f'{threshold} seconds')

        # Add a vertical black line at x=OFFSET_TIME seconds
        plt.axvline(x=OFFSET_TIME, color='black', linestyle='--', linewidth=1)  

        # Get the current time
        timestamp = datetime.now().strftime("%M%S%f")
        plot_image = Path(__file__).parent.joinpath(f'graph_process_startup_{ecu_type}_{timestamp}.png')

        # # Save the plot to a file
        # plot_image = f'bar_chart_process_start_time_{start_row}.png'
        plt.savefig(plot_image)

        # Close the plot
        plt.close()

        # Add the plot to the Excel sheet
        img = Image(plot_image)
        sheet.add_image(img, f'M{start_row}')

def get_log_file_path(ecu_type, setup_type, iterations, current_timestamp, index):
    # Construct the log file name based on the ECU type and timestamp
    basename = f'{current_timestamp}_Startup_Time_Logs_{setup_type}_{ecu_type}_N{index + 1}'
    # basename = f'20250626_125003_Startup_Time_Logs_{setup_type}_{ecu_type}_N{index + 1}'
    logfile = basename+'.log'
    dltfile = basename+'.dlt'

    # Define the directory for storing logs
    logs_dir = local_save_path / "Logs"

    # Define the full path to the log file
    filename = logs_dir / logfile

    # Check if the logs directory exists, and create it if it doesn't
    if not logs_dir.exists():
        # Create the logs directory
        logs_dir.mkdir()

    # Return the log file path and name
    return filename, logfile, dltfile

def get_log_file_paths_for_elite(index, current_timestamp, ecu_config_list, setup_type):    
    parent_dir = local_save_path / "Logs"
    ecu_type_list = [ecu['ecu-type'] for ecu in ecu_config_list]
    logs_dir_list = [parent_dir/ecu_type for ecu_type in ecu_type_list]
    filename_list = {}
   
    for logs_dir, ecu_type in zip(logs_dir_list, ecu_type_list):
        basename = f'{current_timestamp}_Startup_Time_Logs_{setup_type}_{ecu_type}_N{index + 1}'
        # basename = f'20250626_125003_Startup_Time_Logs_{setup_type}_{ecu_type}_N{index + 1}'
        logfile = basename+'.log'
        dltfile = basename+'.dlt'
        filename_list[ecu_type] = tuple((logs_dir / logfile, logfile, dltfile))
        if(not logs_dir.exists()):
            logs_dir.mkdir(parents=True, exist_ok=True)
    print(f"Log files will be saved in the following directories: {filename_list}")
    return filename_list


def get_expected_startup_order(application_name, application_startup_order):
    # Iterate over the application startup order to find the expected startup order for the given application name
    cur_pos = 0
    for order_type, order in application_startup_order:
        if application_name in order:
            print('order type', order_type, (order_type.lower()), (OrderType.SEQUENTIAL.value))
            if order_type.lower() == OrderType.SEQUENTIAL.value:
                return str(cur_pos + order.index(application_name) + 1)
            else:
                if len(order) == 1:
                    return str(cur_pos + 1)
                return str(cur_pos + 1) + '~' + str(cur_pos + len(order))
        cur_pos += len(order)
    return None
 


def write_data_to_excel(dltstart_timestamps, process_timing_info, sheet, application_startup_order, threshold, validate_startup_order):
    start_row = sheet.max_row + 1

    # Iterate over the DLTStart timestamps and differences in parallel using zip
    for position, (process, dltstart_line) in enumerate(dltstart_timestamps.items()):
        # Check if the process names match
       
        if float(dltstart_line + OFFSET_TIME) < threshold:
            result = 'PASS'
        else:
            result = 'FAIL'
        print(">>>", process, process, process_timing_info)
       
        # Create a data row for the process
        expected_order = get_expected_startup_order(process, application_startup_order)
        if not expected_order:
            expected_order='-'

        data_row = [position+1, process, round(dltstart_line, 3), OFFSET_TIME, round(dltstart_line + OFFSET_TIME, 3),result, str(expected_order)]
        print('##',process,validate_startup_order)

        if validate_startup_order:
            order_failure_type = validate_ind_app_startup_order(process, position + 1, application_startup_order)
            data_row.append('PASS' if order_failure_type==0 else 'FAIL')
            if order_failure_type != 0:
                # If the startup order is not valid, set the test case status to 'FAIL'
                data_row.append(OrderFailureType(order_failure_type).name)
            else:
                data_row.append("")

        # Append the data row to the sheet
        sheet.append(data_row)
       
    # Merge cells in column D for the rows created in this scenario
    merged_range = f'D{start_row}:D{sheet.max_row}'
    sheet.merge_cells(merged_range)
   
    for order_type, order in application_startup_order:
        for app in order:
            if app not in dltstart_timestamps:
                expected_order = get_expected_startup_order(app, application_startup_order)
                if not expected_order:
                    expected_order='-'
               
                data_row = ['-', app, '-', '-', '-', '-', str(expected_order)]
               
                if validate_startup_order:
                    data_row.extend(['FAIL', OrderFailureType.APPLICATION_NOT_FOUND.name])
                sheet.append(data_row)
   
    # Apply the border style to the entire merged range
    for row in sheet[merged_range]:
        for cell in row:
            cell.border = border_style


def create_header(sheet, ecu_type, validate_startup_order, app_columns):
    # Check if the sheet has existing rows and append empty rows if necessary
    if sheet.max_row > 1:
        # Append 5 empty rows to separate the header from existing data
        for _ in range(10):
            sheet.append([])

    # Determine the header text and column names based on the avg_flag
    if app_columns == 'min_max_avg_columns':
        # If avg_flag is True, include Min, Max, and Avg in the header
        header = f'Services/Applications Startup Time from QNX Startup on {ecu_type} (Min, Max, Avg)'
        columns = application_startup_time_min_max_avg_columns
   
    elif app_columns == 'min_max_avg_individual':
        # If avg_flag is True, include Min, Max, and Avg in the header
        header = f'Services/Applications Individual Startup Times on {ecu_type} (Min, Max, Avg)'
        columns = application_start_end_time_min_max_avg_columns

    elif app_columns == 'startup_time_columns':
        # If avg_flag is False, only include Startup Time in the header
        header = f'Services/Applications Startup Time on {ecu_type}'
        columns = application_startup_time_columns
        if not validate_startup_order:
            columns=columns[:-2]
   
    elif app_columns == 'info_columns':
        header = f'Services/Applications Init(Up) Time on {ecu_type}'
        columns = application_info_columns
   
    elif app_columns == 'overall_test_columns':
        header = f'Overall Test Case Status for each Iteration on {ecu_type}'
        columns = applications_overall_status_columns
        if not validate_startup_order:
            columns=columns[:-1]

    elif app_columns == 'startup_appendix':
       header = f'Field Description for \n Services/Applications Startup Completion Time on {ecu_type}'
       columns = appendix_columns
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


def each_iteration_test_status(ecu_type, summary_sheet, overall_IG_ON_iteration, config, application_startup_order_status):
    start_row = create_header(summary_sheet, ecu_type, config['validate-startup-order'], 'overall_test_columns')
   
    for i, (overall_value, order_status) in enumerate(zip(overall_IG_ON_iteration, application_startup_order_status)):
        overall_value = overall_value + OFFSET_TIME

        if overall_value > 5:
            test_status = 'FAIL'
        else:
            test_status = 'PASS'        
        data_row=[i+1, overall_value, test_status]
        if config['validate-startup-order']:
            data_row.append("PASS" if order_status else "FAIL")
        summary_sheet.append(data_row)
   
    format_excel_cells(summary_sheet, start_row)

def export_and_plot_average_data_to_excel(sheet, ecu_type, process_times, process_start_times, config):
    # Create a header in the Excel sheet for the average data
    start_row = create_header(sheet, ecu_type, config['validate-startup-order'], 'min_max_avg_columns')

    # Initialize an empty dictionary to store the average differences
    differences = {}
    individual_differences= {}    

    # Initialize an empty list to store the data
    data = []
    individual_list = []

    # Iterate over each process and its times
    for process, times in process_times.items():
        # Calculate the minimum, maximum, and average times for the process
        min_time = min(times)
        max_time = max(times)
        # avg_time = sum(times) / len(times)
        avg_time = round(sum(times) / len(times), 3)
       
        # Create a dictionary for the process with the minimum, maximum, and average times
        data_row = {
            'process': process,
            'min_time': round(min_time, 3),
            'max_time': round(max_time, 3),
            'avg_time': round(avg_time, 3),
        }
       
        # Append the data row to the list
        data.append(data_row)

    # Sort the data based on the average time
    data.sort(key=lambda x: x['avg_time'])

    # Append the sorted data to the Excel sheet
    for data_row in data:
        sheet.append([data_row['process'], data_row['min_time'], data_row['max_time'], data_row['avg_time'], float(data_row['avg_time']) + OFFSET_TIME])

        # Store the average difference in the differences dictionary
        differences[data_row['process']] = float(data_row['avg_time'])

    # Plot the average data as a graph
    plot_process_startup_time_graph(differences, sheet, start_row, ecu_type, config['threshold-in-seconds'], True)

    # Format the Excel cells
    format_excel_cells(sheet, start_row)

    # Create a header in the Excel sheet for the average data
    start_row = create_header(sheet, ecu_type, config['validate-startup-order'], 'min_max_avg_individual')

    for process, start_times in process_start_times.items():
        # Calculate the minimum, maximum, and average start times for the process
        min_time = min(start_times)
        max_time = max(start_times)
        avg_time = sum(start_times) / len(start_times)
        # avg_time = round(sum(start_times) / len(start_times), 3)    

        # Create a dictionary for the process with the minimum, maximum, and average times
        data_row = {
            'process': process,
            'min_time': round(min_time, 3),
            'max_time': round(max_time, 3),
            'avg_time': round(avg_time, 3),
        }
       
        # Append the data row to the list
        individual_list.append(data_row)

    # Sort the data based on the average time
    individual_list.sort(key=lambda x: x['avg_time'])    
       
      # Append the sorted data to the Excel sheet
    for data_row in individual_list:
        sheet.append([data_row['process'], data_row['min_time'], data_row['max_time'], data_row['avg_time']])

        # Store the average difference in the differences dictionary
        individual_differences[data_row['process']] = float(data_row['avg_time'])
   
    # Plot the average data as a graph
    plot_process_individual_apps_avg_graph(individual_differences, sheet, start_row, ecu_type)

    # Format the Excel cells
    format_excel_cells(sheet, start_row)
   
    # Adjust the column width of the Excel sheet
    adjust_column_width(sheet, ecu_type)


def add_logfile_hyperlink(report_path, log_path, sheet):
    # Get the next available row in the sheet
    row_no = sheet.max_row + 2
 
    # Set the text for the hyperlink
    sheet.cell(row=row_no, column=1).value = "Log File:"  
 
    # Use Excel's =HYPERLINK() formula with the relative path
    hyperlink_formula = f'=HYPERLINK("{report_path}", "{log_path}")'
 
    # Insert the hyperlink formula
    sheet.cell(row=row_no + 1, column=1).value = hyperlink_formula
   
    # Set the font color of the hyperlink to blue
    sheet.cell(row=row_no + 1, column=1).font = Font(color="0000FF")


def generate_apps_start_end_time_report(ecu_type, sheet, process_timing_info, config):
    # Create the header for the Excel sheet
    start_row = create_header(sheet, ecu_type, config['validate-startup-order'], 'info_columns')

    for item in process_timing_info:
        if item['start_time_ms']:
            data_row = [item['process'], float(item['start_time_ms'])*1000,float(item['start_time_ms'])]
            sheet.append(data_row)

    # Plot the startup graph
    plot_process_start_end_time_graph(ecu_type, process_timing_info, sheet, start_row)

    # Format the Excel cells
    format_excel_cells(sheet, start_row)


def generate_apps_startup_report_from_QNX_startup(ecu_type, config, sheet, dltstart_timestamps,  process_timing_info, application_startup_order):
    # Create the header for the Excel sheet
    start_row = create_header(sheet, ecu_type, config['validate-startup-order'], 'startup_time_columns')

    # Write the data to the Excel sheet
    write_data_to_excel(dltstart_timestamps, process_timing_info, sheet, application_startup_order, config.get('threshold-in-seconds'), config.get('validate-startup-order') )

    # Plot the differences as a graph
    plot_process_startup_time_graph(dltstart_timestamps, sheet, start_row, ecu_type, config.get('threshold-in-seconds'), False)

    # Format the Excel cells
    format_excel_cells(sheet, start_row)

    generate_apps_start_end_time_report(ecu_type, sheet, process_timing_info, config)

    # Adjust the column width of the Excel sheet
    adjust_column_width(sheet, ecu_type)


def extract_and_sort_process_timestamps(process_Start_End_timestamps, ecu_type):
    process_timing_info = []
    for process, time in process_Start_End_timestamps.items():  
        # Check if both start and end times are available
        # if 'start' in time and 'end' in time:            
        start_time_ms = float(time['init_time'] if 'init_time' in time else '0')
        # logger.info(f"Process: {process}, Start Time: {time['start']}, End Time: {time['end']}, Time Difference: {start_time_ms} ms")

        process_timing_info.append({
        'process': process,
        'start_time_ms': start_time_ms
    })

        # Check if only end time is available
        if 'init_time' not in time:
            logger.warning(f"Process: {process}, Init: Not Available")
     
    process_timing_info.sort(key=lambda x: x['start_time_ms'] if x.get('start_time_ms')is not None else float('inf'))
    return process_timing_info


# Function to calculate the differences between DLTStart timestamps and the welcome timestamp
def calculate_differences(dltstart_timestamps, welcome_timestamp):
    # Initialize an empty dictionary to store differences
    differences = {}
    # Iterate over each DLTStart timestamp
    for process, dltstart_line in dltstart_timestamps.items():
        try:
            # Parse the DLTStart timestamp and welcome timestamp to datetime objects
            dltstart_datetime = datetime.strptime(dltstart_line, '%Y-%m-%d %H:%M:%S.%f')
            welcome_datetime = datetime.strptime(welcome_timestamp, '%Y-%m-%d %H:%M:%S.%f')
            # Calculate the difference between the two timestamps
            difference = (dltstart_datetime - welcome_datetime).total_seconds()
            # Store the difference in the dictionary
            differences[process] = difference

            # logger.info(f"welcome_datetime : {welcome_datetime} appstart_datetime : {dltstart_datetime} difference : {difference}")
        except ValueError:
            # Handle any errors parsing the timestamps
            logger.error(f"Error parsing timestamp for process {process}: {dltstart_line}")
    return differences


def extract_process_timestamps(lines):
    # Initialize an empty dictionary to store the process start and end timestamps
    process_Start_End_timestamps = {}

    # Iterate over each line in the log file
    for line in lines:
        if 'Application:' in line and 'Init(Up) Time:' in line:
           # Split the line to extract the process name and timestamp
           parts = line.split('Application:')
           # Check if the split resulted in more than one part (i.e., the keyword was found)
           if len(parts) > 1:
               # Extract the process information from the second part
               process_info = parts[1]
               # Extract the process name from the process information by splitting at ', Pid:'
               # Remove any trailing '.0' suffix from the process name
               process_name = process_info.split('- Init(Up) Time:')[0].strip()
               # Split the line to extract the end timestamp
               init_timestamp_parts = line.split('Init(Up) Time: ')
               # Check if a timestamp was found
               if len(init_timestamp_parts) > 1:
                   # Extract the timestamp from the second part and convert it to an integer
                   init_timestamp = float(init_timestamp_parts[1].split(' us')[0].strip())/1000
                   # Check if the process name is already in the dictionary
                   if process_name not in process_Start_End_timestamps:
                       # Initialize the process dictionary if it does not exist
                       process_Start_End_timestamps[process_name] = {}
                   # Store the end timestamp in the process dictionary
                   process_Start_End_timestamps[process_name]['init_time'] = init_timestamp
                   # Log the process name and end timestamp
                   # logger.info(f"Process name: {process_name}, End Timestamp: {end_timestamp}")

    return process_Start_End_timestamps


# Function to extract DLTStart timestamps for specified applications
def extract_dltstart_timestamps(lines):
    # Dictionary to store process names as keys and their start timestamps as values
    app_start_timestamps = OrderedDict()  

    # Iterate over each line in the log file
    for line in lines:
        # Check if the line contains the required keywords to indicate a process start event
        #if ':EM: Process' in line and 'Pid:' in line and 'is started' in line:
        if 'EM' in line and 'is started' in line:
            # Split the line into parts based on the ':EM: Process' keyword
            pattern = r'EM.*?\b([^\s]+?)(?=\.0)\.0\b'
            m = re.search(pattern, line)
            #parts = line.split(':EM: Process')
           
            # Check if the split resulted in more than one part (i.e., the keyword was found)
            #if len(parts) > 1:
            if m:
                process_name = m.group(1)                              
                # Use a regular expression to extract the timestamp from the line
                timestamp_match = extract_timestamp_from_dlt(line)
                # Check if a timestamp was found
                if timestamp_match!=None:
                    app_start_timestamps[process_name] = timestamp_match
                else:
                    # Log a warning if no timestamp was found for the process
                    logger.warning(f"No timestamp found for process {process_name}")

    # Return the dictionary of process start timestamps
    return app_start_timestamps

def validate_ind_app_startup_order(application, position, application_startup_order):
   for order_type, order in application_startup_order:
       if len(order) >= position:
           if order_type.lower() == OrderType.SEQUENTIAL.value:
               if order[position - 1] == application:
                   return 0
               else:
                   break
           else:
                if application in order:
                    return 0
                else:
                    break                
       else:
           position -= len(order)
   for order_type, order in application_startup_order:
       if application in order:
           return 1
   return 2


def validate_app_startup_order(dltstart_timestamps, application_startup_order):
    apps = list(dltstart_timestamps.keys())
    cur_len = 0
    for order_type, order in application_startup_order:
        if cur_len + len(order) > len(apps):
            return False
        if order_type.lower() == OrderType.SEQUENTIAL.value:
            if apps[cur_len:cur_len+len(order)]!=order:
                return False
        else:
            if set(apps[cur_len:cur_len+len(order)]) != set(order):
                return False
        cur_len += len(order)
    return True


def extract_timestamp_from_dlt(line):
    """Extract timestamp from DLT output format"""
    parts = line.split(' ')
    # Check if the line has enough parts to extract the timestamp
    if len(parts) > 5:
        # Extract the timestamp from the line
        timestamp = parts[3].strip()
        return float(timestamp)
    return None


# Function to extract the welcome timestamp from the log lines
def extract_welcome_timestamp(lines):
    # Initialize welcome_timestamp to None
    welcome_timestamp = None
    # Iterate over each line in the log file
    for line in lines:
        # Search for the welcome message using regular expression
        match = re.search(r'KSAR Adaptive', line)
        if match:
            # Extract the timestamp from the line containing the welcome message
            #welcome_timestamp = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\]', line).group(1)
            welcome_timestamp = extract_timestamp_from_dlt(line)
            # Break the loop once the welcome timestamp is found
            break
    return welcome_timestamp


def RCAR_ON_OFF_Relay():
    try:
        logger.info("Turning OFF relay...")
        subprocess.run(["usbrelay", "BITFT_1=0"])
        time.sleep(3)  #  delay

        logger.info("Turning ON relay...")
        subprocess.run(["usbrelay", "BITFT_1=1"])
        time.sleep(0.2)  #  delay

    except Exception as e:
        logger.error(f"Error executing usbrelay commands: {e}")
        return False
    return True


def power_ON_OFF_Relay(serial_port_Relay, baudrate_Relay):
    try:
        #set up your serial port with the desire COM port and baudrate.
        signal = serial.Serial(serial_port_Relay, baudrate_Relay, bytesize=8, stopbits=1, timeout=1)
        if not signal.is_open:
            logger.error(f"Failed to open serial port: {serial_port_Relay}")
            return False
       
        logger.info("Turning OFF relay...")
        signal.write("AT+CH1=0".encode())   # Relay OFF
        time.sleep(25)
       
        logger.info("Turning ON relay...")
        signal.write("AT+CH1=1".encode())   # Relay ON
        time.sleep(0.1)  # 100ms delay
    except Exception as e:
        logger.error(f"Failed to open serial port: {e}")
        return False
    return True


def create_workBook(ecu_type, setup_type, iterations, config):
    try:
        # Create the report file name based on the ECU type and current timestamp
        reportName = f"Application_Startup_Time_{setup_type}_{ecu_type}_N{iterations}_{current_timestamp}.xlsx"
       
        # Define the directory where the report will be saved
        report_dir = local_save_path
       
        # Define the full path of the report file
        report_file = report_dir / reportName
       
        # Check if the report directory exists
        if not report_dir.exists():
            # If the directory does not exist, create it
            report_dir.mkdir()
       
    except OSError as e:
        # If an error occurs while creating the directory, logger. the error message and return None
        logger.error(f"Error creating directory: {e}")
        return None, None, None
   
    except Exception as e:
        # If any other exception occurs, logger. the error message and return None
        logger.error(f"An unexpected error occurred: {e}")
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
            sheet_title = f"GEN3_StartupTime_{i:02d}"
            sheet = workbook.create_sheet(title=sheet_title)
            sheets.append(sheet)


        # Create sheet for Appendix
        add_appendix_sheet(workbook, ecu_type, config)
 
        # Remove gridlines from all the sheets in the workbook
        for sheet_exl in sheets:
            # Hide the grid lines in the sheet
            sheet_exl.sheet_view.showGridLines = False

        summary_sheet.sheet_view.showGridLines = False
       
        # Return the report file path, workbook object, and active sheet object
        return report_file, workbook, sheets, summary_sheet
   
    except Exception as e:
        # If any exception occurs while creating the workbook or sheet, logger. the error message and return None
        logger.error(f"An error occurred while creating the workbook or sheet: {e}")
        raise e
        # return None, None, None, None


def load_config(file_path):
    try:
        config_path = Path(__file__).parent.joinpath(file_path)
        root, ext = os.path.splitext(config_path)
        with open(config_path, 'r') as file:
            if ext == '.json':
                config = json.load(file)
            elif ext in ('.yml', '.yaml'):
                config = yaml.safe_load(file)
            else:
                logger.error(f"'{file_path}' is not a valid config file")        
                return None

        return config
    except (FileNotFoundError, PermissionError, yaml.YAMLError, IOError) as e:
        logger.error(f"An error occurred while reading the file '{file_path}': {e}")
        return None


def add_appendix_sheet(workbook, ecu_type, config):
    appendix_sheet = workbook.create_sheet(title='Appendix')
    # appendix_sheet.title = 'Appendix'
    appendix_sheet.sheet_view.showGridLines = False
    start_row = create_header(appendix_sheet, ecu_type, config['validate-startup-order'], 'startup_appendix')
    for data_row in startup_field_descriptions:
        appendix_sheet.append(data_row)
    format_sheet(appendix_sheet, start_row, appendix_columns)
   

def is_merged_cell(sheet, cell):
    return cell.coordinate in sheet.merged_cells
 
   
def format_sheet(sheet, start_row, columns):
    # Dictionary to track max length in each column
    max_col_widths = {}
    # Iterate over rows starting from start_row
    for row in sheet.iter_rows(min_row=start_row, max_row=sheet.max_row):
        # Skip empty rows
        if all(cell.value is None for cell in row):
            continue
        for col_idx, cell in enumerate(row):

            # Update max width tracking
            if cell.value:
                length = len(str(cell.value))
                col_letter = get_column_letter(col_idx + 1)
                if (col_letter not in max_col_widths or max_col_widths[col_letter] < length) and not is_merged_cell(sheet, cell):
                   max_col_widths[col_letter] = length
            if cell.value in columns:
                cell.fill = PatternFill(start_color="B5E6A2", end_color="B5E6A2", fill_type="solid")
                cell.font = Font(bold=True)
                cell.border = border_style
            else:
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = border_style

    # Set the column widths based on content length
    for col_letter, width in max_col_widths.items():
        # Add a little extra space (2 or 3) for padding
        sheet.column_dimensions[col_letter].width = width + 2
 

def create_dlp_files(ecu_config_list, setup_type, config):
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
    else:
        os.makedirs(output_dir_path)
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
            print(f"Warning: 'hostname' not found for ECU {ecu['ecu-type']}")
            continue
        # Set description text to the ECU type
        description = root.find('ecu/description')
        if description is not None:
            description.text = ecu['ecu-type']
        else:
            print(f"Warning: 'description' not found for ECU {ecu['ecu-type']}")
        # Write updated XML to file
        output_path = os.path.join(output_dir_path, project_name)
        dlp_files[ecu['ecu-type']] = output_path
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
   
    return dlp_files


def capture_logs_from_dlt_viewer(log_file_name, dlt_file_name, project_file_name, config, ecu_type):
    print("capture_logs_from_dlt_viewer :: START")
    timeout = config['script-execution-time-in-seconds']
    script_dir = Path(__file__).parent.joinpath("dlt-viewer.bat")

    if sys.platform.startswith("win"):
        isPathSet = config['windows']['isPathSet']
        if isPathSet:
            subprocess.call([script_dir, "dlt-viewer.exe", str(timeout), log_file_name, dlt_file_name, project_file_name])
        else:
            dlt_viewer_path = config['windows']['dltViewerPath']
            # dlt_viewer_path = os.path.join(dlt_viewer_path, "dlt-viewer.exe")
            log_file_name = os.path.join(log_file_name)
            logger.info(f"dlt_viewer_path: {dlt_viewer_path}")
            logger.info(f"log_file_name : {log_file_name}")
            # subprocess.call([r"dlt-viewer.bat", dlt_viewer_path + "\\", str(timeout), log_file_name])
            subprocess.call([script_dir, dlt_viewer_path, str(timeout), log_file_name, dlt_file_name, project_file_name])
    elif sys.platform.startswith("linux"):
        subprocess.run("timeout " + str(timeout) + " dlt-viewer -p "+project_file_name+" -l "+dlt_file_name+" -v", shell=True)
        print("Converting *.dlt to *.txt...")
        subprocess.run("dlt-viewer -c logs.dlt "+str(log_file_name), shell=True)
        print("Conversion done, successfully...")

    size = os.path.getsize(log_file_name)
    if size == 0:
        logger.warning(f"Generated {os.path.basename(log_file_name)} is empty, Please check for valid IP-address / Status of {ecu_type}.")
        return False
    return True

       
def process_log_file(i, ecu_type, log_file_details, dlp_file, config, sheet, overall_IG_ON_iteration, process_start_times, process_times, application_startup_order,application_startup_order_status):
    try:
        # Get the log file path and name for the specified ECU type and timestamp
        filename, logfile, dltfile = log_file_details
        if not capture_logs_from_dlt_viewer(filename, dltfile, dlp_file, config, ecu_type):
            return False

        # Attempt to open the log file in read mode with error handling for encoding issues
        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as file:
                lines = file.readlines()
                time.sleep(2)
        except FileNotFoundError:
            logger.error(f"File not found: {filename}")
            return False
        except UnicodeDecodeError as e:
            logger.error(f"Unicode decode error: {e}")
            return False

        # Extract the welcome timestamp from the log fil
        welcome_timestamp = extract_welcome_timestamp(lines)

        # Check if the welcome timestamp was found
        if welcome_timestamp is None:
            logger.error("KSAR Adaptive not found in log file")
            return False

        # Extract DLTStart timestamps for each application from the log file
        dltstart_timestamps = extract_dltstart_timestamps(lines)

        # Check if the DLTStart timestamps were found
        if not dltstart_timestamps or len(dltstart_timestamps)==0:
            logger.error("Apps DLTStart time is not found in log file")
            return False
       
        application_startup_order_status.append(validate_app_startup_order(dltstart_timestamps, application_startup_order))
        print ("dlttimestamp:"+str(dltstart_timestamps.keys()))

        process_Start_End_timestamps = extract_process_timestamps(lines)
        print ("process_Start_End_timestamp:"+str(process_Start_End_timestamps))
        if not process_Start_End_timestamps or len(process_Start_End_timestamps)==0:
            logger.error("Error: Unable to extract process timestamps.")
            return False
       
        process_timing_info = extract_and_sort_process_timestamps(process_Start_End_timestamps, ecu_type)
        print ("process_timing_info:"+str(process_timing_info))
       
        if not process_timing_info:
            logger.error("Error: No report data available.")
            return False    

        for item in process_timing_info:
            # logger.info(f"Process: {item['process']} Start Timestamp: {item['start_clock']} End Timestamp: {item['end_clock']} start_time_ms: {item['start_time_ms']}")

            # Check if the process is already in the process start times dictionary
            process = item['process']
            if process not in process_start_times:
                # If the process is not in the dictionary, add it with an empty list
                process_start_times[process] = []
            # Append the start_time_ms to the process's list of start times    
            process_start_times[process].append(item['start_time_ms'])                      
       
        for process, process_time in dltstart_timestamps.items():
            # Check if the process is already in the process times dictionary
            if process not in process_times:
                # If the process is not in the dictionary, add it with an empty list
                process_times[process] = []
            # Append the difference to the process's list of times
            process_times[process].append(process_time)
       
        overall_IG_ON_iteration.append(max(dltstart_timestamps.values()))
        print ("overall_IG_ON_iteration:"+str(overall_IG_ON_iteration))

        generate_apps_startup_report_from_QNX_startup(ecu_type, config, sheet, dltstart_timestamps, process_timing_info, application_startup_order)
       
        # Add a hyperlink to the log file in the Excel sheet
        add_logfile_hyperlink(filename, logfile, sheet)

    except Exception as e:
        logger.error(f"Exception :: {e}")
        return False
    return True
   
def save_workbook_and_generate_reports(ecu_type, summary_sheet, overall_IG_ON_iteration, process_times, process_start_times, application_startup_order_status, config, workbook, report_file):
    # Check if the workbook creation was successful
    if summary_sheet is None:
        logger.error("Error: Unable to create workbook.")
        return False

    each_iteration_test_status(ecu_type, summary_sheet, overall_IG_ON_iteration, config, application_startup_order_status)

    # Export the average data to the Excel sheet
    export_and_plot_average_data_to_excel(summary_sheet, ecu_type, process_times, process_start_times, config)

    # Save the Excel workbook
    workbook.save(report_file)

    #remove_png_files()        

    # logger. a success message
    logger.info(f"Test report is created successfully {report_file}")
    return True      

def start_startup_time_measurement():
   
    # Declare global variables
    global cur_dt_time_obj
    cur_dt_time_obj = datetime.now()
    global local_save_path
    local_save_path = Path(__file__).parents[1].joinpath("Reports", "03_Startup_Time", cur_dt_time_obj.strftime("%Y%m%d_%H-%M-%S"))
    local_save_path.mkdir(parents=True, exist_ok=True)
    global workbook_map
    workbook_map = {}
    global current_timestamp
    current_timestamp = cur_dt_time_obj.strftime("%Y%m%d_%H%M%S")


    script_start_time = time.perf_counter()
    try:
        global logger
        logger = setup_logging()

        isSuccess = True
        anySheet = []
        config = load_config('startup_time_config.json')
       
        # Check if the configuration is empty
        if config is None:
            logger.error(f"File 'config_file_path' not found.")
            return False
       
        if config['windows']['dltViewerPath'] and not os.path.isfile(config['windows']['dltViewerPath']):
            logger.error("Configured dlt-viewer path is not valid.")
            return False
        if config.get('threshold-in-seconds', -1) < 0 or config.get('threshold-in-seconds') > 100:
            logger.error("Configured 'threshold-in-seconds' is not valid. Configure its value in range[0, 100].")
            return False
       
        # Retrieve the number of iterations from the configuration
        try:
            iterations = config["iterations"]
            if not isinstance(iterations, int):
                logger.error("Error: 'iterations' must be an integer.")
                return False
        except KeyError:
            logger.error("Error: 'iterations' key not found in the configuration file.")
            return False
       
        try:
            duration = config["script-execution-time-in-seconds"]
            if not isinstance(duration, int):
                logger.error("Error: 'script-execution-time-in-seconds' must be an integer.")
                return False
        except KeyError:
            logger.error("Error: 'script-execution-time-in-seconds' key not found in the configuration file.")
            return False

        process_times_map = {}
        process_start_times_map = {}
        overall_IG_ON_iteration_map = {}
        application_startup_order_status_map = {}
        application_startup_order_map = {}
        setup_type = None
        enabled_ecu_list = set()
               
        if config.get('PADAS', {}).get('RCAR', False):
            enabled_ecu_list.add('RCAR')
            setup_type = 'PADAS'
        else:
            for board_type, enabled in config.get('Elite', {}).items():
                if enabled:
                    enabled_ecu_list.add(board_type)
                    setup_type = 'ELITE'
       
        print(setup_type, enabled_ecu_list)
        if setup_type is None or len(enabled_ecu_list) == 0:
            logger.error("No enabled ECU found in the configuration.")
            return False

        ecu_config_list = [ecu for ecu in config['ecu-config'] if ecu['ecu-type'] in enabled_ecu_list]
        for ecu in ecu_config_list:
            if ecu['ecu-type'] == ECUType.RCAR.value:
                ecu['ip-address'] = config['ECU_setting']['RCAR_IPAddress']
            elif ecu['ecu-type'] == ECUType.SoC0.value:
                ecu['ip-address'] = config['ECU_setting']['Qualcomm_SoC0_IPAddress']
            elif ecu['ecu-type'] == ECUType.SoC1.value:
                ecu['ip-address'] = config['ECU_setting']['Qualcomm_SoC1_IPAddress']
            workbook_map[ecu['ecu-type']] = tuple(create_workBook(ecu['ecu-type'], setup_type, iterations, config))
           
            # Check if the workbook creation was successful
            if workbook_map[ecu['ecu-type']][2] is None:
                logger.error("Error: Unable to create workbook.")
                return False
            process_times_map[ecu['ecu-type']] = {}
            process_start_times_map[ecu['ecu-type']] = {}
            overall_IG_ON_iteration_map[ecu['ecu-type']] = []
            application_startup_order_status_map[ecu['ecu-type']] = []
            application_startup_order = []
            for block in ecu['startup-order']:
                application_startup_order.append(tuple([block['type'], [app.strip() for app in block['apps'].split(',')]]))
            application_startup_order_map[ecu['ecu-type']] = list(application_startup_order)
             
        # Create the Logs directory path
        logs_folder = local_save_path / "Logs"      

        # Get a list of log files in the folder, sorted by last modified time
        log_files = sorted(glob.glob(os.path.join(logs_folder, '*.log')), key=os.path.getmtime)

        # if config['ecu-config']['setup-type'] == ECUType.ELITE.value:
        if not validate_ip_address(ecu_config_list):
            return False
        dlp_files = create_dlp_files(ecu_config_list, setup_type, config)
        if not dlp_files and len(dlp_files)==0:
            return False

        # Loop through the iterations
        for i in range(iterations):
           
            if setup_type == ECUType.RCAR.value:
                if not RCAR_ON_OFF_Relay():
                    return False
            else:
                if not power_ON_OFF_Relay(config.get('serial-port-relay'), config.get('baudrate-relay')):
                    return False
           
            threads = []
            for ecu_type, (report_file, workbook, sheets, summary_sheet) in workbook_map.items():
                print("Thread: ", ecu_type, ": Started")
               
                filename_list = {}
                if setup_type == ECUType.ELITE.value:
                    filename_list = get_log_file_paths_for_elite(i, current_timestamp, ecu_config_list, setup_type)
                else:
                    filename_list[ecu_type] = tuple(get_log_file_path(ecu_type, setup_type, iterations, current_timestamp, i))
                if any(not filename for (filename, logfile, dltfile) in filename_list.values()):
                    logger.error("Log file not created")
                    return False
                thread = ResultThread(
                    target=process_log_file,
                    args=(
                        i,
                        ecu_type,
                        filename_list[ecu_type],
                        dlp_files[ecu_type],
                        config,
                        sheets[i],
                        overall_IG_ON_iteration_map[ecu_type],
                        process_start_times_map[ecu_type],
                        process_times_map[ecu_type],
                        application_startup_order_map[ecu_type],
                        application_startup_order_status_map[ecu_type]
                     )
                )
                threads.append(thread)
                thread.start()
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
                print("Thread result :: ", thread.result)
                # if not thread.result:
                anySheet.append(thread.result)
        print('anySheet:', anySheet)
        if not any(anySheet):
            isSuccess = False

        # Save workbooks and generate reports for each ECU type
        for ecu_type, (report_file, workbook, sheets, summary_sheet) in workbook_map.items():
            if len(overall_IG_ON_iteration_map[ecu_type]) > 0:
                if not save_workbook_and_generate_reports(
                    ecu_type,
                    summary_sheet,
                    overall_IG_ON_iteration_map[ecu_type],
                    process_times_map[ecu_type],
                    process_start_times_map[ecu_type],
                    application_startup_order_status_map[ecu_type],
                    config,
                    workbook,
                    report_file):
                    isSuccess = False

    except KeyError as e:
        logger.error(f"Error: Missing expected key in ECU input fields: {e}")
        isSuccess = False
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        isSuccess = False
    finally:
        remove_png_files()
        script_end_time = time.perf_counter()
        logger.info(f"Total script execution time: {(script_end_time-script_start_time):.3f} seconds")
    print("Final response :: ", isSuccess)
    return isSuccess