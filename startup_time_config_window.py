from imports_utils import *


class CustomIntValidator(QIntValidator):
    def __init__(self, minimum=1, maximum=300, parent=None):
        super().__init__(minimum, maximum, parent)
        self._min = minimum
        self._max = maximum
    def setRange(self, minimum, maximum):
        self._min = minimum
        self._max = maximum
        super().setRange(minimum, maximum)
    def validate(self, input_str, pos):
        if input_str == "":
            return (QIntValidator.Intermediate, input_str, pos)
       
        if input_str.isdigit():
            # Check for leading zeros
            if input_str.startswith('0') and len(input_str) > 1:
                return (QIntValidator.Invalid, input_str, pos)
            value = int(input_str)
 
            if self._min <= value:# <= self._max:
                return (QIntValidator.Acceptable, input_str, pos)
            else:
                return (QIntValidator.Invalid, input_str, pos)
        else:
            return (QIntValidator.Invalid, input_str, pos)
       
           
class StartupTimeConfig(QDialog):
    DEFAULT_CONFIG = {
        # 'DLT-Viewer Log Capture Time': 0,
        # 'Iterations': 0,
        # 'Threshold': 0,
        'Startup Order Judgement': False,
        'windows': {'Is Environment Path Set': False, 'DLT-Viewer Installed Path': ''},
        'ecu-config': []
    }
    CONFIG_GUI_FIELD_MAPPING = {
        'DLT-Viewer Log Capture Time': 'DLT-Viewer Log Capture Time',
        'Threshold': 'Threshold',
        'Iterations': 'Iterations',
        'Startup Order Judgement': 'Startup Order Judgement',
        'Is Environment Path Set': 'Is Environment Path Set',
        'DLT-Viewer Installed Path': 'DLT-Viewer Installed Path',
        'Pre-Generated Logs': 'Pre-Generated Logs',
        'logs-folder-path': 'Pre-Generated Logs Folder Path',
        'Applications': 'Applications',
        'use-default-path': 'Use Default Path'
    }

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.set_window_properties()

        self.config_path = './Startup_Time_Scripts/startup_time_config.json'
        self.config_data = self.load_config()
        self.widgets = {}
        self.ecu_block_list = []
        self.startup_group_list = []
        
        self.isElite, self.isPadas = False, False
        self.isRCAR, self.isSOC0, self.isSOC1 = False, False, False
        
        # Check which ECU type is enabled (only one can be selected at a time)
        self.ecu_selection = main_window.ecu_selection_status

        if self.ecu_selection.get('Elite', {}).get('RCAR', False):
            self.isElite = True
            self.isRCAR = True
        if self.ecu_selection.get('Elite', {}).get('SoC0', False):
            self.isElite = True
            self.isSOC0 = True
        if self.ecu_selection.get('Elite', {}).get('SoC1', False):
            self.isElite = True
            self.isSOC1 = True
        if self.ecu_selection.get('PADAS', {}).get('RCAR', False):
            self.isPadas = True
            self.isRCAR = True

        self.init_ui()
   
    def set_window_properties(self):
        self.setWindowTitle('Startup Time Configuration')
        self.setWindowIcon(QIcon('KPIT_logo.png'))

        # Get the geometry of the MainWindow
        main_window_x = self.main_window.x()
        main_window_y = self.main_window.y()
        main_window_width = self.main_window.width()
        main_window_height = self.main_window.height()

        # Define window dimensions
        window_width = 900
        window_height = 800

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
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        central = QWidget()
        layout = QVBoxLayout(central)
       
        scroll.setWidget(central)
        # self.setCentralWidget(scroll)
        dlg_layout = QVBoxLayout(self)
        dlg_layout.addWidget(scroll)
        self.setLayout(dlg_layout)


        # General Settings
        general_group = QGroupBox('General Settings')
        general_group.setFixedHeight(200)
        general_layout = QFormLayout()
        for key, validator in [
            ('DLT-Viewer Log Capture Time', CustomIntValidator(1, 500)),
            ('Iterations', CustomIntValidator(1, 50)),
            ('Threshold', CustomIntValidator(1, 100)),
            ('Power ON-OFF Delay', CustomIntValidator(1, 100))
        ]:
            widgets_lst = list()
            le = QLineEdit(str(self.config_data.get(key, '')))
            le.setPlaceholderText('0')
            le.textChanged.connect(lambda text: [self.on_change_update_ok_btn_state()])
            le.setValidator(validator)
            le.setFixedWidth(150)
            widgets_lst.append(le)
            row_layout = QHBoxLayout()
            row_layout.addWidget(le)
            if key != 'Iterations':
                sec_lbl = QLabel('sec')
                row_layout.addWidget(sec_lbl)
                widgets_lst.append(sec_lbl)
            key_lbl = QLabel(key)
            widgets_lst.append(key_lbl)
            general_layout.addRow(key_lbl, row_layout)
            self.widgets[key] = widgets_lst
        vcb = QCheckBox(); vcb.setChecked(self.config_data.get('Startup Order Judgement', False))
        general_layout.addRow(QLabel('Startup Order Judgement'), vcb)
        self.widgets['Startup Order Judgement'] = vcb
        pre_gen_logs_cb = QCheckBox(); pre_gen_logs_cb.setChecked(self.config_data.get('Pre-Generated Logs', False))
        general_layout.addRow(QLabel('Pre-Generated Logs'), pre_gen_logs_cb)
        self.widgets['Pre-Generated Logs'] = pre_gen_logs_cb
        
        general_group.setLayout(general_layout)
        layout.addWidget(general_group)

        # Windows Settings
        win_group = QGroupBox('DLT Viewer Path Settings')
        win_group.setFixedHeight(100)
        win_layout = QFormLayout()
        win = self.config_data.get('windows', {})
        path_cb = QCheckBox(); path_cb.setChecked(win.get('Is Environment Path Set', False))
        win_layout.addRow(QLabel('Is Environment Path Set'), path_cb)
        self.widgets['windows.Is Environment Path Set'] = path_cb

        # Path line edit with char count
        path_le = QLineEdit(win.get('DLT-Viewer Installed Path', ''))
        path_le.textChanged.connect(lambda text: [self.on_change_update_ok_btn_state()])
        path_le.setMaxLength(250)
        count_lbl = QLabel(f"{len(path_le.text())} / {path_le.maxLength()}")
        path_le.textChanged.connect(lambda text: count_lbl.setText(f"{len(text)} / {path_le.maxLength()}"))
        browse_btn = QPushButton('Browse')
        browse_btn.clicked.connect(lambda: self.browse_path(path_le))
        hl = QHBoxLayout()
        hl.addWidget(path_le)
        hl.addWidget(browse_btn)
        hl.addWidget(count_lbl)
        dlt_path_lbl = QLabel('DLT-Viewer Installed Path')
        win_layout.addRow(dlt_path_lbl, hl)
        self.widgets['windows.DLT-Viewer Installed Path'] = path_le
        win_group.setLayout(win_layout)
        layout.addWidget(win_group)

        # Enable/disable path based on checkbox
        dlt_path_lbl.setDisabled(path_cb.isChecked())
        path_le.setDisabled(path_cb.isChecked())
        browse_btn.setDisabled(path_cb.isChecked())
        count_lbl.setDisabled(path_cb.isChecked())

        path_cb.toggled.connect(lambda checked: [dlt_path_lbl.setDisabled(checked), path_le.setDisabled(checked), browse_btn.setDisabled(checked), count_lbl.setDisabled(checked), self.on_change_update_ok_btn_state()])

        # ECU Configurations
        self.ec_group = QGroupBox('ECU Configurations')
        ec_vbox = QVBoxLayout()
        self.widgets['ecu-config'] = []

        # Load existing or defaults
        ecu_types = {ecu['ecu-type']: ecu for ecu in self.config_data.get('ecu-config', [])}
        for idx, ecu_type in enumerate(['RCAR', 'SoC0', 'SoC1']):
            ecu_data = ecu_types.get(ecu_type, {'ecu-type': ecu_type, 'startup-order': []})
            block = self._create_ecu_block(ecu_data, idx)
            if ecu_type=='RCAR':
                block.setVisible(self.isRCAR)
            elif ecu_type=='SoC0':
                block.setVisible(self.isSOC0)
            elif ecu_type=='SoC1':
                block.setVisible(self.isSOC1)
            for startup_group in self.startup_group_list:
                startup_group.setEnabled(vcb.isChecked()) 
            self.ecu_block_list.append(block)
            ec_vbox.addWidget(block)

        self.ec_group.setLayout(ec_vbox)
        layout.addWidget(self.ec_group)
        vcb.toggled.connect(lambda checked: [self.on_change_update_ok_btn_state()] + [startup_group.setEnabled(checked) for startup_group in self.startup_group_list])
        pre_gen_logs_cb.toggled.connect(lambda checked: [
            self.on_change_update_ok_btn_state(),
            win_group.setDisabled(checked)] + [
            w.setDisabled(checked) for w in self.widgets['DLT-Viewer Log Capture Time'] + self.widgets['Power ON-OFF Delay']
        ])

        # OK/Cancel
        btn_h = QHBoxLayout()
        btn_h.addStretch()
        self.ok_btn = QPushButton('OK'); self.ok_btn.clicked.connect(self.ok_clicked)
        cancel_btn = QPushButton('Cancel'); cancel_btn.clicked.connect(self.reject)
        btn_h.addWidget(self.ok_btn); btn_h.addWidget(cancel_btn)
        layout.addLayout(btn_h)

        # Trigger check box toggled event to set initial state
        pre_gen_logs_cb.toggled.emit(pre_gen_logs_cb.isChecked())
        self.on_change_update_ok_btn_state()

    def ok_clicked(self):
        self.save_config()
        self.close()

    def done(self, result):
        print("Startup Time configuration window closed successfully")
        super().done(result)

    def _create_ecu_block(self, data, idx):
        gb = QGroupBox(data.get('ecu-type'))
        vbox = QVBoxLayout()
        
        # Startup Order Section
        startup_group = QGroupBox('Startup Order Configuration')
        startup_vbox = QVBoxLayout()
        startup_fl = QFormLayout()
        startup_entries = []
        for order in data.get('startup-order', []):
            row, tp, apps, count_lbl = self._create_startup_row(order.get('Order Type', ''), order.get('Applications', ''), idx)
            startup_fl.addRow(row)
            startup_entries.append((row, tp, apps))
        add_startup_btn = QPushButton('Add Startup Order')
        add_startup_btn.clicked.connect(lambda _, i=idx: [self.add_startup_row(i), self.on_change_update_ok_btn_state()])
        startup_vbox.addLayout(startup_fl)
        startup_vbox.addWidget(add_startup_btn, alignment=Qt.AlignLeft)
        startup_group.setLayout(startup_vbox)

        # Threshold Config Section
        self.threshold_group = QGroupBox('Threshold Configuration')
        threshold_vbox = QVBoxLayout()
        threshold_fl = QFormLayout()
        threshold_entries = []
        for threshold in data.get('threshold-config', []):
            row, apps, thresh, count_lbl = self._create_threshold_row(threshold.get('Applications', ''), threshold.get('Threshold', ''), idx)
            threshold_fl.addRow(row)
            threshold_entries.append((row, apps, thresh))
        add_threshold_btn = QPushButton('Add Threshold Config')
        add_threshold_btn.clicked.connect(lambda _, i=idx: [self.add_threshold_row(i), self.on_change_update_ok_btn_state()])
        threshold_vbox.addLayout(threshold_fl)
        threshold_vbox.addWidget(add_threshold_btn, alignment=Qt.AlignLeft)
        self.threshold_group.setLayout(threshold_vbox)

        vbox.addWidget(startup_group)
        vbox.addWidget(self.threshold_group)
        gb.setLayout(vbox)
        self.startup_group_list.append(startup_group)
        self.widgets['ecu-config'].append({'startup_layout': startup_fl, 'startup': startup_entries, 'threshold_layout': threshold_fl, 'threshold': threshold_entries})
        return gb

    def _create_startup_row(self, type_val, apps_val, ecu_idx):
        row = QWidget()
        main_layout = QHBoxLayout(); row.setLayout(main_layout)
        
        # Left side - form layout for type and apps
        left_widget = QWidget()
        left_form = QFormLayout(left_widget)
        left_form.setContentsMargins(0, 0, 0, 0)
        
        # Type row
        dd = QComboBox(); dd.addItems(["Sequential", "Parallel"])
        dd.setFixedWidth(150)  # Set fixed width to 150 pixels
        idx = dd.findText(type_val)
        dd.setCurrentIndex(idx if idx != -1 else 0)
        # dd.currentIndexChanged.connect(lambda idx: self.ok_btn.setEnabled(True))
        
        # Apps row
        apps = QLineEdit(apps_val)
        apps.setPlaceholderText('App1, App2')
        apps.setMaxLength(250)
        count_lbl = QLabel(f"{len(apps.text())} / {apps.maxLength()}")
        apps.textChanged.connect(lambda text: [count_lbl.setText(f"{len(text)} / {apps.maxLength()}"), self.on_change_update_ok_btn_state()])

        apps_row = QWidget()
        apps_hl = QHBoxLayout(apps_row)
        apps_hl.setContentsMargins(0, 0, 0, 0)
        apps_hl.addWidget(apps)
        apps_hl.addWidget(count_lbl)
        
        left_form.addRow(QLabel('Order Type'), dd)
        left_form.addRow(QLabel('Applications'), apps_row)

        rem = QPushButton('Remove')
        rem.clicked.connect(lambda _, i=ecu_idx, r=row: [self.remove_startup_row(i, r), self.on_change_update_ok_btn_state()])
        
        main_layout.addWidget(left_widget)
        main_layout.addWidget(rem, alignment=Qt.AlignVCenter)
        
        return row, dd, apps, count_lbl

    def _create_threshold_row(self, apps_val, threshold_val, ecu_idx):
        row = QWidget()
        main_layout = QHBoxLayout(); row.setLayout(main_layout)
        
        # Left side - form layout for apps and threshold
        left_widget = QWidget()
        left_form = QFormLayout(left_widget)
        left_form.setContentsMargins(0, 0, 0, 0)
        
        # Applications row
        apps = QLineEdit(apps_val)
        apps.setPlaceholderText('App1, App2, App3')
        apps.setMaxLength(250)
        count_lbl = QLabel(f"{len(apps.text())} / {apps.maxLength()}")
        apps.textChanged.connect(lambda text: [count_lbl.setText(f"{len(text)} / {apps.maxLength()}"), self.on_change_update_ok_btn_state()])

        apps_row = QWidget()
        apps_hl = QHBoxLayout(apps_row)
        apps_hl.setContentsMargins(0, 0, 0, 0)
        apps_hl.addWidget(apps)
        apps_hl.addWidget(count_lbl)
        
        # Threshold row
        thresh = QLineEdit(str(threshold_val))
        thresh.setPlaceholderText('5')
        thresh.setValidator(CustomIntValidator(1, 100))
        thresh.setFixedWidth(80)
        thresh.textChanged.connect(lambda text: self.on_change_update_ok_btn_state())
        
        thresh_row = QWidget()
        thresh_hl = QHBoxLayout(thresh_row)
        thresh_hl.setContentsMargins(0, 0, 0, 0)
        thresh_hl.addWidget(thresh)
        thresh_hl.addWidget(QLabel('sec'))
        thresh_hl.addStretch()  # Push everything to the left

        left_form.addRow(QLabel('Applications'), apps_row)
        left_form.addRow(QLabel('Threshold'), thresh_row)

        # Right side - Remove button (centered vertically)
        rem = QPushButton('Remove')
        rem.clicked.connect(lambda _, i=ecu_idx, r=row: [self.remove_threshold_row(i, r), self.on_change_update_ok_btn_state()])
        
        main_layout.addWidget(left_widget)
        main_layout.addWidget(rem, alignment=Qt.AlignVCenter)
        
        return row, apps, thresh, count_lbl

    def on_change_update_ok_btn_state(self):
        enabled = True
        for key in ['DLT-Viewer Log Capture Time', 'Iterations', 'Threshold', 'Power ON-OFF Delay']:
            if key in ['DLT-Viewer Log Capture Time', 'Power ON-OFF Delay'] and self.widgets['Pre-Generated Logs'].isChecked():
                continue
            text = self.widgets[key][0].text()
            if not text or len(text) == 0:
                enabled = False
                break
        if enabled and not self.widgets['Pre-Generated Logs'].isChecked():
            path_cb = self.widgets['windows.Is Environment Path Set']
            path_le = self.widgets['windows.DLT-Viewer Installed Path']
            if not path_cb.isChecked() and (not path_le.text() or len(path_le.text()) == 0):
                enabled = False
        if enabled:
            vcb = self.widgets['Startup Order Judgement']
            if vcb.isChecked():
                if enabled and self.isRCAR:
                    if len(self.widgets['ecu-config'][0]['startup']) == 0:
                        enabled=False
                    else:
                        for entry in self.widgets['ecu-config'][0]['startup']:
                            if not entry[2].text() or len(entry[2].text()) == 0:
                                enabled = False
                                break
                if enabled and self.isSOC0:
                    if len(self.widgets['ecu-config'][1]['startup']) == 0:
                        enabled=False
                    else:
                        for entry in self.widgets['ecu-config'][1]['startup']:
                            if not entry[2].text() or len(entry[2].text()) == 0:
                                enabled = False
                                break
                if enabled and self.isSOC1:
                    if len(self.widgets['ecu-config'][2]['startup']) == 0:
                        enabled=False
                    else:
                        for entry in self.widgets['ecu-config'][2]['startup']:
                            if not entry[2].text() or len(entry[2].text()) == 0:
                                enabled = False
                                break
        if enabled:
            # Check threshold entries for RCAR
            for entry in self.widgets['ecu-config'][0]['threshold']:
                if not entry[1].text() or len(entry[1].text()) == 0 or not entry[2].text() or len(entry[2].text()) == 0:
                    enabled = False
                    break
        if enabled:
            # Check threshold entries for SoC0
            for entry in self.widgets['ecu-config'][1]['threshold']:
                if not entry[1].text() or len(entry[1].text()) == 0 or not entry[2].text() or len(entry[2].text()) == 0:
                    enabled = False
                    break
        if enabled:
            # Check threshold entries for SoC1
            for entry in self.widgets['ecu-config'][2]['threshold']:
                if not entry[1].text() or len(entry[1].text()) == 0 or not entry[2].text() or len(entry[2].text()) == 0:
                    enabled = False
                    break

        self.ok_btn.setEnabled(enabled)
           
    def add_startup_row(self, idx):
        # self.ok_btn.setDisabled(False)
        entry = self.widgets['ecu-config'][idx]
        row, dd, apps, count_lbl = self._create_startup_row('', '', idx)
        entry['startup_layout'].addRow(row)
        entry['startup'].append((row, dd, apps))

    def remove_startup_row(self, idx, row):
        # self.ok_btn.setDisabled(False)
        entry = self.widgets['ecu-config'][idx]
        fl = entry['startup_layout']
        for i in range(fl.rowCount()):
            w = fl.itemAt(i, QFormLayout.FieldRole).widget()
            if w is row:
                fl.removeRow(i)
                break
        entry['startup'] = [e for e in entry['startup'] if e[0] is not row]

    def add_threshold_row(self, idx):
        entry = self.widgets['ecu-config'][idx]
        row, apps, thresh, count_lbl = self._create_threshold_row('', '', idx)
        entry['threshold_layout'].addRow(row)
        entry['threshold'].append((row, apps, thresh))

    def remove_threshold_row(self, idx, row):
        entry = self.widgets['ecu-config'][idx]
        fl = entry['threshold_layout']
        for i in range(fl.rowCount()):
            w = fl.itemAt(i, QFormLayout.FieldRole).widget()
            if w is row:
                fl.removeRow(i)
                break
        entry['threshold'] = [e for e in entry['threshold'] if e[0] is not row]

    def browse_path(self, line_edit):
        path, _ = QFileDialog.getOpenFileName(self, 'Select dlt-viewer executable', '', 'Executable Files (*.exe)')
        if path:
            line_edit.setText(path)

    def browse_log_folder_path(self, line_edit):
        path = QFileDialog.getExistingDirectory(self, 'Select Log Folder')
        if path:
            line_edit.setText(path)

    def save_config(self):
        data = {}
        for key in ['DLT-Viewer Log Capture Time', 'Iterations', 'Threshold', 'Power ON-OFF Delay']:
            w = self.widgets[key][0]
            # print(w.text())
            if w.text() and len(w.text())>0:
                data[key] = int(w.text())
        data['Startup Order Judgement'] = self.widgets['Startup Order Judgement'].isChecked()
        data['Pre-Generated Logs'] = self.widgets['Pre-Generated Logs'].isChecked()
        data['windows'] = {
            'Is Environment Path Set': self.widgets['windows.Is Environment Path Set'].isChecked(),
            'DLT-Viewer Installed Path': self.widgets['windows.DLT-Viewer Installed Path'].text()
        }
        ec = []
        for idx, item in enumerate(self.widgets['ecu-config']):
            title = self.ecu_block_list[idx].title()
            ec_item = {'ecu-type': title, 'startup-order': [], 'threshold-config': []}
            for _, dd, apps in item['startup']:
                ec_item['startup-order'].append({'Order Type': dd.currentText(), 'Applications': apps.text()})
            for _, apps, thresh in item['threshold']:
                if thresh.text():  # Only save if threshold value is provided
                    ec_item['threshold-config'].append({'Applications': apps.text(), 'Threshold': int(thresh.text())})
            ec.append(ec_item)
        data['ecu-config'] = ec
        try:
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=4)

            self.accept()
        except Exception as e:
            print(f'Failed to save config: {e}')