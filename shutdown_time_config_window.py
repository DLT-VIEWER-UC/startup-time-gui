from imports_utils import *

class CustomIntValidator(QIntValidator):
    def __init__(self, min_value, max_value=2147483647, parent=None):
        super().__init__(min_value, max_value, parent)
        self.min_value = min_value
        self.max_value = max_value

    def validate(self, input_str, pos):
        if input_str == "":
            return (QIntValidator.Intermediate, input_str, pos)

        if input_str.isdigit():
            # Reject leading zeros unless the value is zero itself
            if input_str.startswith('0') and len(input_str) > 1:
                return (QIntValidator.Invalid, input_str, pos)

            value = int(input_str)
            if self.min_value <= value <= self.max_value:
                return (QIntValidator.Acceptable, input_str, pos)
            else:
                return (QIntValidator.Invalid, input_str, pos)
        else:
            return (QIntValidator.Invalid, input_str, pos)

           
class ShutdownTimeConfig(QDialog):
    DEFAULT_CONFIG = {
        'windows': {'Is Environment Path Set': False, 'DLT-Viewer Installed Path': ''}        
    }

    def __init__(self, main_window, is_Checked):
        super().__init__()
        self.main_window = main_window
        self.is_KPI_selected = is_Checked
        self.set_window_properties()

        self.config_path = './Shutdown_Time_Scripts/shutdown_time_config.json'
        self.config_data = self.load_config()
        self.widgets = {}

        self.init_ui()
   
    def set_window_properties(self):
        self.setWindowTitle('Shutdown Time Configuration')
        self.setWindowIcon(QIcon('./GUI_Icons/KPIT_logo.ico'))

        # Get the geometry of the MainWindow
        main_window_x = self.main_window.x()
        main_window_y = self.main_window.y()
        main_window_width = self.main_window.width()
        main_window_height = self.main_window.height()

        # Define window dimensions
        # TODO: update these values as needed
        window_width = 850
        window_height = 250

        # Calculate the position to center the window
        x = main_window_x + (main_window_width - window_width) // 2
        y = main_window_y + (main_window_height - window_height) // 2

        # Set the geometry and fixed size of the window
        self.setGeometry(x, y, window_width, window_height)
        self.setFixedSize(window_width, window_height)

    def load_config(self):
        if not os.path.exists(self.config_path):
            return dict(self.DEFAULT_CONFIG)
        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
            merged = dict(self.DEFAULT_CONFIG)
            merged.update(data)
            return merged
        except Exception as e:
            return dict(self.DEFAULT_CONFIG)

    def init_ui(self):      
        layout = QVBoxLayout()      
       
        self.setLayout(layout)

        # General Settings
        general_group = QGroupBox('General Settings')
        general_group.setStyleSheet(common_groupbox_style)
        # general_group.setFixedHeight(110)
        general_layout = QFormLayout()
        general_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        for key, validator in [
            ('DLT-Viewer Log Capture Time', CustomIntValidator(1)),
            ('Iterations', CustomIntValidator(1))]:

            le = QLineEdit(str(self.config_data.get(key, '')))
            if key == 'DLT-Viewer Log Capture Time':
                le.textChanged.connect(lambda text: [self.update_border('DLT-Viewer Log Capture Time')])
            elif key == 'Iterations':
                le.textChanged.connect(lambda text: [self.update_border('Iterations')])
            # le.textChanged.connect(lambda text: [self.ok_btn.setDisabled(False)])
            le.textChanged.connect(lambda text: [self.on_change_update_ok_btn_state()])
            le.setValidator(validator)
            le.setFixedWidth(100)
            row_layout = QHBoxLayout()
            row_layout.addWidget(le)
            if key != 'Iterations':
                row_layout.addWidget(QLabel('[Int: 150~ (sec)]'))
            else:
                row_layout.addWidget(QLabel('[Int: 1~]'))
            general_layout.addRow(QLabel(key), row_layout)
            self.widgets[key] = le
        general_group.setLayout(general_layout)
        layout.addWidget(general_group)
       
        win = self.config_data.get('windows', {})
        path_cb = QCheckBox(); path_cb.setChecked(win.get('Is Environment Path Set', False))
        general_layout.addRow(QLabel('Is Environment Path Set'), path_cb)
        self.widgets['windows.Is Environment Path Set'] = path_cb

        # Path line edit with char count
        path_le = QLineEdit(win.get('DLT-Viewer Installed Path', ''))
        path_le.setReadOnly(True)
        # path_le.textChanged.connect(lambda text: [self.ok_btn.setDisabled(False)])
        path_le.textChanged.connect(lambda text: [self.on_change_update_ok_btn_state()])
        path_le.setMaxLength(250)
        count_lbl = QLabel(f"{len(path_le.text())} / {path_le.maxLength()}")
        path_le.textChanged.connect(lambda text: [count_lbl.setText(f"{len(text)} / {path_le.maxLength()}"),self.update_border('windows.DLT-Viewer Installed Path')])
        browse_btn = QPushButton('Browse')
        browse_btn.setFocusPolicy(Qt.NoFocus)
        browse_btn.clicked.connect(lambda: self.browse_path(path_le))
        hl = QHBoxLayout()
        hl.addWidget(path_le)
        hl.addWidget(browse_btn)
        hl.addWidget(count_lbl)
        general_layout.addRow(QLabel('DLT-Viewer Installed Path'), hl)
        self.widgets['windows.DLT-Viewer Installed Path'] = path_le
        general_group.setLayout(general_layout)
        layout.addWidget(general_group)

        # Enable/disable path based on checkbox
        path_le.setDisabled(path_cb.isChecked())
        browse_btn.setDisabled(path_cb.isChecked())
        count_lbl.setDisabled(path_cb.isChecked())
       
        path_cb.toggled.connect(lambda checked: [path_le.setDisabled(checked), browse_btn.setDisabled(checked), count_lbl.setDisabled(checked),self.on_change_update_ok_btn_state(), self.update_border('windows.DLT-Viewer Installed Path')])

        btn_h = QHBoxLayout()
        btn_h.addStretch()
        self.ok_btn = QPushButton('OK'); self.ok_btn.clicked.connect(self.ok_clicked)
        self.ok_btn.setFocusPolicy(Qt.NoFocus)
        cancel_btn = QPushButton('Cancel'); cancel_btn.clicked.connect(self.reject)
        cancel_btn.setFocusPolicy(Qt.NoFocus)
        btn_h.addWidget(self.ok_btn); btn_h.addWidget(cancel_btn)
        layout.addLayout(btn_h)

        self.on_change_update_ok_btn_state()
        for key in ['DLT-Viewer Log Capture Time', 'Iterations', 'windows.DLT-Viewer Installed Path']:
            self.update_border(key)
        # self.ok_btn.setDisabled(True)        

    def ok_clicked(self):
        self.save_config()
        self.close()

    def done(self, result):
        # print("Shutdown Time configuration window closed successfully")
        super().done(result)

    def on_radio_changed(self, checked):
        # self.ok_btn.setDisabled(False)
        visible = self.elite_radio.isChecked()
        self.board_selection_group.setDisabled(False)
        if visible:
            self.soc0_cb.setDisabled(False)
            self.soc1_cb.setDisabled(False)
            self.soc0_cb.setChecked(False)
            self.soc1_cb.setChecked(False)
        else:
            self.soc0_cb.setDisabled(True)
            self.soc1_cb.setDisabled(True)
            self.soc0_cb.setChecked(False)
            self.soc1_cb.setChecked(False)
        # for i in (1, 2):
        #     self.ecu_block_list[i].setVisible(visible)
       
    def update_border(self, key):
        widget = self.widgets[key]
        text = widget.text().strip()
        is_valid = True

        if key == 'windows.DLT-Viewer Installed Path':
            path_cb = self.widgets['windows.Is Environment Path Set']
            is_valid = path_cb.isChecked() or (text and text == widget.text())
        elif key == 'DLT-Viewer Log Capture Time':
            is_valid = text and text.isdigit() and 150 <= int(text)
        else:
            is_valid = bool(text)
        widget.setStyleSheet("border: 0px;" if is_valid else "border: 1px solid red;")

    def on_change_update_ok_btn_state(self):
        enabled = True
        for key in ['DLT-Viewer Log Capture Time', 'Iterations']: # , 'threshold-in-seconds'
            text = self.widgets[key].text()
            if not text or len(text) == 0:
                enabled = False
                break
            if key == 'DLT-Viewer Log Capture Time' and not (150 <=int(text)):
                enabled = False
                break
           
        if enabled:
            path_cb = self.widgets['windows.Is Environment Path Set']
            path_le = self.widgets['windows.DLT-Viewer Installed Path']
            if not path_cb.isChecked() and (not path_le.text() or len(path_le.text()) == 0 or path_le.text().startswith(" ")or path_le.text().endswith(" ")):
                enabled = False        

        enabled = enabled and not (self.main_window.is_test_in_progress and self.is_KPI_selected)

        self.ok_btn.setEnabled(enabled)
        if not enabled:
            self.ok_btn.setToolTip("To enable the OK Button, configure all red highlighted fields")
        else:
            self.ok_btn.setToolTip("")

    def browse_path(self, line_edit):
        # Determine starting directory based on current path in line_edit
        current_path = line_edit.text().strip()
        if current_path and os.path.exists(current_path):
            # If the path itself is a directory, use it
            start_dir = current_path
        else:
            # Default to C drive if path is empty or invalid
            start_dir = 'C:\\'
        
        path, _ = QFileDialog.getOpenFileName(self, 'Select dlt-viewer executable', start_dir, 'Executable files (*.exe)')
        if path:
            line_edit.setText(path)

    def save_config(self):
        data = {}
        for key in ['DLT-Viewer Log Capture Time', 'Iterations']: # , 'threshold-in-seconds'
            w = self.widgets[key]
            # print(w.text())
            if w.text() and len(w.text())>0:
                data[key] = int(w.text())
        data['windows'] = {
            'Is Environment Path Set': self.widgets['windows.Is Environment Path Set'].isChecked(),
            'DLT-Viewer Installed Path': self.widgets['windows.DLT-Viewer Installed Path'].text()
        }
       
        try:
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=4)

            self.accept()
        except Exception as e:
            print(f'Failed to save config: {e}')