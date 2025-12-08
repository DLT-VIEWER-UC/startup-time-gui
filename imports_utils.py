import sys, os, json, time, random, subprocess, logging, colorlog, platform, traceback, re, openpyxl, importlib, webbrowser, win32gui, win32con, win32process
from datetime import datetime
from PyQt5.QtGui import (
    # Icons and visuals
    QIcon, QMovie,

    # Validators
    QIntValidator, QValidator, QRegExpValidator, QRegularExpressionValidator
)
from PyQt5.QtCore import (
    # Core types and enums
    Qt, QSize, QLocale, QEvent, QCoreApplication,

    # Regular expressions
    QRegularExpression, QRegExp,

    # Threading and signals
    QThread, pyqtSignal, QObject,

    # File system and timing
    QFileSystemWatcher, QTimer
)
from PyQt5.QtWidgets import (
    # Core application and window components
    QApplication, QMainWindow, QDialog, QWidget, QTabWidget,

    # Layouts
    QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,

    # Input widgets
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox, QRadioButton, QCheckBox,

    # Buttons and controls
    QPushButton, QButtonGroup, QGroupBox,

    # Display and feedback
    QLabel, QMessageBox, QScrollArea,

    # File and style utilities
    QFileDialog, QStyle, QSizePolicy, QCompleter,

    # Table and header
    QTableWidget, QHeaderView
)
# from Event_Trigger_KEV_Scripts.flagManager import FlagManager
# from Continuous_KEV_Scripts.flagManager import FlagManager

common_groupbox_style = """
    QGroupBox {
        background-color: #F5F5F5;
        border: 1px solid #999999;
        border-radius: 5px;
        margin-top: 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top center;
        padding-left: 0px;  /* Move title to the right */
        padding-top: 0px;
    }
"""

# common_groupbox_style = "QGroupBox { background-color: #F5F5F5; border: 1px solid #999999; }"
common_enabled_style = "QPushButton:enabled {background-color: #D6D6D6; border: 1.5px solid #0078D7; }"
common_enabled_style_green = "QPushButton:enabled {background-color: #60A917; border: 1.5px solid #0078D7;}"
common_enabled_style_red = "QPushButton:enabled {background-color: #E51400; border: 1.5px solid #0078D7;}"
common_hover_style = "QPushButton:enabled:hover {background-color: #DAE8FC; border: 0.5px solid #0078D7;}"

# Create a regular expression pattern for IP address validation
ip_address_pattern = r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"

# Create a QRegularExpressionValidator object
ip_address_validator = QRegularExpressionValidator(QRegularExpression(ip_address_pattern))

# Create a regular expression that matches positive integers (1 or more digits)
regexp = QRegExp("^[1-9][0-9]*$")
regexp_initialdelay= QRegExp("^[0-9][0-9]*$")
# regexp_script_exec = QRegExp("^[1-9][0-9]{0,2}$")
regexp_script_exec = QRegExp("^(00|[1-9][0-9]{0,2})$")
regexp_initial_logging = QRegExp("^(0|[1-9]|1[0-9]|2[0-9]|30)$")
regexp_screenshot_interval = QRegExp("^(0|[1-9]|10)$")

# Create a QRegExpValidator
validator = QRegExpValidator(regexp)
validator_initialdelay= QRegExpValidator(regexp_initialdelay)
validator_script_exec=QRegExpValidator(regexp_script_exec)
validator_initial_logging=QRegExpValidator(regexp_initial_logging)
validator_screenshot_interval=QRegExpValidator(regexp_screenshot_interval)

labels = [
            "CPU and Memory Utilization", "Heap Memory", "Startup Time",  "Cyclic and Turnaround Time", "Throughput and Fault Injection",
            "Execution Time", "Shutdown Time", "Positive Response",  "Negative Response",  "Diagnostic Trouble Code (DTC)",  
            "Reprogramming_FOTA", "Reprogramming_Wired", "Diag_All_KPIs", "Continuous KEV", "Event Trigger KEV", "RAM Monitor",
            "Event Trigger RAM Monitor", "APL Communication Layout"
        ]

diag_labels = [
                "Positive Response", "Negative Response", "Diagnostic Trouble Code (DTC)",
                "Reprogramming_FOTA", "Reprogramming_Wired", "Diag_All_KPIs"
            ]

folder_names = {
    "CPU and Memory Utilization": "01_CPU_Memory_Utilization",
    "Heap Memory": "02_Heap_Memory",
    "Startup Time": "03_Startup_Time",
    "Cyclic and Turnaround Time": "04_Cyclic_and_Turnaround_Time",
    "Throughput and Fault Injection": "05_Throughput_and_Fault_Injection",
    "Execution Time": "06_Execution_Time",
    "Shutdown Time": "07_Shutdown_Time",
    "Positive Response": "08_DIAG_KPIs/Positive_Response",
    "Negative Response": "08_DIAG_KPIs/Negative_Response",
    "Diagnostic Trouble Code (DTC)": "08_DIAG_KPIs/Diagnostic_Trouble_Code_DTC",
    "Reprogramming_FOTA": "08_DIAG_KPIs/Reprogramming_FOTA",
    "Reprogramming_Wired": "08_DIAG_KPIs/Reprogramming_Wired",
    "Diag_All_KPIs": "08_DIAG_KPIs/Diag_All_KPIs",
    "Continuous KEV": "09_Continuous_KEV",
    "Event Trigger KEV": "10_Event_Trigger_KEV",
    "RAM Monitor": "11_RAM_Monitor",
    "Event Trigger RAM Monitor": "12_Event_Trigger_RAM_Monitor",
    "APL Communication Layout": "13_APL_Communication_Layout"
}

diag_inputSheet_folders = {
    "Positive Response": "Positive_Response_Input",
    "Negative Response": "Negative_Response_Input",
    "Diagnostic Trouble Code (DTC)": "DTC_Input",
    "Reprogramming_FOTA": "Reprogramming_FOTA_Input",
    "Reprogramming_Wired": "Reprogramming_Wired_Input",
    "Diag_All_KPIs": "Diag_All_KPIs_Input",
}

# Dictionary mapping KPI labels to their config file paths
switch_dict = {
    'CPU and Memory Utilization': './CPU_Memory_Utilization_Scripts/cpu_memory_utilization_config.json',
    'Heap Memory': './Heap_Memory_Scripts/heap_memory_config.json',
    'Startup Time': './Startup_Time_Scripts/startup_time_config.json',
    'Cyclic and Turnaround Time': './Cyclic_Turnaround_Time_Scripts/cyclic_turnaround_config.json',
    'Execution Time': './Execution_Time_Scripts/Execution_Time_Config.json',
    'Throughput and Fault Injection': './Throughput_Scripts/throughput_faultinjection_config.json',
    'Shutdown Time': './Shutdown_Time_Scripts/shutdown_time_config.json',
    'Continuous KEV': './Continuous_KEV_Scripts/kev_gen_and_logMover_config.json',
    'Event Trigger KEV': './Event_Trigger_KEV_Scripts/kev_gen_and_logMover_config.json',
    'RAM Monitor': './RAM_Measurement_Scripts/XCP_RAM_Measurement_Config.json',
    'Event Trigger RAM Monitor': './Event_Trigger_RAM_Measurement_Scripts/XCP_RAM_Event_Trigger_Config.json',
    'APL Communication Layout': './APL_Communication_Layout_Scripts/XCP_APL_Config.json',
    "Positive Response": 'Positive_Response_Config.json',
    "Negative Response": 'Negative_Response_Config.json',
    "Diagnostic Trouble Code (DTC)": 'DTC_Config.json',
    "Reprogramming_FOTA": 'Reprogramming_FOTA_Config.json',
    "Reprogramming_Wired": 'Reprogramming_Wired_Config.json',
    "Diag_All_KPIs": 'Diag_All_KPIs_Config.json',
}

# Mapping of labels to their module and class names
config_dialogs = {
    "CPU and Memory Utilization": ("cpu_memory_utilization_config_window", "CpuMemoryConfig"),
    "Heap Memory": ("heap_memory_config_window", "HeapMemoryConfig"),
    "Startup Time": ("startup_time_config_window", "StartupTimeConfig"),
    "Cyclic and Turnaround Time": ("cyclic_turnaround_time_config_window", "CyclicTurnaroundConfig"),
    "Throughput and Fault Injection": ("throughput_config_window", "ThroughputConfig"),
    "Execution Time": ("execution_time_config_window", "ExecutionTimeConfig"),
    "Shutdown Time": ("shutdown_time_config_window", "ShutdownTimeConfig"),
    "Event Trigger KEV": ("event_trigger_KEV_config_window", "EventTriggerKEVConfig"),
    "Continuous KEV": ("Continous_KEV_config_window", "ContinuousKEVConfig"),
    "RAM Monitor": ("XCP_RAM_measurment_config_window", "XcpRAMMonitoringConfig"),
    "Event Trigger RAM Monitor": ("XCP_RAM_measurement_event_trigger_config_window", "XCPRAMMonitorEventTriggerConfig"),
    "APL Communication Layout": ("XCP_APL_communication_layout_config_window", "XCPAPLCommConfig"),
    "Diag": ("diag_config_window", "DiagConfig")  # Optional fallback for diag labels
}

# Save original streams
original_stdout = sys.__stdout__
original_stderr = sys.__stderr__

py_logger = None  # Global logger

def setup_console_logger(name="console_logger", stream=sys.__stdout__, level=logging.INFO):
    global py_logger

    LOG_FORMAT = (
        '[%(asctime)s] [%(log_color)s%(levelname)s%(reset)s] [%(funcName)s][%(lineno)d] %(message)s'
    )

    LOG_COLORS = {
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white'
    }

    formatter = colorlog.ColoredFormatter(
        LOG_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors=LOG_COLORS
    )

    py_logger = logging.getLogger(name)
    py_logger.setLevel(level)
    py_logger.propagate = False
    py_logger.handlers = []

    handler = logging.StreamHandler(stream)
    handler.setFormatter(formatter)
    py_logger.addHandler(handler)

    return py_logger

def update_logger_stream(stream):
    if py_logger:
        for handler in py_logger.handlers:
            handler.stream = stream

def close_pdf_process(pdf_process):
    """
    Safely closes the Adobe Reader process started by the application.

    Args:
        pdf_process (subprocess.Popen or None): The process object for Adobe Reader.

    Behavior:
    - Checks if the process exists and is still running.
    - If running, terminates it using taskkill (forcefully kills process and its child processes).
    - Logs appropriate messages for success or failure.
    - Returns None after closing (so caller can reset the reference).
    """
    if pdf_process:  # Ensure we have a process object
        try:
            # Check if process is still running
            if pdf_process.poll() is None:  # None means process is alive
                # Kill the process and its child processes silently
                subprocess.call(
                    ['taskkill', '/F', '/T', '/PID', str(pdf_process.pid)],
                    stdout=subprocess.DEVNULL,  # Suppress output
                    stderr=subprocess.DEVNULL   # Suppress errors
                )
                py_logger.info(f"Closed Adobe Reader process (PID: {pdf_process.pid}).")
            else:
                py_logger.info("PDF process already closed by user.")
        except Exception as e:
            py_logger.error(f"Error closing PDF viewer: {e}")

    # Return None so caller can reset the reference
    return None

def open_user_manual(label, pdf_process=None):
    """
    Opens a user manual PDF at the page mapped to the given label.
   
    Behavior:
    - If Adobe Reader is installed and the PDF is already open in an instance created by this code,
      bring that window to the foreground.
    - If not open, create a new Adobe Reader instance and open the PDF at the specified page.
    - If Adobe Reader is not installed, fallback to opening the PDF in the default browser.
   
    Notes:
    - Does NOT bring to foreground if the Adobe instance was not created by this code.
   
    Args:
        label (str): The label to look up in the JSON mapping.
        pdf_process (subprocess.Popen or None): Existing Adobe Reader process if previously opened.
   
    Returns:
        subprocess.Popen or None: The Adobe Reader process if opened, else None.
    """

    # Path to the PDF file
    pdf_path = r"M13_HOKPIT-3661_GEN2_Platform_Testing_GUI_Tool_UM.pdf"
    # Path to Adobe Reader executable
    adobe_reader_path = r"C:\Program Files\Adobe\Acrobat DC\Acrobat\Acrobat.exe"
    # JSON file containing label-to-page mapping
    json_path = r"user_manual_page_mapping.json"

    try:
        # Load the JSON mapping of labels to page numbers
        with open(json_path, 'r') as f:
            page_mapping = json.load(f)

        # Get the page number for the given label
        page_number = page_mapping.get(label)
        if page_number is None:
            py_logger.warning(f"No page mapping found for label: {label}")
            return None

        # Check if Adobe Reader exists on the system
        if os.path.exists(adobe_reader_path):
            # If we already have a process and it's still running
            if pdf_process and pdf_process.poll() is None:
                try:
                    # Bring the existing Adobe Reader window to the foreground
                    def enum_windows_callback(hwnd, pid):
                        """
                        Callback to check if the window belongs to our Adobe Reader process.
                        If yes, restore and bring it to the foreground.
                        """
                        _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                        if found_pid == pid:
                            # Restore the window if minimized
                            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                            # Bring the window to the foreground
                            win32gui.SetForegroundWindow(hwnd)

                    # Enumerate all windows and apply the callback for our process PID
                    win32gui.EnumWindows(lambda hwnd, _: enum_windows_callback(hwnd, pdf_process.pid), None)
                    py_logger.info("Brought existing Adobe Reader window to foreground.")
                    return pdf_process  # Exit after bringing to foreground
                except Exception as e:
                    py_logger.error(f"Failed to bring window to foreground: {e}")
                    return pdf_process

            # If no running process or previous attempt failed, open a new instance
            # /n ensures a new instance, /A page=... jumps to the specific page
            pdf_process = subprocess.Popen(
                [adobe_reader_path, "/n", "/A", f"page={page_number}", pdf_path],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
            py_logger.info("Opened PDF in new Adobe Reader instance.")
            return pdf_process
        else:
            # Fallback: open in default browser (cannot jump to specific page)
            webbrowser.open_new(pdf_path)
            py_logger.info("Adobe Reader not found. Opened in browser.")
            return None

    except Exception as e:
        py_logger.error(f"Error opening PDF: {e}")
        return pdf_process

py_logger = setup_console_logger(stream=original_stdout)
py_logger.info("Launching Gen2 PF GUI Tester Tool, please wait!...")