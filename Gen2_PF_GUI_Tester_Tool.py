import importlib
from imports_utils import *
# from CPU_Memory_Utilization_Scripts.Integrated_CPU_Memory_Measurement import CPU_Memory_measurement

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

class CustomIntValidator(QIntValidator):
    def __init__(self, min_value, max_value, parent=None):
        super().__init__(min_value, max_value, parent)
        self.min_value = min_value
        self.max_value = max_value

    def validate(self, input_str, pos):
        # Case 1: Empty input
        if input_str == "":
            return (QIntValidator.Intermediate, input_str, pos)

        # Case 2: Input is all digits
        if input_str.isdigit():
            # Case 2a: Input is "00" — treat as intermediate
            if input_str == "00":
                return (QIntValidator.Intermediate, input_str, pos)

            # Case 2b: Input is "0"
            if input_str == "0":
                if self.min_value <= 0 <= self.max_value:
                    return (QIntValidator.Acceptable, input_str, pos)
                else:
                    return (QIntValidator.Intermediate, input_str, pos)

            # Case 2c: Input has leading zeros (e.g., "01", "002")
            if input_str.startswith('0') and len(input_str) > 1:
                return (QIntValidator.Invalid, input_str, pos)

            # Case 2d: Normal integer input
            value = int(input_str)

            # Special case: values > 255 are intermediate
            if value > 255:
                return (QIntValidator.Intermediate, input_str, pos)

            # Acceptable range check
            if self.min_value <= value <= self.max_value:
                return (QIntValidator.Acceptable, input_str, pos)
            else:
                return (QIntValidator.Invalid, input_str, pos)

        # Case 3: Input contains non-digit characters
        else:
            return (QIntValidator.Invalid, input_str, pos)

class SpinnerDialog(QDialog):
    def __init__(self, parent=None, title="Processing..."):
        super().__init__(parent)

        # Set a clean and user-friendly window title
        self.setWindowTitle(title)

        # Customize window flags (no minimize/maximize/close buttons)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint | Qt.Tool)

        # Make the dialog non-blocking
        self.setModal(False)

        # Create the main layout
        layout = QVBoxLayout()

        # Spinner GIF label with light gray background
        spinner_label = QLabel(self)
        spinner_movie = QMovie("./GUI_Icons/Hourglass.gif")  # Update path if needed
        spinner_label.setMovie(spinner_movie)
        spinner_movie.start()

        # Add spinner to layout
        layout.addWidget(spinner_label, alignment=Qt.AlignCenter)

        # Add a descriptive message label
        message_label = QLabel("Please wait for ECU cleanup or IG ON...")
        message_label.setStyleSheet("font-size: 9pt;")
        message_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(message_label)

        # Set layout and size
        self.setLayout(layout)
        self.resize(250, 120)

        # Move the dialog to center of the parent window
        if parent:
            self.move(parent.frameGeometry().center() - self.rect().center())

        # Track parent window movement
        if parent:
            parent.installEventFilter(self)

    def eventFilter(self, obj, event):
        # Reposition the dialog when the parent moves
        if obj == self.parent() and event.type() == QEvent.Move:
            self.move(self.parent().frameGeometry().center() - self.rect().center())
        return super().eventFilter(obj, event)

class Worker(QObject):
    finished = pyqtSignal()
    set_status_inProgess = pyqtSignal(str)
    update_status = pyqtSignal(str, str)
    disable_widgets = pyqtSignal()
    enable_widgets = pyqtSignal()
    start_kpi_logging = pyqtSignal(str, str)  # Signal to start logging with KPI label
    stop_kpi_logging = pyqtSignal()      # Signal to stop logging

    def __init__(self, ecu_input_fields, kpi_widgets):
        super().__init__()
        self.ecu_input_fields = ecu_input_fields
        self.kpi_widgets = kpi_widgets
        self.process = None
        self._stop_requested = False
   
    def run(self):
        try:
            self.disable_widgets.emit()
            # self.print_ecu_input_fields()
            self.run_function()
        except Exception as e:
            py_logger.error(f"Error in run: {e}")
        finally:
            # py_logger.info("Closing the Worker Thread...")
            self.enable_widgets.emit()
            self.finished.emit()

    def request_stop(self):
        self._stop_requested = True
        # self.terminate_all_ecu_processes()
   
    def terminate_all_ecu_processes(self):
        exe_name = "High_Level_ECU_Tester.exe"  # Only the executable name, not full path

        try:
            result = subprocess.check_output(f'tasklist | findstr "{exe_name}"', shell=True).decode()
            # py_logger.info(f"[Worker] Raw tasklist result:\n{result}")
            lines = result.strip().split('\n')

            pids_terminated = []

            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    pid = parts[1]
                    try:
                        subprocess.run(f'taskkill /PID {pid} /F', shell=True, check=True)
                       
                        pids_terminated.append(pid)
                    except subprocess.CalledProcessError:
                        py_logger.error(f"[Worker] PID {pid} was already terminated or inaccessible.")

            if not pids_terminated:
                py_logger.warning(f"No active instances of {exe_name} found.")
            else:
                py_logger.info(f"[Worker] Total terminated PIDs: {', '.join(pids_terminated)}")
           
            from diag_abrupt_termination import run_deletion_sequence
            run_deletion_sequence()  
        except subprocess.CalledProcessError:
            py_logger.error("Process scan failed�no matches found.")
        except Exception as e:
            py_logger.error(f"Process termination error: {e}")
 
    def launch_diag_application(self):
        py_logger.info("Launching the Diag High Level ECU Tester, please wait!...")

        current_os = platform.system()
        if current_os == "Windows":
            exe_path = r"High_Level_ECU_Tester.exe"  # Update this path if needed
        elif current_os == "Linux":
            exe_path = r"./High_Level_ECU_Tester"
        else:
            py_logger.error("Unsupported OS.")
            return False

        if not os.path.exists(exe_path):
            py_logger.error(f"Executable not found: {exe_path}")
            return False

        try:
            if current_os == "Linux":
                subprocess.run(["chmod", "+x", exe_path])

            self.process = subprocess.Popen([exe_path])
            time.sleep(3)
            py_logger.info("Diag High Level ECU Tester is Successfully Launched.")

            # Wait for the process to complete or be forcefully stopped
            while self.process.poll() is None:
                if self._stop_requested:
                    self.terminate_all_ecu_processes()
                    return False

                time.sleep(0.2)  # Non-blocking check

            return True  # Process finished naturally

        except Exception as e:
            py_logger.error(f"Error running app: {e}")
            return False

    def run_function(self):
        """
        Description:
            Executes KPI measurement tasks based on selected labels and updates their status.
            Handles dynamic imports, subprocess execution, and diagnostic checks.
            Also updates configuration files with the current timestamp before running each KPI.

        Inputs:
            - self: Instance of the class containing KPI widgets, signals, and helper methods.

        Outputs:
            - emits signals to update UI and logs status.
        """

        # ---------------- Helper Functions ---------------- #

        def update_config_file(label):
            """
            Description:
                Updates the configuration file for the given KPI label with the current timestamp.
                If the label belongs to diagnostic KPIs, uses a default config file.

            Inputs:
                - label (str): KPI label for which the config file needs to be updated.

            Outputs:
                - Current_Timestamp (str): Timestamp in 'YYYYMMDD_HH-MM-SS' format.
            """
            try:
                config_path = switch_dict.get(label)
                if label in diag_labels:
                    config_path = "DIAG_KPI_Config.json"

                if config_path:
                    try:
                        with open(config_path, 'r', encoding="utf-8") as f:
                            data = json.load(f)

                        Current_Timestamp = datetime.now().strftime("%Y%m%d_%H-%M-%S")
                        data["Current_Timestamp"] = Current_Timestamp

                        with open(config_path, 'w', encoding="utf-8") as f:
                            json.dump(data, f, indent=4)

                        return Current_Timestamp

                    except FileNotFoundError:
                        py_logger.error(f"Error: Configuration file '{config_path}' not found.")
                    except json.JSONDecodeError:
                        py_logger.error(f"Error: Configuration file '{config_path}' is not a valid JSON.")
                    except KeyError as e:
                        py_logger.error(f"Error: Missing expected key in ECU input fields: {e}")
            except Exception as e:
                py_logger.error(f"Unexpected error while updating '{config_path}': {e}")

            # Fallback timestamp if update fails
            return datetime.now().strftime("%Y%m%d_%H-%M-%S")

        def get_color(status):
            """Returns green if status is True, else red."""
            return "#60A917" if status else "#E51400"

        def run_subprocess(script_path):
            """
            Runs a Python script as a subprocess and checks flags for success.
            """
            flag_manager = FlagManager()
            process = subprocess.Popen(
                ["python", "-u", script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            for line in process.stdout:
                print(line, end="")
            process.wait()
            return flag_manager.get_event_trigger_status_flag() and flag_manager.get_log_mover_status_flag()

        # ---------------- Label Actions Mapping ---------------- #
        label_actions = {
            'CPU and Memory Utilization': lambda: CPU_Memory_measurement(),
            'Heap Memory': lambda: __import__('Heap_Memory_Scripts.Heap_Memory_Utilization', fromlist=['RUN_HEAP_MEMORY_SCRIPT']).RUN_HEAP_MEMORY_SCRIPT(),
            'Startup Time': lambda: __import__('Startup_Time_Scripts.Applications_StartupTime_IG_ON', fromlist=['start_startup_time_measurement']).start_startup_time_measurement(py_logger),
            'Cyclic and Turnaround Time': lambda: __import__('Cyclic_Turnaround_Time_Scripts.cyclic_turnaround_time_measurement', fromlist=['start_cyclic_turnaround_time_measurement']).start_cyclic_turnaround_time_measurement(),
            'Throughput and Fault Injection': lambda: __import__('Throughput_Scripts.Integrated_Throughput', fromlist=['start_throughput']).start_throughput(),
            'Execution Time': lambda: __import__('Execution_Time_Scripts.Execution_Time_Measurement_Script', fromlist=['start_execution_time_measurement']).start_execution_time_measurement(),
            'Shutdown Time': lambda: __import__('Shutdown_Time_Scripts.Applications_ShutdownTime_IG_ON', fromlist=['start_shutdown_time_measurement']).start_shutdown_time_measurement(py_logger),
            'Continuous KEV': lambda: run_subprocess("./Continuous_KEV_Scripts/main.py"),
            'Event Trigger KEV': lambda: run_subprocess("./Event_Trigger_KEV_Scripts/main.py"),
            'RAM Monitor': lambda: __import__('RAM_Measurement_Scripts.test_executor', fromlist=['start_RAM_measurement']).start_RAM_measurement(),
            'Event Trigger RAM Monitor': lambda: __import__('Event_Trigger_RAM_Measurement_Scripts.test_executor', fromlist=['start_event_trigger_RAM_measurement']).start_event_trigger_RAM_measurement(),
            'APL Communication Layout': lambda: __import__('APL_Communication_Layout_Scripts.test_executor', fromlist=['start_APL_Communication']).start_APL_Communication()
        }

        # ---------------- Main Execution Loop ---------------- #
        for label in labels:
            if self._stop_requested:
                return

            widgets = self.kpi_widgets.get(label)
            if not (widgets and widgets['checkbox'].isChecked()):
                continue

            try:
                status = False
                # Update config file and get timestamp
                current_timestamp = update_config_file(label)
                self.start_kpi_logging.emit(label, current_timestamp)
                self.set_status_inProgess.emit(label)

                # Execute KPI logic
                if label in label_actions:
                    # Access the function mapped to the label and call it
                    status = label_actions[label]()

                elif label in diag_labels:
                    status = self.launch_diag_application()
                    if status:
                        parent_dir = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
                        report_path = os.path.join(parent_dir, 'Reports', folder_names.get(label, ''), current_timestamp)
                        status = os.path.isdir(report_path) and any(file.lower().endswith('.xlsx') for file in os.listdir(report_path))
                        if not status:
                            py_logger.warning(f"File path not found or no .xlsx files: {report_path}")
                else:
                    status = False

                # Update UI with status color
                color = get_color(status)
                self.stop_kpi_logging.emit()
                self.update_status.emit(label, color)
                time.sleep(0.1)

            except Exception as e:
                py_logger.error(f"Error in run_function for label '{label}': {e}")
                self.update_status.emit(label, "#E51400")

    def print_ecu_input_fields(self):
        for ecu, fields in self.ecu_input_fields.items():
            py_logger.info(f"ECU: {ecu} is enabled")
            py_logger.info(f"IP: {fields['IP']}")
            py_logger.info(f"Telnet Username: {fields['telnet_username']}")
            py_logger.info(f"Telnet Password: {fields['telnet_password']}")
            py_logger.info(f"FTP Username: {fields['FTP_username']}")
            py_logger.info(f"FTP Password: {fields['FTP_password']}")
            py_logger.info("------------------------")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.kpi_widgets = {}
        self.ecu_selection_status = {}
        self.configuration_flag = False    
        self.msg_box = None      
        self.is_any_ecu_selected_flag = False
        self.is_test_in_progress = False
        self.current_kpi_label = None
        self.kpi_log_file = None  

        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()

        self.tab_widget.addTab(self.tab1, "Tester")
        self.tab_widget.addTab(self.tab2, "Console")
        self.tab_widget.addTab(self.tab3, "About")        

        self.create_tester_tab()            
        self.create_console_tab()
        self.create_about_tab()
        self.read_ECU_configuration()
        self.set_window_properties()
        self.update_button_states()

        # To remove the stop.flag file
        self.manage_stop_flag(is_create=False)

    def create_console_tab(self):        
        class EmittingStream(QObject):
            text_written = pyqtSignal(str)

            def __init__(self, original_stream):
                super().__init__()
                self.original_stream = original_stream

            def write(self, text):
                # Strip ANSI codes for GUI
                plain_text = self.strip_ansi(text)
                self.text_written.emit(plain_text)

                # Write full colored text to terminal
                if self.original_stream:
                    self.original_stream.write(text)
                    self.original_stream.flush()

            def flush(self):
                if self.original_stream:
                    self.original_stream.flush()

            def strip_ansi(self, text):
                # Regex to remove ANSI escape sequences
                ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
                return ansi_escape.sub('', text)

        layout = QVBoxLayout()

        label = QLabel("Runtime logs will appear below:")
        label.setStyleSheet("color: black; font-weight: bold;")
        layout.addWidget(label)

        self.console_output = QPlainTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setStyleSheet("""
            QPlainTextEdit {
                background-color: black;
                color: white;
                font-family: Consolas, monospace;
                font-size: 12pt;
            }
        """)

        self.clear_logs_button = QPushButton("Clear Logs!")
        self.clear_logs_button.setFixedSize(100, 35)
        self.clear_logs_button.setStyleSheet(common_enabled_style + common_hover_style)
        self.clear_logs_button.clicked.connect(self.console_output.clear)        

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.clear_logs_button)

        layout.addWidget(self.console_output)
        layout.addLayout(button_layout)

        self.tab2.setLayout(layout)

        # Redirect stdout and stderr
        stdout_stream = EmittingStream(original_stdout)
        stderr_stream = EmittingStream(original_stderr)

        stdout_stream.text_written.connect(self.write_to_console)
        stderr_stream.text_written.connect(self.write_to_console)

        sys.stdout = stdout_stream
        sys.stderr = stderr_stream

        # Update logger stream to GUI
        update_logger_stream(stdout_stream)

    def write_to_console(self, text):
        self.console_output.moveCursor(self.console_output.textCursor().End)
        self.console_output.insertPlainText(text)
        self.console_output.moveCursor(self.console_output.textCursor().End)

        if self.kpi_log_file:
            self.kpi_log_file.write(text)
            self.kpi_log_file.flush()

    def start_kpi_logging(self, kpi_label, Current_Timestamp):
        try:
            self.current_kpi_label = kpi_label

            if kpi_label in diag_labels:
                return

            folder_name = folder_names.get(kpi_label)
            if not folder_name:
                raise ValueError(f"Invalid KPI label: {kpi_label}")

            parent_dir = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
            log_dir = os.path.join(parent_dir, 'Reports', folder_name, Current_Timestamp, 'Console_Log')
            os.makedirs(log_dir, exist_ok=True)

            log_file_path = os.path.join(log_dir, f"{folder_name}.log")
            self.kpi_log_file = open(log_file_path, "a", encoding="utf-8")

            separator = f"\n{'#' * 60}\n# KPI Logging Started at {Current_Timestamp}\n{'#' * 60}\n"
            self.kpi_log_file.write(separator)
            self.kpi_log_file.flush()

            py_logger.info(f"Started logging for KPI: {kpi_label}")

        except Exception as e:
            py_logger.error(f"Failed to start KPI logging for {kpi_label}: {e}")
            raise

    def stop_kpi_logging(self):
        if self.kpi_log_file:            
            self.kpi_log_file.close()
            self.kpi_log_file = None

        py_logger.info(f"Completed execution for {self.current_kpi_label} KPI. Logging stopped.")
        print(f"{'='*35} END OF {self.current_kpi_label.upper()} KPI EXECUTION {'='*35}")
        self.current_kpi_label = None    

    def set_window_properties(self) -> None:
        """
        Sets the properties of the window, including its title, icon, size, and position.
        """
        # Set the title of the window
        self.setWindowTitle("Gen2 Platform Validation GUI Tester Tool")

        # Set the icon of the window
        self.setWindowIcon(QIcon('./GUI_Icons/KPIT_logo.ico'))

        # Get the current position of the cursor
        cursor_pos = QApplication.desktop().cursor().pos()

        # Get the list of all screens available
        screens = QApplication.screens()

        # Find the screen that contains the cursor position
        target_screen = None
        for screen in screens:
            if screen.availableGeometry().contains(cursor_pos):
                target_screen = screen
                break

        # Fallback to primary screen if none matched
        if target_screen is None:
            target_screen = QApplication.primaryScreen()

        # Get the geometry of the target screen
        screen_geometry = target_screen.availableGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        # Log the screen resolution
        # py_logger.info(f"Screen Resolution: {screen_width}x{screen_height}")

        # Calculate the window dimensions as a fraction of the screen dimensions
        window_width = int(screen_width * 0.65)  # 60% of the screen width
        window_height = int(screen_height * 0.95)  # 95% of the screen height

        # Ensure the window dimensions do not exceed the screen dimensions
        window_width = min(window_width, screen_width)
        window_height = min(window_height, screen_height)

        # Calculate the position to center the window horizontally and position at top
        x = screen_geometry.x() + (screen_width - window_width) // 2
        y = screen_geometry.y() + 50  # Position at top

        # Set the geometry and fixed size of the window
        self.setGeometry(x, y, window_width, window_height)

        py_logger.info("Gen2 PF GUI Tester Tool is Successfully Launched.")

    def create_tester_tab(self):
        layout = QVBoxLayout()

        layout.addWidget(self.create_kpis_group())

        background_colors = ["#D0CEE2", "#FFFF00", "#60A917", "#E51400"]
        label_names = ["Not Tested", "In Progress", "PASS / Configuration Done", "FAIL / Configuration Not Done"]

        layout.addWidget(self.create_test_status_group(background_colors, label_names))

        layout.addWidget(self.create_configuration_group())

        layout.addLayout(self.create_run_button_layout())

        # Create a QWidget and set the layout
        container = QWidget()
        container.setLayout(layout)

        # Create a QScrollArea and set the container as its widget
        scroll_area = QScrollArea()
        scroll_area.setWidget(container)
        scroll_area.setWidgetResizable(True)

        # Set the scroll area as the layout for tab1
        tab1_layout = QVBoxLayout()
        tab1_layout.addWidget(scroll_area)
        self.tab1.setLayout(tab1_layout)

    def create_about_tab(self):
        self.about_text = QTextEdit()
        self.about_text.setReadOnly(True)
        self.about_text.setHtml("""
            <div style="font-family:Arial; font-size:12pt;">
                <p><span style="font-size:18pt; font-weight:bold;">Automation Test Framework</span></p>
                <p>&copy; KPIT Technologies Limited</p>
                <p>Created in 2025<br>
                Software Version 1.0<br>
                All rights reserved.<br>
                KPIT Technologies Limited owns all the rights to this work.<br>
                This work shall not be copied, reproduced, used, modified or its information disclosed without the prior written authorization of KPIT Technologies Limited.</p>
            </div>
        """)

        self.tab3_layout = QVBoxLayout()
        self.tab3_layout.addWidget(self.about_text)
        self.tab3.setLayout(self.tab3_layout)

    def create_kpis_group(self):
        kpis_group = QGroupBox("KPIs")
        kpis_group.setStyleSheet(common_groupbox_style)
        kpis_layout = QVBoxLayout()

        kpi_diag_layout = QHBoxLayout()
        kpi_widget = self.create_kpi_widget()
        diag_group = self.create_diag_group()
        kpi_diag_layout.addWidget(kpi_widget)
        kpi_diag_layout.addWidget(diag_group)

        kev_xcp_layout = QHBoxLayout()
        kev_group = self.create_kev_group()
        xcp_group = self.create_xcp_group()
        kev_xcp_layout.addWidget(kev_group)
        kev_xcp_layout.addWidget(xcp_group)

        kpis_layout.addLayout(kpi_diag_layout)
        kpis_layout.addLayout(kev_xcp_layout)

        kpis_group.setLayout(kpis_layout)
        return kpis_group

    def create_kpi_widget(self):
        kpi_widget = QWidget()
        kpi_widget.setFixedHeight(380)  

        kpi_layout = QVBoxLayout()
        kpi_layout.addWidget(self.create_kpi_row("CPU and Memory Utilization"))
        kpi_layout.addWidget(self.create_kpi_row("Heap Memory"))
        kpi_layout.addWidget(self.create_kpi_row("Startup Time"))
        kpi_layout.addWidget(self.create_kpi_row("Cyclic and Turnaround Time"))
        kpi_layout.addWidget(self.create_kpi_row("Throughput and Fault Injection"))
        kpi_layout.addWidget(self.create_kpi_row("Execution Time"))
        kpi_layout.addWidget(self.create_kpi_row("Shutdown Time"))
        kpi_layout.setSpacing(0)  

        kpi_widget.setLayout(kpi_layout)
        return kpi_widget    

    def create_diag_group(self):
        diag_group = QGroupBox("Diag")
        diag_group.setStyleSheet("QGroupBox { border: 1px solid #999999; }")
        diag_group.setFixedHeight(380)

        self.Diag_checkboxes = []

        diag_layout = QVBoxLayout()
        diag_layout.addWidget(self.create_kpi_row("Positive Response", checkbox_list=self.Diag_checkboxes))
        diag_layout.addWidget(self.create_kpi_row("Negative Response", checkbox_list=self.Diag_checkboxes))
        diag_layout.addWidget(self.create_kpi_row("Diagnostic Trouble Code (DTC)", checkbox_list=self.Diag_checkboxes))
        diag_layout.addWidget(self.create_kpi_row("Reprogramming_FOTA", checkbox_list=self.Diag_checkboxes))
        diag_layout.addWidget(self.create_kpi_row("Reprogramming_Wired", checkbox_list=self.Diag_checkboxes))
        diag_layout.addWidget(self.create_kpi_row("Diag_All_KPIs", checkbox_list=self.Diag_checkboxes))

        diag_group.setLayout(diag_layout)
        return diag_group    

    def create_kev_group(self):
        kev_group = QGroupBox("KEV Generation and Movement")
        kev_group.setStyleSheet("QGroupBox { border: 1px solid #999999; }")  

        self.kev_checkboxes = []

        kev_layout = QVBoxLayout()        
        kev_layout.addWidget(self.create_kpi_row("Continuous KEV", checkbox_list=self.kev_checkboxes))
        kev_layout.addWidget(self.create_kpi_row("Event Trigger KEV", checkbox_list=self.kev_checkboxes))

        kev_group.setLayout(kev_layout)
        return kev_group

    def create_xcp_group(self):
        xcp_group = QGroupBox("XCP")
        xcp_group.setStyleSheet("QGroupBox { border: 1px solid #999999; }")
        xcp_group.setFixedHeight(200)  

        self.xcp_checkboxes = []

        xcp_layout = QVBoxLayout()
        xcp_layout.addWidget(self.create_kpi_row("RAM Monitor", checkbox_list=self.xcp_checkboxes))
        xcp_layout.addWidget(self.create_kpi_row("Event Trigger RAM Monitor", checkbox_list=self.xcp_checkboxes))
        xcp_layout.addWidget(self.create_kpi_row("APL Communication Layout", checkbox_list=self.xcp_checkboxes))
        xcp_layout.setSpacing(0)

        xcp_group.setLayout(xcp_layout)
        return xcp_group

    def create_kpi_row(self, label, checkbox_list=None):
        row_widget = QWidget()

        row_layout = QHBoxLayout()

        status_label = QLabel()
        status_label.setFixedSize(25, 25)
        status_label.setStyleSheet("background-color: #D0CEE2; border: 0.5px solid #999999;")

        row_layout.addWidget(status_label)

        checkbox = QCheckBox(label)

        row_layout.addWidget(checkbox)

        edit_button = QPushButton()
        edit_button.setFixedSize(30, 30)
        edit_button.setIcon(QIcon('./GUI_Icons/Edit_icon.ico'))
        edit_button.setIconSize(QSize(23, 23))        

        folder_button = QPushButton()
        folder_button.setFixedSize(30, 30)
        folder_button.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        folder_button.setStyleSheet(common_enabled_style + common_hover_style)
        folder_button.setEnabled(False)
        folder_button.clicked.connect(lambda: self.open_file_manager(label))

        edit_button.clicked.connect(lambda: self.on_button_click(label, edit_button, checkbox, folder_button))

        row_layout.addWidget(edit_button)
        row_layout.addWidget(folder_button)

        row_widget.setLayout(row_layout)

        self.kpi_widgets[label] = {
            'checkbox': checkbox,
            'status_label': status_label,
            'edit_button': edit_button,
            'folder_button': folder_button
        }

        checkbox.stateChanged.connect(lambda state: self.toggle_buttons(state, label, checkbox, checkbox_list, edit_button, folder_button))
        checkbox.stateChanged.connect(lambda: self.update_run_button_status())

        if checkbox_list is not None:
            checkbox_list.append(checkbox)

        return row_widget

    def create_test_status_group(self, background_colors, label_names):
        test_status_group = QGroupBox("Test Status")
        test_status_group.setStyleSheet(common_groupbox_style)
        test_status_group.setFixedHeight(85)

        test_status_layout = QHBoxLayout()

        for i in range(len(background_colors)):
            row_widget = QWidget()

            row_layout = QHBoxLayout()

            status = QLabel()
            status.setFixedSize(40, 30)
            status.setStyleSheet(f"background-color: {background_colors[i]}; border: 0.5px solid #999999;")

            status_label = QLabel(label_names[i])
            status_label.setFixedHeight(30)

            row_layout.addWidget(status)
            row_layout.addWidget(status_label)

            row_widget.setLayout(row_layout)

            test_status_layout.addWidget(row_widget)

        test_status_group.setLayout(test_status_layout)
        return test_status_group    

    def create_configuration_group(self):
        configuration_group = QGroupBox('Configuration')
        configuration_group.setStyleSheet(common_groupbox_style)

        configuration_layout = self.create_configuration_layout()

        configuration_group.setLayout(configuration_layout)
        return configuration_group    

    def create_configuration_layout(self):
        configuration_layout = QVBoxLayout()

        configuration_status_layout = self.create_configuration_status_layout()

        ecu_selection_login_credential_layout = self.create_ecu_selection_login_credential_layout()

        configuration_layout.addLayout(configuration_status_layout)
        configuration_layout.addLayout(ecu_selection_login_credential_layout)
        return configuration_layout    

    def create_configuration_status_layout(self):
        configuration_status_layout = QHBoxLayout()

        self.configuration_status_label = QLabel()
        self.configuration_status_label.setFixedSize(30, 30)
        self.configuration_status_label.setStyleSheet("background-color: #E51400; border: 1px solid #999999;")

        configuration_status_layout.addStretch()
        configuration_status_layout.addWidget(self.configuration_status_label)
        return configuration_status_layout    

    def create_ecu_selection_login_credential_layout(self):
        ecu_select_login_credential_layout = QHBoxLayout()

        ecu_selection_group = self.create_ecu_selection_group()
        login_credential_group = self.create_login_credential_group()

        ecu_select_login_credential_layout.addWidget(ecu_selection_group)
        ecu_select_login_credential_layout.addWidget(login_credential_group)
        return ecu_select_login_credential_layout    

    def create_ecu_selection_group(self):
        ecu_selection_group = QGroupBox('ECU Selection')
        ecu_selection_group.setFixedWidth(450)
        ecu_selection_group.setStyleSheet(common_groupbox_style)

        ecu_selection_layout = self.create_ecu_selection_layout()

        ecu_selection_group.setLayout(ecu_selection_layout)
        return ecu_selection_group    

    def create_ecu_selection_layout(self):
        ecu_selection_layout = QVBoxLayout()

        padas_group = self.create_padas_group()

        elite_group = self.create_elite_group()

        ignition_status_group = self.create_ignition_status_group()

        ecu_selection_layout.addWidget(padas_group)
        ecu_selection_layout.addWidget(elite_group)
        ecu_selection_layout.addWidget(ignition_status_group)
        return ecu_selection_layout    

    def create_padas_group(self):
        padas_group = QGroupBox('PADAS')
        padas_group.setStyleSheet(common_groupbox_style)
        padas_group.setFixedHeight(80)

        padas_layout = QVBoxLayout()

        self.padas_checkbox = QCheckBox('R-Car S4 (PADAS)')
        self.padas_checkbox.stateChanged.connect(self.update_checkbox_states)

        padas_layout.addWidget(self.padas_checkbox)

        padas_group.setLayout(padas_layout)
        return padas_group        

    def create_elite_group(self):
        elite_group = QGroupBox('Elite')
        elite_group.setStyleSheet(common_groupbox_style)

        elite_layout = QVBoxLayout()

        self.RCar_checkbox = QCheckBox('R-Car S4')
        self.RCar_checkbox.stateChanged.connect(self.update_checkbox_states)
        self.SoC0_checkbox = QCheckBox('Qualcomm SoC0')
        self.SoC0_checkbox.stateChanged.connect(self.update_checkbox_states)
        self.SoC1_checkbox = QCheckBox('Qualcomm SoC1')
        self.SoC1_checkbox.stateChanged.connect(self.update_checkbox_states)

        elite_layout.addWidget(self.RCar_checkbox)
        elite_layout.addWidget(self.SoC0_checkbox)
        elite_layout.addWidget(self.SoC1_checkbox)

        elite_group.setLayout(elite_layout)
        return elite_group        

    def create_ignition_status_group(self):
        ignition_status_group = QGroupBox('Ignition Status')
        ignition_status_group.setStyleSheet(common_groupbox_style)

        ignition_status_layout = QVBoxLayout()

        relay_layout = self.create_relay_layout()

        IG_button_layout = self.create_IG_button_layout()

        ignition_status_layout.addLayout(relay_layout)
        ignition_status_layout.addLayout(IG_button_layout)

        ignition_status_group.setLayout(ignition_status_layout)
        return ignition_status_group    

    def create_relay_layout(self):
        relay_layout = QFormLayout()
        relay_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        relay_port_label = QLabel('Relay Serial Port')

        relay_port_layout = QHBoxLayout()

        self.relay_port_input = QLineEdit()
        self.relay_port_input.setObjectName("relay_port_input")
        self.relay_port_input.setFixedWidth(80)
        self.relay_port_input.textChanged.connect(lambda: self.update_button_states())

        relay_port_unit_label = QLabel('(e.g., COM1 or COM4)')
        relay_port_unit_label.setStyleSheet("font-size: 12px;")

        relay_port_layout.addWidget(self.relay_port_input)
        relay_port_layout.addWidget(relay_port_unit_label)

        relay_layout.addRow(relay_port_label, relay_port_layout)

        relay_baudrate_layout = QHBoxLayout()

        relay_baudrate_label = QLabel('Relay Baudrate')

        # QIntValidator only supports 32-bit signed integers (qint32)
        # So the maximum value must be within the range: -2,147,483,648 to 2,147,483,647
        # Here, we set the minimum value to 1
        # and the maximum value to 2147483647 (maximum for qint32)
        max_int = 2147483647
        validator = QIntValidator(1, max_int)

        # Use the "C" locale to ensure consistent number formatting
        # This avoids issues like commas or periods being interpreted as thousands separators
        locale = QLocale("C")
        validator.setLocale(locale)

        self.relay_baudrate_input = QLineEdit()
        # Apply the validator to the QLineEdit      
        self.relay_baudrate_input.setValidator(validator)
        self.relay_baudrate_input.setFixedWidth(80)
        self.relay_baudrate_input.textChanged.connect(lambda: self.update_button_states())

        relay_baudrate_unit_label = QLabel('(e.g., 9600 or 115200 bps)')
        relay_baudrate_unit_label.setStyleSheet("font-size: 12px;")

        relay_baudrate_layout.addWidget(self.relay_baudrate_input)
        relay_baudrate_layout.addWidget(relay_baudrate_unit_label)

        relay_layout.addRow(relay_baudrate_label, relay_baudrate_layout)
        return relay_layout        

    def create_IG_button_layout(self):
        IG_button_layout = QHBoxLayout()

        self.IG_OFF_button = QPushButton('IG OFF')
        # self.IG_OFF_button.setFixedSize(150,35)
        self.IG_OFF_button.setStyleSheet(common_enabled_style + common_hover_style)
        self.IG_OFF_button.clicked.connect(self.IG_ON_Off)
        self.IG_OFF_button.setEnabled(False)

        self.IG_ON_button = QPushButton('IG ON')
        # self.IG_ON_button.setFixedSize(150, 35)
        self.IG_ON_button.setStyleSheet(common_enabled_style + common_hover_style)
        self.IG_ON_button.clicked.connect(self.IG_ON_Off)
        self.IG_ON_button.setEnabled(False)

        IG_button_layout.addWidget(self.IG_OFF_button)
        IG_button_layout.addWidget(self.IG_ON_button)
        return IG_button_layout    

    def create_login_credential_group(self):
        login_credential_group = QGroupBox('Login Credentials')
        login_credential_group.setStyleSheet(common_groupbox_style)

        login_credential_layout = self.create_login_credential_layout()

        login_credential_group.setLayout(login_credential_layout)
        return login_credential_group    

    def create_login_credential_layout(self):
        login_credential_layout = QVBoxLayout()

        Rcar_group = self.create_Rcar_group()
        SoC0_group = self.create_SoC0_group()
        SoC1_group = self.create_SoC1_group()

        login_credential_layout.addWidget(Rcar_group)
        login_credential_layout.addWidget(SoC0_group)
        login_credential_layout.addWidget(SoC1_group)
        return login_credential_layout    

    def create_Rcar_group(self):
        Rcar_group = QGroupBox('R-Car S4')
        Rcar_group.setStyleSheet(common_groupbox_style)

        Rcar_layout = self.create_Rcar_layout()

        Rcar_group.setLayout(Rcar_layout)
        return Rcar_group    

    def create_Rcar_layout(self):
        Rcar_layout = QHBoxLayout()

        Rcar_telent_layout = self.create_Rcar_telent_layout()

        Rcar_FTP_layout = self.create_Rcar_FTP_layout()

        Rcar_layout.addLayout(Rcar_telent_layout)
        Rcar_layout.addLayout(Rcar_FTP_layout)
        return Rcar_layout    

    def create_Rcar_telent_layout(self):
        Rcar_telent_layout = QFormLayout()
        Rcar_telent_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.Rcar_IP_label = QLabel('R-Car IP Address')
        self.Rcar_IP_label.setEnabled(False)

        # Create four QLineEdit fields for each IP octet
        self.rcar_ip1 = QLineEdit()
        self.rcar_ip2 = QLineEdit()
        self.rcar_ip3 = QLineEdit()
        self.rcar_ip4 = QLineEdit()

        for ip in [self.rcar_ip1, self.rcar_ip2, self.rcar_ip3, self.rcar_ip4]:
            ip.setFixedWidth(40)
            ip.setMaxLength(3)
            ip.setValidator(CustomIntValidator(0, 999))
            ip.setAlignment(Qt.AlignCenter)
            ip.setEnabled(False)
            ip.textChanged.connect(self.update_button_states)

        dot_style = "font-size: 20px;"  # Define style for dots

        ip_layout = QHBoxLayout()
        ip_layout.setSpacing(0)

        # Add first IP part
        ip_layout.addWidget(self.rcar_ip1)

        # Add dot and next IP parts
        dot1 = QLabel(".")
        dot1.setStyleSheet(dot_style)
        ip_layout.addWidget(dot1)

        ip_layout.addWidget(self.rcar_ip2)

        dot2 = QLabel(".")
        dot2.setStyleSheet(dot_style)
        ip_layout.addWidget(dot2)

        ip_layout.addWidget(self.rcar_ip3)

        dot3 = QLabel(".")
        dot3.setStyleSheet(dot_style)
        ip_layout.addWidget(dot3)

        ip_layout.addWidget(self.rcar_ip4)

        # Add stretch at the end
        ip_layout.addStretch()

        # Add to form layout
        Rcar_telent_layout.addRow(self.Rcar_IP_label, ip_layout)

        self.Rcar_telnet_username_label = QLabel('Telnet Username')
        self.Rcar_telnet_username_label.setEnabled(False)

        self.Rcar_telnet_username_input = QLineEdit()
        self.Rcar_telnet_username_input.setObjectName('Rcar_telnet_username_input')
        self.Rcar_telnet_username_input.setFixedWidth(180)
        self.Rcar_telnet_username_input.setPlaceholderText('Enter Username')
        self.Rcar_telnet_username_input.textChanged.connect(lambda: self.update_button_states())
        self.Rcar_telnet_username_input.setEnabled(False)

        Rcar_telent_layout.addRow(self.Rcar_telnet_username_label, self.Rcar_telnet_username_input)

        self.Rcar_telnet_password_label = QLabel('Telnet Password')
        self.Rcar_telnet_password_label.setEnabled(False)

        self.Rcar_telnet_password_input = QLineEdit()
        self.Rcar_telnet_password_input.setObjectName('Rcar_telnet_password_input')
        self.Rcar_telnet_password_input.setFixedWidth(180)  
        self.Rcar_telnet_password_input.setPlaceholderText('Enter Password')
        self.Rcar_telnet_password_input.textChanged.connect(lambda: self.update_button_states())
        self.Rcar_telnet_password_input.setEnabled(False)

        Rcar_telent_layout.addRow(self.Rcar_telnet_password_label, self.Rcar_telnet_password_input)
        return Rcar_telent_layout    

    def create_Rcar_FTP_layout(self):
        Rcar_FTP_layout = QFormLayout()
        Rcar_FTP_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.Rcar_FTP_username_label = QLabel('FTP Username')
        self.Rcar_FTP_username_label.setEnabled(False)

        self.Rcar_FTP_username_input = QLineEdit()
        self.Rcar_FTP_username_input.setObjectName('Rcar_FTP_username_input')
        self.Rcar_FTP_username_input.setFixedWidth(180)
        self.Rcar_FTP_username_input.setPlaceholderText('Enter Username')
        self.Rcar_FTP_username_input.textChanged.connect(lambda: self.update_button_states())
        self.Rcar_FTP_username_input.setEnabled(False)

        Rcar_FTP_layout.addRow(self.Rcar_FTP_username_label, self.Rcar_FTP_username_input)

        self.Rcar_FTP_password_label = QLabel('FTP Password')
        self.Rcar_FTP_password_label.setEnabled(False)

        self.Rcar_FTP_password_input = QLineEdit()
        self.Rcar_FTP_password_input.setObjectName('Rcar_FTP_password_input')
        self.Rcar_FTP_password_input.setFixedWidth(180)
        self.Rcar_FTP_password_input.setPlaceholderText('Enter Password')
        self.Rcar_FTP_password_input.textChanged.connect(lambda: self.update_button_states())
        self.Rcar_FTP_password_input.setEnabled(False)

        Rcar_FTP_layout.addRow(self.Rcar_FTP_password_label, self.Rcar_FTP_password_input)
        return Rcar_FTP_layout    

    def create_SoC0_group(self):
        SoC0_group = QGroupBox('SoC0')
        SoC0_group.setStyleSheet(common_groupbox_style)

        SoC0_layout = self.create_SoC0_layout()

        SoC0_group.setLayout(SoC0_layout)
        return SoC0_group    

    def create_SoC0_layout(self):
        SoC0_layout = QHBoxLayout()

        SoC0_telent_layout = self.create_SoC0_telent_layout()

        SoC0_FTP_layout = self.create_SoC0_FTP_layout()

        SoC0_layout.addLayout(SoC0_telent_layout)
        SoC0_layout.addLayout(SoC0_FTP_layout)
        return SoC0_layout    

    def create_SoC0_telent_layout(self):
        SoC0_telent_layout = QFormLayout()
        SoC0_telent_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.SoC0_IP_label = QLabel('SoC0 IP Address')
        self.SoC0_IP_label.setEnabled(False)

        # Create four QLineEdit fields for each IP octet
        self.soc0_ip1 = QLineEdit()
        self.soc0_ip2 = QLineEdit()
        self.soc0_ip3 = QLineEdit()
        self.soc0_ip4 = QLineEdit()

        for ip in [self.soc0_ip1, self.soc0_ip2, self.soc0_ip3, self.soc0_ip4]:
            ip.setFixedWidth(40)
            ip.setMaxLength(3)
            ip.setValidator(CustomIntValidator(0, 999))
            ip.setAlignment(Qt.AlignCenter)
            ip.setEnabled(False)
            ip.textChanged.connect(self.update_button_states)

        dot_style = "font-size: 20px;"  # Define style for dots

        ip_layout = QHBoxLayout()
        ip_layout.setSpacing(0)

        # Add first IP part
        ip_layout.addWidget(self.soc0_ip1)

        # Add dot and next IP parts
        dot1 = QLabel(".")
        dot1.setStyleSheet(dot_style)
        ip_layout.addWidget(dot1)

        ip_layout.addWidget(self.soc0_ip2)

        dot2 = QLabel(".")
        dot2.setStyleSheet(dot_style)
        ip_layout.addWidget(dot2)

        ip_layout.addWidget(self.soc0_ip3)

        dot3 = QLabel(".")
        dot3.setStyleSheet(dot_style)
        ip_layout.addWidget(dot3)

        ip_layout.addWidget(self.soc0_ip4)

        # Add stretch at the end
        ip_layout.addStretch()

        # Add to form layout
        SoC0_telent_layout.addRow(self.SoC0_IP_label, ip_layout)

        self.SoC0_telnet_username_label = QLabel('Telnet Username')
        self.SoC0_telnet_username_label.setEnabled(False)

        self.SoC0_telnet_username_input = QLineEdit()
        self.SoC0_telnet_username_input.setObjectName('SoC0_telnet_username_input')
        self.SoC0_telnet_username_input.setFixedWidth(180)
        self.SoC0_telnet_username_input.setPlaceholderText('Enter Username')
        self.SoC0_telnet_username_input.textChanged.connect(lambda: self.update_button_states())
        self.SoC0_telnet_username_input.setEnabled(False)

        SoC0_telent_layout.addRow(self.SoC0_telnet_username_label, self.SoC0_telnet_username_input)

        self.SoC0_telnet_password_label = QLabel('Telnet Password')
        self.SoC0_telnet_password_label.setEnabled(False)

        self.SoC0_telnet_password_input = QLineEdit()
        self.SoC0_telnet_password_input.setObjectName('SoC0_telnet_password_input')
        self.SoC0_telnet_password_input.setFixedWidth(180)
        self.SoC0_telnet_password_input.setPlaceholderText('Enter Password')
        self.SoC0_telnet_password_input.textChanged.connect(lambda: self.update_button_states())
        self.SoC0_telnet_password_input.setEnabled(False)

        SoC0_telent_layout.addRow(self.SoC0_telnet_password_label, self.SoC0_telnet_password_input)
        return SoC0_telent_layout    

    def create_SoC0_FTP_layout(self):
        SoC0_FTP_layout = QFormLayout()
        SoC0_FTP_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.SoC0_FTP_username_label = QLabel('FTP Username')
        self.SoC0_FTP_username_label.setEnabled(False)

        self.SoC0_FTP_username_input = QLineEdit()
        self.SoC0_FTP_username_input.setObjectName('SoC0_FTP_username_input')
        self.SoC0_FTP_username_input.setFixedWidth(180)
        self.SoC0_FTP_username_input.setPlaceholderText('Enter Username')
        self.SoC0_FTP_username_input.textChanged.connect(lambda: self.update_button_states())
        self.SoC0_FTP_username_input.setEnabled(False)

        SoC0_FTP_layout.addRow(self.SoC0_FTP_username_label, self.SoC0_FTP_username_input)

        self.SoC0_FTP_password_label = QLabel('FTP Password')
        self.SoC0_FTP_password_label.setEnabled(False)

        self.SoC0_FTP_password_input = QLineEdit()
        self.SoC0_FTP_password_input.setObjectName('SoC0_FTP_password_input')
        self.SoC0_FTP_password_input.setFixedWidth(180)
        self.SoC0_FTP_password_input.setPlaceholderText('Enter Password')
        self.SoC0_FTP_password_input.textChanged.connect(lambda: self.update_button_states())
        self.SoC0_FTP_password_input.setEnabled(False)

        SoC0_FTP_layout.addRow(self.SoC0_FTP_password_label, self.SoC0_FTP_password_input)
        return SoC0_FTP_layout    

    def create_SoC1_group(self):
        SoC1_group = QGroupBox('SoC1')
        SoC1_group.setStyleSheet(common_groupbox_style)

        SoC1_layout = self.create_SoC1_layout()

        SoC1_group.setLayout(SoC1_layout)
        return SoC1_group    

    def create_SoC1_layout(self):
        SoC1_layout = QHBoxLayout()

        SoC1_telnet_layout = self.create_SoC1_telnet_layout()

        SoC1_FTP_layout = self.create_SoC1_FTP_layout()

        SoC1_layout.addLayout(SoC1_telnet_layout)
        SoC1_layout.addLayout(SoC1_FTP_layout)
        return SoC1_layout    

    def create_SoC1_telnet_layout(self):
        SoC1_telent_layout = QFormLayout()
        SoC1_telent_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.SoC1_IP_label = QLabel('SoC1 IP Address')
        self.SoC1_IP_label.setEnabled(False)

        # Create four QLineEdit fields for each IP octet
        self.soc1_ip1 = QLineEdit()
        self.soc1_ip2 = QLineEdit()
        self.soc1_ip3 = QLineEdit()
        self.soc1_ip4 = QLineEdit()

        for ip in [self.soc1_ip1, self.soc1_ip2, self.soc1_ip3, self.soc1_ip4]:
            ip.setFixedWidth(40)
            ip.setMaxLength(3)
            ip.setValidator(CustomIntValidator(0, 999))
            ip.setAlignment(Qt.AlignCenter)
            ip.setEnabled(False)
            ip.textChanged.connect(self.update_button_states)

        dot_style = "font-size: 20px;"  # Define style for dots

        ip_layout = QHBoxLayout()
        ip_layout.setSpacing(0)

        # Add first IP part
        ip_layout.addWidget(self.soc1_ip1)

        # Add dot and next IP parts
        dot1 = QLabel(".")
        dot1.setStyleSheet(dot_style)
        ip_layout.addWidget(dot1)

        ip_layout.addWidget(self.soc1_ip2)

        dot2 = QLabel(".")
        dot2.setStyleSheet(dot_style)
        ip_layout.addWidget(dot2)

        ip_layout.addWidget(self.soc1_ip3)

        dot3 = QLabel(".")
        dot3.setStyleSheet(dot_style)
        ip_layout.addWidget(dot3)

        ip_layout.addWidget(self.soc1_ip4)

        # Add stretch at the end
        ip_layout.addStretch()

        # Add to form layout
        SoC1_telent_layout.addRow(self.SoC1_IP_label, ip_layout)

        self.SoC1_telnet_username_label = QLabel('Telnet Username')
        self.SoC1_telnet_username_label.setEnabled(False)

        self.SoC1_telnet_username_input = QLineEdit()
        self.SoC1_telnet_username_input.setObjectName('SoC1_telnet_username_input')
        self.SoC1_telnet_username_input.setFixedWidth(180)
        self.SoC1_telnet_username_input.setPlaceholderText('Enter Username')
        self.SoC1_telnet_username_input.textChanged.connect(lambda: self.update_button_states())
        self.SoC1_telnet_username_input.setEnabled(False)

        SoC1_telent_layout.addRow(self.SoC1_telnet_username_label, self.SoC1_telnet_username_input)

        self.SoC1_telnet_password_label = QLabel('Telnet Password')
        self.SoC1_telnet_password_label.setEnabled(False)

        self.SoC1_telnet_password_input = QLineEdit()
        self.SoC1_telnet_password_input.setObjectName('SoC1_telnet_password_input')
        self.SoC1_telnet_password_input.setFixedWidth(180)
        self.SoC1_telnet_password_input.setPlaceholderText('Enter Password')
        self.SoC1_telnet_password_input.textChanged.connect(lambda: self.update_button_states())
        self.SoC1_telnet_password_input.setEnabled(False)

        SoC1_telent_layout.addRow(self.SoC1_telnet_password_label, self.SoC1_telnet_password_input)
        return SoC1_telent_layout    

    def create_SoC1_FTP_layout(self):
        SoC1_FTP_layout = QFormLayout()
        SoC1_FTP_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.SoC1_FTP_username_label = QLabel('FTP Username')
        self.SoC1_FTP_username_label.setEnabled(False)

        self.SoC1_FTP_username_input = QLineEdit()
        self.SoC1_FTP_username_input.setObjectName('SoC1_FTP_username_input')
        self.SoC1_FTP_username_input.setFixedWidth(180)
        self.SoC1_FTP_username_input.setPlaceholderText('Enter Username')
        self.SoC1_FTP_username_input.textChanged.connect(lambda: self.update_button_states())
        self.SoC1_FTP_username_input.setEnabled(False)

        SoC1_FTP_layout.addRow(self.SoC1_FTP_username_label, self.SoC1_FTP_username_input)

        self.SoC1_FTP_password_label = QLabel('FTP Password')
        self.SoC1_FTP_password_label.setEnabled(False)

        self.SoC1_FTP_password_input = QLineEdit()
        self.SoC1_FTP_password_input.setObjectName('SoC1_FTP_password_input')
        self.SoC1_FTP_password_input.setFixedWidth(180)
        self.SoC1_FTP_password_input.setPlaceholderText('Enter Password')
        self.SoC1_FTP_password_input.textChanged.connect(lambda: self.update_button_states())
        self.SoC1_FTP_password_input.setEnabled(False)

        SoC1_FTP_layout.addRow(self.SoC1_FTP_password_label, self.SoC1_FTP_password_input)
        return SoC1_FTP_layout

    def create_run_button_layout(self):
        run_button_layout = QHBoxLayout()

        self.run_button = QPushButton(' RUN')
        self.run_button.setFixedSize(180, 50)
        self.run_button.setIcon(QIcon('./GUI_Icons/RUN_icon.ico'))
        self.run_button.setIconSize(QSize(30, 30))
        self.run_button.setWindowIconText(None)  # Icon beside text
        self.run_button.setStyleSheet("QPushButton:enabled { font-size: 30px; }" + common_enabled_style + common_hover_style)
        self.run_button.clicked.connect(self.on_run_button_click)
        self.run_button.setEnabled(False)

        self.stop_KPIs_execution_button = QPushButton(' STOP')
        self.stop_KPIs_execution_button.setFixedSize(180, 50)
        self.stop_KPIs_execution_button.setStyleSheet("QPushButton:enabled { font-size: 30px; }" + common_enabled_style + common_hover_style)
        self.stop_KPIs_execution_button.setIcon(QIcon('./GUI_Icons/STOP_icon.ico'))
        self.stop_KPIs_execution_button.setIconSize(QSize(30, 30))
        self.stop_KPIs_execution_button.setWindowIconText(None)  # Icon beside text
        self.stop_KPIs_execution_button.clicked.connect(lambda: self.stop_worker_thread("Stopping the KPIs execution..."))
        self.stop_KPIs_execution_button.setEnabled(False)

        run_button_layout.addStretch()
        run_button_layout.addWidget(self.run_button)
        run_button_layout.addWidget(self.stop_KPIs_execution_button)
        run_button_layout.addStretch()
        return run_button_layout

    def set_RCAR_ip_address(self, ip_address: str):
        """
        Sets the RCAR IP address fields based on the provided IP string.
        If the IP is invalid, defaults to 192.168.1.5.

        Args:
            ip_address (str): The IP address in dotted-decimal format (e.g., "192.168.1.5").
        """

        try:
            # Split the IP address into parts and convert each part to an integer
            parts = [int(part) for part in ip_address.split(".")]

            # Validate: IP must have exactly 4 parts and each part should be in range 0-255
            if len(parts) == 4 and all(0 <= part <= 255 for part in parts):
                # Convert back to strings for setting text fields
                ip_values = [str(part) for part in parts]
            else:
                # If validation fails, raise an error to trigger fallback
                raise ValueError

        except (ValueError, AttributeError):
            # Fallback IP address if input is invalid or not a string
            ip_values = ["192", "168", "1", "5"]

        # Set the text fields with the validated or fallback IP values
        self.rcar_ip1.setText(ip_values[0])
        self.rcar_ip2.setText(ip_values[1])
        self.rcar_ip3.setText(ip_values[2])
        self.rcar_ip4.setText(ip_values[3])

    def set_SoC0_ip_address(self, ip_address: str):
        """
        Sets the SoC0 IP address fields based on the provided IP string.
        If the IP is invalid, no changes are made (or optionally set defaults).

        Args:
            ip_address (str): The IP address in dotted-decimal format (e.g., "192.168.1.3").
        """

        try:
            # Split the IP address into parts and convert each part to an integer
            parts = [int(part) for part in ip_address.split(".")]

            # Validate: IP must have exactly 4 parts and each part should be in range 0-255
            if len(parts) == 4 and all(0 <= part <= 255 for part in parts):
                # Convert back to strings for setting text fields
                ip_values = [str(part) for part in parts]
            else:
                raise ValueError  # Trigger fallback if validation fails

        except (ValueError, AttributeError):
            # Fallback IP address if input is invalid or not a string
            ip_values = ["192", "168", "1", "3"]  # Example default for SoC0

        # Set the text fields with the validated or fallback IP values
        self.soc0_ip1.setText(ip_values[0])
        self.soc0_ip2.setText(ip_values[1])
        self.soc0_ip3.setText(ip_values[2])
        self.soc0_ip4.setText(ip_values[3])

    def set_SoC1_ip_address(self, ip_address: str):
        """
        Sets the SoC1 IP address fields based on the provided IP string.
        If the IP is invalid, no changes are made (or optionally set defaults).

        Args:
            ip_address (str): The IP address in dotted-decimal format (e.g., "192.168.1.58").
        """

        try:
            # Split the IP address into parts and convert each part to an integer
            parts = [int(part) for part in ip_address.split(".")]

            # Validate: IP must have exactly 4 parts and each part should be in range 0-255
            if len(parts) == 4 and all(0 <= part <= 255 for part in parts):
                # Convert back to strings for setting text fields
                ip_values = [str(part) for part in parts]
            else:
                raise ValueError  # Trigger fallback if validation fails

        except (ValueError, AttributeError):
            # Fallback IP address if input is invalid or not a string
            ip_values = ["192", "168", "1", "58"]  # Example default for SoC1

        # Set the text fields with the validated or fallback IP values
        self.soc1_ip1.setText(ip_values[0])
        self.soc1_ip2.setText(ip_values[1])
        self.soc1_ip3.setText(ip_values[2])
        self.soc1_ip4.setText(ip_values[3])

    def read_ECU_configuration(self):
        try:
            with open('ECU_Config.json', 'r', encoding="utf-8") as file:
                ecu_config = json.load(file)

            if 'RCAR' in ecu_config:
                self.set_RCAR_ip_address(ecu_config['RCAR']['IP'])
                self.Rcar_telnet_username_input.setText(ecu_config['RCAR']['telnet_username'])
                self.Rcar_telnet_password_input.setText(ecu_config['RCAR']['telnet_password'])
                self.Rcar_FTP_username_input.setText(ecu_config['RCAR']['FTP_username'])
                self.Rcar_FTP_password_input.setText(ecu_config['RCAR']['FTP_password'])

            if 'SoC0' in ecu_config:
                self.set_SoC0_ip_address(ecu_config['SoC0']['IP'])
                self.SoC0_telnet_username_input.setText(ecu_config['SoC0']['telnet_username'])
                self.SoC0_telnet_password_input.setText(ecu_config['SoC0']['telnet_password'])
                self.SoC0_FTP_username_input.setText(ecu_config['SoC0']['FTP_username'])
                self.SoC0_FTP_password_input.setText(ecu_config['SoC0']['FTP_password'])

            if 'SoC1' in ecu_config:
                self.set_SoC1_ip_address(ecu_config['SoC1']['IP'])
                self.SoC1_telnet_username_input.setText(ecu_config['SoC1']['telnet_username'])
                self.SoC1_telnet_password_input.setText(ecu_config['SoC1']['telnet_password'])
                self.SoC1_FTP_username_input.setText(ecu_config['SoC1']['FTP_username'])
                self.SoC1_FTP_password_input.setText(ecu_config['SoC1']['FTP_password'])

            if 'Relay' in ecu_config:
                self.relay_port_input.setText(ecu_config['Relay']['relay_port'])
                self.relay_baudrate_input.setText(str(ecu_config['Relay']['relay_baudrate']))

        except FileNotFoundError:
            pass
        except json.JSONDecodeError:
            py_logger.error("Invalid JSON format")

    def get_RCAR_ip_address(self):
        """
        Retrieves the RCAR IP address from the UI fields and returns it as a string.
        If any part is invalid, returns an empty string.

        Returns:
            str: The IP address in dotted-decimal format (e.g., "192.168.1.5") or an empty string if invalid.
        """

        # Collect the four IP parts from the UI text fields
        ip_parts = [
            self.rcar_ip1.text(),
            self.rcar_ip2.text(),
            self.rcar_ip3.text(),
            self.rcar_ip4.text()
        ]

        # Validate each part:
        # - Must be numeric (isdigit())
        # - Must be in range 0 to 999 (though typical IP range is 0-255)
        # NOTE: Using 999 here might be intentional for UI flexibility, but usually 255 is correct for IPv4.
        if all(part.isdigit() and 0 <= int(part) <= 999 for part in ip_parts):
            # If valid, join the parts with dots to form the IP address string
            return ".".join(ip_parts)

        # If validation fails, return an empty string to indicate invalid IP
        return ""

    def get_SoC0_ip_address(self):
        """
        Retrieves the SoC0 IP address from the UI fields and returns it as a string.
        If any part is invalid, returns an empty string.

        Returns:
            str: The IP address in dotted-decimal format (e.g., "192.168.1.3") or an empty string if invalid.
        """

        # Collect the four IP parts from the SoC0 UI text fields
        ip_parts = [
            self.soc0_ip1.text(),
            self.soc0_ip2.text(),
            self.soc0_ip3.text(),
            self.soc0_ip4.text()
        ]

        # Validate each part:
        # - Must be numeric (isdigit())
        # - Must be in range 0 to 999 (though typical IPv4 range is 0-255)
        # NOTE: If 999 is intentional for UI flexibility, document why.
        if all(part.isdigit() and 0 <= int(part) <= 999 for part in ip_parts):
            # If valid, join the parts with dots to form the IP address string
            return ".".join(ip_parts)

        # If validation fails, return an empty string to indicate invalid IP
        return ""

    def get_SoC1_ip_address(self):
        """
        Retrieves the SoC1 IP address from the UI fields and returns it as a string.
        If any part is invalid, returns an empty string.

        Returns:
            str: The IP address in dotted-decimal format (e.g., "192.168.1.58") or an empty string if invalid.
        """

        # Collect the four IP parts from the SoC1 UI text fields
        ip_parts = [
            self.soc1_ip1.text(),
            self.soc1_ip2.text(),
            self.soc1_ip3.text(),
            self.soc1_ip4.text()
        ]

        # Validate each part:
        # - Must be numeric (isdigit())
        # - Must be in range 0 to 999 (though typical IPv4 range is 0-255)
        # NOTE: If 999 is intentional for UI flexibility, document why.
        if all(part.isdigit() and 0 <= int(part) <= 999 for part in ip_parts):
            # If valid, join the parts with dots to form the IP address string
            return ".".join(ip_parts)

        # If validation fails, return an empty string to indicate invalid IP
        return ""

    def Write_ECU_Configuration(self):
        try:
            ecu_input_fields = {}

            ecu_input_fields['RCAR'] = {
                'IP': self.get_RCAR_ip_address(),
                'telnet_username': self.Rcar_telnet_username_input.text(),
                'telnet_password': self.Rcar_telnet_password_input.text(),
                'FTP_username': self.Rcar_FTP_username_input.text(),
                'FTP_password': self.Rcar_FTP_password_input.text()
            }

            ecu_input_fields['SoC0'] = {
                'IP': self.get_SoC0_ip_address(),
                'telnet_username': self.SoC0_telnet_username_input.text(),
                'telnet_password': self.SoC0_telnet_password_input.text(),
                'FTP_username': self.SoC0_FTP_username_input.text(),
                'FTP_password': self.SoC0_FTP_password_input.text()
            }

            ecu_input_fields['SoC1'] = {
                'IP': self.get_SoC1_ip_address(),
                'telnet_username': self.SoC1_telnet_username_input.text(),
                'telnet_password': self.SoC1_telnet_password_input.text(),
                'FTP_username': self.SoC1_FTP_username_input.text(),
                'FTP_password': self.SoC1_FTP_password_input.text()
            }  

            ecu_input_fields['Relay'] = {
                'relay_port': self.relay_port_input.text(),
                'relay_baudrate': int(self.relay_baudrate_input.text())
            }
            with open('ECU_Config.json', 'w', encoding="utf-8") as file:
                json.dump(ecu_input_fields, file, indent=4)
        except Exception as e:
            print("Error writing to file: ", str(e))

    def get_dialog_instance(self, label, checkbox):
        try:
            # Determine if label is a diag type
            is_diag = label in diag_labels

            # Get module and class name from mapping
            module_name, class_name = config_dialogs.get(label) if not is_diag else config_dialogs.get("Diag")

            if not module_name or not class_name:
                py_logger.warning(f"No dialog mapping found for label: '{label}'")
                return None

            # Dynamically import module and get class
            module = importlib.import_module(module_name)
            dialog_class = getattr(module, class_name)

            # Instantiate and return dialog
            return dialog_class(self, label, checkbox.isChecked()) if is_diag else dialog_class(self, checkbox.isChecked())

        except ModuleNotFoundError:
            py_logger.error(f"Module '{module_name}' not found for label '{label}'.")
        except AttributeError:
            py_logger.error(f"Class '{class_name}' not found in module '{module_name}' for label '{label}'.")
        except Exception as e:
            py_logger.error(f"Failed to load dialog for '{label}': {e}")

        return None

    def on_button_click(self, label, edit_button, checkbox, folder_button):
        try:
            self.setEnabled(False)

            dialog = self.get_dialog_instance(label, checkbox)

            if dialog:
                dialog.setModal(True)
                dialog.exec_()
            else:
                self.setEnabled(True)
                return

            self.setEnabled(True)
            self.is_any_ecu_selected()
            self.check_KPIs_config(label, edit_button, checkbox, folder_button)

            if not self.is_test_in_progress:
                self.update_run_button_status()

        except Exception as e:
            py_logger.error(traceback.format_exc())
            self.setEnabled(True)

    def open_file_manager(self, label):
        try:
            parent_dir = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
            path = os.path.join(parent_dir, 'Reports', folder_names[label])
            os.makedirs(path, exist_ok=True)

            if os.path.exists(path):
                if os.name == 'nt': # Windows
                    os.startfile(path)
                elif os.name == 'posix': # macOS or Linux
                    os.system(f'open "{path}"' if sys.platform == 'darwin' else f'xdg-open "{path}"')
            else:
                QMessageBox.warning(self, "Path Not Found", f"The path '{path}' does not exist.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"An error occurred: {str(e)}")    

    def toggle_buttons(self, state, label, current_checkbox, checkbox_list, edit_button, folder_button):
        try:
            enabled = state == Qt.Checked

            # folder_button.setEnabled(enabled)

            if enabled:            
                if checkbox_list is not None:
                    for checkbox in checkbox_list:
                        if checkbox != current_checkbox:
                            checkbox.setEnabled(False)
            else:
                if checkbox_list is not None:
                    for checkbox in checkbox_list:
                        checkbox.setEnabled(True)
        except Exception as e:
            py_logger.error(f"Error in toggle_buttons: {e}")

    def is_folder_present(self, label):
        """
        Description:
            Checks if the Reports/<folder_name> path exists and contains at least one subfolder.

        Inputs:
            - label (str): KPI label used to find the corresponding folder name.

        Outputs:
            - bool: True if at least one subfolder exists, False otherwise.
        """
        try:
            # Construct the path to the reports folder
            parent_dir = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
            path = os.path.join(parent_dir, 'Reports', folder_names.get(label, ''))

            # If path doesn't exist or isn't a directory, return False
            if not os.path.isdir(path):
                return False

            # Check if any subfolder exists using a generator expression
            return any(os.path.isdir(os.path.join(path, item)) for item in os.listdir(path))

        except KeyError:
            py_logger.error(f"Error: Label '{label}' not found in folder_names dictionary.")
            return False
        except OSError as e:
            py_logger.error(f"File system error: {e}")
            return False
        except Exception as e:
            py_logger.error(f"Unexpected error: {e}")
            return False
   
    def check_KPIs_config(self, label, edit_button, checkbox, folder_button):
        """
        Validates KPI configuration for a given label and updates the button style accordingly.

        Args:
            label (str): The KPI label to validate.
            edit_button (QPushButton): Button whose style will be updated based on validation.
            checkbox (QCheckBox): Checkbox indicating additional validation requirement.
            folder_button (QPushButton): Button to enable/disable based on folder presence.

        Returns:
            bool: True if configuration is valid, False otherwise.
        """

        # Helper function to set button style based on validity
        def set_button_style(is_valid: bool):
            style = common_enabled_style_green if is_valid else common_enabled_style_red
            edit_button.setStyleSheet(style + common_hover_style)

        # Helper function to validate ECU configuration
        def validate_ECU_configuration(data: dict) -> bool:
            """
            Checks if any ECU configuration is both selected and configured.

            Args:
                data (dict): JSON data containing ECU settings.

            Returns:
                bool: True if at least one ECU setting is valid, False otherwise.
            """
            # Extract only relevant ECU sections
            partial_data = {
                "PADAS": data.get("ECU_setting", {}).get("PADAS", {}),
                "Elite": data.get("ECU_setting", {}).get("Elite", {})
            }

            comparison_result = []

            # Compare ECU selection status with configuration data
            for section, keys in partial_data.items():
                for key in keys:
                    is_selected = self.ecu_selection_status.get(section, {}).get(key, False)
                    is_configured = keys.get(key, False)
                    comparison_result.append(is_selected and is_configured)

            # Return True if any ECU setting is valid
            return any(comparison_result)

        # Enable folder button if folder exists for the label
        folder_button.setEnabled(self.is_folder_present(label))

        try:
            # Labels that require ECU configuration validation
            ecu_validation_labels = [
                "Heap Memory",
                "Startup Time",
                "Cyclic and Turnaround Time",
                "Throughput and Fault Injection",
                "Execution Time"
            ]

            # Initialize validation flag as False
            is_valid = False

            # Get configuration file path for the given label from switch_dict
            config_path = switch_dict.get(label)

            # Load configuration file if path exists
            if config_path:
                with open(config_path, 'r', encoding="utf-8") as f:
                    data = json.load(f)

                # Safely get validation flag from JSON
                is_valid = data.get("is_all_fields_valid", False)

            # Additional ECU validation for specific labels
            if label in ecu_validation_labels:
                if is_valid and self.is_any_ecu_selected_flag and checkbox.isChecked():
                    is_valid = validate_ECU_configuration(data)

            # Update button style and return result
            set_button_style(is_valid)
            return is_valid

        except (FileNotFoundError, json.JSONDecodeError):
            pass
        except Exception as e:
            py_logger.error(f"Error validating '{label}' configuration: {e}")

        # Default case: invalid configuration
        set_button_style(False)
        return False    

    def print_ecu_selection_status(self):
        for category, components in self.ecu_selection_status.items():
            py_logger.info(f"{category}:")
            for component, is_selected in components.items():
                py_logger.info(f"  {component}: {is_selected}")

    def is_any_ecu_selected(self):
        try:
            elite_rcar = self.RCar_checkbox.isChecked()
            elite_soc0 = self.SoC0_checkbox.isChecked()
            elite_soc1 = self.SoC1_checkbox.isChecked()
            padas_rcar = self.padas_checkbox.isChecked()

            self.ecu_selection_status = {
                "PADAS": {
                    "RCAR": padas_rcar
                },
                "Elite": {
                    "RCAR": elite_rcar,
                    "SoC0": elite_soc0,
                    "SoC1": elite_soc1
                }
            }

            self.is_any_ecu_selected_flag = any([elite_rcar, elite_soc0, elite_soc1, padas_rcar])

            # self.print_ecu_selection_status()
        except Exception as e:
            py_logger.error(f"Error in ECU validation: {e}")
            self.is_any_ecu_selected_flag = False

    def update_checkbox_enabling(self) -> None:
        """
        Handles enabling/disabling of checkboxes based on selection rules.
        Description:
            This function updates the enabled state of checkboxes based on the selection rules.
            If the Padas checkbox is checked, all Elite checkboxes are disabled.
            If any of the Elite checkboxes are checked, the Padas checkbox is disabled.
            Otherwise, all checkboxes are enabled.
        """
        other_checkboxes = [self.RCar_checkbox, self.SoC0_checkbox, self.SoC1_checkbox]

        if self.padas_checkbox.isChecked():
            for cb in other_checkboxes:
                cb.setEnabled(False)
        elif any(cb.isChecked() for cb in other_checkboxes):
            self.padas_checkbox.setEnabled(False)
        else:
            self.padas_checkbox.setEnabled(True)
            for cb in other_checkboxes:
                cb.setEnabled(True)

    def get_checkbox_widget_map(self) -> dict:
        """
        Returns a mapping of checkboxes to their associated widgets.
        Output:
            A dictionary where the keys are checkboxes and the values are lists of associated widgets.
        Returns:
            dict
        Description:
            This function returns a dictionary that maps each checkbox to its associated widgets.
            The dictionary is used to update the enabled state of widgets based on checkbox selections.
        """
        return {
            self.RCar_checkbox: [
                self.Rcar_IP_label, self.rcar_ip1, self.rcar_ip2, self.rcar_ip3, self.rcar_ip4,
                self.Rcar_telnet_username_label, self.Rcar_telnet_username_input,
                self.Rcar_telnet_password_label, self.Rcar_telnet_password_input,
                self.Rcar_FTP_username_label, self.Rcar_FTP_username_input,
                self.Rcar_FTP_password_label, self.Rcar_FTP_password_input
            ],
            self.SoC0_checkbox: [
                self.SoC0_IP_label, self.soc0_ip1, self.soc0_ip2, self.soc0_ip3, self.soc0_ip4,
                self.SoC0_telnet_username_label, self.SoC0_telnet_username_input,
                self.SoC0_telnet_password_label, self.SoC0_telnet_password_input,
                self.SoC0_FTP_username_label, self.SoC0_FTP_username_input,
                self.SoC0_FTP_password_label, self.SoC0_FTP_password_input
            ],
            self.SoC1_checkbox: [
                self.SoC1_IP_label, self.soc1_ip1, self.soc1_ip2, self.soc1_ip3, self.soc1_ip4,
                self.SoC1_telnet_username_label, self.SoC1_telnet_username_input,
                self.SoC1_telnet_password_label, self.SoC1_telnet_password_input,
                self.SoC1_FTP_username_label, self.SoC1_FTP_username_input,
                self.SoC1_FTP_password_label, self.SoC1_FTP_password_input
            ]
        }

    def update_checkbox_states(self) -> None:
        """
        Main method to update widget states based on checkbox selections.
        Description:
            This function updates the enabled state of widgets based on checkbox selections.
            It uses the checkbox widget map to determine which widgets to enable or disable.
            The function also handles mutual exclusivity between checkboxes.
        """
        checkbox_widget_map = self.get_checkbox_widget_map()

        def set_widgets_enabled(widgets, enabled):
            """
            Enable or disable widgets.
            Input:
                widgets (list): A list of widgets to enable or disable.
                enabled (bool): Whether to enable or disable the widgets.
            """
            for widget in widgets:
                widget.setEnabled(enabled)

        # Update widgets for RCar
        rcar_enabled = self.padas_checkbox.isChecked() or self.RCar_checkbox.isChecked()
        set_widgets_enabled(checkbox_widget_map[self.RCar_checkbox], rcar_enabled)

        # Update widgets for SoC checkboxes
        for checkbox in [self.SoC0_checkbox, self.SoC1_checkbox]:
            set_widgets_enabled(checkbox_widget_map[checkbox], checkbox.isChecked())

        # Handle mutual exclusivity between checkboxes
        self.update_checkbox_enabling()

        self.is_any_ecu_selected()

        self.update_button_states()

    def update_button_states(self) -> None:
        """
        Updates the state of IG_ON and IG_OFF buttons and configuration status label
        based on the overall configuration validity.
        """
        # Check if all required inputs are valid and borders are correctly updated
        if self.is_configuration_valid():
            # Enable IG buttons and show success status
            self.IG_OFF_button.setEnabled(True)
            self.IG_ON_button.setEnabled(True)
            self.configuration_status_label.setStyleSheet(
                "background-color: #60A917; border: 0.5px solid #999999;"
            )
            self.configuration_flag = True
        else:
            # Disable IG buttons and show error status
            self.IG_OFF_button.setEnabled(False)
            self.IG_ON_button.setEnabled(False)
            self.configuration_status_label.setStyleSheet(
                "background-color: #E51400; border: 0.5px solid #999999;"
            )
            self.configuration_flag = False

        # Update the run button state based on ECU checkbox status
        self.update_run_button_status()
   
    def validate_kpi_configurations(self) -> bool:
        """
        Validates the KPI configurations by checking each KPI's status and validation result.
        Output:
            bool: True if all selected KPIs are valid, False otherwise.
        Returns:
            bool
        """
        # Initialize an empty list to store the validation results of KPIs
        kpi_results = []

        # Iterate over each KPI configuration
        for label, widgets in self.kpi_widgets.items():
            # Get the checkbox and edit button for the current KPI
            checkbox = widgets['checkbox']
            edit_button = widgets['edit_button']
            folder_button = widgets['folder_button']

            # Always collect the status of the KPI configuration
            result = self.check_KPIs_config(label, edit_button, checkbox, folder_button)

            # Only validate the KPI if its checkbox is checked and at least one ECU is selected
            if checkbox.isChecked() and self.is_any_ecu_selected_flag:
                # Append the validation result to the list
                kpi_results.append(result)

        # Return True if at least one KPI was selected for validation and all selected KPIs are valid
        # Return False if no KPIs were selected for validation or any selected KPI failed validation
        return bool(kpi_results) and all(kpi_results)

    def update_run_button_status(self):    
        if self.validate_kpi_configurations() and self.configuration_flag:
            self.run_button.setEnabled(True)
            self.run_button.setToolTip("")            
        else:
            self.run_button.setEnabled(False)
            self.run_button.setToolTip("To enable the RUN Button, configure all red highlighted fields")

    def is_configuration_valid(self) -> bool:
        """
        Validates all relevant input widgets regardless of checkbox state.
        Returns True if at least one ECU is selected, all widgets pass border validation,
        and relay inputs are valid. Logs any validation failures for debugging.        
        Output:
            bool: True if the configuration is valid, False otherwise.
        """
        # Get the checkbox widget map
        checkbox_widget_map = self.get_checkbox_widget_map()

        # Remove specific widgets from the map
        checkbox_widget_map[self.SoC0_checkbox].remove(self.SoC0_telnet_password_input)
        checkbox_widget_map[self.SoC0_checkbox].remove(self.SoC0_FTP_password_input)
        checkbox_widget_map[self.SoC1_checkbox].remove(self.SoC1_telnet_password_input)
        checkbox_widget_map[self.SoC1_checkbox].remove(self.SoC1_FTP_password_input)

        all_inputs_valid = True

        # Check if at least one ECU checkbox is selected
        if not any([
            self.padas_checkbox.isChecked(),
            self.RCar_checkbox.isChecked(),
            self.SoC0_checkbox.isChecked(),
            self.SoC1_checkbox.isChecked()
        ]):
            all_inputs_valid = False

        # Validate all widgets in the checkbox map
        for checkbox, widgets in checkbox_widget_map.items():
            for widget in widgets:
                if not self.update_border(widget):
                    all_inputs_valid = False

        # Validate relay input widgets
        relay_widgets = [self.relay_port_input, self.relay_baudrate_input]
        for widget in relay_widgets:
            if not self.update_border(widget):
                all_inputs_valid = False

        return all_inputs_valid

    def update_border(self, widget: QLineEdit) -> bool:
        """
        Updates the border of a QLineEdit widget based on its content and validation state.
        Returns True if the widget passes validation, False otherwise.
        Skips processing for other widget types.
        Input:
            widget (QLineEdit): The QLineEdit widget to update.
        Output:
            bool: True if the widget passes validation, False otherwise.
        Description:
            This function checks the input in the QLineEdit widget and updates its border accordingly.
            If the input is valid, the border is cleared. If the input is invalid, a red border is applied.
        """
        # Define a helper function to apply a red border to the widget
        def apply_red_border() -> None:
            """
            Description:
                This function applies a red border to the widget to indicate invalid input.
            """
            widget.setStyleSheet("border: 2px solid red;")

        # Define a helper function to clear the border of the widget
        def clear_border() -> None:
            """
            Description:
                This function clears the border of the widget to indicate valid input.
            """
            widget.setStyleSheet("")

        # Only process QLineEdit widgets
        if not isinstance(widget, QLineEdit):
            # Consider non-QLineEdit widgets as valid by default
            return True

        # Clear border if widget is disabled
        if not widget.isEnabled():
            clear_border()
            return True

        # Begin validation
        is_input_valid = True
        text = widget.text()
        stripped_text = text.strip()

        # Check for empty or whitespace-only input
        if not stripped_text or text != stripped_text:
            apply_red_border()
            is_input_valid = False
        else:
            # Validate input based on widget object name
            if "username_input" in widget.objectName() or "password_input" in widget.objectName():
                """
                Description:
                    This section validates the input for the username or password field.
                    It ensures the input matches the expected format and only contains allowed characters.
                """
                # Regex pattern to allow only specific characters
                allowed_pattern = r"^[A-Za-z0-9!#$%&'()\-\^@{}\[\],.;=~_`+]+$"

                if not re.match(allowed_pattern, stripped_text):
                    apply_red_border()
                    is_input_valid = False
                else:
                    # If validator is set, check it
                    if widget.validator() and not widget.hasAcceptableInput():
                        apply_red_border()
                        is_input_valid = False
                    else:
                        clear_border()            
            elif "relay_port_input" in widget.objectName():
                """
                Description:
                    This section validates the input for the relay port field.
                    It checks if the input matches the expected format.
                """
                if not re.match(r'^[A-Z]{3}[1-9][0-9]*$', stripped_text):
                    apply_red_border()
                    is_input_valid = False
                else:
                    clear_border()
            else:
                # If validator is set, check it
                if widget.validator() and not widget.hasAcceptableInput():
                    apply_red_border()
                    is_input_valid = False
                else:
                    clear_border()

        return is_input_valid    

    def IG_ON_Off(self):
        sender = self.sender()
        if sender == self.IG_ON_button:
            # Code to be executed when IG ON button is clicked
            QMessageBox.information(self, "IG ON", "'IG ON' functionality implementation is in progress.")
        elif sender == self.IG_OFF_button:
            # Code to be executed when IG OFF button is clicked
            QMessageBox.information(self, "IG OFF", "'IG OFF' functionality implementation is in progress.")

    def check_kpi_compatibility(self):
        try:
            restricted_kpis = ["Shutdown Time", "RAM Monitor", "Event Trigger RAM Monitor", "APL Communication Layout"]

            for label, widgets in self.kpi_widgets.items():
                checkbox = widgets['checkbox']

                if checkbox.isChecked() and label in restricted_kpis:
                    if not self.padas_checkbox.isChecked():
                        QMessageBox.warning(self, "Incompatible ECU and KPI Selection",
                                        f"The selected KPI '{label}' are only compatible with PADAS.\n"
                                        "Please select either PADAS ECU or deselect KPI to proceed.")
                        return False
            return True
        except Exception as e:
            py_logger.error(f"Error in check KPI compatibility as {e}")
            return False

    def on_run_button_click(self):
        if not self.check_kpi_compatibility():
            return

        ecu_input_fields = self.get_ecu_input_fields()
        self.run_and_update_config(ecu_input_fields)
        self.prepare_and_store_widget_states()
        self.stop_KPIs_execution_button.setEnabled(True)

        self.thread = QThread()
        self.worker = Worker(ecu_input_fields, self.kpi_widgets)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(self.worker_finished)
        self.thread.finished.connect(self.thread.deleteLater)

        # Connect signals        
        self.worker.start_kpi_logging.connect(self.start_kpi_logging)
        self.worker.stop_kpi_logging.connect(self.stop_kpi_logging)
        self.worker.set_status_inProgess.connect(self.set_status_label_inProgess)
        self.worker.update_status.connect(self.set_status_label_and_enable_widgets)
        self.worker.disable_widgets.connect(self.disable_all_widgets)
        self.worker.enable_widgets.connect(self.restore_widget_states)

        self.thread.start()

    def manage_stop_flag(self, is_create):
        """
        Creates or removes the stop.flag file based on the is_create flag.

        Args:
            is_create (bool):
                - True to create the stop.flag file.
                - False to remove the stop.flag file if it exists.
        """
        stop_flag_path = os.path.join(os.getcwd(), "stop.flag")  # Full path to stop.flag

        try:
            if is_create:
                # Create the stop.flag file and write the stop signal
                with open(stop_flag_path, "w", encoding="utf-8") as f:
                    f.write("stop")
                py_logger.info(f"stop.flag created at {stop_flag_path}")
            else:
                # Remove the stop.flag file if it exists
                if os.path.exists(stop_flag_path):
                    os.remove(stop_flag_path)
                    py_logger.info(f"stop.flag removed from {stop_flag_path}")
        except Exception as e:
            # Log any error during creation or removal
            action = "create" if is_create else "remove"
            py_logger.error(f"Failed to {action} stop.flag: {e}")

    def stop_worker_thread(self, spinner_title):
        """
        Safely stops the worker thread if it exists and is active.
        Handles UI updates, spinner dialog, stop flag creation/removal,
        and ensures the GUI remains responsive during shutdown.

        Steps:
            1. Check if the worker thread exists and is active.
            2. Show a spinner dialog to indicate ongoing shutdown if not already shown.
            3. Create a stop flag file for external monitoring.
            4. Request the worker thread to stop using its custom method.
            5. Process GUI events in a loop until the thread stops.
            6. Close spinner dialog if it exists.
            7. Remove the stop flag file after shutdown completes.
        """
        try:
            self.stop_KPIs_execution_button.setEnabled(False)

            # Check if a worker thread exists and is active
            if hasattr(self, 'worker') and self.worker is not None:
                py_logger.info("Worker thread is alive. Closing it...")

                # Show spinner dialog to indicate shutdown in progress only if not already shown
                if not hasattr(self, 'spinner_dialog') or self.spinner_dialog is None:
                    self.spinner_dialog = SpinnerDialog(self, title=spinner_title)
                    self.spinner_dialog.show()

                # Create stop.flag file for external monitoring
                self.manage_stop_flag(is_create=True)

                # Request the worker thread to stop
                self.worker.request_stop()

                # Keep processing GUI events while waiting for the thread to stop
                while self.worker is not None:
                    QCoreApplication.processEvents()  # Prevent GUI freeze
                    time.sleep(0.1)  # Brief pause before checking again

                py_logger.info("Worker thread has stopped successfully.")

                # Close spinner dialog if it exists
                if hasattr(self, 'spinner_dialog') and self.spinner_dialog:
                    self.spinner_dialog.close()
                    self.spinner_dialog = None

            # Remove stop.flag file after shutdown
            self.manage_stop_flag(is_create=False)

        except Exception as e:
            py_logger.error(f"Error while stopping worker thread: {e}")

    def closeEvent(self, event):
        """
        Handles the window close event.
        Shows a confirmation dialog and performs cleanup before closing the application.
        """
        reply = QMessageBox.question(
            self,
            'Close Gen2 PF Validation Tester Tool',  # Dialog title
            'Are you sure you want to close the tool?',  # Confirmation message
            QMessageBox.Ok | QMessageBox.Cancel,  # Buttons
            QMessageBox.Cancel  # Default button
        )

        if reply == QMessageBox.Ok:
            try:
                # Log the start of the shutdown process
                py_logger.info("Closing Gen2 PF Validation Tester Tool, please wait!...")

                # Disable close button to prevent repeated close attempts
                self.setWindowFlag(Qt.WindowCloseButtonHint, False)
                self.setWindowFlags(self.windowFlags())
                self.show()

                # Call to stop the worker thread safely
                self.stop_worker_thread("Closing the GUI application...")

                # Final log before closing the application
                py_logger.info("Gen2 PF Validation Tester Tool Closed Successfully.")

                # Accept the close event to allow the window to close
                event.accept()

            except Exception as e:
                # Log any unexpected error during shutdown
                py_logger.error(f"Error While Closing Gen2 PF Validation Tester Tool: {e}")
                event.accept()  # Still close the window to avoid hanging
        else:
            # If user cancels the close action, ignore the event and keep the GUI open
            event.ignore()

    def worker_finished(self):
        # py_logger.info("Successfully closed Worker Thread.")
        self.worker = None
        self.is_test_in_progress = False

    def get_ecu_input_fields(self):
        ecu_input_fields = {}

        if self.padas_checkbox.isChecked():
            ecu_input_fields['RCAR'] = {
                'IP': self.get_RCAR_ip_address(),
                'telnet_username': self.Rcar_telnet_username_input.text(),
                'telnet_password': self.Rcar_telnet_password_input.text(),
                'FTP_username': self.Rcar_FTP_username_input.text(),
                'FTP_password': self.Rcar_FTP_password_input.text()
            }

        if self.RCar_checkbox.isChecked():
            ecu_input_fields['RCAR'] = {
                'IP': self.get_RCAR_ip_address(),
                'telnet_username': self.Rcar_telnet_username_input.text(),
                'telnet_password': self.Rcar_telnet_password_input.text(),
                'FTP_username': self.Rcar_FTP_username_input.text(),
                'FTP_password': self.Rcar_FTP_password_input.text()
            }

        if self.SoC0_checkbox.isChecked():
            ecu_input_fields['SoC0'] = {
                'IP': self.get_SoC0_ip_address(),
                'telnet_username': self.SoC0_telnet_username_input.text(),
                'telnet_password': self.SoC0_telnet_password_input.text(),
                'FTP_username': self.SoC0_FTP_username_input.text(),
                'FTP_password': self.SoC0_FTP_password_input.text()
            }

        if self.SoC1_checkbox.isChecked():
            ecu_input_fields['SoC1'] = {
                'IP': self.get_SoC1_ip_address(),
                'telnet_username': self.SoC1_telnet_username_input.text(),
                'telnet_password': self.SoC1_telnet_password_input.text(),
                'FTP_username': self.SoC1_FTP_username_input.text(),
                'FTP_password': self.SoC1_FTP_password_input.text()
            }

        return ecu_input_fields

    def run_and_update_config(self, ecu_input_fields):
        self.Write_ECU_Configuration()

        def build_ecu_settings():
            return {            
                "RCAR_IPAddress": ecu_input_fields.get("RCAR", {}).get("IP", ""),
                "RCAR_Telnet_Username": ecu_input_fields.get("RCAR", {}).get("telnet_username", ""),
                "RCAR_Telnet_Password": ecu_input_fields.get("RCAR", {}).get("telnet_password", ""),
                "RCAR_FTP_Username": ecu_input_fields.get("RCAR", {}).get("FTP_username", ""),
                "RCAR_FTP_Password": ecu_input_fields.get("RCAR", {}).get("FTP_password", ""),
                "Qualcomm_SoC0_IPAddress": ecu_input_fields.get("SoC0", {}).get("IP", ""),
                "SoC0_Telnet_Username": ecu_input_fields.get("SoC0", {}).get("telnet_username", ""),
                "SoC0_Telnet_Password": ecu_input_fields.get("SoC0", {}).get("telnet_password", ""),
                "SoC0_FTP_Username": ecu_input_fields.get("SoC0", {}).get("FTP_username", ""),
                "SoC0_FTP_Password": ecu_input_fields.get("SoC0", {}).get("FTP_password", ""),
                "Qualcomm_SoC1_IPAddress": ecu_input_fields.get("SoC1", {}).get("IP", ""),
                "SoC1_Telnet_Username": ecu_input_fields.get("SoC1", {}).get("telnet_username", ""),
                "SoC1_Telnet_Password": ecu_input_fields.get("SoC1", {}).get("telnet_password", ""),
                "SoC1_FTP_Username": ecu_input_fields.get("SoC1", {}).get("FTP_username", ""),
                "SoC1_FTP_Password": ecu_input_fields.get("SoC1", {}).get("FTP_password", "")
            }

        def compare_ecu_settings(data, label):
            """
            Compare ECU settings between self.ecu_selection_status and the given data,
            and save extracted ECU settings to a JSON file under the given label.

            Description:
            ------------
            This function extracts only the 'PADAS' and 'Elite' sections from the input `data`
            (which contains ECU settings) and compares them with `self.ecu_selection_status`.
            For each key inside these sections, the result will be True only if both dictionaries
            have True for that key; otherwise, False. It also saves the extracted ECU settings
            to 'all_KPIs_ECU_settings.json' under the key `label`.

            Input:
            ------
            data : dict
                A dictionary containing ECU settings in the format:
                {
                    "ECU_setting": {
                        "PADAS": {...},
                        "Elite": {...}
                    },
                    "Current_Timestamp": "..."
                }
            label : str
                A unique identifier for saving the extracted ECU settings.

                    Output:
                    -------
                    comparison_result : dict
                        A dictionary with the same structure as 'PADAS' and 'Elite', where each key
                        is True only if both sources have True, else False.
                        Example:
                        {
                            "PADAS": {"RCAR": True},
                            "Elite": {"RCAR": False, "SoC0": False, "SoC1": False}
                        }

                    Logic:
                    ------
                    1. Extract 'PADAS' and 'Elite' from the input `data` safely using `.get()`.
                    2. Loop through each section ('PADAS', 'Elite') and their keys.
                    3. For each key, check:
                    - If `self.ecu_selection_status[section][key]` is True AND
                        `partial_data[section][key]` is True → set True.
                    - Else → set False.
                    4. Return the comparison result dictionary.
                    """

            # Step 1: Extract only the required part from data
            partial_data = {
                "PADAS": data.get("ECU_setting", {}).get("PADAS", {}),
                "Elite": data.get("ECU_setting", {}).get("Elite", {})
            }

            # Step 2: Initialize result dictionary
            comparison_result = {}

            # Step 3: Compare values
            for section in partial_data:
                comparison_result[section] = {}
                for key in partial_data[section]:
                    comparison_result[section][key] = (
                        self.ecu_selection_status.get(section, {}).get(key, False)
                        and partial_data[section].get(key, False)
                    )

            # Step 4: Save partial_data to JSON under label
            file_name = "all_KPIs_ECU_settings.json"
            if os.path.exists(file_name):
                with open(file_name, "r", encoding="utf-8") as f:
                    all_data = json.load(f)
            else:
                all_data = {}

            all_data[label] = partial_data

            with open(file_name, "w", encoding="utf-8") as f:
                json.dump(all_data, f, indent=4)

            # Step 5: Log info
            # py_logger.info(
            #     f"\n{'#'*70}\n"
            #     f"Label: {label}\n"
            #     f"KPI_ecu_settings: {partial_data}\n"
            #     f"mainwindow_ecu_settings: {self.ecu_selection_status}\n"
            #     f"comparison_result: {comparison_result}\n"
            #     f"{'#'*70}"
            # )

            # Step 6: Return result
            return comparison_result

        def update_config_file(file_path, label):
            try:
                with open(file_path, 'r', encoding="utf-8") as f:
                    data = json.load(f)

                if label in ["Startup Time", "Shutdown Time", "Throughput and Fault Injection"]:
                    data['serial-port-relay'] = self.relay_port_input.text()
                    data['baudrate-relay'] = self.relay_baudrate_input.text()

                if label in ["Heap Memory", "Startup Time", "Cyclic and Turnaround Time", "Execution Time", "Throughput and Fault Injection"]:
                    final_config = compare_ecu_settings(data, label)
                    if final_config:
                        data["ECU_setting"] = {}
                        data["ECU_setting"] = final_config                    
                else:
                    if "ECU_setting" not in data:
                        data["ECU_setting"] = {}

                    data["ECU_setting"]["PADAS"] = {
                        "RCAR": self.padas_checkbox.isChecked()
                    }

                    data["ECU_setting"]["Elite"] = {
                        "RCAR": self.RCar_checkbox.isChecked(),
                        "SoC0": self.SoC0_checkbox.isChecked(),
                        "SoC1": self.SoC1_checkbox.isChecked()
                    }

                data["ECU_setting"].update(build_ecu_settings())                

                with open(file_path, 'w', encoding="utf-8") as f:
                    json.dump(data, f, indent=4)

            except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
                py_logger.error(f"Error with JSON: {e}", exc_info=True)
            except Exception as e:
                py_logger.error(f"Unexpected error while updating '{file_path}': {e}")
       
        try:
            for label, widgets in self.kpi_widgets.items():
                if widgets['checkbox'].isChecked():
                    config_path = switch_dict.get(label)
                    if config_path:
                        if label in diag_labels:                            
                            with open(config_path, 'r', encoding="utf-8") as f:
                                data = json.load(f)

                            # Update KPI checkbox states
                            for key in diag_labels:
                                data[key] = self.kpi_widgets[key]['checkbox'].isChecked()

                            with open('DIAG_KPI_Config.json', 'w', encoding="utf-8") as f:
                                json.dump(data, f, indent=4)

                            update_config_file('DIAG_KPI_Config.json', label)
                        else:
                            update_config_file(config_path, label)
        except Exception as e:
            py_logger.error(f"Error updating config file: {e}")

    def prepare_and_store_widget_states(self):
        self.is_test_in_progress = True
        self.kpi_widgets_status = {}

        for label, widgets in self.kpi_widgets.items():
            checkbox = widgets['checkbox']
            status_label = widgets['status_label']

            status_label.setStyleSheet("background-color: #D0CEE2; border: 0.5px solid #999999;")
            # if checkbox.isChecked():
            #     status_label.setStyleSheet("background-color: #FFFF00; border: 0.5px solid #999999;")

            self.kpi_widgets_status[label] = {
                'checkbox': checkbox.isEnabled(),
            }

    def set_status_label_inProgess(self, label):
        if label in self.kpi_widgets:
            widgets = self.kpi_widgets[label]
            widgets['status_label'].setStyleSheet("background-color: #FFFF00; border: 0.5px solid #999999;")

    def set_status_label_and_enable_widgets(self, label, color):
        if label in self.kpi_widgets:
            widgets = self.kpi_widgets[label]
            widgets['status_label'].setStyleSheet(
                f"background-color: {color}; border: 0.5px solid #999999;"
            )
            widgets['checkbox'].setEnabled(True)

    def disable_all_widgets(self):
        self.run_button.setEnabled(False)
        self.IG_OFF_button.setEnabled(False)
        self.IG_ON_button.setEnabled(False)

        for widget in self.findChildren((QCheckBox, QLineEdit)):
            widget.setEnabled(False)        

    def restore_KPIs_ECU_settings(self, label):
        """
        Restore ECU settings from 'all_KPIs_ECU_settings.json' for the given label
        and update the corresponding config file.

        Steps:
        ------
        1. Load all saved ECU settings from 'all_KPIs_ECU_settings.json'.
        2. Find the config file path using `switch_dict[label]`.
        3. Load the config file data.
        4. Replace its 'ECU_setting' section with the saved settings for the label.
        5. Save the updated config back to the file.
        """

        file_name = "all_KPIs_ECU_settings.json"

        # Step 1: Check if JSON file exists
        if not os.path.exists(file_name):
            py_logger.warning(f"File '{file_name}' not found. Cannot restore settings.")
            return

        # Step 2: Load all saved ECU settings
        with open(file_name, "r", encoding="utf-8") as f:
            all_data = json.load(f)

        # Step 3: Validate label
        if label not in all_data:
            # py_logger.warning(f"Label '{label}' not found in '{file_name}'.")
            return

        # Step 4: Get config path from switch_dict
        config_path = switch_dict.get(label)
        if not config_path or not os.path.exists(config_path):
            py_logger.warning(f"Config path for label '{label}' not found or invalid.")
            return

        # Step 5: Load config file data
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Step 6: Update ECU_setting in config data
        data["ECU_setting"] = all_data[label]

        # Step 7: Save updated config back to file
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def restore_widget_states(self):
        for label, widgets in self.kpi_widgets.items():
            if label in self.kpi_widgets_status:
                widgets['checkbox'].setEnabled(self.kpi_widgets_status[label]['checkbox'])

                self.restore_KPIs_ECU_settings(label)

        self.enable_input_fields_based_on_checkboxes()
        self.update_button_states()

    def enable_input_fields_based_on_checkboxes(self):
        # Enable or disable checkboxes
        self.padas_checkbox.setEnabled(not (self.RCar_checkbox.isChecked() or
                                            self.SoC0_checkbox.isChecked() or self.SoC1_checkbox.isChecked()))
        self.RCar_checkbox.setEnabled(not self.padas_checkbox.isChecked())
        self.SoC0_checkbox.setEnabled(not self.padas_checkbox.isChecked())
        self.SoC1_checkbox.setEnabled(not self.padas_checkbox.isChecked())

        # Enable or disable input fields based on checkboxes
        self.rcar_ip1.setEnabled(self.padas_checkbox.isChecked() or self.RCar_checkbox.isChecked())
        self.rcar_ip2.setEnabled(self.padas_checkbox.isChecked() or self.RCar_checkbox.isChecked())
        self.rcar_ip3.setEnabled(self.padas_checkbox.isChecked() or self.RCar_checkbox.isChecked())
        self.rcar_ip4.setEnabled(self.padas_checkbox.isChecked() or self.RCar_checkbox.isChecked())
        self.Rcar_telnet_username_input.setEnabled(self.padas_checkbox.isChecked() or self.RCar_checkbox.isChecked())
        self.Rcar_telnet_password_input.setEnabled(self.padas_checkbox.isChecked() or self.RCar_checkbox.isChecked())
        self.Rcar_FTP_username_input.setEnabled(self.padas_checkbox.isChecked() or self.RCar_checkbox.isChecked())
        self.Rcar_FTP_password_input.setEnabled(self.padas_checkbox.isChecked() or self.RCar_checkbox.isChecked())

        self.soc0_ip1.setEnabled(self.SoC0_checkbox.isChecked())
        self.soc0_ip2.setEnabled(self.SoC0_checkbox.isChecked())
        self.soc0_ip3.setEnabled(self.SoC0_checkbox.isChecked())
        self.soc0_ip4.setEnabled(self.SoC0_checkbox.isChecked())
        self.SoC0_telnet_username_input.setEnabled(self.SoC0_checkbox.isChecked())
        self.SoC0_telnet_password_input.setEnabled(self.SoC0_checkbox.isChecked())
        self.SoC0_FTP_username_input.setEnabled(self.SoC0_checkbox.isChecked())
        self.SoC0_FTP_password_input.setEnabled(self.SoC0_checkbox.isChecked())

        self.soc1_ip1.setEnabled(self.SoC1_checkbox.isChecked())
        self.soc1_ip2.setEnabled(self.SoC1_checkbox.isChecked())
        self.soc1_ip3.setEnabled(self.SoC1_checkbox.isChecked())
        self.soc1_ip4.setEnabled(self.SoC1_checkbox.isChecked())
        self.SoC1_telnet_username_input.setEnabled(self.SoC1_checkbox.isChecked())
        self.SoC1_telnet_password_input.setEnabled(self.SoC1_checkbox.isChecked())
        self.SoC1_FTP_username_input.setEnabled(self.SoC1_checkbox.isChecked())
        self.SoC1_FTP_password_input.setEnabled(self.SoC1_checkbox.isChecked())

        # Enable buttons
        self.relay_port_input.setEnabled(True)
        self.relay_baudrate_input.setEnabled(True)
        self.stop_KPIs_execution_button.setEnabled(False)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Set global tooltip style before creating any widgets
    app.setStyleSheet("""
        QToolTip {
            background-color: white;
            color: black;
            border: 2px solid red;
            border-radius: 4px;
            padding: 5px;
        }
    """)

    main_window = MainWindow()
    main_window.show()

    sys.exit(app.exec_())