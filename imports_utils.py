import sys, os, json, time, random, subprocess, logging, colorlog, platform, traceback, re
from datetime import datetime
import openpyxl
from PyQt5.QtGui import (
    # Icons and visuals
    QIcon, QMovie,

    # Validators
    QIntValidator, QValidator, QRegExpValidator, QRegularExpressionValidator
)
from PyQt5.QtCore import (
    # Core types and enums
    Qt, QSize, QLocale, QEvent,

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
        font-size: 14px;
        font-weight: 200;
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

py_logger = setup_console_logger(stream=original_stdout)
py_logger.info("Launching Gen2 PF GUI Tester Tool, please wait!...")