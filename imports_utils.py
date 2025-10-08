# PyQt5 imports for the GUI application
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QFormLayout, QGroupBox, QLabel, QPushButton, QLineEdit, QTextEdit,
    QCheckBox, QComboBox, QScrollArea, QFileDialog, QDialog,
    QSizePolicy, QRadioButton, QButtonGroup
)
from PyQt5.QtCore import (
    Qt, QTimer, QObject, QThread, pyqtSignal, QFileSystemWatcher,
    QCoreApplication, QPropertyAnimation, QSize
)
from PyQt5.QtGui import QIcon, QFont, QPixmap, QIntValidator

# Standard library imports
import sys
import os
import json
import subprocess
import platform
import time
import datetime
from pathlib import Path

# Excel handling
import openpyxl