from imports_utils import *

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
            # Case 2a: Input is "00" — always invalid
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
            if self.min_value <= value <= self.max_value:
                return (QIntValidator.Acceptable, input_str, pos)
            elif value<self.min_value:
                return (QIntValidator.Intermediate, input_str, pos)
            else:
                return (QIntValidator.Invalid, input_str, pos)

        # Case 3: Input contains non-digit characters
        else:
            return (QIntValidator.Invalid, input_str, pos)

class LimitedTextEdit(QTextEdit):
    def __init__(self, max_length):
        super().__init__()
        self.max_length = max_length

    def keyPressEvent(self, event):
        current_text = self.toPlainText()

        if len(current_text) >= self.max_length and event.text() and event.key() != Qt.Key_Backspace:
            event.ignore()
            return
       
        super().keyPressEvent(event)

    def insertPlainText(self, text):
        current_text = self.toPlainText()

        if len(current_text) + len(text) > self.max_length:
            remaining_length = self.max_length - len(current_text)
            text = text[:remaining_length]

        super().insertPlainText(text)

    def insertFromMimeData(self, source):
        current_text = self.toPlainText()
        new_text = source.text()

        if len(current_text) + len(new_text) > self.max_length:
            remaining_length = self.max_length - len(current_text)
            new_text = new_text[:remaining_length]

        super().insertPlainText(new_text)

class CpuMemoryConfig(QDialog):
    def __init__(self, main_window, is_Checked):
        super().__init__()

        self.main_window = main_window  # Store the main window reference
        # self.is_test_in_progress = main_window.is_test_in_progress
        self.is_KPI_selected = is_Checked
        self.max_int = 2147483647

        self.config_path = switch_dict.get("CPU and Memory Utilization")
        self.pdf_process = None

        self.set_window_properties()    
        self.create_main_layout()
   
    def done(self, result):
        self.pdf_process = close_pdf_process(self.pdf_process)

        super().done(result)
   
    def set_window_properties(self):
        # Enable minimize/maximize buttons and the context-help '?' hint
        flags = (self.windowFlags()
                #  | Qt.WindowMinimizeButtonHint
                 | Qt.WindowMaximizeButtonHint            
                 | Qt.Window)
       
        self.setWindowFlags(flags)
        self.setWindowTitle('CPU and Memory Utilization Configuration')
        self.setWindowIcon(QIcon('./GUI_Icons/KPIT_logo.ico'))

        # Get the geometry of the MainWindow
        main_window_x = self.main_window.x()
        main_window_y = self.main_window.y()
        main_window_width = self.main_window.width()
        main_window_height = self.main_window.height()

        # Define window dimensions
        window_width = 750
        window_height = 400

        # Calculate the position to center the window
        x = main_window_x + (main_window_width - window_width) // 2
        y = main_window_y + (main_window_height - window_height) // 2

        # Set the geometry and fixed size of the window
        self.setGeometry(x, y, window_width, window_height)
        # self.resize(window_width, window_height)        

    def create_main_layout(self):
        main_layout = QHBoxLayout()

        threshold_group = self.create_threshold_group()

        script_logging_report_button_layout = self.create_script_logging_report_button_layout()

        main_layout.addWidget(threshold_group)
        main_layout.addLayout(script_logging_report_button_layout)
       
        self.setLayout(main_layout)
        self.load_data()
        self.connect_signals()        

    def create_threshold_group(self):
        threshold_group = QGroupBox("Threshold [Int:0-100%]")
        threshold_group.setStyleSheet(common_groupbox_style)

        threshold_layout = QFormLayout()
        threshold_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.create_cpu_usage_input(threshold_layout)
        self.create_memory_usage_input(threshold_layout)
        self.create_cpu_inputs(threshold_layout)

        threshold_group.setLayout(threshold_layout)
        return threshold_group

    def create_cpu_usage_input(self, layout):
        cpu_usage_label = QLabel('CPU Usage')

        self.cpu_usage_input = QLineEdit()
        self.cpu_usage_input.setValidator(CustomIntValidator(0, 100))

        cpu_usage_unit_label = QLabel('%')

        cpu_usage_layout = QHBoxLayout()
        cpu_usage_layout.addWidget(self.cpu_usage_input)
        # cpu_usage_layout.addWidget(cpu_usage_unit_label)

        layout.addRow(cpu_usage_label, cpu_usage_layout)

    def create_memory_usage_input(self, layout):
        memory_usage_label = QLabel('Memory Usage')

        self.memory_usage_input = QLineEdit()
        self.memory_usage_input.setValidator(CustomIntValidator(0, 100))

        memory_usage_unit_label = QLabel('%')

        memory_usage_layout = QHBoxLayout()
        memory_usage_layout.addWidget(self.memory_usage_input)
        # memory_usage_layout.addWidget(memory_usage_unit_label)

        layout.addRow(memory_usage_label, memory_usage_layout)

    def create_cpu_inputs(self, layout):
        self.cpu_inputs = []

        for i in range(8):
            label_text = f'CPU{i}'

            label = QLabel(label_text)

            input_field = QLineEdit()
            input_field.setValidator(CustomIntValidator(0, 100))

            unit_label = QLabel('%')

            cpu_layout = QHBoxLayout()
            cpu_layout.addWidget(input_field)
            # cpu_layout.addWidget(unit_label)

            layout.addRow(label, cpu_layout)

            self.cpu_inputs.append(input_field)

    def create_script_logging_report_button_layout(self):
        script_logging_report_button_layout = QFormLayout()
        script_logging_report_button_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.create_dropdown(script_logging_report_button_layout)
        self.create_cpumon_dropdown(script_logging_report_button_layout)
        self.create_script_exec_time_input(script_logging_report_button_layout)
        self.create_initial_logging_delay_input(script_logging_report_button_layout)
        self.create_test_report_name_input(script_logging_report_button_layout)
        self.create_buttons(script_logging_report_button_layout)

        return script_logging_report_button_layout
   
    def create_cpumon_dropdown (self,layout):
        cpumon_dropdown_layout = QHBoxLayout()

        label = QLabel("CPUmon delay")

        self.cpumon_selection_dropdown = QComboBox()
        self.cpumon_selection_dropdown.addItem("50ms", "")
        self.cpumon_selection_dropdown.addItem("100ms", "")
        self.cpumon_selection_dropdown.addItem("200ms", "")  
        self.cpumon_selection_dropdown.addItem("500ms", "")  
        self.cpumon_selection_dropdown.addItem("1s", "")  
        # self.tool_selection_dropdown.setFixedWidth(80) # Set the size of the kev generation dropdown

        cpumon_dropdown_layout.addWidget(self.cpumon_selection_dropdown)

        layout.addRow(label, cpumon_dropdown_layout)

    def create_dropdown(self,layout):
        dropdown_layout = QHBoxLayout()

        label = QLabel("Tool Selection")

        self.tool_selection_dropdown = QComboBox()
        self.tool_selection_dropdown.addItem("CPU: top | Memory: top", "")
        self.tool_selection_dropdown.addItem("CPU: CPUmon | Memory: top", "")
        self.tool_selection_dropdown.addItem("CPU: CPUmon | Memory: pidin info", "")  
        # self.tool_selection_dropdown.setFixedWidth(80) # Set the size of the kev generation dropdown

        dropdown_layout.addWidget(self.tool_selection_dropdown)

        layout.addRow(label, dropdown_layout)

    def create_script_exec_time_input(self, layout):
        script_exec_time_layout = QHBoxLayout()

        script_exec_time_label = QLabel('Script Execution Time')
        script_exec_time_label.setAlignment(Qt.AlignCenter)

        self.script_exec_time_input = QLineEdit()
        self.script_exec_time_input.setValidator(CustomIntValidator(5,self.max_int))
        self.script_exec_time_input.setFixedWidth(100)

        script_exec_time_unit_label = QLabel('[Int: 5 ~ (sec)]')

        script_exec_time_layout.addWidget(script_exec_time_label)
        script_exec_time_layout.addWidget(self.script_exec_time_input)
        script_exec_time_layout.addWidget(script_exec_time_unit_label)

        layout.addRow(script_exec_time_layout)

    def create_initial_logging_delay_input(self, layout):
        initial_logging_delay_layout = QHBoxLayout()

        initial_logging_delay_label = QLabel('Initial Logging Delay')
        initial_logging_delay_label.setAlignment(Qt.AlignCenter)

        self.initial_logging_delay_input = QLineEdit()
        self.initial_logging_delay_input.setValidator(CustomIntValidator(0,self.max_int))
        self.initial_logging_delay_input.setFixedWidth(100)

        initial_logging_delay_unit_label = QLabel('[Int: 0 ~ (sec)]')

        initial_logging_delay_layout.addWidget(initial_logging_delay_label)
        initial_logging_delay_layout.addWidget(self.initial_logging_delay_input)
        initial_logging_delay_layout.addWidget(initial_logging_delay_unit_label)

        layout.addRow(initial_logging_delay_layout)

    def create_test_report_name_input(self, layout):
        test_report_name_layout = QHBoxLayout()

        test_report_name_label = QLabel('Test Report Name')
        test_report_name_label.setAlignment(Qt.AlignCenter)
       
        parent_dir = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
        total_path=os.path.join(parent_dir,'Reports/01_CPU_Memory_Utilization/20250717_15-22-00/Log_Files/SoC0_memory_.txt')
        length=len(total_path)
        length+=5
        char_count_label = QLabel(f'{length}/250')

        self.test_report_name_input = LimitedTextEdit(250-length)
        self.test_report_name_input.setTabChangesFocus(True)
        self.test_report_name_input.setFixedHeight(150)  # Adjust height to fit 250 characters
        self.test_report_name_input.setFixedWidth(250)  # Adjust width
        self.test_report_name_input.setPlaceholderText("Enter test report name here...")
        self.test_report_name_input.textChanged.connect(lambda: char_count_label.setText(f"{len(self.test_report_name_input.toPlainText())+length}/250"))
       
        test_report_name_layout.addWidget(test_report_name_label)        
        test_report_name_layout.addWidget(self.test_report_name_input)
        test_report_name_layout.addWidget(char_count_label)

        layout.addRow(test_report_name_layout)

    def create_buttons(self, layout):
        buttons_layout = QHBoxLayout()
       
        self.ok_button = QPushButton('OK')
        self.ok_button.setFixedHeight(35)
        self.ok_button.setEnabled(True)
        self.ok_button.setFocusPolicy(Qt.NoFocus)
        self.ok_button.clicked.connect(self.save_and_close)

        cancel_button = QPushButton('Cancel')
        cancel_button.setFixedHeight(35)
        cancel_button.setFocusPolicy(Qt.NoFocus)
        cancel_button.clicked.connect(self.reject)

        help_button = QPushButton()
        help_button.setIcon(QIcon('./GUI_Icons/Help_icon.ico'))
        help_button.setFixedSize(35,35)
        help_button.setToolTip("Help")
        help_button.clicked.connect(self.handle_help_click)
        # help_button.setIconSize(QSize(30, 30))
        help_button.setWindowIconText(None)  # Icon beside text
        help_button.setFocusPolicy(Qt.NoFocus)

        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(cancel_button)
        buttons_layout.addWidget(help_button)

        layout.addRow(buttons_layout)

    def handle_help_click(self):
        """
        Slot for help button click.
        Opens the user manual and updates pdf_process reference.
        """
        self.pdf_process = open_user_manual("CPU and Memory Utilization", self.pdf_process)

    def connect_signals(self):
        self.cpu_usage_input.textChanged.connect(self.validate_all_fields)
        self.memory_usage_input.textChanged.connect(self.validate_all_fields)

        for cpu_input in self.cpu_inputs:
            cpu_input.textChanged.connect(self.validate_all_fields)

        self.script_exec_time_input.textChanged.connect(self.validate_all_fields)
        self.initial_logging_delay_input.textChanged.connect(self.validate_all_fields)
        self.test_report_name_input.textChanged.connect(self.validate_all_fields)  
        self.tool_selection_dropdown.currentIndexChanged.connect(self.update_cpumon_dropdown)
        # self.tool_selection_dropdown
        # self.tool_selection_dropdown.cure.connect(self.update_cpumon_dropdown)        
   
    def update_cpumon_dropdown(self,index):
        if index==0:
            self.cpumon_selection_dropdown.setCurrentIndex(4)
            self.cpumon_selection_dropdown.setEnabled(False)
        else:
            self.cpumon_selection_dropdown.setEnabled(True)
   
    def validate_all_fields(self):
        is_valid = self.update_border()

        fields_filled = (
            self.cpu_usage_input.text() and
            self.memory_usage_input.text() and
            all(cpu_input.text() for cpu_input in self.cpu_inputs) and
            self.script_exec_time_input.text() and
            self.initial_logging_delay_input.text() and
            self.test_report_name_input.toPlainText()
        )

        # script_exec_time_valid = int(self.script_exec_time_input.text()) > 0 if self.script_exec_time_input.text() else False

        # is_valid = is_valid and fields_filled
        is_valid = (is_valid and
                    fields_filled and
                    int(self.script_exec_time_input.text()) > 4 if self.script_exec_time_input.text() else False)
       
        self.ok_button.setEnabled(False if(self.main_window.is_test_in_progress and self.is_KPI_selected) else True)
        return is_valid
       
    def update_border(self) -> bool:
        """
        Updates the border of a given widget based on its validation status.        
        Args:
            widget: The widget to update the border for.        
        Returns:
            bool: True if the widget is valid, False otherwise.
        """        
        widgets=[self.script_exec_time_input,
                 self.initial_logging_delay_input,
                 self.cpu_usage_input,
                 self.memory_usage_input,
                 self.cpu_inputs,
                 self.test_report_name_input]
        for widget in widgets:
            # Define a function to apply a red border to the widget
            def apply_red_border(item):
                item.setStyleSheet("border: 2px solid red;")

            # Define a function to clear the border from the widget
            def clear_border(item):
                item.setStyleSheet("")                

            # If the widget is disabled, clear its border and return True
            if not isinstance(widget,list):
                if not widget.isEnabled():
                    clear_border()
                    return True

            # Initialize a flag to track the validity of the widget
            is_valid = True

            # Check the type of widget and validate its content accordingly
            if isinstance(widget, QLineEdit):
                # Get the text from the line edit widget
                text = widget.text()

                # Strip any leading or trailing whitespace from the text
                stripped_text = text.strip()
               
                # If the text is empty or contains only whitespace, apply a red border and set the validity flag to False
                if not stripped_text or text != stripped_text:
                    apply_red_border(widget)
                    is_valid = False
                # Otherwise, clear the border
                else:
                        validator = widget.validator()
                        if validator:
                            state, _, _ = validator.validate(text, 0)
                            if state == QIntValidator.Acceptable:
                                clear_border(widget)
                            else:
                                apply_red_border(widget)
                                is_valid = False
                        else:
                            clear_border(widget)

                if widget==self.script_exec_time_input:
                    if widget.text()!="":
                        if int(widget.text())==0:
                            apply_red_border(widget)
                            is_valid = False
               
            elif isinstance(widget, QTextEdit):
                # Get the text from the text edit widget
                text = widget.toPlainText()

                # Strip any leading or trailing whitespace from the text
                stripped_text = text.strip()
               
                # If the text is empty or contains only whitespace, apply a red border and set the validity flag to False
                if text != stripped_text or not stripped_text:
                    apply_red_border(widget)
                    is_valid = False
                # Otherwise, clear the border
                else:
                    clear_border(widget)
            elif isinstance(widget,list):
                for w in widget:
                    text=w.text()
                    stripped_text = text.strip()
                   
                    # If the text is empty or contains only whitespace, apply a red border and set the validity flag to False
                    if not stripped_text or text != stripped_text:
                        apply_red_border(w)
                        is_valid = False
                    # Otherwise, clear the border
                    else:
                # Usins custom validator here
                        validator = w.validator()
                        if validator:
                            state, _, _ = validator.validate(text, 0)
                            if state == QIntValidator.Acceptable:
                                clear_border(w)
                            else:
                                apply_red_border(w)
                                is_valid = False
                        else:
                            clear_border(w)            
        # Return the validity flag
        return is_valid

    def load_data(self):
        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)

                # Load Threshold values
                threshold = data.get("Threshold", {})
                self.cpu_usage_input.setText(str(threshold.get("TotalCPU", "")))
                self.memory_usage_input.setText(str(threshold.get("TotalMemory", "")))
               
                for i, cpu_input in enumerate(self.cpu_inputs):
                    cpu_input.setText(str(threshold.get(f"CPU{i}", "")))

                # Load timing and report fields
                self.script_exec_time_input.setText(str(data.get("scriptExecutionTimeInSeconds", "")))
                self.initial_logging_delay_input.setText(str(data.get("initialLoggingDelayInSeconds", "")))
                self.test_report_name_input.setPlainText(data.get("defaultReportFilename", ""))
                self.tool_selection_dropdown.setCurrentIndex(data['ToolSelection'])
                self.cpumon_selection_dropdown.setCurrentIndex(data['cpu_core_monitor_selection'])
                if data['ToolSelection']==0:
                    self.cpumon_selection_dropdown.setCurrentIndex(4)
                    self.cpumon_selection_dropdown.setEnabled(False)                

            self.validate_all_fields()  # Call validate_all_fields after loading data

        except FileNotFoundError:
            pass
        except json.JSONDecodeError:
            pass
        except Exception as e:
            py_logger.error(f"Unexpected error while loading config: {e}")

    def _to_int_or_blank(self, txt: str):
        """Return ``int`` when *txt* holds a number, otherwise an empty string."""
        txt = txt.strip()
        return int(txt) if txt else ""

    def save_and_close(self):
        # -----------------------------------------------------------------
        # Helper to safely fetch values from QLineEdit/QPlainTextEdit controls
        # -----------------------------------------------------------------
        try:
            data = {
                "scriptExecutionTimeInSeconds": self._to_int_or_blank(self.script_exec_time_input.text()),
                "ToolSelection": int(self.tool_selection_dropdown.currentIndex()),
                "cpu_core_monitor_selection": int(self.cpumon_selection_dropdown.currentIndex()),
                "defaultReportFilename": self.test_report_name_input.toPlainText(),
                "initialLoggingDelayInSeconds": self._to_int_or_blank(self.initial_logging_delay_input.text()),
                "Threshold": {
                    "TotalCPU": self._to_int_or_blank(self.cpu_usage_input.text()),
                    "TotalMemory": self._to_int_or_blank(self.memory_usage_input.text()),
                    **{
                        f"CPU{i}": self._to_int_or_blank(self.cpu_inputs[i].text())
                        for i in range(8)
                    }
                }
            }

            data["is_all_fields_valid"] = self.validate_all_fields()

            # Write the configuration file
            with open(self.config_path, "w") as f:
                json.dump(data, f, indent=4)

        except Exception as e:
            # Log and show error
            py_logger.error(f"Error saving configuration: {e}", exc_info=True)

        self.accept()