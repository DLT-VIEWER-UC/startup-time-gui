from imports_utils import *

from cpu_memory_utilization_config_window import CpuMemoryConfig
from diag_config_window import DiagConfig
from heap_memory_config_window import HeapMemoryConfig
from execution_time_config_window import ExecutionTimeConfig
from startup_time_config_window import StartupTimeConfig

# Import the function
from CPU_Memory_Utilization_Scripts.CPU_memory_utilization_measure_script import start_cpu_memory_utilization_measurement
from Heap_Memory_Scripts.Heap_Memory_Measurement_Script import start_heap_measurement
from Startup_Time_Scripts.Applications_StartupTime_IG_ON import start_startup_time_measurement
from Execution_Time_Scripts.exe import start_execution_time_measurement

class EmittingStream(QObject):
    text_written = pyqtSignal(str)

    def __init__(self, original_stream):
        super().__init__()
        self.original_stream = original_stream

    def write(self, text):
        self.text_written.emit(str(text))
        if self.original_stream:
            self.original_stream.write(text)
            self.original_stream.flush()

    def flush(self):
        if self.original_stream:
            self.original_stream.flush()

class Worker(QObject):
    finished = pyqtSignal()
    update_status = pyqtSignal(str, str)
    disable_widgets = pyqtSignal()
    enable_widgets = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, ecu_input_fields, kpi_widgets):
        super().__init__()
        self.ecu_input_fields = ecu_input_fields
        self.kpi_widgets = kpi_widgets
        self.process = None
        self._stop_requested = False

    def request_stop(self):
        self._stop_requested = True
        self.terminate_process()

    def terminate_process(self):
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            except Exception as e:
                self.error_signal.emit(f"Process termination failed: {e}")

    def run(self):
        try:
            self.disable_widgets.emit()
            # self.print_ecu_input_fields()
            self.run_function()
        except Exception as e:
            self.error_signal.emit(f"Error in run_function: {e}")
        finally:
            self.enable_widgets.emit()
            self.finished.emit()
   
    def launch_diag_application(self):
        current_os = platform.system()

        if current_os == "Windows":
            exe_path = r"High_Level_ECU_Tester.exe"  # Update this path if needed
        elif current_os == "Linux":
            exe_path = r"High_Level_ECU_Tester"
        else:
            self.error_signal.emit("Unsupported OS.")
            return False

        if not os.path.exists(exe_path):
            self.error_signal.emit(f"Executable not found: {exe_path}")
            return False  

        try:
            if current_os == "Linux":
                subprocess.run(["chmod", "+x", exe_path])

            self.process = subprocess.Popen([exe_path])
           
            # Wait for the process to complete or be forcefully stopped
            while self.process.poll() is None:
                if self._stop_requested:
                    self.terminate_process()
                    return False
                time.sleep(0.2)  # Non-blocking check

            return True  # Process finished naturally

        except Exception as e:
            self.error_signal.emit(f"Error running app: {e}")
            return False

    def run_function(self):
        for label in labels:
            widgets = self.kpi_widgets.get(label)
            if widgets and widgets['checkbox'].isChecked():
                time.sleep(5)
                if label == 'CPU and Memory Utilization':
                    status = start_cpu_memory_utilization_measurement()
                    color = "#60A917" if status else "#E51400"
               
                elif label == 'Heap Memory':
                    status = start_heap_measurement()
                    color = "#60A917" if status else "#E51400"

                elif label == 'Startup Time':
                    status = self.validate_ECU_configuration('./Startup_Time_Scripts/startup_time_config.json', label)

                    if status:
                        status = start_startup_time_measurement()

                    color = "#60A917" if status else "#E51400"
               
                elif label == 'Execution Time':
                    status = self.validate_ECU_configuration('./Execution_Time_Scripts/Execution_Time_Config.json', label)

                    if status:
                        status = start_execution_time_measurement()

                    color = "#60A917" if status else "#E51400"

                elif label in diag_labels:
                    status = self.launch_diag_application()
   
                    if status:
                        with open('DIAG_KPI_Config.json', 'r') as f:
                            data = json.load(f)

                        # Construct the full path
                        report_path = os.path.join(
                            'Reports',
                            folder_names.get(label, ''),
                            data.get("Current_Timestamp", '')
                        )

                        # Check if path exists and contains at least one .xlsx file
                        if os.path.isdir(report_path):
                            status = any(
                                file.lower().endswith('.xlsx') for file in os.listdir(report_path)
                            )
                        else:
                            status = False  # Path is invalid
                            print(f"file path not found {report_path}")

                    color = "#60A917" if status else "#E51400"

                else:  
                    color = "#60A917" if self.is_even() else "#E51400"

                self.update_status.emit(label, color)
   
    def validate_ECU_configuration(self, file_path, label):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            isvalid = (
                data['PADAS']['RCAR'] == data['ECU_setting']['PADAS']['RCAR'] and
                data['Elite']['RCAR'] == data['ECU_setting']['Elite']['RCAR'] and
                data['Elite']['SoC0'] == data['ECU_setting']['Elite']['SoC0'] and
                data['Elite']['SoC1'] == data['ECU_setting']['Elite']['SoC1']
            )

            if not isvalid:
                print(f"The ECU details configured in the main window do not match the ECU details configured in the {label} Dialog window.")
               
            return isvalid

        except FileNotFoundError:
            self.logger.error(f"Error: Configuration file '{file_path}' not found.")
            return False
        except json.JSONDecodeError:
            self.logger.error(f"Error: Configuration file '{file_path}' is not a valid JSON.")
            return False
        except KeyError as e:
            self.logger.error(f"Error: Missing expected key in ECU input fields: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error while updating '{file_path}': {e}")
            return False

    def print_ecu_input_fields(self):
        for ecu, fields in self.ecu_input_fields.items():
            self.logger.info(f"ECU: {ecu} is enabled")
            self.logger.info(f"IP: {fields['IP']}")
            self.logger.info(f"Telnet Username: {fields['telnet_username']}")
            self.logger.info(f"Telnet Password: {fields['telnet_password']}")
            self.logger.info(f"FTP Username: {fields['FTP_username']}")
            self.logger.info(f"FTP Password: {fields['FTP_password']}")
            self.logger.info("------------------------")

    def is_even(self):
        return random.randint(0, 1) % 2 == 0

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.set_window_properties()

        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()

        self.tab_widget.addTab(self.tab1, "Tester")
        self.tab_widget.addTab(self.tab2, "Console")
        self.tab_widget.addTab(self.tab3, "About")

        self.kpi_widgets = {}
        self.configuration_flag = False

        self.create_tester_tab()            
        self.create_console_tab()
        self.create_about_tab()

        self.read_ECU_configuration()
   
    def create_console_tab(self):
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

        self.console_input = QLineEdit()
        self.console_input.returnPressed.connect(self.execute_command)

        download_button = QPushButton("Download Logs!")
        download_button.setFixedSize(150, 35)
        download_button.setStyleSheet(common_enabled_style + common_hover_style)
        download_button.clicked.connect(self.download_console_output)

        button_layout = QHBoxLayout()
        button_layout.addStretch()  # Pushes the button to the right
        button_layout.addWidget(download_button)

        layout.addWidget(self.console_output)
        # layout.addWidget(self.console_input)
        layout.addLayout(button_layout)

        self.tab2.setLayout(layout)

        # Redirect stdout and stderr
        stdout_stream = EmittingStream(original_stdout)
        stderr_stream = EmittingStream(original_stderr)

        stdout_stream.text_written.connect(self.write_to_console)
        stderr_stream.text_written.connect(self.write_to_console)

        sys.stdout = stdout_stream
        sys.stderr = stderr_stream
       
        # Setup logging to use the same stream
        self.logger = setup_logging(stream=stdout_stream)

        print("Gen2 PF GUI Tester Tool is Successfully Launched.")

    def write_to_console(self, text):
        self.console_output.moveCursor(self.console_output.textCursor().End)
        self.console_output.insertPlainText(text)
        self.console_output.moveCursor(self.console_output.textCursor().End)

    def download_console_output(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Console Output", "", "Text Files (*.txt);;All Files (*)", options=options)
        if file_path:
            with open(file_path, 'w') as file:
                file.write(self.console_output.toPlainText())

    def execute_command(self):
        command = self.console_input.text()
        self.console_output.appendPlainText(f"> {command}")
        self.console_input.clear()

        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            output = result.stdout if result.stdout else result.stderr
            self.console_output.appendPlainText(output)
        except Exception as e:
            self.console_output.appendPlainText(f"Error: {str(e)}")

    def set_window_properties(self):
        self.setWindowTitle("Gen2 Platform Validation Test Automation Framework")
        self.setWindowIcon(QIcon('KPIT_logo.png'))

        # Get the screen geometry
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        # Define window dimensions
        window_width = 1150
        window_height = 960

        # Ensure the window dimensions do not exceed the screen dimensions
        window_width = min(window_width, screen_width)
        window_height = min(window_height, screen_height)

        # Calculate the position to center the window horizontally and position at top
        x = (screen_width - window_width) // 2
        y = 10  # Position at top

        # Set the geometry and fixed size of the window
        self.setGeometry(x, y, window_width, window_height)
        self.setFixedSize(window_width, window_height)

        # Remove the maximize button
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMaximizeButtonHint)      
   
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
        edit_button.setIcon(QIcon('pencil_write_icon.png'))
        edit_button.setIconSize(QSize(25, 25))
        edit_button.setEnabled(False)
        edit_button.clicked.connect(lambda: self.on_button_click(label, edit_button))

        folder_button = QPushButton()
        folder_button.setFixedSize(30, 30)
        folder_button.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        folder_button.setStyleSheet(common_enabled_style + common_hover_style)
        folder_button.setEnabled(False)
        folder_button.clicked.connect(lambda: self.open_file_manager(label))

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
        checkbox.stateChanged.connect(self.update_run_button_status)

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
        self.relay_port_input.setText("COM4")
        self.relay_port_input.setFixedWidth(80)
        self.relay_port_input.textChanged.connect(self.update_button_states)


        relay_port_unit_label = QLabel('(e.g. COM1, COM4)')
        relay_port_unit_label.setStyleSheet("font-size: 12px;")

        relay_port_layout.addWidget(self.relay_port_input)
        relay_port_layout.addWidget(relay_port_unit_label)

        relay_layout.addRow(relay_port_label, relay_port_layout)

        relay_baudrate_layout = QHBoxLayout()

        relay_baudrate_label = QLabel('Relay Baudrate')

        self.relay_baudrate_input = QLineEdit()
        self.relay_baudrate_input.setValidator(QIntValidator())
        self.relay_baudrate_input.setText("9600")
        self.relay_baudrate_input.setFixedWidth(80)
        self.relay_baudrate_input.textChanged.connect(self.update_button_states)

        relay_baudrate_unit_label = QLabel('(e.g. 9600, 115200)')
        relay_baudrate_unit_label.setStyleSheet("font-size: 12px;")
       
        relay_baudrate_layout.addWidget(self.relay_baudrate_input)
        relay_baudrate_layout.addWidget(relay_baudrate_unit_label)

        relay_layout.addRow(relay_baudrate_label, relay_baudrate_layout)
        return relay_layout    

    def create_IG_button_layout(self):
        IG_button_layout = QHBoxLayout()

        self.IG_OFF_button = QPushButton('IG OFF')  
        self.IG_OFF_button.setFixedSize(150,35)    
        self.IG_OFF_button.setStyleSheet(common_enabled_style + common_hover_style)
        self.IG_OFF_button.clicked.connect(self.IG_ON_Off)
        self.IG_OFF_button.setEnabled(False)

        self.IG_ON_button = QPushButton('IG ON')
        self.IG_ON_button.setFixedSize(150, 35)
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
       
        self.Rcar_IP_input = QLineEdit()
        self.Rcar_IP_input.setFixedWidth(150)
        self.Rcar_IP_input.setPlaceholderText('Enter IP Address')
        self.Rcar_IP_input.setValidator(ip_address_validator)
        # self.Rcar_IP_input.setText("192.168.1.3")
        self.Rcar_IP_input.textChanged.connect(lambda: self.validate_IP(self.Rcar_IP_input))
        self.Rcar_IP_input.textChanged.connect(self.update_button_states)
        self.Rcar_IP_input.setEnabled(False)
       
        Rcar_telent_layout.addRow(self.Rcar_IP_label, self.Rcar_IP_input)
       
        self.Rcar_telnet_username_label = QLabel('Telnet Username')
        self.Rcar_telnet_username_label.setEnabled(False)
       
        self.Rcar_telnet_username_input = QLineEdit()
        self.Rcar_telnet_username_input.setFixedWidth(150)
        self.Rcar_telnet_username_input.setPlaceholderText('Enter Username')
        # self.Rcar_telnet_username_input.setText("root")
        self.Rcar_telnet_username_input.textChanged.connect(self.update_button_states)
        self.Rcar_telnet_username_input.setEnabled(False)
       
        Rcar_telent_layout.addRow(self.Rcar_telnet_username_label, self.Rcar_telnet_username_input)
       
        self.Rcar_telnet_password_label = QLabel('Telnet Password')
        self.Rcar_telnet_password_label.setEnabled(False)
       
        self.Rcar_telnet_password_input = QLineEdit()
        self.Rcar_telnet_password_input.setFixedWidth(150)  
        self.Rcar_telnet_password_input.setPlaceholderText('Enter Password')
        # self.Rcar_telnet_password_input.setText("root")
        self.Rcar_telnet_password_input.textChanged.connect(self.update_button_states)
        self.Rcar_telnet_password_input.setEnabled(False)
       
        Rcar_telent_layout.addRow(self.Rcar_telnet_password_label, self.Rcar_telnet_password_input)
        return Rcar_telent_layout    

    def create_Rcar_FTP_layout(self):
        Rcar_FTP_layout = QFormLayout()
        Rcar_FTP_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
       
        self.Rcar_FTP_username_label = QLabel('FTP Username')
        self.Rcar_FTP_username_label.setEnabled(False)

        self.Rcar_FTP_username_input = QLineEdit()
        self.Rcar_FTP_username_input.setFixedWidth(150)
        self.Rcar_FTP_username_input.setPlaceholderText('Enter Username')
        # self.Rcar_FTP_username_input.setText("qnxuser")
        self.Rcar_FTP_username_input.textChanged.connect(self.update_button_states)
        self.Rcar_FTP_username_input.setEnabled(False)

        Rcar_FTP_layout.addRow(self.Rcar_FTP_username_label, self.Rcar_FTP_username_input)

        self.Rcar_FTP_password_label = QLabel('FTP Password')
        self.Rcar_FTP_password_label.setEnabled(False)

        self.Rcar_FTP_password_input = QLineEdit()
        self.Rcar_FTP_password_input.setFixedWidth(150)
        self.Rcar_FTP_password_input.setPlaceholderText('Enter Password')
        # self.Rcar_FTP_password_input.setText("qnxuser")
        self.Rcar_FTP_password_input.textChanged.connect(self.update_button_states)
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

        self.SoC0_IP_input = QLineEdit()
        self.SoC0_IP_input.setFixedWidth(150)
        self.SoC0_IP_input.setPlaceholderText('Enter IP Address')
        self.SoC0_IP_input.setValidator(ip_address_validator)
        self.SoC0_IP_input.textChanged.connect(lambda: self.validate_IP(self.SoC0_IP_input))
        self.SoC0_IP_input.textChanged.connect(self.update_button_states)
        self.SoC0_IP_input.setEnabled(False)

        SoC0_telent_layout.addRow(self.SoC0_IP_label, self.SoC0_IP_input)

        self.SoC0_telnet_username_label = QLabel('Telnet Username')
        self.SoC0_telnet_username_label.setEnabled(False)

        self.SoC0_telnet_username_input = QLineEdit()
        self.SoC0_telnet_username_input.setFixedWidth(150)
        self.SoC0_telnet_username_input.setPlaceholderText('Enter Username')
        self.SoC0_telnet_username_input.textChanged.connect(self.update_button_states)
        self.SoC0_telnet_username_input.setEnabled(False)

        SoC0_telent_layout.addRow(self.SoC0_telnet_username_label, self.SoC0_telnet_username_input)

        self.SoC0_telnet_password_label = QLabel('Telnet Password')
        self.SoC0_telnet_password_label.setEnabled(False)

        self.SoC0_telnet_password_input = QLineEdit()
        self.SoC0_telnet_password_input.setFixedWidth(150)
        self.SoC0_telnet_password_input.setPlaceholderText('Enter Password')
        self.SoC0_telnet_password_input.textChanged.connect(self.update_button_states)
        self.SoC0_telnet_password_input.setEnabled(False)

        SoC0_telent_layout.addRow(self.SoC0_telnet_password_label, self.SoC0_telnet_password_input)
        return SoC0_telent_layout    

    def create_SoC0_FTP_layout(self):
        SoC0_FTP_layout = QFormLayout()
        SoC0_FTP_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.SoC0_FTP_username_label = QLabel('FTP Username')
        self.SoC0_FTP_username_label.setEnabled(False)

        self.SoC0_FTP_username_input = QLineEdit()
        self.SoC0_FTP_username_input.setFixedWidth(150)
        self.SoC0_FTP_username_input.setPlaceholderText('Enter Username')
        self.SoC0_FTP_username_input.textChanged.connect(self.update_button_states)
        self.SoC0_FTP_username_input.setEnabled(False)

        SoC0_FTP_layout.addRow(self.SoC0_FTP_username_label, self.SoC0_FTP_username_input)

        self.SoC0_FTP_password_label = QLabel('FTP Password')
        self.SoC0_FTP_password_label.setEnabled(False)

        self.SoC0_FTP_password_input = QLineEdit()
        self.SoC0_FTP_password_input.setFixedWidth(150)
        self.SoC0_FTP_password_input.setPlaceholderText('Enter Password')
        self.SoC0_FTP_password_input.textChanged.connect(self.update_button_states)
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

        SoC1_telent_layout = self.create_SoC1_telent_layout()

        SoC1_FTP_layout = self.create_SoC1_FTP_layout()

        SoC1_layout.addLayout(SoC1_telent_layout)
        SoC1_layout.addLayout(SoC1_FTP_layout)
        return SoC1_layout    

    def create_SoC1_telent_layout(self):
        SoC1_telent_layout = QFormLayout()
        SoC1_telent_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.SoC1_IP_label = QLabel('SoC1 IP Address')
        self.SoC1_IP_label.setEnabled(False)

        self.SoC1_IP_input = QLineEdit()
        self.SoC1_IP_input.setFixedWidth(150)
        self.SoC1_IP_input.setPlaceholderText('Enter IP Address')
        self.SoC1_IP_input.setValidator(ip_address_validator)
        self.SoC1_IP_input.textChanged.connect(lambda: self.validate_IP(self.SoC1_IP_input))
        self.SoC1_IP_input.textChanged.connect(self.update_button_states)
        self.SoC1_IP_input.setEnabled(False)

        SoC1_telent_layout.addRow(self.SoC1_IP_label, self.SoC1_IP_input)

        self.SoC1_telnet_username_label = QLabel('Telnet Username')
        self.SoC1_telnet_username_label.setEnabled(False)

        self.SoC1_telnet_username_input = QLineEdit()
        self.SoC1_telnet_username_input.setFixedWidth(150)
        self.SoC1_telnet_username_input.setPlaceholderText('Enter Username')
        self.SoC1_telnet_username_input.textChanged.connect(self.update_button_states)
        self.SoC1_telnet_username_input.setEnabled(False)

        SoC1_telent_layout.addRow(self.SoC1_telnet_username_label, self.SoC1_telnet_username_input)

        self.SoC1_telnet_password_label = QLabel('Telnet Password')
        self.SoC1_telnet_password_label.setEnabled(False)

        self.SoC1_telnet_password_input = QLineEdit()
        self.SoC1_telnet_password_input.setFixedWidth(150)
        self.SoC1_telnet_password_input.setPlaceholderText('Enter Password')
        self.SoC1_telnet_password_input.textChanged.connect(self.update_button_states)
        self.SoC1_telnet_password_input.setEnabled(False)

        SoC1_telent_layout.addRow(self.SoC1_telnet_password_label, self.SoC1_telnet_password_input)
        return SoC1_telent_layout    

    def create_SoC1_FTP_layout(self):
        SoC1_FTP_layout = QFormLayout()
        SoC1_FTP_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.SoC1_FTP_username_label = QLabel('FTP Username')
        self.SoC1_FTP_username_label.setEnabled(False)

        self.SoC1_FTP_username_input = QLineEdit()
        self.SoC1_FTP_username_input.setFixedWidth(150)
        self.SoC1_FTP_username_input.setPlaceholderText('Enter Username')
        self.SoC1_FTP_username_input.textChanged.connect(self.update_button_states)
        self.SoC1_FTP_username_input.setEnabled(False)

        SoC1_FTP_layout.addRow(self.SoC1_FTP_username_label, self.SoC1_FTP_username_input)

        self.SoC1_FTP_password_label = QLabel('FTP Password')
        self.SoC1_FTP_password_label.setEnabled(False)

        self.SoC1_FTP_password_input = QLineEdit()
        self.SoC1_FTP_password_input.setFixedWidth(150)
        self.SoC1_FTP_password_input.setPlaceholderText('Enter Password')
        self.SoC1_FTP_password_input.textChanged.connect(self.update_button_states)
        self.SoC1_FTP_password_input.setEnabled(False)

        SoC1_FTP_layout.addRow(self.SoC1_FTP_password_label, self.SoC1_FTP_password_input)
        return SoC1_FTP_layout

    def create_run_button_layout(self):
        run_button_layout = QHBoxLayout()

        self.run_button = QPushButton('RUN')
        self.run_button.setFixedSize(250, 50)
        self.run_button.setStyleSheet("QPushButton:enabled {font-size: 25px;} " + common_enabled_style + common_hover_style)
        self.run_button.clicked.connect(self.on_run_button_click)
        self.run_button.setEnabled(False)

        run_button_layout.addStretch()
        run_button_layout.addWidget(self.run_button)
        run_button_layout.addStretch()
        return run_button_layout    
   
    def read_ECU_configuration(self):
        try:
            with open('ECU_Config.json', 'r') as file:
                ecu_config = json.load(file)
                if 'RCAR' in ecu_config:
                    self.Rcar_IP_input.setText(ecu_config['RCAR']['IP'])
                    self.Rcar_telnet_username_input.setText(ecu_config['RCAR']['telnet_username'])
                    self.Rcar_telnet_password_input.setText(ecu_config['RCAR']['telnet_password'])
                    self.Rcar_FTP_username_input.setText(ecu_config['RCAR']['FTP_username'])
                    self.Rcar_FTP_password_input.setText(ecu_config['RCAR']['FTP_password'])
               
                if 'SoC0' in ecu_config:
                    self.SoC0_IP_input.setText(ecu_config['SoC0']['IP'])
                    self.SoC0_telnet_username_input.setText(ecu_config['SoC0']['telnet_username'])
                    self.SoC0_telnet_password_input.setText(ecu_config['SoC0']['telnet_password'])
                    self.SoC0_FTP_username_input.setText(ecu_config['SoC0']['FTP_username'])
                    self.SoC0_FTP_password_input.setText(ecu_config['SoC0']['FTP_password'])
               
                if 'SoC1' in ecu_config:
                    self.SoC1_IP_input.setText(ecu_config['SoC1']['IP'])
                    self.SoC1_telnet_username_input.setText(ecu_config['SoC1']['telnet_username'])
                    self.SoC1_telnet_password_input.setText(ecu_config['SoC1']['telnet_password'])
                    self.SoC1_FTP_username_input.setText(ecu_config['SoC1']['FTP_username'])
                    self.SoC1_FTP_password_input.setText(ecu_config['SoC1']['FTP_password'])
        except FileNotFoundError:
            pass
        except json.JSONDecodeError:
            print("Invalid JSON format")

    def Write_ECU_Configuration(self):
        ecu_input_fields = {}
        ecu_input_fields['RCAR'] = {
            'IP': self.Rcar_IP_input.text(),
            'telnet_username': self.Rcar_telnet_username_input.text(),
            'telnet_password': self.Rcar_telnet_password_input.text(),
            'FTP_username': self.Rcar_FTP_username_input.text(),
            'FTP_password': self.Rcar_FTP_password_input.text()
        }
       
        ecu_input_fields['SoC0'] = {
            'IP': self.SoC0_IP_input.text(),
            'telnet_username': self.SoC0_telnet_username_input.text(),
            'telnet_password': self.SoC0_telnet_password_input.text(),
            'FTP_username': self.SoC0_FTP_username_input.text(),
            'FTP_password': self.SoC0_FTP_password_input.text()
        }
       
        ecu_input_fields['SoC1'] = {
            'IP': self.SoC1_IP_input.text(),
            'telnet_username': self.SoC1_telnet_username_input.text(),
            'telnet_password': self.SoC1_telnet_password_input.text(),
            'FTP_username': self.SoC1_FTP_username_input.text(),
            'FTP_password': self.SoC1_FTP_password_input.text()
        }
       
        try:
            with open('ECU_Config.json', 'w') as file:
                json.dump(ecu_input_fields, file, indent=4)
        except Exception as e:
            print("Error writing to file: ", str(e))


    def on_button_click(self, label, edit_button):
        self.logger.info(f"{label} edit button is clicked")      
       
        try:
            self.setEnabled(False)

            if label == "CPU and Memory Utilization":
                dialog = CpuMemoryConfig(self)

            elif label == "Heap Memory":
                dialog = HeapMemoryConfig(self)
           
            elif label == "Startup Time":
                dialog = StartupTimeConfig(self)
           
            elif label == "Execution Time":
                dialog = ExecutionTimeConfig(self)

            elif label in diag_labels:
                dialog = DiagConfig(self)

            else:
                # self.logger.warning(f"Unknown label: {label}")
                QMessageBox.warning(self, f"{label}", "Configuration Dialog is not created")
                self.setEnabled(True)
                return

            dialog.setModal(True)
            dialog.exec_()

            self.setEnabled(True)
            self.check_KPIs_config(label, edit_button)
            self.update_run_button_status()

        except Exception as e:
            self.logger.debug(traceback.format_exc())
            self.setEnabled(True)

    def open_file_manager(self, label):
        try:
            current_dir = os.getcwd()
            path = os.path.join(current_dir, 'Reports', folder_names[label])
            os.makedirs(path, exist_ok=True)

            self.logger.info(path)

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
        enabled = state == Qt.Checked

        edit_button.setEnabled(enabled)
        folder_button.setEnabled(enabled)

        if enabled:            
            if checkbox_list is not None:
                for checkbox in checkbox_list:
                    if checkbox != current_checkbox:
                        checkbox.setEnabled(False)                    

            self.check_KPIs_config(label, edit_button)
        else:      
            edit_button.setStyleSheet("")

            if checkbox_list is not None:
                for checkbox in checkbox_list:
                    checkbox.setEnabled(True)
       
        # if label in diag_labels:
        #     self.padas_checkbox.setChecked(enabled)
        #     self.update_checkbox_states()

    def check_KPIs_config(self, label, edit_button):
        def set_button_style(is_valid):
            style = common_enabled_style_green if is_valid else common_enabled_style_red
            edit_button.setStyleSheet(style + common_hover_style)

        try:
            if label == "CPU and Memory Utilization":
                with open('./CPU_Memory_Utilization_Scripts/cpu_memory_utilization_config.json', 'r') as f:
                    data = json.load(f)

                threshold = data.get("Threshold", {})
                required_keys = {"TotalCPU", "TotalMemory"} | {f"CPU{i}" for i in range(8)}

                is_valid = (
                    required_keys.issubset(threshold.keys()) and
                    data.get("scriptExecutionTimeInSeconds") is not None and
                    data.get("defaultReportFilename") and
                    data.get("initialLoggingDelayInSeconds") is not None
                )
                set_button_style(is_valid)
                return is_valid
           
            elif label == "Heap Memory":
                with open('./Heap_Memory_Scripts/heap_memory_config.json', 'r') as f:
                    data = json.load(f)
               
                is_valid = (
                    data.get("delayInAppSelectInSeconds") is not None and
                    data.get("ReportFileName") and
                    data.get("heapMemoryCaptureIntervalInSeconds") is not None and
                    data.get("heapMonitoringTimePerAppInSeconds") is not None and
                    data.get("iterations") is not None
                )
                set_button_style(is_valid)
                return is_valid
           
            elif label == "Startup Time":
                with open('./Startup_Time_Scripts/startup_time_config.json', 'r') as file:
                    data = json.load(file)
               
                is_valid = (
                    isinstance(data.get("script-execution-time-in-seconds"), int) and
                    isinstance(data.get("iterations"), int) and
                    isinstance(data.get("threshold-in-seconds"), int) and
                    data.get("validate-startup-order") is not None and
                    isinstance(data.get("windows", {}), dict) and
                    data.get("windows", {}).get("isPathSet") is not None and
                    isinstance(data.get("windows", {}).get("dltViewerPath"), str) and
                    isinstance(data.get("PADAS", {}), dict) and
                    data.get("PADAS", {}).get("RCAR") is not None and
                    isinstance(data.get("Elite", {}), dict) and
                    data.get("Elite", {}).get("RCAR") is not None and
                    data.get("Elite", {}).get("SoC0") is not None and
                    data.get("Elite", {}).get("SoC1") is not None and
                    isinstance(data.get("ecu-config", []), list) and
                    all(
                        isinstance(item, dict) and
                        item.get("ecu-type") and
                        isinstance(item.get("startup-order", []), list) and
                        all(
                            isinstance(order, dict) and
                            order.get("type") and
                            order.get("apps")
                            for order in item.get("startup-order", [])
                        )
                        for item in data.get("ecu-config", [])
                    )
                )
                set_button_style(is_valid)
                return is_valid
           
            elif label == "Execution Time":
                with open('./Execution_Time_Scripts/Execution_Time_Config.json', 'r') as file:
                    data = json.load(file)

                is_valid = (
                    data.get("kev_duration") and
                    data.get("QNXInstalledPath") and
                    data.get("workspacePath") and
                    data.get("momenticsProjectName") and
                    data.get("kev_generation") is not None
                )

                if "PADAS" in data and data["PADAS"]["RCAR"]:
                    is_valid = is_valid and (
                        data.get("RCAR_report_name") and
                        isinstance(data.get("rcar_application_names"), list)
                    )

                elif "Elite" in data:
                    elite_rcar = data["Elite"].get("RCAR", False)
                    elite_soc0 = data["Elite"].get("SoC0", False)
                    elite_soc1 = data["Elite"].get("SoC1", False)

                    if elite_rcar:
                        is_valid = is_valid and (
                            data.get("RCAR_report_name") and
                            isinstance(data.get("rcar_application_names"), list)
                        )

                    if elite_soc0:
                        is_valid = is_valid and (
                            data.get("SOC0_report_name") and
                            isinstance(data.get("soc0_application_names"), list)
                        )

                    if elite_soc1:
                        is_valid = is_valid and (
                            data.get("SOC1_report_name") and
                            isinstance(data.get("soc1_application_names"), list)
                        )

                set_button_style(is_valid)
                return is_valid
           
            elif label in diag_labels:
                with open('DIAG_KPI_Config.json', 'r') as f:
                    data = json.load(f)

                is_valid = bool(data.get("excel_name"))
               
                set_button_style(is_valid)
                return is_valid

            else:
                set_button_style(False)                
                return False

        except (FileNotFoundError, json.JSONDecodeError):
            set_button_style(False)
            return False

    def set_widgets_enabled(self, widgets, enabled, checkbox):
        for widget in widgets:
            widget.setEnabled(enabled)
       
        if checkbox == self.RCar_checkbox or checkbox == self.padas_checkbox:
            IP_input = self.Rcar_IP_input
        elif checkbox == self.SoC0_checkbox:
            IP_input = self.SoC0_IP_input
        elif checkbox == self.SoC1_checkbox:
            IP_input = self.SoC1_IP_input
        else: return
       
        self.validate_ip_on_checkbox_state_change(checkbox, IP_input)

    def update_checkbox_states(self):
        checkbox_widget_map = {
            self.RCar_checkbox: [
                self.Rcar_IP_label, self.Rcar_IP_input,
                self.Rcar_telnet_username_label, self.Rcar_telnet_username_input,
                self.Rcar_telnet_password_label, self.Rcar_telnet_password_input,
                self.Rcar_FTP_username_label, self.Rcar_FTP_username_input,
                self.Rcar_FTP_password_label, self.Rcar_FTP_password_input
            ],
            self.SoC0_checkbox: [
                self.SoC0_IP_label, self.SoC0_IP_input,
                self.SoC0_telnet_username_label, self.SoC0_telnet_username_input,
                self.SoC0_telnet_password_label, self.SoC0_telnet_password_input,
                self.SoC0_FTP_username_label, self.SoC0_FTP_username_input,
                self.SoC0_FTP_password_label, self.SoC0_FTP_password_input
            ],
            self.SoC1_checkbox: [
                self.SoC1_IP_label, self.SoC1_IP_input,
                self.SoC1_telnet_username_label, self.SoC1_telnet_username_input,
                self.SoC1_telnet_password_label, self.SoC1_telnet_password_input,
                self.SoC1_FTP_username_label, self.SoC1_FTP_username_input,
                self.SoC1_FTP_password_label, self.SoC1_FTP_password_input
            ]
        }

        rcar_enabled = self.padas_checkbox.isChecked() or self.RCar_checkbox.isChecked()

        if self.padas_checkbox.isChecked():
            self.set_widgets_enabled(checkbox_widget_map[self.RCar_checkbox], rcar_enabled, self.padas_checkbox)
        else:
            self.set_widgets_enabled(checkbox_widget_map[self.RCar_checkbox], rcar_enabled, self.RCar_checkbox)

        for checkbox in [self.SoC0_checkbox, self.SoC1_checkbox]:
            self.set_widgets_enabled(checkbox_widget_map[checkbox], checkbox.isChecked(), checkbox)

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

        return self.update_button_states()      

    def validate_ip_on_checkbox_state_change(self, checkbox, IP_input):
        if checkbox.isChecked():
            if IP_input.text():
                if IP_input.hasAcceptableInput():
                    IP_input.setStyleSheet("")
                    return True
                else:
                    IP_input.setStyleSheet("border: 2px solid #FF0000")
                    return False
            else:
                IP_input.setStyleSheet("")
        else:
            IP_input.setStyleSheet("")

    def validate_IP(self, IP_input):
        if IP_input.text():

            if IP_input.hasAcceptableInput():
                IP_input.setStyleSheet("")
                return True
            else:
                IP_input.setStyleSheet("border: 2px solid #FF0000")
                return False
        else:
            IP_input.setStyleSheet("")

    def update_button_states(self):    
        if self.configuration_section_input_fields():
            self.IG_OFF_button.setEnabled(True)        
            self.IG_ON_button.setEnabled(True)
            self.configuration_status_label.setStyleSheet("background-color: #60A917; border: 0.5px solid #999999;")
            self.configuration_flag = True            
        else:
            self.IG_OFF_button.setEnabled(False)
            self.IG_ON_button.setEnabled(False)
            self.configuration_status_label.setStyleSheet("background-color: #E51400; border: 0.5px solid #999999;")

            self.configuration_flag = False    

        self.update_run_button_status()

    def configuration_section_input_fields(self):
        input_fields = []

        if self.padas_checkbox.isChecked() or self.RCar_checkbox.isChecked():
            if not self.Rcar_IP_input.hasAcceptableInput():
                return False
           
            input_fields.extend([
                self.Rcar_IP_input.text(),
                self.Rcar_telnet_username_input.text(),
                self.Rcar_telnet_password_input.text(),
                self.Rcar_FTP_username_input.text(),
                self.Rcar_FTP_password_input.text()
            ])
       
        if self.SoC0_checkbox.isChecked():
            if not self.SoC0_IP_input.hasAcceptableInput():
                return False
           
            input_fields.extend([
                self.SoC0_IP_input.text(),
                self.SoC0_telnet_username_input.text(),
                self.SoC0_telnet_password_input.text(),
                self.SoC0_FTP_username_input.text(),
                self.SoC0_FTP_password_input.text()
            ])
           
        if self.SoC1_checkbox.isChecked():
            if not self.SoC1_IP_input.hasAcceptableInput():
                return False
           
            input_fields.extend([
                self.SoC1_IP_input.text(),
                self.SoC1_telnet_username_input.text(),
                self.SoC1_telnet_password_input.text(),
                self.SoC1_FTP_username_input.text(),
                self.SoC1_FTP_password_input.text()
            ])                    
           
        if input_fields:  # Check if any of the checkboxes are checked
            input_fields.extend([
                self.relay_port_input.text(),
                self.relay_baudrate_input.text()
            ])
       
        # print("Input Fields:", input_fields)
       
        if not input_fields:  # If input_fields is empty, return False
            return False
        else:
            return all(input_fields)

    def IG_ON_Off(self):
        sender = self.sender()
        if sender == self.IG_ON_button:
            # Code to be executed when IG ON button is clicked
            self.logger.info("IG ON button clicked")
        elif sender == self.IG_OFF_button:
            # Code to be executed when IG OFF button is clicked
            self.logger.info("IG OFF button clicked")

    def validate_kpi_configurations(self):
        kpi_results = []
        for label, widgets in self.kpi_widgets.items():
            checkbox = widgets['checkbox']
            status_label = widgets['status_label']
            edit_button = widgets['edit_button']

            if checkbox.isChecked():
                result = self.check_KPIs_config(label, edit_button)
                kpi_results.append(result)      

        # Check if the list is empty or if any of the results are False
        if not kpi_results or any(not result for result in kpi_results):
            return False
        else:
            return True        

    def update_run_button_status(self):        
        if self.validate_kpi_configurations() and self.configuration_flag:
            self.run_button.setEnabled(True)            
        else:
            self.run_button.setEnabled(False)                    
   
    def on_run_button_click(self):
        ecu_input_fields = self.get_ecu_input_fields()
        self.run_and_update_config(ecu_input_fields)
        self.prepare_and_store_widget_states()

        self.thread = QThread()
        self.worker = Worker(ecu_input_fields, self.kpi_widgets)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.error_signal.connect(self.process_error)
        self.thread.finished.connect(self.thread.deleteLater)

        # Connect signals
        self.worker.update_status.connect(self.set_status_label_and_enable_widgets)
        self.worker.disable_widgets.connect(self.disable_all_widgets)
        self.worker.enable_widgets.connect(self.restore_widget_states)

        self.thread.start()
   
    def closeEvent(self, event):
        print("[MainWindow] Closing application...")

        try:
            if hasattr(self, 'worker') and self.worker:
                self.worker.request_stop()

            if hasattr(self, 'thread') and isinstance(self.thread, QThread):
                if self.thread.isRunning():  # This line is correct, isRunning() is a method
                    self.thread.quit()
                    self.thread.wait()

        except Exception as e:
            print(f"[MainWindow] Error during shutdown: {e}")

        print("[MainWindow] Closed cleanly.")
        event.accept()

    def process_error(self, message):
        self.logger.error(message)

    def get_ecu_input_fields(self):
        ecu_input_fields = {}

        if self.padas_checkbox.isChecked():
            ecu_input_fields['RCAR'] = {
                'IP': self.Rcar_IP_input.text(),
                'telnet_username': self.Rcar_telnet_username_input.text(),
                'telnet_password': self.Rcar_telnet_password_input.text(),
                'FTP_username': self.Rcar_FTP_username_input.text(),
                'FTP_password': self.Rcar_FTP_password_input.text()
            }
           
        if self.RCar_checkbox.isChecked():
            ecu_input_fields['RCAR'] = {
                'IP': self.Rcar_IP_input.text(),
                'telnet_username': self.Rcar_telnet_username_input.text(),
                'telnet_password': self.Rcar_telnet_password_input.text(),
                'FTP_username': self.Rcar_FTP_username_input.text(),
                'FTP_password': self.Rcar_FTP_password_input.text()
            }
           
        if self.SoC0_checkbox.isChecked():
            ecu_input_fields['SoC0'] = {
                'IP': self.SoC0_IP_input.text(),
                'telnet_username': self.SoC0_telnet_username_input.text(),
                'telnet_password': self.SoC0_telnet_password_input.text(),
                'FTP_username': self.SoC0_FTP_username_input.text(),
                'FTP_password': self.SoC0_FTP_password_input.text()
            }
           
        if self.SoC1_checkbox.isChecked():
            ecu_input_fields['SoC1'] = {
                'IP': self.SoC1_IP_input.text(),
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
                "Elite": {
                    "RCAR": self.RCar_checkbox.isChecked(),
                    "SoC0": self.SoC0_checkbox.isChecked(),
                    "SoC1": self.SoC1_checkbox.isChecked()
                },
                "PADAS": {
                    "RCAR": self.padas_checkbox.isChecked()
                },
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

        def update_config_file(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)

                data["ECU_setting"] = build_ecu_settings()
                data['serial-port-relay'] = self.relay_port_input.text()
                data['baudrate-relay'] = self.relay_baudrate_input.text()

                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=4)

            except FileNotFoundError:
                self.logger.error(f"Error: Configuration file '{file_path}' not found.")
            except json.JSONDecodeError:
                self.logger.error(f"Error: Configuration file '{file_path}' is not a valid JSON.")
            except KeyError as e:
                self.logger.error(f"Error: Missing expected key in ECU input fields: {e}")
            except Exception as e:
                self.logger.error(f"Unexpected error while updating '{file_path}': {e}")

        for label, widgets in self.kpi_widgets.items():
            if widgets['checkbox'].isChecked():
                if label == 'CPU and Memory Utilization':
                    update_config_file('./CPU_Memory_Utilization_Scripts/cpu_memory_utilization_config.json')
               
                elif label == 'Startup Time':
                    update_config_file('./Startup_Time_Scripts/startup_time_config.json')

                elif label == 'Execution Time':
                    update_config_file('./Execution_Time_Scripts/Execution_Time_Config.json')

                elif label in diag_labels:
                    try:
                        with open('DIAG_KPI_Config.json', 'r') as f:
                            data = json.load(f)

                        data["Current_Timestamp"] = datetime.now().strftime("%Y%m%d_%H-%M-%S")

                        # Update KPI checkbox states
                        for key in diag_labels:
                            data[key] = self.kpi_widgets[key]['checkbox'].isChecked()

                        with open('DIAG_KPI_Config.json', 'w') as f:
                            json.dump(data, f, indent=4)

                        update_config_file('DIAG_KPI_Config.json')
                    except Exception as e:
                        self.logger.error(f"Error updating DIAG_KPI_Config.json: {e}")

    def prepare_and_store_widget_states(self):
        self.kpi_widgets_status = {}
        for label, widgets in self.kpi_widgets.items():
            checkbox = widgets['checkbox']
            status_label = widgets['status_label']
            edit_button = widgets['edit_button']
            folder_button = widgets['folder_button']

            status_label.setStyleSheet("background-color: #D0CEE2; border: 0.5px solid #999999;")
            if checkbox.isChecked():
                status_label.setStyleSheet("background-color: #FFFF00; border: 0.5px solid #999999;")

            self.kpi_widgets_status[label] = {
                'checkbox': checkbox.isEnabled(),
                'edit_button': edit_button.isEnabled(),
                'folder_button': folder_button.isEnabled()
            }

    def set_status_label_and_enable_widgets(self, label, color):
        if label in self.kpi_widgets:
            widgets = self.kpi_widgets[label]
            widgets['status_label'].setStyleSheet(
                f"background-color: {color}; border: 0.5px solid #999999;"
            )
            widgets['checkbox'].setEnabled(True)
            widgets['folder_button'].setEnabled(True)

    def disable_all_widgets(self):
        for widget in self.findChildren((QPushButton, QCheckBox, QLineEdit)):
            widget.setEnabled(False)

    def restore_widget_states(self):
        for label, widgets in self.kpi_widgets.items():
            if label in self.kpi_widgets_status:
                widgets['checkbox'].setEnabled(self.kpi_widgets_status[label]['checkbox'])
                widgets['edit_button'].setEnabled(self.kpi_widgets_status[label]['edit_button'])
                widgets['folder_button'].setEnabled(self.kpi_widgets_status[label]['folder_button'])

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
        self.Rcar_IP_input.setEnabled(self.padas_checkbox.isChecked() or self.RCar_checkbox.isChecked())
        self.Rcar_telnet_username_input.setEnabled(self.padas_checkbox.isChecked() or self.RCar_checkbox.isChecked())
        self.Rcar_telnet_password_input.setEnabled(self.padas_checkbox.isChecked() or self.RCar_checkbox.isChecked())
        self.Rcar_FTP_username_input.setEnabled(self.padas_checkbox.isChecked() or self.RCar_checkbox.isChecked())
        self.Rcar_FTP_password_input.setEnabled(self.padas_checkbox.isChecked() or self.RCar_checkbox.isChecked())

        self.SoC0_IP_input.setEnabled(self.SoC0_checkbox.isChecked())
        self.SoC0_telnet_username_input.setEnabled(self.SoC0_checkbox.isChecked())
        self.SoC0_telnet_password_input.setEnabled(self.SoC0_checkbox.isChecked())
        self.SoC0_FTP_username_input.setEnabled(self.SoC0_checkbox.isChecked())
        self.SoC0_FTP_password_input.setEnabled(self.SoC0_checkbox.isChecked())

        self.SoC1_IP_input.setEnabled(self.SoC1_checkbox.isChecked())
        self.SoC1_telnet_username_input.setEnabled(self.SoC1_checkbox.isChecked())
        self.SoC1_telnet_password_input.setEnabled(self.SoC1_checkbox.isChecked())
        self.SoC1_FTP_username_input.setEnabled(self.SoC1_checkbox.isChecked())
        self.SoC1_FTP_password_input.setEnabled(self.SoC1_checkbox.isChecked())

        # Enable relay port and baudrate input fields
        self.relay_port_input.setEnabled(True)
        self.relay_baudrate_input.setEnabled(True)            

if __name__ == "__main__":
    app = QApplication(sys.argv)

    main_window = MainWindow()
    main_window.show()

    sys.exit(app.exec_())