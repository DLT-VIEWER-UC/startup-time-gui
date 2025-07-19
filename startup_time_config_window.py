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
        # 'script-execution-time-in-seconds': 0,
        # 'iterations': 0,
        # 'threshold-in-seconds': 0,
        'validate-startup-order': False,
        'windows': {'isPathSet': False, 'dltViewerPath': ''},
        'ecu-config': []
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
        self.isElite, self.isPadas = True, False
        self.isRCAR, self.isSOC0, self.isSOC1 = True, True, True

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
        general_group.setFixedHeight(180)
        general_layout = QFormLayout()
        for key, validator in [
            ('script-execution-time-in-seconds', CustomIntValidator(1, 500)),
            ('iterations', CustomIntValidator(1, 50)),
            ('threshold-in-seconds', CustomIntValidator(1, 100))
        ]:
            # print(key, str(self.config_data.get(key, '')))
            le = QLineEdit(str(self.config_data.get(key, '')))
            le.setPlaceholderText('0')
            le.textChanged.connect(lambda text: [self.on_change_update_ok_btn_state()])
            le.setValidator(validator)
            le.setFixedWidth(150)
            row_layout = QHBoxLayout()
            row_layout.addWidget(le)
            if key != 'iterations':
                row_layout.addWidget(QLabel('sec'))
            general_layout.addRow(QLabel(key), row_layout)
            self.widgets[key] = le
        vcb = QCheckBox(); vcb.setChecked(self.config_data.get('validate-startup-order', False))
        general_layout.addRow(QLabel('validate-startup-order'), vcb)
        self.widgets['validate-startup-order'] = vcb
        general_group.setLayout(general_layout)
        layout.addWidget(general_group)

        # Windows Settings
        win_group = QGroupBox('Windows Settings')
        win_group.setFixedHeight(100)
        win_layout = QFormLayout()
        win = self.config_data.get('windows', {})
        path_cb = QCheckBox(); path_cb.setChecked(win.get('isPathSet', False))
        win_layout.addRow(QLabel('isPathSet'), path_cb)
        self.widgets['windows.isPathSet'] = path_cb

        # Path line edit with char count
        path_le = QLineEdit(win.get('dltViewerPath', ''))
        # path_le.textChanged.connect(lambda text: [self.ok_btn.setDisabled(False)])
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
        win_layout.addRow(QLabel('dltViewerPath'), hl)
        self.widgets['windows.dltViewerPath'] = path_le
        win_group.setLayout(win_layout)
        layout.addWidget(win_group)

        # Enable/disable path based on checkbox
        path_le.setDisabled(path_cb.isChecked())
        browse_btn.setDisabled(path_cb.isChecked())
        count_lbl.setDisabled(path_cb.isChecked())
       
        path_cb.toggled.connect(lambda checked: [path_le.setDisabled(checked), browse_btn.setDisabled(checked), count_lbl.setDisabled(checked), self.on_change_update_ok_btn_state()])#, self.ok_btn.setDisabled(False)])

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


        # OK/Cancel
        btn_h = QHBoxLayout()
        btn_h.addStretch()
        self.ok_btn = QPushButton('OK'); self.ok_btn.clicked.connect(self.ok_clicked)
        cancel_btn = QPushButton('Cancel'); cancel_btn.clicked.connect(self.reject)
        btn_h.addWidget(self.ok_btn); btn_h.addWidget(cancel_btn)
        layout.addLayout(btn_h)

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
        startup_group = QGroupBox('Startup Order')
        startup_vbox = QVBoxLayout()
        startup_fl = QFormLayout()
        startup_entries = []
        for order in data.get('startup-order', []):
            row, tp, apps, count_lbl = self._create_startup_row(order.get('type', ''), order.get('apps', ''), idx)
            startup_fl.addRow(row)
            startup_entries.append((row, tp, apps))
        add_startup_btn = QPushButton('Add Startup Order')
        add_startup_btn.clicked.connect(lambda _, i=idx: [self.add_startup_row(i), self.on_change_update_ok_btn_state()])
        startup_vbox.addLayout(startup_fl)
        startup_vbox.addWidget(add_startup_btn, alignment=Qt.AlignLeft)
        startup_group.setLayout(startup_vbox)

        # Threshold Config Section
        self.threshold_group = QGroupBox('Threshold Config')
        threshold_vbox = QVBoxLayout()
        threshold_fl = QFormLayout()
        threshold_entries = []
        for threshold in data.get('threshold-config', []):
            row, apps, thresh, count_lbl = self._create_threshold_row(threshold.get('application-group', ''), threshold.get('threshold-in-seconds', ''), idx)
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
        hl = QHBoxLayout(); row.setLayout(hl)
        dd = QComboBox(); dd.addItems(["Sequential", "Parallel"])
        idx = dd.findText(type_val)
        dd.setCurrentIndex(idx if idx != -1 else 0)
        # dd.currentIndexChanged.connect(lambda idx: self.ok_btn.setEnabled(True))
       
        apps = QLineEdit(apps_val)
        apps.setPlaceholderText('App1, App2')
        apps.setMaxLength(250)
        count_lbl = QLabel(f"{len(apps.text())} / {apps.maxLength()}")
        apps.textChanged.connect(lambda text: [count_lbl.setText(f"{len(text)} / {apps.maxLength()}"), self.on_change_update_ok_btn_state()])#, self.ok_btn.setDisabled(False)])

        rem = QPushButton('Remove')
        rem.clicked.connect(lambda _, i=ecu_idx, r=row: [self.remove_startup_row(i, r), self.on_change_update_ok_btn_state()])

        hl.addWidget(QLabel('type')); hl.addWidget(dd)
        hl.addWidget(QLabel('apps')); hl.addWidget(apps)
        hl.addWidget(count_lbl)
        hl.addWidget(rem)
        return row, dd, apps, count_lbl

    def _create_threshold_row(self, apps_val, threshold_val, ecu_idx):
        row = QWidget()
        hl = QHBoxLayout(); row.setLayout(hl)
        
        apps = QLineEdit(apps_val)
        apps.setPlaceholderText('App1, App2, App3')
        apps.setMaxLength(250)
        count_lbl = QLabel(f"{len(apps.text())} / {apps.maxLength()}")
        apps.textChanged.connect(lambda text: [count_lbl.setText(f"{len(text)} / {apps.maxLength()}"), self.on_change_update_ok_btn_state()])

        thresh = QLineEdit(str(threshold_val))
        thresh.setPlaceholderText('5')
        thresh.setValidator(CustomIntValidator(1, 100))
        thresh.setFixedWidth(80)
        thresh.textChanged.connect(lambda text: self.on_change_update_ok_btn_state())

        rem = QPushButton('Remove')
        rem.clicked.connect(lambda _, i=ecu_idx, r=row: [self.remove_threshold_row(i, r), self.on_change_update_ok_btn_state()])

        hl.addWidget(QLabel('applications')); hl.addWidget(apps)
        hl.addWidget(count_lbl)
        hl.addWidget(QLabel('threshold')); hl.addWidget(thresh)
        hl.addWidget(QLabel('sec'))
        hl.addWidget(rem)
        return row, apps, thresh, count_lbl

    def on_change_update_ok_btn_state(self):
        enabled = True
        for key in ['script-execution-time-in-seconds', 'iterations', 'threshold-in-seconds']:
            text = self.widgets[key].text()
            if not text or len(text) == 0:
                enabled = False
                break
        if enabled:
            path_cb = self.widgets['windows.isPathSet']
            path_le = self.widgets['windows.dltViewerPath']
            if not path_cb.isChecked() and (not path_le.text() or len(path_le.text()) == 0):
                enabled = False
        if enabled:
            vcb = self.widgets['validate-startup-order']
            if vcb.isChecked():
                if enabled and self.isRCAR:
                    if len(self.widgets['ecu-config'][0]['startup']) == 0:
                        enabled=False
                    else:
                        for entry in self.widgets['ecu-config'][0]['startup']:
                            if not entry[2].text() or len(entry[2].text()) == 0:
                                enabled = False
                                break
                        # Check threshold entries for RCAR
                        for entry in self.widgets['ecu-config'][0]['threshold']:
                            if not entry[1].text() or len(entry[1].text()) == 0 or not entry[2].text() or len(entry[2].text()) == 0:
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
                        # Check threshold entries for SoC0
                        for entry in self.widgets['ecu-config'][1]['threshold']:
                            if not entry[1].text() or len(entry[1].text()) == 0 or not entry[2].text() or len(entry[2].text()) == 0:
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
                        # Check threshold entries for SoC1
                        for entry in self.widgets['ecu-config'][2]['threshold']:
                            if not entry[1].text() or len(entry[1].text()) == 0 or not entry[2].text() or len(entry[2].text()) == 0:
                                enabled = False
                                break
                    # print(idx, len(ecu_widgets['startup']))

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
        path, _ = QFileDialog.getOpenFileName(self, 'Select dlt-viewer executable')
        if path:
            line_edit.setText(path)

    def save_config(self):
        data = {}
        for key in ['script-execution-time-in-seconds', 'iterations', 'threshold-in-seconds']:
            w = self.widgets[key]
            # print(w.text())
            if w.text() and len(w.text())>0:
                data[key] = int(w.text())
        data['validate-startup-order'] = self.widgets['validate-startup-order'].isChecked()
        data['windows'] = {
            'isPathSet': self.widgets['windows.isPathSet'].isChecked(),
            'dltViewerPath': self.widgets['windows.dltViewerPath'].text()
        }
        data['PADAS'] = {
            'RCAR': self.isPadas and self.isRCAR
        }
        data['Elite'] = {
                'RCAR': self.isRCAR and self.isElite,
                'SoC0': self.isSOC0 and self.isElite,
                'SoC1': self.isSOC1 and self.isElite
        }
        ec = []
        for idx, item in enumerate(self.widgets['ecu-config']):
            title = self.ecu_block_list[idx].title()
            ec_item = {'ecu-type': title, 'startup-order': [], 'threshold-config': []}
            for _, dd, apps in item['startup']:
                ec_item['startup-order'].append({'type': dd.currentText(), 'apps': apps.text()})
            for _, apps, thresh in item['threshold']:
                if thresh.text():  # Only save if threshold value is provided
                    ec_item['threshold-config'].append({'application-group': apps.text(), 'threshold-in-seconds': int(thresh.text())})
            ec.append(ec_item)
        data['ecu-config'] = ec
        try:
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=4)

            self.accept()
        except Exception as e:
            print(f'Failed to save config: {e}')