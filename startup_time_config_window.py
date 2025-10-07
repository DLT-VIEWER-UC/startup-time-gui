from collapsible_groupbox import CollapsibleGroupBox
import os
import subprocess
import platform
from pathlib import Path
from PyQt5.QtCore import QFileSystemWatcher
from imports_utils import *


class CustomIntValidator(QIntValidator):
    def __init__(self, min_value, max_value, parent=None):
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
       
           
class StartupTimeConfig(QDialog):
    DEFAULT_CONFIG = {
        # 'DLT-Viewer Log Capture Time': 0,
        # 'Iterations': 0,
        # 'Threshold': 0,
        'Startup Order Judgement': False,
        'Application Registration': False,
        'Order Mismatch Judgement': False,
        'Not Found Judgement': False,
        'Not Configured Judgement': False,
        'windows': {'Is Environment Path Set': False, 'DLT-Viewer Installed Path': ''},
        'ecu-config': []
    }

    def __init__(self, main_window, is_checked):
        super().__init__()
        self.main_window = main_window
        self.set_window_properties()

        self.config_path = './Startup_Time_Scripts/startup_time_config.json'
        self.config_data = self.load_config()
        self.widgets = {}
        self.ecu_block_list = []
        self.startup_group_list = []
        
        self.isElite, self.isPadas = True, True
        self.isRCAR, self.isSOC0, self.isSOC1 = True, True, True

        # Flag indicating whether any ECU is selected in the main window
        self.is_any_ecu_selected_flag = main_window.is_any_ecu_selected_flag
        
        # Check which ECU type is enabled (only one can be selected at a time)
        # self.ecu_selection = {
        #     'Elite': {'RCAR': True, 'SoC0': False, 'SoC1': True},
        #     'PADAS': {'RCAR': False}
        # }
        
        self.ecu_selection = main_window.ecu_selection_status
        if self.is_any_ecu_selected_flag and is_checked:
            if self.ecu_selection.get('PADAS', {}).get('RCAR', False):
                self.isElite = False
                self.isSOC0 = False
                self.isSOC1 = False
            else:
                if self.ecu_selection.get('Elite', {}).get('RCAR', False):
                    self.isPadas = False
                else:
                    self.isRCAR = False
                if self.ecu_selection.get('Elite', {}).get('SoC0', False):
                    self.isPadas = False
                else:
                    self.isSOC0 = False
                if self.ecu_selection.get('Elite', {}).get('SoC1', False):
                    self.isPadas = False
                else:
                    self.isSOC1 = False

        # Initialize file system watcher for logs folder
        self.logs_path = Path(__file__).parent.joinpath('Startup_Time_Scripts/Pre-Generated_Logs/Logs')
        self.setup_file_watcher()

        # Initialize application list from Excel file
        self.application_list = None
        self.parse_application_input_list()

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
        window_height = 850

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

    def setup_file_watcher(self):
        """Setup file system watcher for the logs folder and its subdirectories"""
        self.file_watcher = QFileSystemWatcher()
        
        # Create directories if they don't exist and add them to watcher
        directories_to_watch = [
            self.logs_path / 'PADAS_RCAR',
            self.logs_path / 'ELITE_RCAR',
            self.logs_path / 'ELITE_SoC0', 
            self.logs_path / 'ELITE_SoC1'
        ]
        
        for directory in directories_to_watch:
            if not directory.exists():
                try:
                    directory.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    print(f"Error creating directory {directory}: {e}")
                    continue
            
            # Add directory to watcher
            self.file_watcher.addPath(str(directory))
        
        # Add the current directory to watch for ApplicationInputList.xlsx
        current_dir = Path(__file__).parent
        self.app_input_file_path = current_dir / 'ApplicationInputList.xlsx'
        self.file_watcher.addPath(str(current_dir))
        
        # Connect the watcher signals to update methods
        self.file_watcher.directoryChanged.connect(self.update_logs_tooltip)
        self.file_watcher.fileChanged.connect(self.update_logs_tooltip)
        self.file_watcher.directoryChanged.connect(self.update_app_input_button)
        self.file_watcher.directoryChanged.connect(self.refresh_application_list)

    def check_log_files(self):
        """Check for .log files in the specified directories and return status"""
        status = {
            'main': False,
            'rcar': False, 
            'soc0': False,
            'soc1': False
        }
        
        try:
            # Check main Logs folder
            padas_path = self.logs_path / 'PADAS_RCAR'
            if padas_path.exists():
                status['main'] = any(padas_path.glob('*.log'))

            # Check RCAR subfolder
            rcar_path = self.logs_path / 'ELITE_RCAR'
            if rcar_path.exists():
                status['rcar'] = any(rcar_path.glob('*.log'))
            
            # Check SoC0 subfolder  
            soc0_path = self.logs_path / 'ELITE_SoC0'
            if soc0_path.exists():
                status['soc0'] = any(soc0_path.glob('*.log'))
            
            # Check SoC1 subfolder
            soc1_path = self.logs_path / 'ELITE_SoC1'
            if soc1_path.exists():
                status['soc1'] = any(soc1_path.glob('*.log'))
                
        except Exception as e:
            print(f"Error checking log files: {e}")
        
        return status

    def update_logs_tooltip(self):
        """Update the tooltip based on the presence of log files"""
        if not hasattr(self, 'open_logs_btn'):
            return
            
        status = self.check_log_files()
        active_status = list()
        
        # Create tooltip text based on status
        tooltip_lines = ["Pre-Generated Logs Folder Status:"]
        
        # Main folder
        main_status = "✓" if status['main'] else "✗"
        if self.isPadas and self.isRCAR:
            active_status.append(status['main'])
            tooltip_lines.append(f"{main_status} RCAR Logs folder (PADAS): {'Has .log files' if status['main'] else 'No .log files'}")
        
        # RCAR folder
        rcar_status = "✓" if status['rcar'] else "✗"
        if self.isElite and self.isRCAR:
            active_status.append(status['rcar'])
            tooltip_lines.append(f"{rcar_status} RCAR folder (Elite): {'Has .log files' if status['rcar'] else 'No .log files'}")
        
        # SoC0 folder
        soc0_status = "✓" if status['soc0'] else "✗"
        if self.isElite and self.isSOC0:
            active_status.append(status['soc0'])
            tooltip_lines.append(f"{soc0_status} SoC0 folder (Elite): {'Has .log files' if status['soc0'] else 'No .log files'}")

        # SoC1 folder
        soc1_status = "✓" if status['soc1'] else "✗"
        if self.isElite and self.isSOC1:
            active_status.append(status['soc1'])
            tooltip_lines.append(f"{soc1_status} SoC1 folder (Elite): {'Has .log files' if status['soc1'] else 'No .log files'}")

        # Set the tooltip
        tooltip_text = '\n'.join(tooltip_lines)
        self.open_logs_btn.setToolTip(tooltip_text)
        
        # Update stylesheet with proper state handling
        border_color = 'green' if all(active_status) else 'red'
        self.open_logs_btn.setStyleSheet(f"""
            QPushButton:enabled {{
                background-color: white;
                color: black;
                border: 1px solid {border_color};
                border-radius: 5px;
            }}
            QPushButton:disabled {{
                background-color: #f0f0f0;
                color: #808080;
                border: 1px solid #d0d0d0;
                border-radius: 5px;
            }}
        """)

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
        general_group.setFixedHeight(280)
        general_layout = QFormLayout()
        for key, validator in [
            ('DLT-Viewer Log Capture Time', CustomIntValidator(1, 500)),
            ('Iterations', CustomIntValidator(1, 50)),
            ('Power ON-OFF Delay', CustomIntValidator(1, 100))
        ]:
            widgets_lst = list()
            le = QLineEdit(str(self.config_data.get(key, '')))
            le.textChanged.connect(lambda text: [self.on_change_update_ok_btn_state()])
            le.setValidator(validator)
            le.setFixedWidth(150)
            widgets_lst.append(le)
            row_layout = QHBoxLayout()
            row_layout.addWidget(le)
            units_text = ''
            if key == 'DLT-Viewer Log Capture Time':
                units_text = '[Int: 20-500 sec]'
            elif key == 'Iterations':
                units_text = '[Int: 1-50]'
            elif key == 'Power ON-OFF Delay':
                units_text = '[Int: 20-50 sec]'
            units_lbl = QLabel(units_text)
            row_layout.addWidget(units_lbl)
            widgets_lst.append(units_lbl)
            key_lbl = QLabel(key)
            widgets_lst.append(key_lbl)
            general_layout.addRow(key_lbl, row_layout)
            self.widgets[key] = widgets_lst
        
        # Application Input List row
        app_input_layout = QHBoxLayout()
        self.app_input_btn = QPushButton()
        self.app_input_btn.setFixedSize(30, 24)  # Make it square and slightly larger for the icon
        self.app_input_btn.setText("📋")  # Use clipboard/Excel emoji as icon
        self.app_input_btn.clicked.connect(self.open_application_input_list)
        app_input_layout.addWidget(self.app_input_btn)
        app_input_layout.addStretch()  # Push everything to the left
        general_layout.addRow(QLabel('Application Input List'), app_input_layout)
        
        vcb = QCheckBox(); vcb.setChecked(self.config_data.get('Startup Order Judgement', False))
        general_layout.addRow(QLabel('Startup Order Judgement'), vcb)
        self.widgets['Startup Order Judgement'] = vcb
        
        # Add the four new checkboxes that depend on 'Startup Order Judgement'
        app_registration_cb = QCheckBox(); app_registration_cb.setChecked(self.config_data.get('Application Registration', False))
        app_registration_label = QLabel('Application Registration')
        general_layout.addRow(app_registration_label, app_registration_cb)
        self.widgets['Application Registration'] = app_registration_cb
        
        # Create horizontal layout for the three judgement checkboxes without header
        judgement_hlayout = QHBoxLayout()
        judgement_hlayout.setContentsMargins(0, 0, 0, 0)
        
        # Order Mismatch Judgement
        order_mismatch_label = QLabel('Order Mismatch Judgement')
        order_mismatch_cb = QCheckBox()
        order_mismatch_cb.setChecked(self.config_data.get('Order Mismatch Judgement', False))
        self.widgets['Order Mismatch Judgement'] = order_mismatch_cb
        
        # Not Found Judgement
        not_found_label = QLabel('Not Found Judgement')
        not_found_cb = QCheckBox()
        not_found_cb.setChecked(self.config_data.get('Not Found Judgement', False))
        self.widgets['Not Found Judgement'] = not_found_cb
        
        # Not Configured Judgement
        not_configured_label = QLabel('Not Configured Judgement')
        not_configured_cb = QCheckBox()
        not_configured_cb.setChecked(self.config_data.get('Not Configured Judgement', False))
        self.widgets['Not Configured Judgement'] = not_configured_cb
        
        # Add components to horizontal layout with spacing
        judgement_hlayout.addWidget(order_mismatch_label)
        judgement_hlayout.addSpacing(16)
        judgement_hlayout.addWidget(order_mismatch_cb)
        judgement_hlayout.addSpacing(40)  # Space between first and second option
        judgement_hlayout.addWidget(not_found_label)
        judgement_hlayout.addSpacing(16)
        judgement_hlayout.addWidget(not_found_cb)
        judgement_hlayout.addSpacing(40)  # Space between second and third option
        judgement_hlayout.addWidget(not_configured_label)
        judgement_hlayout.addSpacing(16)
        judgement_hlayout.addWidget(not_configured_cb)
        judgement_hlayout.addStretch()  # Push everything to the left
        
        # Add the horizontal layout directly to the form layout
        general_layout.addRow(judgement_hlayout)
        
        self.pre_gen_logs_cb = QCheckBox(); self.pre_gen_logs_cb.setChecked(self.config_data.get('Pre-Generated Logs', False))
        
        # Create horizontal layout for Pre-Generated Logs with button
        pre_gen_layout = QHBoxLayout()
        pre_gen_layout.addWidget(self.pre_gen_logs_cb)
        
        # Add button to open File Explorer
        self.open_logs_btn = QPushButton()
        self.open_logs_btn.setFixedSize(30, 24)  # Make it square and slightly larger for the icon
        self.open_logs_btn.setText("📁")  # Use folder emoji as icon
        self.open_logs_btn.clicked.connect(self.open_logs_folder)
        self.open_logs_btn.setEnabled(self.pre_gen_logs_cb.isChecked())  # Initially set based on checkbox state
        
        # Set style for disabled state to make it grey for better readability
        self.open_logs_btn.setStyleSheet("""
            QPushButton:enabled {
                background-color: white;
                color: black;
            }
            QPushButton:disabled {
                background-color: #f0f0f0;
                color: #808080;
                border: 1px solid #d0d0d0;
            }
        """)
        
        # Set initial tooltip
        self.update_logs_tooltip()
        pre_gen_layout.addWidget(self.open_logs_btn)
        pre_gen_layout.addStretch()  # Push everything to the left
        
        general_layout.addRow(QLabel('Pre-Generated Logs'), pre_gen_layout)
        self.widgets['Pre-Generated Logs'] = self.pre_gen_logs_cb
        
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
        path_le.textChanged.connect(lambda text: [count_lbl.setText(f"{len(text)} / {path_le.maxLength()}"), self.update_border('windows.DLT-Viewer Installed Path')])
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

        path_cb.toggled.connect(lambda checked: [dlt_path_lbl.setDisabled(checked), path_le.setDisabled(checked), browse_btn.setDisabled(checked), count_lbl.setDisabled(checked), self.on_change_update_ok_btn_state(), self.update_border('windows.DLT-Viewer Installed Path')])

        # ECU Configurations
        self.ec_group = QGroupBox('ECU Configurations')
        ec_vbox = QVBoxLayout()
        self.widgets['ecu-config'] = []

        # Load existing or defaults
        ecu_types = {ecu['ecu-type']: ecu for ecu in self.config_data.get('ecu-config', [])}
        for idx, ecu_type in enumerate(['PADAS', 'RCAR', 'SoC0', 'SoC1']):
            ecu_data = ecu_types.get(ecu_type, {'ecu-type': ecu_type, 'startup-order': []})
            block = self._create_ecu_block(ecu_data, idx)
            valid_gb = True
            if ecu_type == 'PADAS':
                # block.setVisible(self.isPadas and self.isRCAR)
                valid_gb = self.is_any_ecu_selected_flag and (self.isPadas and self.isRCAR)
                block.disableRemoveButton(valid_gb)
            if ecu_type=='RCAR':
                # block.setVisible(self.isRCAR and self.isElite)
                valid_gb = self.is_any_ecu_selected_flag and (self.isElite and self.isRCAR)
                block.disableRemoveButton(valid_gb)
            elif ecu_type=='SoC0':
                # block.setVisible(self.isSOC0 and self.isElite)
                valid_gb = self.is_any_ecu_selected_flag and (self.isElite and self.isSOC0)
                block.disableRemoveButton(valid_gb)
            elif ecu_type=='SoC1':
                # block.setVisible(self.isSOC1 and self.isElite)
                valid_gb = self.is_any_ecu_selected_flag and (self.isElite and self.isSOC1)
                block.disableRemoveButton(valid_gb)
            print(f"ECU: {ecu_type}, Valid: {valid_gb}")
            block.setStyleSheet(block.styleSheet()+f"CollapsibleGroupBox{{border: {'1px solid red' if self.is_any_ecu_selected_flag and not valid_gb else '0px'};}}")  # Set border color based on validity
            for startup_group in self.startup_group_list:
                startup_group.setEnabled(vcb.isChecked()) 
            self.ecu_block_list.append(block)
            ec_vbox.addWidget(block)

        self.ec_group.setLayout(ec_vbox)
        layout.addWidget(self.ec_group)
        
        # Enable/disable the dependent checkboxes and startup groups based on 'Startup Order Judgement'
        def toggle_startup_order_dependent_controls(checked):
            self.on_change_update_ok_btn_state()
            # Enable/disable startup groups
            for startup_group in self.startup_group_list:
                startup_group.setEnabled(checked)
            # Enable/disable the four dependent checkboxes
            app_registration_cb.setEnabled(checked)
            app_registration_label.setEnabled(checked)
            order_mismatch_cb.setEnabled(checked)
            order_mismatch_label.setEnabled(checked)
            not_found_cb.setEnabled(checked)
            not_found_label.setEnabled(checked)
            not_configured_cb.setEnabled(checked)
            not_configured_label.setEnabled(checked)
        
        # Set initial state for dependent controls
        startup_order_enabled = vcb.isChecked()
        app_registration_cb.setEnabled(startup_order_enabled)
        order_mismatch_cb.setEnabled(startup_order_enabled)
        not_found_cb.setEnabled(startup_order_enabled)
        not_configured_cb.setEnabled(startup_order_enabled)
        
        vcb.toggled.connect(toggle_startup_order_dependent_controls)
        self.pre_gen_logs_cb.toggled.connect(lambda checked: [
            self.on_change_update_ok_btn_state(),
            win_group.setDisabled(checked),
            self.open_logs_btn.setEnabled(checked)] + [  # Enable/disable the logs folder button
            w.setDisabled(checked) for w in self.widgets['DLT-Viewer Log Capture Time'] + self.widgets['Power ON-OFF Delay']
        ] + [
            self.update_border('DLT-Viewer Log Capture Time'),
            self.update_border('Power ON-OFF Delay'),
            self.update_border('Iterations'),
            self.update_border('windows.DLT-Viewer Installed Path')
        ])

        # OK/Cancel
        btn_h = QHBoxLayout()
        btn_h.addStretch()
        self.ok_btn = QPushButton('OK'); self.ok_btn.clicked.connect(self.ok_clicked)
        cancel_btn = QPushButton('Cancel'); cancel_btn.clicked.connect(self.reject)
        btn_h.addWidget(self.ok_btn); btn_h.addWidget(cancel_btn)
        layout.addLayout(btn_h)

        self.widgets['DLT-Viewer Log Capture Time'][0].textChanged.connect(lambda text: [self.update_border('DLT-Viewer Log Capture Time')])
        self.widgets['Iterations'][0].textChanged.connect(lambda text: [self.update_border('Iterations')])
        self.widgets['Power ON-OFF Delay'][0].textChanged.connect(lambda text: [self.update_border('Power ON-OFF Delay')])

        # Trigger check box toggled event to set initial state
        self.pre_gen_logs_cb.toggled.emit(self.pre_gen_logs_cb.isChecked())
        for i, ecu_config in enumerate(self.widgets['ecu-config']):
            if len(ecu_config['startup']) == 0:
                self.add_startup_row(i)
        
        for idx, ecu_type in enumerate(['PADAS', 'RCAR', 'SoC0', 'SoC1']):
            block = self.ecu_block_list[idx]
            # Define the condition for each ECU type
            ecu_conditions = {
                'PADAS': self.isPadas and self.isRCAR,
                'RCAR': self.isElite and self.isRCAR,
                'SoC0': self.isElite and self.isSOC0,
                'SoC1': self.isElite and self.isSOC1
            }
            if self.is_any_ecu_selected_flag:
                if ecu_conditions[ecu_type]:
                    # ECU is selected, keep it visible
                    pass
                elif ecu_type not in ecu_types:
                    # ECU is not selected and not in config, remove it
                    block.remove_button.click()
        
        # Set initial state for Application Input List button
        self.update_app_input_button()
        
        self.on_change_update_ok_btn_state()

    def update_border(self, key):
        
        if key == 'DLT-Viewer Log Capture Time':
            text = self.widgets[key][0].text()
            if self.pre_gen_logs_cb.isChecked() or (text and 20 <= int(text) <= 500):
                self.widgets[key][0].setStyleSheet('border: 0px;')
            else:
                self.widgets[key][0].setStyleSheet('border: 1px solid red;')
        elif key == 'Power ON-OFF Delay':
            text = self.widgets[key][0].text()
            if self.pre_gen_logs_cb.isChecked() or (text and 20 <= int(text) <= 50):
                self.widgets[key][0].setStyleSheet('border: 0px;')
            else:
                self.widgets[key][0].setStyleSheet('border: 1px solid red;')
        elif key == 'Iterations':
            text = self.widgets[key][0].text()
            if (text and 1 <= int(text) <= 50):
                self.widgets[key][0].setStyleSheet('border: 0px;')
            else:
                self.widgets[key][0].setStyleSheet('border: 1px solid red;')
        elif key == 'windows.DLT-Viewer Installed Path':
            text = self.widgets[key].text()
            if self.widgets['windows.Is Environment Path Set'].isChecked() or self.pre_gen_logs_cb.isChecked() or (text and not text.startswith(' ') and not text.endswith(' ')):
                self.widgets[key].setStyleSheet('border: 0px;')
            else:
                self.widgets[key].setStyleSheet('border: 1px solid red;')

    def handle_group_removed(self, removed_group):
        """Handle when a CollapsibleGroupBox is removed - replace it with a restore button."""
        # Check if we should add a restore button
        # Only add restore button if ECU is not selected in main window
        should_add_restore = True
        
        if self.is_any_ecu_selected_flag:
            # Check if this ECU type is selected in the main window
            ecu_type = removed_group.title
            if ecu_type == 'PADAS' and  not (self.isPadas and self.isRCAR):
                should_add_restore = False
            elif ecu_type == 'RCAR' and not (self.isElite and self.isRCAR):
                should_add_restore = False
            elif ecu_type == 'SoC0' and not (self.isElite and self.isSOC0):
                should_add_restore = False
            elif ecu_type == 'SoC1' and not (self.isElite and self.isSOC1):
                should_add_restore = False
        
        if should_add_restore:
            # Create a restore button
            restore_button = removed_group.create_restore_button()
            
            # Connect the restore button to update OK button state when clicked
            restore_button.clicked.connect(self.on_change_update_ok_btn_state)
            
            # Add the restore button to the same layout position
            if removed_group.parent_layout and removed_group.layout_index >= 0:
                removed_group.parent_layout.insertWidget(removed_group.layout_index, restore_button)
            
        # Update the OK button state when a group is removed
        self.on_change_update_ok_btn_state()

    def ok_clicked(self):
        self.save_config()
        self.close()

    def done(self, result):
        print("Startup Time configuration window closed successfully")
        super().done(result)

    def _create_ecu_block(self, data, idx):
        # Create the main collapsible group box for the ECU
        gb = CollapsibleGroupBox(data.get('ecu-type'))
        vbox = QVBoxLayout()
        
        # Startup Order Section
        startup_group = QGroupBox('Startup Order Configuration')
        startup_vbox = QVBoxLayout()
        startup_fl = QFormLayout()
        startup_entries = []
        for order in data.get('startup-order', []):
            row, tp, apps, rem = self._create_startup_row(order.get('Order Type', ''), order.get('Applications', ''), idx)
            startup_fl.addRow(row)
            startup_entries.append((row, tp, apps, rem))
        add_startup_btn = QPushButton('Add Startup Order')
        add_startup_btn.clicked.connect(lambda _, i=idx: [self.add_startup_row(i), self.on_change_update_ok_btn_state(), gb.content_changed()])
        startup_vbox.addLayout(startup_fl)
        startup_vbox.addWidget(add_startup_btn, alignment=Qt.AlignLeft)
        startup_group.setLayout(startup_vbox)
        if len(startup_entries) == 1:
            startup_entries[0][3].setDisabled(True)

        # Threshold Config Section
        self.threshold_group = QGroupBox('Threshold Configuration')
        threshold_vbox = QVBoxLayout()
        threshold_fl = QFormLayout()
        threshold_entries = []
        for threshold in data.get('threshold-config', []):
            row, apps, thresh = self._create_threshold_row(threshold.get('Applications', ''), threshold.get('Threshold', ''), idx)
            threshold_fl.addRow(row)
            threshold_entries.append((row, apps, thresh))
        add_threshold_btn = QPushButton('Add Threshold Config')
        add_threshold_btn.clicked.connect(lambda _, i=idx: [self.add_threshold_row(i), self.on_change_update_ok_btn_state(), gb.content_changed()])
        threshold_vbox.addLayout(threshold_fl)
        threshold_vbox.addWidget(add_threshold_btn, alignment=Qt.AlignLeft)
        self.threshold_group.setLayout(threshold_vbox)

        vbox.addWidget(startup_group)
        vbox.addWidget(self.threshold_group)
        
        # Set the content layout for the collapsible group box
        gb.setContentLayout(vbox)
        
        # Connect the removed signal to handle restore functionality
        gb.removed.connect(self.handle_group_removed)
        
        self.startup_group_list.append(startup_group)
        self.widgets['ecu-config'].append({'startup_layout': startup_fl, 'startup': startup_entries, 'threshold_layout': threshold_fl, 'threshold': threshold_entries, 'add_startup_btn': add_startup_btn, 'add_threshold_btn': add_threshold_btn})
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
        # apps.setMaxLength(250)
        apps.textChanged.connect(lambda text: [self.on_change_update_ok_btn_state()])

        apps_row = QWidget()
        apps_hl = QHBoxLayout(apps_row)
        apps_hl.setContentsMargins(0, 0, 0, 0)
        apps_hl.addWidget(apps)
        
        left_form.addRow(QLabel('Order Type'), dd)
        left_form.addRow(QLabel('Applications'), apps_row)

        rem = QPushButton('Remove')
        rem.clicked.connect(lambda _, i=ecu_idx, r=row: [self.remove_startup_row(i, r), self.on_change_update_ok_btn_state(), self._notify_content_changed(i)])
        
        main_layout.addWidget(left_widget)
        main_layout.addWidget(rem, alignment=Qt.AlignVCenter)
        
        return row, dd, apps, rem

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
        # apps.setMaxLength(250)
        apps.textChanged.connect(lambda text: [self.on_change_update_ok_btn_state()])

        apps_row = QWidget()
        apps_hl = QHBoxLayout(apps_row)
        apps_hl.setContentsMargins(0, 0, 0, 0)
        apps_hl.addWidget(apps)
        
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
        thresh_hl.addWidget(QLabel('[Int: 1 - 100 sec]'))
        thresh_hl.addStretch()  # Push everything to the left

        left_form.addRow(QLabel('Applications'), apps_row)
        left_form.addRow(QLabel('Threshold'), thresh_row)

        # Right side - Remove button (centered vertically)
        rem = QPushButton('Remove')
        rem.clicked.connect(lambda _, i=ecu_idx, r=row: [self.remove_threshold_row(i, r), self.on_change_update_ok_btn_state(), self._notify_content_changed(i)])
        
        main_layout.addWidget(left_widget)
        main_layout.addWidget(rem, alignment=Qt.AlignVCenter)
        
        return row, apps, thresh

    def on_change_update_ok_btn_state(self):
        enabled = True
        ecu_error_list = [False, False, False, False]
        if self.is_any_ecu_selected_flag:
            if self.isPadas:
                for i in range(1, 4):
                    if not self.ecu_block_list[i].disabled:
                        enabled = False
            elif self.isElite:
                if not self.ecu_block_list[0].disabled:
                    enabled = False
                if not self.isRCAR and not self.ecu_block_list[1].disabled:
                    enabled = False
                if not self.isSOC0 and not self.ecu_block_list[2].disabled:
                    enabled = False
                if not self.isSOC1 and not self.ecu_block_list[3].disabled:
                    enabled = False
        
        for i in range(4):
            if self.ecu_block_list[i].disabled:
                continue
            for entry in self.widgets['ecu-config'][i]['startup']:
                if self.widgets['Startup Order Judgement'].isChecked() and (not entry[2].text() or len(entry[2].text()) == 0 or entry[2].text().startswith(' ') or entry[2].text().endswith(' ')):
                    entry[2].setStyleSheet('border: 1px solid red;')
                    enabled = False
                    ecu_error_list[i] = True
                else:
                    entry[2].setStyleSheet('border: 0px;')
            for entry in self.widgets['ecu-config'][i]['threshold']:
                if (not entry[1].text() or len(entry[1].text()) == 0 or entry[1].text().startswith(' ') or entry[1].text().endswith(' ')):
                    entry[1].setStyleSheet('border: 1px solid red;')
                    enabled = False
                    ecu_error_list[i] = True
                else:
                    entry[1].setStyleSheet('border: 0px;')
                if (not entry[2].text() or len(entry[2].text()) == 0 or not entry[2].text().isdigit() or not (1 <= int(entry[2].text()) <= 100)):
                    entry[2].setStyleSheet('border: 1px solid red;')
                else:
                    entry[2].setStyleSheet('border: 0px;')
        for key in ['DLT-Viewer Log Capture Time', 'Iterations', 'Power ON-OFF Delay']:
            if key in ['DLT-Viewer Log Capture Time', 'Power ON-OFF Delay'] and self.widgets['Pre-Generated Logs'].isChecked():
                continue
            text = self.widgets[key][0].text()
            if not text or len(text) == 0:
                enabled = False
                break
            if key == 'DLT-Viewer Log Capture Time':
                if not (self.pre_gen_logs_cb.isChecked() or (text and 20 <= int(text) <= 500)):
                    enabled = False
            elif key == 'Power ON-OFF Delay':
                if not (self.pre_gen_logs_cb.isChecked() or (text and 20 <= int(text) <= 50)):
                    enabled = False
            elif key == 'Iterations':
                if not (text and 1 <= int(text) <= 50):
                    enabled = False
        if not self.widgets['Pre-Generated Logs'].isChecked():
            path_cb = self.widgets['windows.Is Environment Path Set']
            path_le = self.widgets['windows.DLT-Viewer Installed Path']
            if not path_cb.isChecked() and (not path_le.text() or len(path_le.text()) == 0 or path_le.text().startswith(' ') or path_le.text().endswith(' ')):
                enabled = False
        vcb = self.widgets['Startup Order Judgement']
        if vcb.isChecked():
            if self.isRCAR and self.isPadas and not self.ecu_block_list[0].disabled:
                if len(self.widgets['ecu-config'][0]['startup']) == 0:
                    enabled=False
                    ecu_error_list[0] = True
                else:
                    for entry in self.widgets['ecu-config'][0]['startup']:
                        if not entry[2].text() or len(entry[2].text()) == 0:
                            enabled = False
                            ecu_error_list[0] = True
                            break
            if self.isRCAR and self.isElite and not self.ecu_block_list[1].disabled:
                if len(self.widgets['ecu-config'][1]['startup']) == 0:
                    enabled=False
                    ecu_error_list[1] = True
                else:
                    for entry in self.widgets['ecu-config'][1]['startup']:
                        if not entry[2].text() or len(entry[2].text()) == 0:
                            enabled = False
                            ecu_error_list[1] = True
                            break
            if self.isSOC0 and self.isElite and not self.ecu_block_list[2].disabled:
                if len(self.widgets['ecu-config'][2]['startup']) == 0:
                    enabled=False
                    ecu_error_list[2] = True
                else:
                    for entry in self.widgets['ecu-config'][2]['startup']:
                        if not entry[2].text() or len(entry[2].text()) == 0:
                            enabled = False
                            ecu_error_list[2] = True
                            break
            if self.isSOC1 and self.isElite and not self.ecu_block_list[3].disabled:
                if len(self.widgets['ecu-config'][3]['startup']) == 0:
                    enabled=False
                    ecu_error_list[3] = True
                else:
                    for entry in self.widgets['ecu-config'][3]['startup']:
                        if not entry[2].text() or len(entry[2].text()) == 0:
                            enabled = False
                            ecu_error_list[3] = True
                            break
        if self.isRCAR and self.isPadas and not self.ecu_block_list[0].disabled:
            # Check threshold entries for RCAR-PADAS
            for entry in self.widgets['ecu-config'][0]['threshold']:
                if not entry[1].text() or len(entry[1].text()) == 0 or not entry[2].text() or len(entry[2].text()) == 0:
                    enabled = False
                    ecu_error_list[0] = True
                    break
        if self.isRCAR and self.isElite and not self.ecu_block_list[1].disabled:
            # Check threshold entries for RCAR
            for entry in self.widgets['ecu-config'][1]['threshold']:
                if not entry[1].text() or len(entry[1].text()) == 0 or not entry[2].text() or len(entry[2].text()) == 0:
                    enabled = False
                    ecu_error_list[1] = True
                    break
        if self.isSOC0 and self.isElite and not self.ecu_block_list[2].disabled:
            # Check threshold entries for SoC0
            for entry in self.widgets['ecu-config'][2]['threshold']:
                if not entry[1].text() or len(entry[1].text()) == 0 or not entry[2].text() or len(entry[2].text()) == 0:
                    enabled = False
                    ecu_error_list[2] = True
                    break
        if self.isSOC1 and self.isElite and not self.ecu_block_list[3].disabled:
            # Check threshold entries for SoC1
            for entry in self.widgets['ecu-config'][3]['threshold']:
                if not entry[1].text() or len(entry[1].text()) == 0 or not entry[2].text() or len(entry[2].text()) == 0:
                    enabled = False
                    ecu_error_list[3] = True
                    break
        for i in range(4):
            self.update_ecu_block_styles(self.ecu_block_list[i], ecu_error_list[i])

        self.ok_btn.setEnabled(enabled)
        
    def update_ecu_block_styles(self, ecu_gb, has_error):
        """Update the styles of the ECU block based on error state."""
        # Define condition mappings for each ECU type
        ecu_conditions = {
            'PADAS': self.isPadas and self.isRCAR,
            'RCAR': self.isRCAR and self.isElite,
            'SoC0': self.isSOC0 and self.isElite,
            'SoC1': self.isSOC1 and self.isElite
        }
        
        # Determine if border should be red
        should_have_red_border = (
            has_error or 
            (self.is_any_ecu_selected_flag and not ecu_conditions.get(ecu_gb.title, True))
        )
        
        # Apply appropriate border style
        border_style = '1px solid red' if should_have_red_border else '0px'
        ecu_gb.setStyleSheet(f"{ecu_gb.styleSheet()}CollapsibleGroupBox{{border: {border_style};}}")

    def _notify_content_changed(self, ecu_idx):
        """Notify the corresponding ECU block that content has changed."""
        if ecu_idx < len(self.ecu_block_list):
            self.ecu_block_list[ecu_idx].content_changed()
           
    def add_startup_row(self, idx):
        # self.ok_btn.setDisabled(False)
        entry = self.widgets['ecu-config'][idx]
        row, dd, apps, rem = self._create_startup_row('', '', idx)
        entry['startup_layout'].addRow(row)
        entry['startup'].append((row, dd, apps, rem))
        if len(entry['startup']) == 1:
            rem.setDisabled(True)
        else:
            for e in entry['startup']:
                e[3].setDisabled(False)
        self._notify_content_changed(idx)

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
        if len(entry['startup']) == 1:
            # If only one row left, disable the remove button
            entry['startup'][0][3].setDisabled(True)

    def add_threshold_row(self, idx):
        entry = self.widgets['ecu-config'][idx]
        row, apps, thresh = self._create_threshold_row('', '', idx)
        entry['threshold_layout'].addRow(row)
        entry['threshold'].append((row, apps, thresh))
        self._notify_content_changed(idx)

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

    def open_logs_folder(self):
        """Open the Pre-Generated Logs folder in File Explorer"""
        
        # Use the instance variable logs_path
        logs_path = self.logs_path

        # Check if the directory exists
        if not logs_path.exists():
            # Create the directory if it doesn't exist
            try:
                logs_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(f"Error creating logs directory: {e}")
                return
        
        # Open the folder in the default file manager
        try:
            if platform.system() == "Windows":
                os.startfile(logs_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", logs_path])
            else:  # Linux and other Unix-like systems
                subprocess.run(["xdg-open", logs_path])
        except Exception as e:
            print(f"Error opening logs folder: {e}")
            
        # Update tooltip after opening (in case folder structure changed)
        self.update_logs_tooltip()

    def open_application_input_list(self):
        """Open the ApplicationInputList.xlsx file"""
        app_input_path = self.app_input_file_path
        
        # Check if the file exists
        if not app_input_path.exists():
            print(f"ApplicationInputList.xlsx not found at: {app_input_path}")
            return
        
        # Open the Excel file with the default application
        try:
            if platform.system() == "Windows":
                os.startfile(app_input_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", app_input_path])
            else:  # Linux and other Unix-like systems
                subprocess.run(["xdg-open", app_input_path])
        except Exception as e:
            print(f"Error opening ApplicationInputList.xlsx: {e}")
    
    def check_app_input_file(self):
        """Check if ApplicationInputList.xlsx exists"""
        return self.app_input_file_path.exists()
    
    def update_app_input_button(self):
        """Update the Application Input List button appearance based on file presence"""
        if not hasattr(self, 'app_input_btn'):
            return
            
        file_exists = self.check_app_input_file()
        
        # Create tooltip text
        if file_exists:
            tooltip_lines = ["ApplicationInputList.xlsx found - Click to open", ""]
            
            # Add application counts if available
            if hasattr(self, 'application_list') and self.application_list:
                tooltip_lines.append("Loaded Applications:")
                for ecu_family, ecu_types in self.application_list.items():
                    for ecu_type, apps in ecu_types.items():
                        if apps:
                            tooltip_lines.append(f"  {ecu_family}({ecu_type}): {len(apps)} apps")
            else:
                tooltip_lines.append("No applications loaded yet")
            
            tooltip_text = "\n".join(tooltip_lines)
            border_color = 'green'
        else:
            tooltip_text = "ApplicationInputList.xlsx not found in current directory"
            border_color = 'red'
        
        self.app_input_btn.setToolTip(tooltip_text)
        
        # Update button style with border color
        self.app_input_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: white;
                color: black;
                border: 1px solid {border_color};
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: #f0f0f0;
            }}
        """)

    def parse_application_input_list(self):
        """Parse the ApplicationInputList.xlsx file and extract applications by ECU type"""
        if not self.check_app_input_file():
            print("ApplicationInputList.xlsx not found, cannot parse applications")
            return None
        
        try:
            # Load the Excel workbook
            workbook = openpyxl.load_workbook(self.app_input_file_path)
            worksheet = workbook.active
            
            # Initialize the applications dictionary
            applications = {
                'ELITE': {
                    'RCAR': [],
                    'SoC0': [],
                    'SoC1': []
                },
                'PADAS': {
                    'RCAR': []
                }
            }
            
            # Column mapping according to the Excel structure
            # Column B = ELITE RCAR, Column C = ELITE SoC0, Column D = ELITE SoC1, Column E = PADAS RCAR
            column_mapping = {
                'B': ('ELITE', 'RCAR'),
                'C': ('ELITE', 'SoC0'), 
                'D': ('ELITE', 'SoC1'),
                'E': ('PADAS', 'RCAR')
            }
            
            # Start reading from row 3 (row 1 has title, row 2 has column headers)
            # We'll read up to row 100 or until we find 10 consecutive empty rows
            max_row = min(worksheet.max_row, 100)
            empty_row_count = 0
            
            for row_num in range(3, max_row + 1):
                row_has_data = False
                
                for col_letter, (ecu_family, ecu_type) in column_mapping.items():
                    cell_value = worksheet[f'{col_letter}{row_num}'].value
                    
                    if cell_value and str(cell_value).strip():
                        app_name = str(cell_value).strip()
                        
                        # Skip header-like values
                        if app_name.upper() not in ['ELITE', 'PADAS', 'RCAR', 'SOC0', 'SOC1', 'NO.']:
                            applications[ecu_family.upper()][ecu_type.upper()].append(app_name)
                            row_has_data = True
                
                if row_has_data:
                    empty_row_count = 0
                else:
                    empty_row_count += 1
                    
                # Stop if we encounter 10 consecutive empty rows
                if empty_row_count >= 10:
                    break
            
            workbook.close()
            
            # Store the parsed applications for later use
            self.application_list = applications
            
            # Print parsed data for debugging
            print("Parsed Application Input List:")
            for ecu_family, ecu_types in applications.items():
                for ecu_type, apps in ecu_types.items():
                    if apps:
                        print(f"  {ecu_family} {ecu_type}: {apps}")
            
            return applications
            
        except Exception as e:
            print(f"Error parsing ApplicationInputList.xlsx: {e}")
            return None
    
    def get_applications_for_ecu(self, ecu_family, ecu_type):
        """Get the list of applications for a specific ECU type"""
        ecu_family = ecu_family.upper()
        ecu_type = ecu_type.upper()
        if not hasattr(self, 'application_list') or not self.application_list:
            self.parse_application_input_list()
        
        if self.application_list and ecu_family in self.application_list:
            return self.application_list[ecu_family].get(ecu_type, [])
        return []
    
    def refresh_application_list(self):
        """Refresh the application list by re-parsing the Excel file"""
        print("Refreshing Application Input List...")
        self.parse_application_input_list()

    def save_config(self):
        data = {}
        for key in ['DLT-Viewer Log Capture Time', 'Iterations', 'Power ON-OFF Delay']:
            w = self.widgets[key][0]
            # print(w.text())
            if w.text() and len(w.text())>0:
                data[key] = int(w.text())
        data['Startup Order Judgement'] = self.widgets['Startup Order Judgement'].isChecked()
        data['Application Registration'] = self.widgets['Application Registration'].isChecked()
        data['Order Mismatch Judgement'] = self.widgets['Order Mismatch Judgement'].isChecked()
        data['Not Found Judgement'] = self.widgets['Not Found Judgement'].isChecked()
        data['Not Configured Judgement'] = self.widgets['Not Configured Judgement'].isChecked()
        data['Pre-Generated Logs'] = self.widgets['Pre-Generated Logs'].isChecked()
        data['windows'] = {
            'Is Environment Path Set': self.widgets['windows.Is Environment Path Set'].isChecked(),
            'DLT-Viewer Installed Path': self.widgets['windows.DLT-Viewer Installed Path'].text()
        }
        ec = []
        for idx, item in enumerate(self.widgets['ecu-config']):
            title = self.ecu_block_list[idx].title
            ec_item = {'ecu-type': title, 'startup-order': [], 'threshold-config': []}
            if self.ecu_block_list[idx].disabled or ((title == 'PADAS' and not (self.isRCAR and self.isPadas)) or 
               (title == 'RCAR' and not (self.isRCAR and self.isElite)) or 
               (title == 'SoC0' and not (self.isSOC0 and self.isElite)) or 
               (title == 'SoC1' and not (self.isSOC1 and self.isElite))):
                continue
            for entry in item['startup']:
                # entry is (row, dd, apps, count_lbl, rem)
                _, dd, apps, _ = entry
                ec_item['startup-order'].append({'Order Type': dd.currentText(), 'Applications': apps.text()})
            for entry in item['threshold']:
                # entry is (row, apps, thresh)
                _, apps, thresh = entry
                if thresh.text():  # Only save if threshold value is provided
                    ec_item['threshold-config'].append({'Applications': apps.text(), 'Threshold': int(thresh.text())})
            ec.append(ec_item)
        data['ecu-config'] = ec
        data['ECU_setting'] = self.ecu_selection
        try:
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=4)

            self.accept()
        except Exception as e:
            print(f'Failed to save config: {e}')