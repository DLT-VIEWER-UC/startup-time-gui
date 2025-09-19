from imports_utils import *
from CPU_Memory_Utilization_Scripts.Integrated_CPU_Memory_Measurement import CPU_Memory_measurement

class Worker(QObject):
    finished = pyqtSignal()
    update_status = pyqtSignal(str, str)
    disable_widgets = pyqtSignal()
    enable_widgets = pyqtSignal()

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
            time.sleep(10)
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
        for label in labels:
            widgets = self.kpi_widgets.get(label)

            if self._stop_requested:
                return

            if widgets and widgets['checkbox'].isChecked():                
                try:
                    if label == 'CPU and Memory Utilization':
                        # from CPU_Memory_Utilization_Scripts.Integrated_CPU_Memory_Measurement import CPU_Memory_measurement
                        status = CPU_Memory_measurement()
                        color = "#60A917" if status else "#E51400"
                   
                    elif label == 'Heap Memory':
                        from Heap_Memory_Scripts.Heap_Memory_Utilization import RUN_HEAP_MEMORY_SCRIPT
                        status = RUN_HEAP_MEMORY_SCRIPT()
                        color = "#60A917" if status else "#E51400"

                    elif label == 'Startup Time':
                        from Startup_Time_Scripts.Applications_StartupTime_IG_ON import start_startup_time_measurement
                        status = start_startup_time_measurement(py_logger)
                        color = "#60A917" if status else "#E51400"
                   
                    elif label == 'Cyclic and Turnaround Time':
                        from Cyclic_Turnaround_Time_Scripts.language_switcher import start_cyclic_turnaround_time_measurement
                        status = start_cyclic_turnaround_time_measurement()
                        color = "#60A917" if status else "#E51400"
                   
                    elif label == 'Throughput and Fault Injection':
                        from Throughput_Scripts.Integrated_Throughput import start_throughput
                        status = start_throughput()
                        color = "#60A917" if status else "#E51400"
                   
                    elif label == 'Execution Time':
                        from Execution_Time_Scripts.Execution_Time_Measurement_Script import start_execution_time_measurement
                        status = start_execution_time_measurement()
                        color = "#60A917" if status else "#E51400"
                   
                    elif label == 'Shutdown Time':
                        from Shutdown_Time_Scripts.Applications_ShutdownTime_IG_ON import  start_shutdown_time_measurement
                        status = start_shutdown_time_measurement(py_logger)
                        color = "#60A917" if status else "#E51400"
                   
                    elif label == 'Continuous KEV':
                        flagManagerObject = FlagManager()
                        subprocess.run(["python", "./Continuous_KEV_Scripts/main.py"])

                        eventTriggerScriptRunStatus = flagManagerObject.get_event_trigger_status_flag()
                        eventLogMoverRunStatus = flagManagerObject.get_log_mover_status_flag()
                       
                        status = False
                        if eventTriggerScriptRunStatus and eventLogMoverRunStatus:
                            status = True
                       
                        color = "#60A917" if status else "#E51400"
                   
                    elif label == 'Event Trigger KEV':
                        flagManagerObject = FlagManager()
                        subprocess.run(["python", "./Event_Trigger_KEV_Scripts/main.py"])

                        eventTriggerScriptRunStatus = flagManagerObject.get_event_trigger_status_flag()
                        eventLogMoverRunStatus = flagManagerObject.get_log_mover_status_flag()
                       
                        status = False
                        if eventTriggerScriptRunStatus and eventLogMoverRunStatus:
                            status = True                            
                       
                        color = "#60A917" if status else "#E51400"
                   
                    elif label == "RAM Monitor":
                        from RAM_Measurement_Scripts.test_executor import start_RAM_measurement
                        status = start_RAM_measurement()
                        color = "#60A917" if status else "#E51400"

                    elif label == "Event Trigger RAM Monitor":
                        from Event_Trigger_RAM_Measurement_Scripts.test_executor import start_event_trigger_RAM_measurement
                        status = start_event_trigger_RAM_measurement()
                        color = "#60A917" if status else "#E51400"
                   
                    elif label == "APL Communication Layout":
                        from APL_Communication_Layout_Scripts.test_executor import start_APL_Communication
                        status = start_APL_Communication()
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
                                py_logger.warning(f"file path not found {report_path}")

                        color = "#60A917" if status else "#E51400"    
                    else:
                        color = "#E51400"        

                    self.update_status.emit(label, color)
                    time.sleep(0.1)
                except Exception as e:
                    py_logger.error(f"Error in run_function: {e}")  
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
        self.manage_stop_flag(create=False)    
   
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

        self.download_button = QPushButton("Download Logs!")
        self.download_button.setFixedSize(150, 35)
        self.download_button.setStyleSheet(common_enabled_style + common_hover_style)
        self.download_button.clicked.connect(self.download_console_output)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.clear_logs_button)
        button_layout.addWidget(self.download_button)

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

        py_logger.info("Gen2 PF GUI Tester Tool is Successfully Launched.")

    def write_to_console(self, text):
        self.console_output.moveCursor(self.console_output.textCursor().End)
        self.console_output.insertPlainText(text)
        self.console_output.moveCursor(self.console_output.textCursor().End)

    def download_console_output(self):
        if not self.console_output.toPlainText():
            return
       
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Console Output", "", "Text Files (*.txt);;All Files (*)", options=options)
        if file_path:
            with open(file_path, 'w') as file:
                file.write(self.console_output.toPlainText())

    def set_window_properties(self) -> None:
        """
        Sets the properties of the window, including its title, icon, size, and position.
        """
        # Set the title of the window
        self.setWindowTitle("Gen2 Platform Validation GUI Tester Tool")
       
        # Set the icon of the window
        self.setWindowIcon(QIcon('KPIT_logo.png'))

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
        window_width = int(screen_width * 0.6)  # 60% of the screen width
        window_height = int(screen_height * 0.95)  # 95% of the screen height

        # Ensure the window dimensions do not exceed the screen dimensions
        window_width = min(window_width, screen_width)
        window_height = min(window_height, screen_height)

        # Calculate the position to center the window horizontally and position at top
        x = screen_geometry.x() + (screen_width - window_width) // 2
        y = screen_geometry.y() + 50  # Position at top

        # Set the geometry and fixed size of the window
        self.setGeometry(x, y, window_width, window_height)

        # Remove the maximize button
        # self.setWindowFlags(self.windowFlags() & ~Qt.WindowMaximizeButtonHint)

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

        validator = QIntValidator(9600, 115200)
        locale = QLocale("C")  # Use the "C" locale, which does not use a comma as a thousands separator
        validator.setLocale(locale)

        self.relay_baudrate_input = QLineEdit()        
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
       
        self.Rcar_IP_input = QLineEdit()
        # self.Rcar_IP_input.setFixedWidth(150)
        self.Rcar_IP_input.setPlaceholderText('Enter IP Address')
        self.Rcar_IP_input.setValidator(ip_address_validator)
        self.Rcar_IP_input.textChanged.connect(lambda: self.update_button_states())
        self.Rcar_IP_input.setEnabled(False)
       
        Rcar_telent_layout.addRow(self.Rcar_IP_label, self.Rcar_IP_input)
       
        self.Rcar_telnet_username_label = QLabel('Telnet Username')
        self.Rcar_telnet_username_label.setEnabled(False)
       
        self.Rcar_telnet_username_input = QLineEdit()
        self.Rcar_telnet_username_input.setObjectName('Rcar_telnet_username_input')
        # self.Rcar_telnet_username_input.setFixedWidth(150)
        self.Rcar_telnet_username_input.setPlaceholderText('Enter Username')
        self.Rcar_telnet_username_input.textChanged.connect(lambda: self.update_button_states())
        self.Rcar_telnet_username_input.setEnabled(False)
       
        Rcar_telent_layout.addRow(self.Rcar_telnet_username_label, self.Rcar_telnet_username_input)
       
        self.Rcar_telnet_password_label = QLabel('Telnet Password')
        self.Rcar_telnet_password_label.setEnabled(False)
       
        self.Rcar_telnet_password_input = QLineEdit()
        self.Rcar_telnet_password_input.setObjectName('Rcar_telnet_password_input')
        # self.Rcar_telnet_password_input.setFixedWidth(150)  
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
        # self.Rcar_FTP_username_input.setFixedWidth(150)
        self.Rcar_FTP_username_input.setPlaceholderText('Enter Username')
        self.Rcar_FTP_username_input.textChanged.connect(lambda: self.update_button_states())
        self.Rcar_FTP_username_input.setEnabled(False)

        Rcar_FTP_layout.addRow(self.Rcar_FTP_username_label, self.Rcar_FTP_username_input)

        self.Rcar_FTP_password_label = QLabel('FTP Password')
        self.Rcar_FTP_password_label.setEnabled(False)

        self.Rcar_FTP_password_input = QLineEdit()
        self.Rcar_FTP_password_input.setObjectName('Rcar_FTP_password_input')
        # self.Rcar_FTP_password_input.setFixedWidth(150)
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

        self.SoC0_IP_input = QLineEdit()
        # self.SoC0_IP_input.setFixedWidth(150)
        self.SoC0_IP_input.setPlaceholderText('Enter IP Address')
        self.SoC0_IP_input.setValidator(ip_address_validator)
        self.SoC0_IP_input.textChanged.connect(lambda: self.update_button_states())
        self.SoC0_IP_input.setEnabled(False)

        SoC0_telent_layout.addRow(self.SoC0_IP_label, self.SoC0_IP_input)

        self.SoC0_telnet_username_label = QLabel('Telnet Username')
        self.SoC0_telnet_username_label.setEnabled(False)

        self.SoC0_telnet_username_input = QLineEdit()
        self.SoC0_telnet_username_input.setObjectName('SoC0_telnet_username_input')
        # self.SoC0_telnet_username_input.setFixedWidth(150)
        self.SoC0_telnet_username_input.setPlaceholderText('Enter Username')
        self.SoC0_telnet_username_input.textChanged.connect(lambda: self.update_button_states())
        self.SoC0_telnet_username_input.setEnabled(False)

        SoC0_telent_layout.addRow(self.SoC0_telnet_username_label, self.SoC0_telnet_username_input)

        self.SoC0_telnet_password_label = QLabel('Telnet Password')
        self.SoC0_telnet_password_label.setEnabled(False)

        self.SoC0_telnet_password_input = QLineEdit()
        self.SoC0_telnet_password_input.setObjectName('SoC0_telnet_password_input')
        # self.SoC0_telnet_password_input.setFixedWidth(150)
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
        # self.SoC0_FTP_username_input.setFixedWidth(150)
        self.SoC0_FTP_username_input.setPlaceholderText('Enter Username')
        self.SoC0_FTP_username_input.textChanged.connect(lambda: self.update_button_states())
        self.SoC0_FTP_username_input.setEnabled(False)

        SoC0_FTP_layout.addRow(self.SoC0_FTP_username_label, self.SoC0_FTP_username_input)

        self.SoC0_FTP_password_label = QLabel('FTP Password')
        self.SoC0_FTP_password_label.setEnabled(False)

        self.SoC0_FTP_password_input = QLineEdit()
        self.SoC0_FTP_password_input.setObjectName('SoC0_FTP_password_input')
        # self.SoC0_FTP_password_input.setFixedWidth(150)
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

        self.SoC1_IP_input = QLineEdit()
        # self.SoC1_IP_input.setFixedWidth(150)
        self.SoC1_IP_input.setPlaceholderText('Enter IP Address')
        self.SoC1_IP_input.setValidator(ip_address_validator)
        self.SoC1_IP_input.textChanged.connect(lambda: self.update_button_states())
        self.SoC1_IP_input.setEnabled(False)

        SoC1_telent_layout.addRow(self.SoC1_IP_label, self.SoC1_IP_input)

        self.SoC1_telnet_username_label = QLabel('Telnet Username')
        self.SoC1_telnet_username_label.setEnabled(False)

        self.SoC1_telnet_username_input = QLineEdit()
        self.SoC1_telnet_username_input.setObjectName('SoC1_telnet_username_input')
        # self.SoC1_telnet_username_input.setFixedWidth(150)
        self.SoC1_telnet_username_input.setPlaceholderText('Enter Username')
        self.SoC1_telnet_username_input.textChanged.connect(lambda: self.update_button_states())
        self.SoC1_telnet_username_input.setEnabled(False)

        SoC1_telent_layout.addRow(self.SoC1_telnet_username_label, self.SoC1_telnet_username_input)

        self.SoC1_telnet_password_label = QLabel('Telnet Password')
        self.SoC1_telnet_password_label.setEnabled(False)

        self.SoC1_telnet_password_input = QLineEdit()
        self.SoC1_telnet_password_input.setObjectName('SoC1_telnet_password_input')
        # self.SoC1_telnet_password_input.setFixedWidth(150)
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
        # self.SoC1_FTP_username_input.setFixedWidth(150)
        self.SoC1_FTP_username_input.setPlaceholderText('Enter Username')
        self.SoC1_FTP_username_input.textChanged.connect(lambda: self.update_button_states())
        self.SoC1_FTP_username_input.setEnabled(False)

        SoC1_FTP_layout.addRow(self.SoC1_FTP_username_label, self.SoC1_FTP_username_input)

        self.SoC1_FTP_password_label = QLabel('FTP Password')
        self.SoC1_FTP_password_label.setEnabled(False)

        self.SoC1_FTP_password_input = QLineEdit()
        self.SoC1_FTP_password_input.setObjectName('SoC1_FTP_password_input')
        # self.SoC1_FTP_password_input.setFixedWidth(150)
        self.SoC1_FTP_password_input.setPlaceholderText('Enter Password')
        self.SoC1_FTP_password_input.textChanged.connect(lambda: self.update_button_states())
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
           
            if 'Relay' in ecu_config:
                self.relay_port_input.setText(ecu_config['Relay']['relay_port'])
                self.relay_baudrate_input.setText(str(ecu_config['Relay']['relay_baudrate']))

        except FileNotFoundError:
            pass
        except json.JSONDecodeError:
            py_logger.error("Invalid JSON format")

    def Write_ECU_Configuration(self):
        try:
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

            ecu_input_fields['Relay'] = {
                'relay_port': self.relay_port_input.text(),
                'relay_baudrate': int(self.relay_baudrate_input.text())
            }
       
            with open('ECU_Config.json', 'w') as file:
                json.dump(ecu_input_fields, file, indent=4)
        except Exception as e:
            print("Error writing to file: ", str(e))

    def on_button_click(self, label, edit_button, checkbox, folder_button):        
        try:
            self.setEnabled(False)

            if label == "CPU and Memory Utilization":
                from cpu_memory_utilization_config_window import CpuMemoryConfig
                dialog = CpuMemoryConfig(self, checkbox.isChecked())

            elif label == "Heap Memory":
                from heap_memory_config_window import HeapMemoryConfig
                dialog = HeapMemoryConfig(self, checkbox.isChecked())
           
            elif label == "Startup Time":
                from startup_time_config_window import StartupTimeConfig
                dialog = StartupTimeConfig(self, checkbox.isChecked())
           
            elif label == "Cyclic and Turnaround Time":
                from cyclic_turnaround_time_config_window import CyclicTurnaroundConfig
                dialog = CyclicTurnaroundConfig(self, checkbox.isChecked())
           
            elif label=='Throughput and Fault Injection':
                from throughput_config_window import ThroughputConfig
                dialog= ThroughputConfig(self, checkbox.isChecked())
           
            elif label == "Execution Time":
                from execution_time_config_window import ExecutionTimeConfig
                dialog = ExecutionTimeConfig(self, checkbox.isChecked())

            elif label == "Shutdown Time":
                from shutdown_time_config_window import ShutdownTimeConfig
                dialog = ShutdownTimeConfig(self, checkbox.isChecked())
           
            elif label == "Event Trigger KEV":
                from event_trigger_KEV_config_window import EventTriggerKEVConfig
                dialog = EventTriggerKEVConfig(self, checkbox.isChecked())
           
            elif label == "Continuous KEV":
                from Continous_KEV_config_window import ContinuousKEVConfig
                dialog = ContinuousKEVConfig(self, checkbox.isChecked())
               
            elif label == "RAM Monitor":
                from XCP_RAM_measurment_config_window import XcpRAMMonitoringConfig
                dialog = XcpRAMMonitoringConfig(self, checkbox.isChecked())
           
            elif label == "Event Trigger RAM Monitor":
                from XCP_RAM_measurement_event_trigger_config_window import XCPRAMMonitorEventTriggerConfig
                dialog = XCPRAMMonitorEventTriggerConfig(self, checkbox.isChecked())
           
            elif label == "APL Communication Layout":
                from XCP_APL_communication_layout_config_window import XCPAPLCommConfig
                dialog = XCPAPLCommConfig(self, checkbox.isChecked())

            elif label in diag_labels:
                from diag_config_window import DiagConfig
                dialog = DiagConfig(self, label, checkbox.isChecked())

            else:
                QMessageBox.information(self, f"{label}", "Configuration Dialog implementation is in progress.")
                self.setEnabled(True)
                return

            dialog.setModal(True)
            dialog.exec_()

            self.setEnabled(True)
            self.check_KPIs_config(label, edit_button, checkbox, folder_button)

            if not self.is_test_in_progress:
                self.update_run_button_status()

        except Exception as e:
            py_logger.error(traceback.format_exc())
            self.setEnabled(True)

    def open_file_manager(self, label):
        try:
            current_dir = os.getcwd()
            path = os.path.join(current_dir, 'Reports', folder_names[label])
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
                # self.check_KPIs_config(label, edit_button)
            else:  
                # edit_button.setEnabled(enabled)    
                # edit_button.setStyleSheet("")

                if checkbox_list is not None:
                    for checkbox in checkbox_list:
                        checkbox.setEnabled(True)
        except Exception as e:
            py_logger.error(f"Error in toggle_buttons: {e}")

    def show_warning_once(self, label):
        # Check if a message box is already open
        if hasattr(self, 'msg_box') and self.msg_box is not None and self.msg_box.isVisible():
            return  # Don't show again if already visible

        # Create and show the message box
        self.msg_box = QMessageBox(self)
        self.msg_box.setIcon(QMessageBox.Warning)
        self.msg_box.setWindowTitle(f'{label} Configuration Mismatch')
        self.msg_box.setText(f"'ECU Selection' in the main window does not match the '{label}' configuration in the config window.\n Please also check other KPIs configuration highlighted in red.")
        self.msg_box.setStandardButtons(QMessageBox.Ok)
        self.msg_box.show()

        # from PyQt5.QtCore import QTimer
        # Auto-close after 3 seconds
        # QTimer.singleShot(3000, msg_box.close)

    # Function to check if a folder with a specific date format exists
    def is_folder_with_date_format_present(self, label):
        try:
            # Get the current working directory
            current_dir = os.getcwd()
           
            # Construct the path to the reports folder
            path = os.path.join(current_dir, 'Reports', folder_names[label])
           
            # Check if the path exists
            if not os.path.exists(path):
                # py_logger.info(f"The path {path} does not exist.")
                # Return False to indicate that the path does not exist
                return False

            # Check for folders with the specified date format
            for filename in os.listdir(path):
                # Check if the filename is a directory
                if os.path.isdir(os.path.join(path, filename)):
                    # Define the expected date formats
                    for date_format in ["%Y%m%d_%H-%M-%S", "%Y-%m-%d_%H-%M-%S", "%Y-%m-%d-%H-%M-%S"]:
                        try:
                            # Attempt to parse the filename as a date using the specified format
                            datetime.strptime(filename, date_format)
                            # py_logger.info(f"Folder found with format '{date_format}': {filename}")
                            # Return True to indicate that a folder with the expected date format was found
                            return True
                        except ValueError:
                            # If the filename does not match the date format, continue to the next iteration
                            pass            
           
            # py_logger.info("No folders found with the expected date format.")
            # Return False to indicate that no folders with the expected date format were found
            return False

        except KeyError as e:
            # Handle the exception if the label is not found in the folder_names dictionary
            py_logger.error(f"Error: Label '{label}' not found in folder_names dictionary.")
            return False

        except OSError as e:
            # Handle the exception if there is an error accessing the file system
            py_logger.error(f"Error: {e}")
            return False

        except Exception as e:
            # Handle any other unexpected exceptions
            py_logger.error(f"An unexpected error occurred: {e}")
            return False

    def check_KPIs_config(self, label, edit_button, checkbox, folder_button):
        def set_button_style(is_valid):
            style = common_enabled_style_green if is_valid else common_enabled_style_red
            edit_button.setStyleSheet(style + common_hover_style)

        def validate_ECU_configuration(data):
            try:
                # Flatten both dictionaries for easier comparison
                expected_config = data['ECU_setting']
                current_config = self.ecu_selection_status

                for ecu_type, settings in expected_config.items():
                    if isinstance(settings, dict):  # Only process nested ECU sections
                        for key, value in settings.items():
                            if value:  # If expected is True
                                if not current_config.get(ecu_type, {}).get(key, False):
                                    set_button_style(False)

                                    # if self.is_any_ecu_selected_flag:
                                    #     self.show_warning_once(label)

                                    return False

                set_button_style(True)
                return True  # All required True values are matched

            except Exception as e:
                py_logger.error(f"Error validating ECU configuration '{label}': {e}")
                set_button_style(False)
                return False

        folder_button.setEnabled(self.is_folder_with_date_format_present(label))    

        try:
            is_valid = True
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
                    data.get("rcar_application_names") is not None and
                    data.get("soc0_application_names") is not None and
                    data.get("soc1_application_names") is not None and
                    data.get("Test_Report_Name") and
                    data.get("heapMemoryCaptureIntervalInSeconds") is not None and
                    data.get("heapMonitoringTimePerAppInSeconds") is not None and
                    data.get("QNXInstalledPath") is not None
                )
                if is_valid and self.is_any_ecu_selected_flag and checkbox.isChecked():
                    return bool(validate_ECU_configuration(data))
                else:
                    set_button_style(is_valid)
                    return is_valid
           
            elif label == "Startup Time":
                with open('./Startup_Time_Scripts/startup_time_config.json', 'r') as file:
                    data = json.load(file)
               
                is_valid = True

                if not data.get("Pre-Generated Logs"):
                    is_valid = is_valid and (
                        isinstance(data.get("DLT-Viewer Log Capture Time"), int) and
                        data.get("DLT-Viewer Log Capture Time") > 0 and
                        isinstance(data.get("Power ON-OFF Delay"), int) and
                        data.get("Power ON-OFF Delay") > 0 and
                        isinstance(data.get("windows"), dict) and
                        isinstance(data.get("windows", {}).get("Is Environment Path Set"), bool)
                    )

                    if not data.get("windows", {}).get("Is Environment Path Set"):
                        is_valid = is_valid and (
                            isinstance(data.get("windows", {}).get("DLT-Viewer Installed Path"), str) and
                            data.get("windows", {}).get("DLT-Viewer Installed Path")
                        )

                is_valid = is_valid and (
                    isinstance(data.get("ecu-config"), list) and
                    all(isinstance(ecu, dict) for ecu in data.get("ecu-config", [])) and
                    all(isinstance(ecu.get("ecu-type"), str) and
                        isinstance(ecu.get("startup-order"), list) and
                        all(isinstance(order, dict) for order in ecu.get("startup-order", [])) and
                        all(isinstance(order.get("Order Type"), str) and
                            isinstance(order.get("Applications"), str) for order in ecu.get("startup-order", [])) and
                        isinstance(ecu.get("threshold-config"), list)
                        for ecu in data.get("ecu-config", []))
                )

                if is_valid and self.is_any_ecu_selected_flag and checkbox.isChecked():
                    return bool(validate_ECU_configuration(data))
                else:
                    set_button_style(is_valid)
                    return is_valid
           
            elif label == 'Cyclic and Turnaround Time':
                with open('./Cyclic_Turnaround_Time_Scripts/cyclic_turnaround_config.json', 'r') as file:
                    data = json.load(file)

                is_valid = (
                    isinstance(data.get("QNXInstalledPath"), str) and
                    data.get("QNXInstalledPath") and
                    isinstance(data.get("GenerateKEVFile"), bool) and
                    isinstance(data.get("Test_Report_Name"), str) and
                    data.get("Test_Report_Name") and
                    isinstance(data.get("Threshold Margin"), int) and
                    data.get("Threshold Margin") > 0 and
                    isinstance(data.get("Application_Settings"), list) and
                    data.get("Application_Settings") and
                    all(
                        isinstance(app.get("Application"), str) and
                        isinstance(app.get("CyclicThreshold"), int) and
                        isinstance(app.get("TurnaroundThreshold"), int) and
                        isinstance(app.get("Soc"), str)
                        for app in data.get("Application_Settings", [])
                    )
                )

                if data.get("GenerateKEVFile"):
                    is_valid = is_valid and (
                        isinstance(data.get("Kev_duration"), int) and
                        data.get("Kev_duration") > 0
                    )

                if is_valid and self.is_any_ecu_selected_flag and checkbox.isChecked():
                    return bool(validate_ECU_configuration(data))
                else:
                    set_button_style(is_valid)
                    return is_valid
           
            elif label =='Throughput and Fault Injection':
                with open('./Throughput_Scripts/throughput_faultinjection_config.json','r')as file:
                    data=json.load(file)
                is_valid=(
                    isinstance(data.get('scriptExecutionTimeInSeconds'),int) and
                    isinstance(data.get('threshold_option'),int) and
                    isinstance(data.get('ReportFileName'),str) and
                    isinstance(data.get('power_on_off_delay'),int)
                )                
               
                if is_valid and self.is_any_ecu_selected_flag and checkbox.isChecked():
                    return bool(validate_ECU_configuration(data))
                else:
                    set_button_style(is_valid)
                    return is_valid
           
            elif label == "Execution Time":
                with open('./Execution_Time_Scripts/Execution_Time_Config.json', 'r') as file:
                    data = json.load(file)

                is_valid = (
                    isinstance(data.get("QNXInstalledPath"), str) and
                    data.get("QNXInstalledPath") and
                    isinstance(data.get("workspacePath"), str) and
                    data.get("workspacePath") and
                    isinstance(data.get("test_report_name"), str) and
                    data.get("test_report_name") and
                    isinstance(data.get("Application_Settings"), dict) and
                    isinstance(data.get("Application_Settings", {}).get("padas_application_names"), list) and
                    all(isinstance(app, str) for app in data.get("Application_Settings", {}).get("padas_application_names", [])) and
                    isinstance(data.get("Application_Settings", {}).get("rcar_application_names"), list) and
                    all(isinstance(app, str) for app in data.get("Application_Settings", {}).get("rcar_application_names", [])) and
                    isinstance(data.get("Application_Settings", {}).get("soc0_application_names"), list) and
                    all(isinstance(app, str) for app in data.get("Application_Settings", {}).get("soc0_application_names", [])) and
                    isinstance(data.get("Application_Settings", {}).get("soc1_application_names"), list) and
                    all(isinstance(app, str) for app in data.get("Application_Settings", {}).get("soc1_application_names", []))
                )

                if data.get("kev_generation"):
                    is_valid = is_valid and (
                        isinstance(data.get("kev_duration"), int) and
                        data.get("kev_duration") > 0
                    )

                if is_valid and self.is_any_ecu_selected_flag and checkbox.isChecked():
                    return bool(validate_ECU_configuration(data))
                else:
                    set_button_style(is_valid)
                    return is_valid
           
            elif label == "Shutdown Time":
                with open('./Shutdown_Time_Scripts/shutdown_time_config.json', 'r') as file:
                    data = json.load(file)
               
                is_valid = (
                    isinstance(data.get("DLT-Viewer Log Capture Time"), int) and
                    isinstance(data.get("Iterations"), int) and
                    data.get("windows", {}).get("Is Environment Path Set") is not None and
                    isinstance(data.get("windows", {}).get("DLT-Viewer Installed Path"), str)                    
                )                

                set_button_style(is_valid)
                return is_valid
            elif label == "Continuous KEV":
                with open('./Continuous_KEV_Scripts/kev_gen_and_logMover_config.json', 'r') as file:
                    data = json.load(file)
               
                is_valid = (

                    isinstance(data.get("kevlogger", {}), dict) and
                    isinstance(data.get("kevlogger", {}).get("kev_duration"), int) and
                    data.get("kevlogger", {}).get("kev_duration") > 0 and                    
                    data.get("kevlogger", {}).get("TerminateAllECUExecutionOnError") is not None and
                    isinstance(data.get("logMover", {}), dict) and
                    isinstance(data.get("logMover", {}).get("pythonScriptRunTime"), int) and
                    data.get("logMover", {}).get("pythonScriptRunTime") > 0 and
                    data.get("logMover", {}).get("await_file_transfer") is not None and
                    isinstance(data.get("filterEvents", {}), dict) and
                    all(data.get("filterEvents", {}).get(param) is not None for param in ["disableKernelcallsclass", "disableInterruptclass", "disableProcessclass", "disableThreadclass", "disableVThreadclass", "disableCommunicationclass", "disableSystemclass"])
                )

                set_button_style(is_valid)
                return is_valid
           
            elif label == "Event Trigger KEV":
                with open('./Event_Trigger_KEV_Scripts/kev_gen_and_logMover_config.json', 'r') as file:
                    data = json.load(file)
               
                is_valid = (
                    isinstance(data.get("kevlogger", {}), dict) and
                    isinstance(data.get("kevlogger", {}).get("kev_duration"), int) and
                    data.get("kevlogger", {}).get("kev_duration") > 0 and
                    isinstance(data.get("kevlogger", {}).get("reportName"), str) and
                    data.get("kevlogger", {}).get("reportName") and
                    isinstance(data.get("kevlogger", {}).get("cpu_stable_runin_period"), int) and
                    data.get("kevlogger", {}).get("cpu_stable_runin_period") > 0 and
                    data.get("kevlogger", {}).get("TerminateAllECUExecutionOnError") is not None and
                    isinstance(data.get("logMover", {}), dict) and
                    isinstance(data.get("logMover", {}).get("pythonScriptRunTime"), int) and
                    data.get("logMover", {}).get("pythonScriptRunTime") > 0 and
                    data.get("logMover", {}).get("await_file_transfer") is not None and
                    isinstance(data.get("filterEvents", {}), dict) and
                    all(data.get("filterEvents", {}).get(param) is not None for param in ["disableKernelcallsclass", "disableInterruptclass", "disableProcessclass", "disableThreadclass", "disableVThreadclass", "disableCommunicationclass", "disableSystemclass"]) and
                    isinstance(data.get("eventTriggerKEVGeneration", {}), dict) and
                    data.get("eventTriggerKEVGeneration", {}).get("trigger_type") and
                    isinstance(data.get("eventTriggerKEVGeneration", {}).get("parameters_enabled"), dict) and
                    all(data.get("eventTriggerKEVGeneration", {}).get("parameters_enabled", {}).get(param) is not None for param in ["total_CPU", "CPU_0", "CPU_1", "CPU_2", "CPU_3", "CPU_4", "CPU_5", "CPU_6", "CPU_7", "total_RAM"]) and
                    isinstance(data.get("eventTriggerKEVGeneration", {}).get("threshold_values"), dict) and
                    all(isinstance(data.get("eventTriggerKEVGeneration", {}).get("threshold_values", {}).get(param), int) for param in ["total_CPU", "CPU_0", "CPU_1", "CPU_2", "CPU_3", "CPU_4", "CPU_5", "CPU_6", "CPU_7", "total_RAM"]) and
                    isinstance(data.get("eventTriggerKEVGeneration", {}).get("cpu_core_monitor_selection"), dict) and
                    all(data.get("eventTriggerKEVGeneration", {}).get("cpu_core_monitor_selection", {}).get(param) is not None for param in ["cpu_core_monitor_50ms", "cpu_core_monitor_100ms", "cpu_core_monitor_200ms", "cpu_core_monitor_500ms", "cpu_core_monitor_1s"])
                )

                set_button_style(is_valid)
                return is_valid
           
            elif label == "RAM Monitor":
                with open('./RAM_Measurement_Scripts/XCP_RAM_Measurement_Config.json', 'r') as file:
                    data = json.load(file)

                is_valid = (
                    isinstance(data.get("SCRIPT_EXECUTION_TIME"), int) and
                    data.get("SCRIPT_EXECUTION_TIME") > 0 and
                    isinstance(data.get("XCP_PORT"), int) and
                    data.get("XCP_PORT") > 0 and
                    isinstance(data.get("ELF_FILE/A2L_FILE"), str) and
                    data.get("ELF_FILE/A2L_FILE") and
                    isinstance(data.get("CYCLIC_INTERVAL"), int) and
                    data.get("CYCLIC_INTERVAL") > 0 and
                    isinstance(data.get("VARIABLES_TO_MEASURE"), list) and
                    all(isinstance(var, str) for var in data.get("VARIABLES_TO_MEASURE", [])) and
                    isinstance(data.get("VARIABLE_TO_GENERATE_GRAPH"), list) and
                    all(isinstance(var, str) for var in data.get("VARIABLE_TO_GENERATE_GRAPH", [])) and
                    isinstance(data.get("REPORT_FILE_NAME"), str) and
                    data.get("REPORT_FILE_NAME")
                )

                set_button_style(is_valid)
                return is_valid
           
            elif label == "Event Trigger RAM Monitor":
                with open('./Event_Trigger_RAM_Measurement_Scripts/XCP_RAM_Event_Trigger_Config.json', 'r') as file:
                    data = json.load(file)

                is_valid = (
                    isinstance(data.get("SCRIPT_EXECUTION_TIME"), int) and
                    data.get("SCRIPT_EXECUTION_TIME") > 0 and
                    isinstance(data.get("XCP_PORT"), int) and
                    data.get("XCP_PORT") > 0 and
                    isinstance(data.get("ELF_FILE/A2L_FILE"), str) and
                    data.get("ELF_FILE/A2L_FILE") and
                    isinstance(data.get("CYCLIC_INTERVAL"), int) and
                    data.get("CYCLIC_INTERVAL") > 0 and
                    isinstance(data.get("CPU_THRESHOLD_VALUE_PERCENT"), int) and
                    0 <= data.get("CPU_THRESHOLD_VALUE_PERCENT") <= 100 and
                    isinstance(data.get("MEMORY_THRESHOLD_VALUE_PERCENT"), int) and
                    0 <= data.get("MEMORY_THRESHOLD_VALUE_PERCENT") <= 100 and
                    isinstance(data.get("RAM_THRESHOLD"), int) and
                    data.get("RAM_THRESHOLD") > 0 and
                    isinstance(data.get("BEFORE_AFTER_MEASUREMENT"), int) and
                    data.get("BEFORE_AFTER_MEASUREMENT") > 0 and
                    isinstance(data.get("VARIABLES_TO_MEASURE"), list) and
                    all(isinstance(var, str) for var in data.get("VARIABLES_TO_MEASURE", [])) and
                    isinstance(data.get("VARIABLE_TO_CHECK_THRESHOLD"), list) and
                    all(isinstance(var, str) for var in data.get("VARIABLE_TO_CHECK_THRESHOLD", [])) and
                    isinstance(data.get("VARIABLE_TO_GENERATE_GRAPH"), list) and
                    all(isinstance(var, str) for var in data.get("VARIABLE_TO_GENERATE_GRAPH", [])) and
                    isinstance(data.get("XCP_REPORT_FILE_NAME"), str) and
                    data.get("XCP_REPORT_FILE_NAME")
                )

                set_button_style(is_valid)
                return is_valid
           
            elif label == "APL Communication Layout":
                with open('./APL_Communication_Layout_Scripts/XCP_APL_Config.json', 'r') as file:
                    data = json.load(file)
               
                is_valid = (
                    isinstance(data.get("SCRIPT_EXECUTION_TIME"), int) and
                    data.get("SCRIPT_EXECUTION_TIME") > 0 and
                    isinstance(data.get("VARIABLE_TO_GENERATE_GRAPH"), list) and
                    all(isinstance(var, str) for var in data.get("VARIABLE_TO_GENERATE_GRAPH", [])) and
                    isinstance(data.get("REPORT_FILE_NAME"), str) and
                    data.get("REPORT_FILE_NAME")
                )

                set_button_style(is_valid)
                return is_valid

            elif label in diag_labels:
                with open('DIAG_KPI_Config.json', 'r') as f:
                    data = json.load(f)
               
                is_valid = (
                    bool(data.get("excel_name")) and
                    isinstance(data.get("No. of Selected Files"), list) and
                    len(data.get("No. of Selected Files", [])) > 0 and
                    all(isinstance(sheet, str) and sheet.endswith('.xlsx') for sheet in data.get("No. of Selected Files", []))
                )

                set_button_style(is_valid)
                return is_valid

            else:
                set_button_style(False)                
                return False
        except FileNotFoundError:
            pass
        except json.JSONDecodeError as e:
             py_logger.error(f"Error parsing JSON: {e}")
        except Exception as e:
            py_logger.error(f"Error validating '{label}' configuration : {e}.")      

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
            restricted_kpis = ["RAM Monitor", "Event Trigger RAM Monitor", "APL Communication Layout"]

            for label, widgets in self.kpi_widgets.items():
                checkbox = widgets['checkbox']
               
                if checkbox.isChecked() and label in restricted_kpis:
                    if not self.padas_checkbox.isChecked():
                        QMessageBox.warning(self, "Incompatible ECU and KPI Selection",
                                        f"The selected KPI '{label}' are only compatible with PADAS.\n"
                                        "Please select either PADAS ECU or deselect KPIs from XCP sections to proceed.")
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

        self.thread = QThread()
        self.worker = Worker(ecu_input_fields, self.kpi_widgets)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(self.worker_finished)
        self.thread.finished.connect(self.thread.deleteLater)

        # Connect signals
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
                with open(stop_flag_path, "w") as f:
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

    def closeEvent(self, event):
        # Show a confirmation dialog when the user tries to close the GUI
        # Input: User clicks the window close button
        # Output: QMessageBox with Ok/Cancel options
        reply = QMessageBox.question(
            self,
            'Close Gen2 PF Validation Tester Tool',  # Title of the dialog
            'Are you sure you want to close the tool?',  # Message shown to the user
            QMessageBox.Ok | QMessageBox.Cancel,  # Buttons available
            QMessageBox.Cancel  # Default selected button
        )

        # If user confirms closure
        if reply == QMessageBox.Ok:
            try:
                # Log the start of the shutdown process
                py_logger.info("Closing Gen2 PF Validation Tester Tool, please wait!...")                

                # Check if a worker thread exists and is active
                if hasattr(self, 'worker') and self.worker is not None:
                    py_logger.info("Worker Thread is alive")

                    # To create the stop.flag file
                    self.manage_stop_flag(create=True)

                    # Request the worker thread to stop (custom method in your thread class)
                    self.worker.request_stop()

                    # Keep processing GUI events while waiting for the thread to stop
                    from PyQt5.QtCore import QCoreApplication
                    while self.worker is not None:
                        QCoreApplication.processEvents()  # Prevent GUI from freezing
                        time.sleep(0.1)  # Wait briefly before checking again

                    py_logger.info("Worker Thread has stopped")  # Log thread shutdown
               
                # To remove the stop.flag file
                self.manage_stop_flag(create=False)

                # Final log before closing the application
                py_logger.info("Gen2 PF Validation Tester Tool Closed Successfully.")

                # Accept the close event to allow the window to close
                event.accept()

            except Exception as e:
                # Log any unexpected error during shutdown
                py_logger.error(f"Error While Closing Gen PF Validation Tester Tool: {e}")
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

        def update_config_file(file_path, label):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)

                if label in ["Startup Time", "Shutdown Time", "Throughput and Fault Injection"]:
                    data['serial-port-relay'] = self.relay_port_input.text()
                    data['baudrate-relay'] = self.relay_baudrate_input.text()

                if not label in ["Heap Memory", "Startup Time", "Cyclic and Turnaround Time", "Execution Time", "Throughput and Fault Injection"]:            
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

                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=4)

            except FileNotFoundError:
                py_logger.error(f"Error: Configuration file '{file_path}' not found.")
            except json.JSONDecodeError:
                py_logger.error(f"Error: Configuration file '{file_path}' is not a valid JSON.")
            except KeyError as e:
                py_logger.error(f"Error: Missing expected key in ECU input fields: {e}")
            except Exception as e:
                py_logger.error(f"Unexpected error while updating '{file_path}': {e}")

        for label, widgets in self.kpi_widgets.items():
            if widgets['checkbox'].isChecked():
                if label == 'CPU and Memory Utilization':
                    update_config_file('./CPU_Memory_Utilization_Scripts/cpu_memory_utilization_config.json', label)
               
                elif label == 'Heap Memory':
                    update_config_file('./Heap_Memory_Scripts/heap_memory_config.json', label)
               
                elif label == 'Startup Time':
                    update_config_file('./Startup_Time_Scripts/startup_time_config.json', label)
               
                elif label == 'Cyclic and Turnaround Time':
                    update_config_file('./Cyclic_Turnaround_Time_Scripts/cyclic_turnaround_config.json', label)

                elif label == 'Execution Time':
                    update_config_file('./Execution_Time_Scripts/Execution_Time_Config.json', label)
               
                elif label == 'Throughput and Fault Injection':
                    update_config_file('./Throughput_Scripts/throughput_faultinjection_config.json', label)
               
                elif label == 'Shutdown Time':
                    update_config_file('./Shutdown_Time_Scripts/shutdown_time_config.json', label)
                elif label == "Continuous KEV":
                    update_config_file('./Continuous_KEV_Scripts/kev_gen_and_logMover_config.json', label)

                elif label == "Event Trigger KEV":
                    update_config_file('./Event_Trigger_KEV_Scripts/kev_gen_and_logMover_config.json', label)
               
                elif label == "RAM Monitor":
                    update_config_file('./RAM_Measurement_Scripts/XCP_RAM_Measurement_Config.json', label)

                elif label == "Event Trigger RAM Monitor":
                    update_config_file('./Event_Trigger_RAM_Measurement_Scripts/XCP_RAM_Event_Trigger_Config.json', label)              

                elif label == "APL Communication Layout":
                    update_config_file('./APL_Communication_Layout_Scripts/XCP_APL_Config.json', label)

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

                        update_config_file('DIAG_KPI_Config.json', label)
                    except Exception as e:
                        py_logger.error(f"Error updating DIAG_KPI_Config.json: {e}")

    def prepare_and_store_widget_states(self):
        self.is_test_in_progress = True
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
                # 'edit_button': edit_button.isEnabled(),
                # 'folder_button': folder_button.isEnabled()
            }

    def set_status_label_and_enable_widgets(self, label, color):
        if label in self.kpi_widgets:
            widgets = self.kpi_widgets[label]
            widgets['status_label'].setStyleSheet(
                f"background-color: {color}; border: 0.5px solid #999999;"
            )
            widgets['checkbox'].setEnabled(True)
            # widgets['folder_button'].setEnabled(True)

    def disable_all_widgets(self):
        self.run_button.setEnabled(False)
        self.IG_OFF_button.setEnabled(False)
        self.IG_ON_button.setEnabled(False)
        self.clear_logs_button.setEnabled(False)
        self.download_button.setEnabled(False)

        for widget in self.findChildren((QCheckBox, QLineEdit)):
            widget.setEnabled(False)        

    def restore_widget_states(self):
        for label, widgets in self.kpi_widgets.items():
            if label in self.kpi_widgets_status:
                widgets['checkbox'].setEnabled(self.kpi_widgets_status[label]['checkbox'])
                # widgets['edit_button'].setEnabled(self.kpi_widgets_status[label]['edit_button'])
                # widgets['folder_button'].setEnabled(self.kpi_widgets_status[label]['folder_button'])

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

        # Enable buttons
        self.relay_port_input.setEnabled(True)
        self.relay_baudrate_input.setEnabled(True)
        self.download_button.setEnabled(True)
        self.clear_logs_button.setEnabled(True)      

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