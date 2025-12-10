from collapsible_groupbox import CollapsibleGroupBox
import os
import subprocess
import platform
from pathlib import Path
from PyQt5.QtCore import QFileSystemWatcher
from imports_utils import *

common_groupbox_style = """
    QGroupBox {
        background-color: #F5F5F5;
        border: 1px solid #999999;
        border-radius: 5px;
        margin-top: 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top center;
        padding-left: 0px;
        padding-top: 0px;
    }
"""



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


class CustomDecimalValidator(QDoubleValidator):
    def __init__(self, min_value=0.0, max_value=float('inf'), decimals=2, parent=None):
        super().__init__(min_value, max_value, decimals, parent)
        self.min_value = min_value
        self.max_value = max_value
        self.decimals = decimals
        self.setNotation(QDoubleValidator.StandardNotation)

    def validate(self, input_str, pos):
        if input_str == "":
            return (QDoubleValidator.Intermediate, input_str, pos)

        # Allow incomplete input like "0.", "1.", etc.
        if input_str.endswith('.'):
            # Check if the integer part is valid
            try:
                int_part = input_str[:-1]
                if int_part == "" or int_part == "0":
                    return (QDoubleValidator.Intermediate, input_str, pos)
                value = float(int_part)
                if value >= self.min_value:
                    return (QDoubleValidator.Intermediate, input_str, pos)
            except ValueError:
                return (QDoubleValidator.Invalid, input_str, pos)

        # Check if it's a valid decimal number
        try:
            value = float(input_str)
            
            # Check if value is within range
            if value < self.min_value:
                return (QDoubleValidator.Invalid, input_str, pos)
            
            # Check decimal places
            if '.' in input_str:
                decimal_part = input_str.split('.')[1]
                if len(decimal_part) > self.decimals:
                    return (QDoubleValidator.Invalid, input_str, pos)
            
            # Reject leading zeros for numbers >= 1 (e.g., "01.5" is invalid, but "0.5" is valid)
            if input_str.startswith('0') and len(input_str) > 1 and not input_str.startswith('0.'):
                return (QDoubleValidator.Invalid, input_str, pos)
            
            return (QDoubleValidator.Acceptable, input_str, pos)
            
        except ValueError:
            return (QDoubleValidator.Invalid, input_str, pos)


class ApplicationSelectorWidget(QWidget):
    """Custom widget for selecting applications with dropdown checkboxes and editable text field"""
   
    def __init__(self, parent=None, ecu_family=None, ecu_type=None, ecu_idx=None, placeholder_text="App1, App2"):
        super().__init__(parent)
        self.parent_dialog = parent
        self.ecu_family = ecu_family.upper() if ecu_family else None
        self.ecu_type = ecu_type.upper() if ecu_type else None
        self.ecu_idx = ecu_idx
        self.application_checkboxes = {}
        self.select_all_checkbox = None
        self.updating_from_text = False
        self.updating_from_checkboxes = False
       
        self.setup_ui(placeholder_text)
        self.load_applications()
       
    def setup_ui(self, placeholder_text):
        """Setup the UI components"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)  # Remove spacing between text field and button
       
        # Text field for editing applications
        self.text_field = QLineEdit()
        self.text_field.setPlaceholderText(placeholder_text)
        self.text_field.textChanged.connect(self.on_text_changed)
        self.text_field.editingFinished.connect(self.on_editing_finished)
       
        # Track if there are duplicates
        self.has_duplicates = False
       
        # Dropdown button
        self.dropdown_btn = QPushButton("▼")
        self.dropdown_btn.setFocusPolicy(Qt.NoFocus)
        self.dropdown_btn.setFixedSize(25, 24)
        self.dropdown_btn.clicked.connect(self.toggle_dropdown)
        self.dropdown_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #cccccc;
                border-left: none;
                background-color: #f0f0f0;
                border-radius: 0px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
       
        # Dropdown menu (initially hidden)
        self.dropdown_menu = QWidget()
        self.dropdown_menu.setWindowFlags(Qt.Popup)
        self.dropdown_menu.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 3px;
            }
            QCheckBox {
                padding: 6px 8px;
                margin: 0px;
                border: none;
                background-color: transparent;
            }
            QCheckBox:hover {
                background-color: #e6f3ff;
            }
            QCheckBox:disabled {
                color: #999999;
                background-color: #f5f5f5;
            }
            QScrollArea {
                border: none;
                background-color: white;
            }
            QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 12px;
                border-radius: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #c0c0c0;
                min-height: 20px;
                border-radius: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #a0a0a0;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
                width: 0px;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
       
        dropdown_layout = QVBoxLayout(self.dropdown_menu)
        dropdown_layout.setContentsMargins(0, 0, 0, 0)
        dropdown_layout.setSpacing(0)
       
        # Scroll area for applications
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMaximumHeight(200)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
       
        self.apps_widget = QWidget()
        self.apps_layout = QVBoxLayout(self.apps_widget)
        self.apps_layout.setContentsMargins(0, 0, 0, 0)
        self.apps_layout.setSpacing(0)
       
        self.scroll_area.setWidget(self.apps_widget)
        dropdown_layout.addWidget(self.scroll_area)
       
        layout.addWidget(self.text_field)
        layout.addWidget(self.dropdown_btn)
       
    def load_applications(self):
        """Load applications from the parent dialog's application list"""
        self.clear_checkboxes()
       
        if not self.parent_dialog or not hasattr(self.parent_dialog, 'application_list'):
            return
           
        if not self.parent_dialog.application_list:
            return
           
        # Get applications for this ECU type
        apps = []
        if self.ecu_family and self.ecu_type:
            apps = self.parent_dialog.application_list.get(self.ecu_family, {}).get(self.ecu_type, [])
       
        if not apps:
            return
           
        # Add "Select All" checkbox
        self.select_all_checkbox = QCheckBox("Select All")
        # Use clicked signal to avoid recursive calls and ensure it's always responsive
        self.select_all_checkbox.clicked.connect(self.on_select_all_clicked)
        self.select_all_checkbox.setStyleSheet("font-weight: bold; padding: 8px;")
        self.apps_layout.addWidget(self.select_all_checkbox)
       
        # Add separator
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #cccccc; margin: 2px 0px;")
        self.apps_layout.addWidget(separator)
       
        # Add application checkboxes
        for app in apps:
            checkbox = QCheckBox(app)
            # Use clicked signal instead of stateChanged to avoid recursive calls
            checkbox.clicked.connect(self.on_application_checkbox_changed)
            self.application_checkboxes[app] = checkbox
            self.apps_layout.addWidget(checkbox)
           
        # Pre-render disabled states (but defer if parent widgets aren't ready)
        try:
            self.update_disabled_states()
        except (IndexError, AttributeError):
            # If parent widget structure isn't ready yet, skip for now
            # This will be called again later when needed
            pass
       
        # Update dropdown size to match text field width
        self.update_dropdown_size()
       
    def clear_checkboxes(self):
        """Clear all checkboxes from the dropdown"""
        # Remove all widgets from layout
        while self.apps_layout.count():
            child = self.apps_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
               
        self.application_checkboxes.clear()
        self.select_all_checkbox = None
       
    def update_dropdown_size(self):
        """Update dropdown size to match text field width"""
        if hasattr(self, 'dropdown_menu') and hasattr(self, 'text_field'):
            # Get the combined width of text field and button
            total_width = self.text_field.width() + self.dropdown_btn.width()
            self.dropdown_menu.setFixedWidth(total_width)
           
    def update_disabled_states(self):
        """Update disabled states for all checkboxes based on cross-group selections within same group type"""
        if not self.parent_dialog or self.ecu_idx is None or self.updating_from_checkboxes:
            return
           
        # Safety check - ensure parent widget structure is ready
        if not hasattr(self.parent_dialog, 'widgets') or 'ecu-config' not in self.parent_dialog.widgets:
            return
           
        # Skip during checkbox updates to avoid interference
        if hasattr(self, 'updating_from_text') and self.updating_from_text:
            return
           
        # Determine if this widget is in startup or threshold group
        is_startup_widget = self.is_startup_widget()
       
        # Get all selected applications from same group type for this ECU
        selected_apps_in_group = set()
        if hasattr(self.parent_dialog, 'widgets') and 'ecu-config' in self.parent_dialog.widgets:
            # Add bounds checking to prevent IndexError
            ecu_configs = self.parent_dialog.widgets['ecu-config']
            if self.ecu_idx >= len(ecu_configs):
                return  # Exit early if index is out of range
               
            ecu_config = ecu_configs[self.ecu_idx]
           
            # Collect widgets of the same type (startup or threshold)
            same_type_widgets = []
            if is_startup_widget:
                for entry in ecu_config['startup']:
                    if len(entry) >= 3 and hasattr(entry[2], 'application_checkboxes') and entry[4].isChecked():
                        same_type_widgets.append(entry[2])
            else:
                for entry in ecu_config['threshold']:
                    if len(entry) >= 2 and hasattr(entry[1], 'application_checkboxes') and entry[3].isChecked():
                        same_type_widgets.append(entry[1])
           
            # Collect all currently selected applications from same group type
            for widget in same_type_widgets:
                if widget != self:  # Don't include this widget's selections yet
                    for app, checkbox in widget.application_checkboxes.items():
                        if checkbox.isChecked():
                            selected_apps_in_group.add(app)
           
            # Update only this widget's checkboxes based on other widgets' selections
            for app, checkbox in self.application_checkboxes.items():
                # Enable checkbox if app is not selected in other widgets of same type
                is_selected_elsewhere = app in selected_apps_in_group
                checkbox.setEnabled(not is_selected_elsewhere or checkbox.isChecked())
                   
        # Update Select All checkbox state
        self.update_select_all_state()
       
    def is_startup_widget(self):
        """Determine if this widget is in a startup group by checking parent hierarchy"""
        if not self.parent_dialog or self.ecu_idx is None:
            return True  # Default to startup
           
        if hasattr(self.parent_dialog, 'widgets') and 'ecu-config' in self.parent_dialog.widgets:
            # Add bounds checking to prevent IndexError
            ecu_configs = self.parent_dialog.widgets['ecu-config']
            if self.ecu_idx >= len(ecu_configs):
                return True  # Default to startup if index is out of range
               
            ecu_config = ecu_configs[self.ecu_idx]
           
            # Check if this widget is in startup entries
            for entry in ecu_config['startup']:
                if len(entry) >= 3 and entry[2] is self:
                    return True
                   
            # Check if this widget is in threshold entries  
            for entry in ecu_config['threshold']:
                if len(entry) >= 2 and entry[1] is self:
                    return False
                   
        return True  # Default to startup if not found
       
    def update_select_all_state(self):
        """Update the Select All checkbox state based on enabled applications"""
        if not self.select_all_checkbox or self.updating_from_checkboxes:
            return
           
        self.update_select_all_visual_state()
       
    def update_select_all_visual_state(self):
        """Update the visual state of Select All checkbox without triggering events"""
        if not self.select_all_checkbox:
            return
           
        # Temporarily disconnect signal to avoid recursive calls
        self.select_all_checkbox.clicked.disconnect()
       
        enabled_checkboxes = [cb for cb in self.application_checkboxes.values() if cb.isEnabled()]
       
        # Always keep Select All enabled so users can interact with it
        self.select_all_checkbox.setEnabled(True)
       
        if not enabled_checkboxes:
            # If no enabled checkboxes, set to unchecked but keep clickable
            self.select_all_checkbox.setCheckState(Qt.Unchecked)
        else:
            checked_enabled = [cb for cb in enabled_checkboxes if cb.isChecked()]
           
            if len(checked_enabled) == 0:
                self.select_all_checkbox.setCheckState(Qt.Unchecked)
            elif len(checked_enabled) == len(enabled_checkboxes):
                self.select_all_checkbox.setCheckState(Qt.Checked)
            else:
                self.select_all_checkbox.setCheckState(Qt.PartiallyChecked)
       
        # Reconnect the signal
        self.select_all_checkbox.clicked.connect(self.on_select_all_clicked)
       
    def merge_checkbox_and_manual_apps(self):
        """Merge checkbox selections with manually entered applications, preserving order of entry"""
        # Get current text and parse all applications
        current_text = self.text_field.text()
        all_current_apps = [app.strip() for app in current_text.split(',') if app.strip()]
       
        # Get applications from checkboxes that are checked
        checked_apps = {app for app, checkbox in self.application_checkboxes.items()
                       if checkbox.isChecked()}
       
        # Build final list preserving the order from text field
        final_apps = []
        seen = set()
       
        # First, add all apps from current text that are still valid (either checked or manual)
        for app in all_current_apps:
            if app not in seen:
                # Keep if it's either checked or a manual entry (not in dropdown)
                if app in checked_apps or app not in self.application_checkboxes:
                    final_apps.append(app)
                    seen.add(app)
       
        # Then add any newly checked apps that weren't in the text field yet
        for app in checked_apps:
            if app not in seen:
                final_apps.append(app)
                seen.add(app)
       
        return final_apps
   
    def check_for_duplicates(self):
        """Check if there are duplicate applications in the text field"""
        text = self.text_field.text()
        apps = [app.strip() for app in text.split(',') if app.strip()]
       
        # Check for duplicates
        seen = set()
        has_duplicates = False
        for app in apps:
            if app in seen:
                has_duplicates = True
                break
            seen.add(app)
       
        return has_duplicates
   
    def remove_duplicates_from_text(self):
        """Remove duplicate applications, keeping only the first occurrence"""
        text = self.text_field.text()
        apps = [app.strip() for app in text.split(',') if app.strip()]
       
        # Remove duplicates while preserving order
        unique_apps = []
        seen = set()
        for app in apps:
            if app not in seen:
                unique_apps.append(app)
                seen.add(app)
       
        return unique_apps
           
    def update_all_cross_group_disabling(self):
        """Update cross-group disabling for all widgets in the same ECU and same group type"""
        if self.parent_dialog and hasattr(self.parent_dialog, 'widgets') and 'ecu-config' in self.parent_dialog.widgets:
            # Add bounds checking to prevent IndexError
            ecu_configs = self.parent_dialog.widgets['ecu-config']
            if self.ecu_idx >= len(ecu_configs):
                return  # Exit early if index is out of range
               
            ecu_config = ecu_configs[self.ecu_idx]
           
            # Determine if this is a startup or threshold widget
            is_startup = self.is_startup_widget()
           
            # Update only widgets of the same type
            if is_startup:
                # Update all startup widgets for this ECU
                for entry in ecu_config['startup']:
                    if len(entry) >= 3 and hasattr(entry[2], 'update_disabled_states'):
                        entry[2].update_disabled_states()
            else:
                # Update all threshold widgets for this ECU
                for entry in ecu_config['threshold']:
                    if len(entry) >= 2 and hasattr(entry[1], 'update_disabled_states'):
                        entry[1].update_disabled_states()
       
    def toggle_dropdown(self):
        """Toggle the dropdown visibility"""
        if self.dropdown_menu.isVisible():
            self.dropdown_menu.hide()
        else:
            # Update dropdown size and disabled states before showing
            self.update_dropdown_size()
            self.update_disabled_states()
           
            # Position dropdown below the widget with some spacing
            pos = self.mapToGlobal(self.text_field.geometry().bottomLeft())
            pos.setY(pos.y() + 5)  # Add 5 pixels spacing below the button
            self.dropdown_menu.move(pos)
            self.dropdown_menu.show()
            self.dropdown_menu.raise_()
           
    def on_text_changed(self):
        """Handle text field changes"""
        if self.updating_from_checkboxes:
            return
           
        self.updating_from_text = True
       
        # Parse applications from text
        text = self.text_field.text()
        selected_apps = [app.strip() for app in text.split(',') if app.strip()]
       
        # Check for duplicates and update border
        self.has_duplicates = self.check_for_duplicates()
       
        # Temporarily disconnect checkbox signals to avoid recursive calls
        for app, checkbox in self.application_checkboxes.items():
            checkbox.clicked.disconnect()
            checkbox.setChecked(app in selected_apps)
            checkbox.clicked.connect(self.on_application_checkbox_changed)
       
        # Update Select All state
        self.update_select_all_visual_state()
               
        # Update cross-group disabling for all widgets (after a small delay)
        if hasattr(self.parent_dialog, 'update_all_disabled_states_delayed'):
            self.parent_dialog.update_all_disabled_states_delayed()
       
        self.updating_from_text = False
   
    def on_editing_finished(self):
        """Handle when user finishes editing the text field (loses focus or presses Enter)"""
        if self.has_duplicates:
            # Remove duplicates keeping first occurrence
            unique_apps = self.remove_duplicates_from_text()
           
            # Update the text field with deduplicated list
            self.updating_from_checkboxes = True
            self.text_field.setText(', '.join(unique_apps))
            self.updating_from_checkboxes = False
           
            # Update checkboxes to match the deduplicated list
            self.updating_from_text = True
            for app, checkbox in self.application_checkboxes.items():
                checkbox.clicked.disconnect()
                checkbox.setChecked(app in unique_apps)
                checkbox.clicked.connect(self.on_application_checkbox_changed)
            self.updating_from_text = False
           
            # Clear duplicate flag and border
            self.has_duplicates = False
           
            # Update Select All state
            self.update_select_all_visual_state()
           
            # Trigger validation update on parent dialog
            if hasattr(self.parent_dialog, 'validate_all_fields'):
                self.parent_dialog.validate_all_fields()
       
    def on_application_checkbox_changed(self):
        """Handle individual application checkbox changes"""
        if self.updating_from_text:
            return
           
        self.updating_from_checkboxes = True
       
        # Merge checkbox selections with manually entered applications
        final_apps = self.merge_checkbox_and_manual_apps()
       
        # Update text field with combined applications
        self.text_field.setText(', '.join(final_apps))
       
        # Update Select All visual state
        self.update_select_all_visual_state()
               
        # Trigger validation update on parent dialog
        if hasattr(self.parent_dialog, 'validate_all_fields'):
            self.parent_dialog.validate_all_fields()
       
        self.updating_from_checkboxes = False
       
        # Update cross-group disabling after the current operation is complete
        if hasattr(self.parent_dialog, 'update_all_disabled_states_delayed'):
            self.parent_dialog.update_all_disabled_states_delayed()
       
    def on_select_all_clicked(self):
        """Handle select all checkbox clicks - only affects this dropdown's applications"""
        if self.updating_from_text or not self.select_all_checkbox:
            return
           
        self.updating_from_checkboxes = True
       
        # Get all enabled checkboxes
        enabled_checkboxes = [(app, cb) for app, cb in self.application_checkboxes.items() if cb.isEnabled()]
       
        if not enabled_checkboxes:
            self.updating_from_checkboxes = False
            return
       
        # Count currently selected enabled applications
        selected_enabled = [cb for app, cb in enabled_checkboxes if cb.isChecked()]
       
        # Determine action based on current selection state:
        # - If all enabled apps are selected -> uncheck all
        # - If no apps or some apps are selected -> check all enabled apps
        if len(selected_enabled) == len(enabled_checkboxes):
            # All enabled apps are selected, so uncheck all
            check_all = False
        else:
            # No apps or some apps selected, so check all enabled apps
            check_all = True
       
        # Update only the enabled checkboxes in this dropdown
        for app, checkbox in enabled_checkboxes:
            checkbox.setChecked(check_all)
       
        # Merge checkbox selections with manually entered applications
        final_apps = self.merge_checkbox_and_manual_apps()
       
        # Update text field with combined applications
        self.text_field.setText(', '.join(final_apps))
       
        # Update Select All visual state
        self.update_select_all_visual_state()
           
        # Update cross-group disabling for all widgets in same group type
        self.update_all_cross_group_disabling()
       
        # Trigger validation update on parent dialog
        if hasattr(self.parent_dialog, 'validate_all_fields'):
            self.parent_dialog.validate_all_fields()
       
        self.updating_from_checkboxes = False
       

                               
    def get_text(self):
        """Get the current text value"""
        return self.text_field.text()
       
    def set_text(self, text):
        """Set the text value"""
        self.text_field.setText(text)
        self.on_text_changed()  # Trigger update
       
    def refresh_applications(self):
        """Refresh the application list from the parent dialog"""
        current_text = self.text_field.text()
        self.load_applications()
        self.set_text(current_text)  # Restore current selections


class StartupTimeConfig(QDialog):
    DEFAULT_CONFIG = {
        # 'DLT-Viewer Log Capture Time': 0,
        # 'Iterations': 0,
        # 'Threshold': 0,
        'Startup Order Application Registration': False,
        'Startup Order Judgement': False,
        'Missing Judgement': False,
        'Unexpected Judgement': False,
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
        self.ecu_error_list = []
        self.startup_group_list = []
       
        self.isElite, self.isPadas = True, True
        self.isRCAR, self.isSOC0, self.isSOC1 = True, True, True

        # Flag indicating whether any ECU is selected in the main window
        self.is_any_ecu_selected_flag = main_window.is_any_ecu_selected_flag
       
        self.is_checked = is_checked      
        # Check which ECU type is enabled (only one can be selected at a time)
        self.ecu_selection = {
            'Elite': {'RCAR': False, 'SoC0': False, 'SoC1': False},
            'PADAS': {'RCAR': False}
        }
        self.ecu_block_list_selection_map = {
            0: False,
            1: False,
            2: False,
            3: False
        }

        self.ecu_map = {
            "PADAS": "PADAS_RCAR",
            "RCAR": "ELITE_RCAR",
            "SoC0": "ELITE_SoC0",
            "SoC1": "ELITE_SoC1",
            "PADAS_RCAR": "PADAS",
            "ELITE_RCAR": "RCAR",
            "ELITE_SoC0": "SoC0",
            "ELITE_SoC1": "SoC1"
        }
       
        # self.ecu_selection = main_window.ecu_selection_status
        if self.is_any_ecu_selected_flag and self.is_checked:
            self.ecu_selection = main_window.ecu_selection_status
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
           
            self.ecu_block_list_selection_map = {
                0: self.isPadas and self.isRCAR,
                1: self.isElite and self.isRCAR,
                2: self.isElite and self.isSOC0,
                3: self.isElite and self.isSOC1
            }

        # Initialize file system watcher for logs folder
        self.logs_path = Path(__file__).parent.joinpath('Startup_Time_Scripts/Pre-Generated_Logs')
        self.setup_file_watcher()

        # Initialize application list from Excel file
        self.application_list = None
        self.parse_application_input_list()

        # Track the Excel file path for cleanup
        self.excel_file_path = None
        self.pdf_process = None

        self.init_ui()
   
    def set_window_properties(self):
        # Enable minimize/maximize buttons and the context-help '?' hint
        flags = (self.windowFlags()
                #  | Qt.WindowMinimizeButtonHint
                 | Qt.WindowMaximizeButtonHint            
                 | Qt.Window)
       
        self.setWindowFlags(flags)
        self.setWindowTitle('Startup Time Configuration')
        self.setWindowIcon(QIcon('./GUI_Icons/KPIT_logo.ico'))

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
        self.setMinimumSize(window_width, window_height)

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
       
        # Add the current directory to watch for Application_Input_List_for_Startup_Time.xlsx
        current_dir = Path(__file__).parent
        self.app_input_file_path = current_dir / 'Application_Input_List_for_Startup_Time.xlsx'
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

    def handle_help_click(self):
        """
        Slot for help button click.
        Opens the user manual and updates pdf_process reference.
        """
        self.pdf_process = open_user_manual("Startup Time", self.pdf_process)

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
        general_group.setStyleSheet(common_groupbox_style + "QGroupBox { font-weight: 500; font-size: 9pt; }")
        general_group.setFixedHeight(300)
        
        # Base vertical layout for general settings group box
        general_base_layout = QVBoxLayout()
        
        # First horizontal layout containing two vertical layouts
        general_horizontal_layout = QHBoxLayout()
        
        # Left vertical layout for existing fields
        left_vlayout = QVBoxLayout()
        left_vlayout.setSpacing(18)  # Set spacing between widgets in the layout
        left_form_layout = QFormLayout()
        
        for key, validator in [
            ('DLT-Viewer Log Capture Time', CustomIntValidator(1)),
            ('Iterations', CustomIntValidator(1)),
            ('Power ON-OFF Delay', CustomIntValidator(1))
        ]:
            widgets_lst = list()
            le = QLineEdit(str(self.config_data.get(key, '')))
            le.textChanged.connect(lambda text: [self.validate_all_fields()])
            le.setValidator(validator)
            le.setFixedWidth(150)
            widgets_lst.append(le)
            row_layout = QHBoxLayout()
            row_layout.addWidget(le)
            units_text = ''
            if key == 'DLT-Viewer Log Capture Time':
                units_text = '[Int: 1~ (sec)]'
            elif key == 'Iterations':
                units_text = '[Int: 1~]'
            elif key == 'Power ON-OFF Delay':
                units_text = '[Int: 1~ (sec)]'
            units_lbl = QLabel(units_text)
            row_layout.addWidget(units_lbl)
            widgets_lst.append(units_lbl)
            key_lbl = QLabel(key)
            widgets_lst.append(key_lbl)
            left_form_layout.addRow(key_lbl, row_layout)
            self.widgets[key] = widgets_lst
       
        # Application Input List row
        app_input_layout = QHBoxLayout()
        self.app_input_btn = QPushButton()
        self.app_input_btn.setFocusPolicy(Qt.NoFocus)
        self.app_input_btn.setFixedSize(30, 24)  # Make it square and slightly larger for the icon
        # self.app_input_btn.setText("📋")  # Use clipboard/Excel emoji as icon
        self.app_input_btn.setIcon(QIcon("./GUI_Icons/Excel_icon.ico"))
        self.app_input_btn.clicked.connect(self.open_application_input_list)
        app_input_layout.addWidget(self.app_input_btn)
        app_input_layout.addStretch()  # Push everything to the left
        left_form_layout.addRow(QLabel('Application Input List'), app_input_layout)
        
        left_vlayout.addLayout(left_form_layout)
        left_vlayout.addStretch()
        
        # Right vertical layout for IG-ON to QNX startup times
        right_vlayout = QVBoxLayout()
        
        # Create "IG-ON to QNX startup times" group box
        igon_qnx_group = QGroupBox('IG-ON to QNX startup times')
        igon_qnx_group.setStyleSheet(common_groupbox_style + "QGroupBox { font-weight: 500; font-size: 8pt; }")
        igon_qnx_group.setMinimumHeight(160)  # Set minimum height for the group box
        igon_qnx_layout = QVBoxLayout()
        igon_qnx_form_layout = QFormLayout()
        
        # Add 4 rows for each ECU type
        for ecu_name in ['PADAS_RCAR', 'ELITE_RCAR', 'ELITE_SoC0', 'ELITE_SoC1']:
            widgets_lst = list()
            le = QLineEdit(str(self.config_data.get(f'IG-ON to QNX startup time {ecu_name}', '')))
            le.textChanged.connect(lambda text, name=ecu_name: [self.validate_all_fields(), self.update_border(f'IG-ON to QNX startup time {name}')])
            le.setValidator(CustomDecimalValidator())
            le.setFixedWidth(150)
            widgets_lst.append(le)
            
            row_layout = QHBoxLayout()
            row_layout.addWidget(le)
            units_lbl = QLabel('[Int: 0~ (sec)]')
            row_layout.addWidget(units_lbl)
            widgets_lst.append(units_lbl)
            
            ecu_lbl = QLabel(ecu_name)
            widgets_lst.append(ecu_lbl)
            igon_qnx_form_layout.addRow(ecu_lbl, row_layout)
            self.widgets[f'IG-ON to QNX startup time {ecu_name}'] = widgets_lst
        
        igon_qnx_layout.addLayout(igon_qnx_form_layout)
        igon_qnx_group.setLayout(igon_qnx_layout)
        right_vlayout.addWidget(igon_qnx_group)
        right_vlayout.addStretch()
        
        # Add both vertical layouts to the horizontal layout with spacing
        general_horizontal_layout.addLayout(left_vlayout)
        general_horizontal_layout.addSpacing(20)  # Add 20px spacing between left and right sections
        general_horizontal_layout.addLayout(right_vlayout)
        
        # Add the horizontal layout to the base vertical layout
        general_base_layout.addLayout(general_horizontal_layout)
        
        # Set the base vertical layout to the general group
        general_group.setLayout(general_base_layout)
       
        # Create group box with checkbox as title
        startup_order_group = QGroupBox()
        startup_order_group.setCheckable(True)
        startup_order_group.setChecked(self.config_data.get('Startup Order Application Registration', False))
        startup_order_group.setTitle('Startup Order Application Registration')
        self.widgets['Startup Order Application Registration'] = startup_order_group
       
        # Create horizontal layout for the three judgement checkboxes
        judgement_hlayout = QHBoxLayout()
        judgement_hlayout.setContentsMargins(10, 10, 10, 10)
       
        # Order Mismatch Judgement
        order_mismatch_label = QLabel('Startup Order Judgement')  
        order_mismatch_cb = QCheckBox()
        order_mismatch_cb.setChecked(self.config_data.get('Startup Order Judgement', False))
        self.widgets['Startup Order Judgement'] = order_mismatch_cb
       
        # Not Found Judgement
        not_found_label = QLabel('Missing Judgement')
        not_found_cb = QCheckBox()
        not_found_cb.setChecked(self.config_data.get('Missing Judgement', False))
        self.widgets['Missing Judgement'] = not_found_cb
       
        # Not Configured Judgement
        not_configured_label = QLabel('Unexpected Judgement')
        not_configured_cb = QCheckBox()
        not_configured_cb.setChecked(self.config_data.get('Unexpected Judgement', False))
        self.widgets['Unexpected Judgement'] = not_configured_cb
       
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
       
        # Set the layout to the group box
        startup_order_group.setLayout(judgement_hlayout)
       
        # Override the inherited style to use default appearance
        startup_order_group.setStyleSheet("""
            QGroupBox {
                padding: 5px;
                margin-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                margin-top: 5px;
                left: 15px;
                padding: 0 5px;
            }
        """)
       
        # Add the startup order group box to the general base layout
        general_base_layout.addWidget(startup_order_group)
       
        self.pre_gen_logs_cb = QCheckBox(); self.pre_gen_logs_cb.setChecked(self.config_data.get('Pre-Generated Logs', False))
       
        # Create horizontal layout for Pre-Generated Logs with button
        pre_gen_layout = QHBoxLayout()
        pre_gen_layout.setSpacing(10)
        pre_gen_layout.addWidget(self.pre_gen_logs_cb)
       
        # Add button to open File Explorer
        self.open_logs_btn = QPushButton()
        self.open_logs_btn.setFocusPolicy(Qt.NoFocus)
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
       
        # Create a form layout for Pre-Generated Logs row
        pre_gen_form_layout = QFormLayout()
        pre_gen_form_layout.setHorizontalSpacing(50)
        pre_gen_form_layout.addRow(QLabel('Pre-Generated Logs'), pre_gen_layout)
        self.widgets['Pre-Generated Logs'] = self.pre_gen_logs_cb
       
        # Add the pre-generated logs form layout to the general base layout
        general_base_layout.addLayout(pre_gen_form_layout)
        
        # Add the general group to the main layout
        layout.addWidget(general_group)

        # Windows Settings
        win_group = QGroupBox('DLT Viewer Path Settings')
        win_group.setStyleSheet(common_groupbox_style + "QGroupBox { font-weight: 500; font-size: 9pt; }")
        win_group.setFixedHeight(100)
        win_layout = QFormLayout()
        win = self.config_data.get('windows', {})
        path_cb = QCheckBox(); path_cb.setChecked(win.get('Is Environment Path Set', False))
        win_layout.addRow(QLabel('Is Environment Path Set'), path_cb)
        self.widgets['windows.Is Environment Path Set'] = path_cb

        # Path line edit with char count
        path_le = QLineEdit(win.get('DLT-Viewer Installed Path', ''))
        path_le.textChanged.connect(lambda text: [self.validate_all_fields()])
        path_le.setMaxLength(250)
        count_lbl = QLabel(f"{len(path_le.text())} / {path_le.maxLength()}")
        path_le.textChanged.connect(lambda text: [count_lbl.setText(f"{len(text)} / {path_le.maxLength()}"), self.update_border('windows.DLT-Viewer Installed Path')])
        browse_btn = QPushButton('Browse')
        browse_btn.setFocusPolicy(Qt.NoFocus)
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

        path_cb.toggled.connect(lambda checked: [dlt_path_lbl.setDisabled(checked), path_le.setDisabled(checked), browse_btn.setDisabled(checked), count_lbl.setDisabled(checked), self.validate_all_fields(), self.update_border('windows.DLT-Viewer Installed Path')])

        # ECU Configurations
        self.ec_group = QGroupBox('ECU Configurations')
        self.ec_group.setStyleSheet(common_groupbox_style + "QGroupBox { font-weight: 500; font-size: 9pt; }")
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
                valid_gb = self.is_any_ecu_selected_flag and self.is_checked and (self.isPadas and self.isRCAR)
                block.disableRemoveButton(valid_gb)
            if ecu_type=='RCAR':
                # block.setVisible(self.isRCAR and self.isElite)
                valid_gb = self.is_any_ecu_selected_flag and self.is_checked and (self.isElite and self.isRCAR)
                block.disableRemoveButton(valid_gb)
            elif ecu_type=='SoC0':
                # block.setVisible(self.isSOC0 and self.isElite)
                valid_gb = self.is_any_ecu_selected_flag and self.is_checked and (self.isElite and self.isSOC0)
                block.disableRemoveButton(valid_gb)
            elif ecu_type=='SoC1':
                # block.setVisible(self.isSOC1 and self.isElite)
                valid_gb = self.is_any_ecu_selected_flag and self.is_checked and (self.isElite and self.isSOC1)
                block.disableRemoveButton(valid_gb)
            # print(f"ECU: {ecu_type}, Valid: {valid_gb}")
            block.setStyleSheet(block.styleSheet()+f"CollapsibleGroupBox{{border: {'1px solid red' if self.is_any_ecu_selected_flag and self.is_checked and not valid_gb else '1px solid #999999'};}}")  # Set border color based on validity
            # for startup_group in self.startup_group_list:
            #     startup_group.setEnabled(startup_order_group.isChecked())
            self.ecu_block_list.append(block)
            ec_vbox.addWidget(block)

        self.ec_group.setLayout(ec_vbox)
        layout.addWidget(self.ec_group)
       
        # Enable/disable the dependent checkboxes based on 'Startup Order Application Registration'
        # Note: Startup groups remain enabled regardless of this checkbox state
        def toggle_startup_order_dependent_controls(checked):
            self.validate_all_fields()
            # Startup groups should always remain enabled
            # Only enable/disable the three judgement checkboxes inside the group box
            order_mismatch_cb.setEnabled(checked)
            order_mismatch_label.setEnabled(checked)
            not_found_cb.setEnabled(checked)
            not_found_label.setEnabled(checked)
            not_configured_cb.setEnabled(checked)
            not_configured_label.setEnabled(checked)
       
        # Set initial state for dependent controls
        startup_order_enabled = startup_order_group.isChecked()
        order_mismatch_cb.setEnabled(startup_order_enabled)
        not_found_cb.setEnabled(startup_order_enabled)
        not_configured_cb.setEnabled(startup_order_enabled)
       
        startup_order_group.toggled.connect(toggle_startup_order_dependent_controls)
        self.pre_gen_logs_cb.toggled.connect(lambda checked: [
            self.validate_all_fields(),
            win_group.setDisabled(checked),
            self.open_logs_btn.setEnabled(checked)] + [  # Enable/disable the logs folder button
            w.setDisabled(checked) for w in self.widgets['DLT-Viewer Log Capture Time'] + self.widgets['Power ON-OFF Delay'] + self.widgets['Iterations']
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
        self.ok_btn.setFixedHeight(35)
        self.ok_btn.setFocusPolicy(Qt.NoFocus)
        cancel_btn = QPushButton('Cancel'); cancel_btn.clicked.connect(self.reject)
        cancel_btn.setFixedHeight(35)
        cancel_btn.setFocusPolicy(Qt.NoFocus)
       
        help_button = QPushButton()
        help_button.setIcon(QIcon('./GUI_Icons/Help_icon.ico'))
        help_button.setFixedSize(35,35)
        help_button.setToolTip("Help")
        help_button.clicked.connect(self.handle_help_click)
        # help_button.setIconSize(QSize(30, 30))
        help_button.setWindowIconText(None)  # Icon beside text
        help_button.setFocusPolicy(Qt.NoFocus)
        btn_h.addWidget(self.ok_btn); btn_h.addWidget(cancel_btn); btn_h.addWidget(help_button)
        layout.addLayout(btn_h)

        self.widgets['DLT-Viewer Log Capture Time'][0].textChanged.connect(lambda text: [self.update_border('DLT-Viewer Log Capture Time')])
        self.widgets['Iterations'][0].textChanged.connect(lambda text: [self.update_border('Iterations')])
        self.widgets['Power ON-OFF Delay'][0].textChanged.connect(lambda text: [self.update_border('Power ON-OFF Delay')])

        # Trigger check box toggled event to set initial state
        self.pre_gen_logs_cb.toggled.emit(self.pre_gen_logs_cb.isChecked())
        for i, ecu_config in enumerate(self.widgets['ecu-config']):
            if len(ecu_config['startup']) == 0:
                self.add_startup_row(ecu_config['ecu_type'], i)
       
        for idx, ecu_type in enumerate(['PADAS', 'RCAR', 'SoC0', 'SoC1']):
            block = self.ecu_block_list[idx]
            # Define the condition for each ECU type
            ecu_conditions = {
                'PADAS': self.isPadas and self.isRCAR,
                'RCAR': self.isElite and self.isRCAR,
                'SoC0': self.isElite and self.isSOC0,
                'SoC1': self.isElite and self.isSOC1
            }
            if self.is_any_ecu_selected_flag and self.is_checked:
                if ecu_conditions[ecu_type]:
                    # ECU is selected, keep it visible
                    pass
                elif ecu_type not in ecu_types:
                    # ECU is not selected and not in config, remove it
                    block.remove_button.click()
       
        # Set initial state for Application Input List button
        self.update_app_input_button()
       
        self.validate_all_fields()
        for ecu_widgets in self.widgets['ecu-config']:
            apply_checkbox = ecu_widgets['apply_checkbox']
            apply_checkbox.toggled.connect(self.validate_all_fields)

    def update_border(self, key):
       
        if key == 'DLT-Viewer Log Capture Time':
            text = self.widgets[key][0].text()
            if self.pre_gen_logs_cb.isChecked() or (text and 1 <= int(text)):
                self.widgets[key][0].setStyleSheet('border: 0px;')
            else:
                self.widgets[key][0].setStyleSheet('border: 1px solid red;')
        elif key == 'Power ON-OFF Delay':
            text = self.widgets[key][0].text()
            if self.pre_gen_logs_cb.isChecked() or (text and 1 <= int(text)):
                self.widgets[key][0].setStyleSheet('border: 0px;')
            else:
                self.widgets[key][0].setStyleSheet('border: 1px solid red;')
        elif key == 'Iterations':
            text = self.widgets[key][0].text()
            if self.pre_gen_logs_cb.isChecked() or (text and 1 <= int(text)):
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
       
        if self.is_any_ecu_selected_flag and self.is_checked:
            # Check if this ECU type is selected in the main window
            ecu_type = removed_group.title
            if ecu_type == 'PADAS_RCAR' and  not (self.isPadas and self.isRCAR):
                should_add_restore = False
            elif ecu_type == 'ELITE_RCAR' and not (self.isElite and self.isRCAR):
                should_add_restore = False
            elif ecu_type == 'ELITE_SoC0' and not (self.isElite and self.isSOC0):
                should_add_restore = False
            elif ecu_type == 'ELITE_SoC1' and not (self.isElite and self.isSOC1):
                should_add_restore = False
       
        if should_add_restore:
            # Create a restore button
            restore_button = removed_group.create_restore_button()
           
            # Connect the restore button to update OK button state when clicked
            restore_button.clicked.connect(self.validate_all_fields)
           
            # Add the restore button to the same layout position
            if removed_group.parent_layout and removed_group.layout_index >= 0:
                removed_group.parent_layout.insertWidget(removed_group.layout_index, restore_button)
           
        # Update the OK button state when a group is removed
        self.validate_all_fields()

    def ok_clicked(self):
        self.save_config()
        self.close()

    def _create_ecu_block(self, data, idx):
        # Create the main collapsible group box for the ECU
        gb = CollapsibleGroupBox(data.get('ecu-type'))
       
        # Create a scroll area for the ECU content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setMaximumHeight(400)  # Set maximum height before scrolling
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
       
        # Create a widget to hold the content
        content_widget = QWidget()
        vbox = QVBoxLayout(content_widget)
        vbox.setContentsMargins(10, 10, 10, 10)
       
        # Startup Order Section
        startup_group = QGroupBox('Startup Order Configuration')
        startup_group.setStyleSheet(common_groupbox_style + "QGroupBox { font-weight: 500; font-size: 9pt; }")
        startup_vbox = QVBoxLayout()
        startup_fl = QFormLayout()
        startup_entries = []
        for order in data.get('startup-order', []):
            enabled = order.get('enabled', True)
            row, tp, apps, rem, enable_cb = self._create_startup_row(data.get('ecu-type'), order.get('Order Type', ''), order.get('Applications', ''), idx, enabled)
            startup_fl.addRow(row)
            startup_entries.append((row, tp, apps, rem, enable_cb))
        add_startup_btn = QPushButton('Add Startup Order')
        add_startup_btn.setFocusPolicy(Qt.NoFocus)
        add_startup_btn.clicked.connect(lambda _, i=idx: [self.add_startup_row(data.get('ecu-type'), i), self.validate_all_fields(), gb.content_changed()])
        startup_vbox.addLayout(startup_fl)
        startup_vbox.addWidget(add_startup_btn, alignment=Qt.AlignLeft)
        startup_group.setLayout(startup_vbox)
        if len(startup_entries) == 1:
            startup_entries[0][3].setDisabled(True)

        # Threshold Config Section
        self.threshold_group = QGroupBox('Threshold Configuration')
        self.threshold_group.setStyleSheet(common_groupbox_style+"QGroupBox { font-weight: 500; font-size: 9pt; }")
        threshold_vbox = QVBoxLayout()
       
        # Non-Configured Application Settings
        non_config_group = QGroupBox('Non-Configured Application Settings for Startup Time Threshold')
        non_config_group.setStyleSheet(common_groupbox_style + "QGroupBox { font-weight: 300; font-size: 8pt; }")
        non_config_layout = QHBoxLayout()
       
        # Get settings from config data
        non_config_settings = data.get('non-configured-settings', {})
        apply_threshold = non_config_settings.get('apply', False)
        threshold_value = non_config_settings.get('threshold', 5)
       
        # Apply checkbox
        apply_checkbox = QCheckBox('Apply')
        apply_checkbox.setChecked(apply_threshold)
       
        # Threshold input section
        threshold_label = QLabel('Threshold')
        threshold_input = QLineEdit(str(threshold_value))
        threshold_input.setValidator(CustomIntValidator(1))
        threshold_input.setFixedWidth(80)
        threshold_input.textChanged.connect(lambda text: self.validate_all_fields())
        sec_label = QLabel('[Int: 1~ (sec)]')
       
        # Enable/disable threshold row based on checkbox selection
        def toggle_threshold_row():
            enabled = apply_checkbox.isChecked()
            threshold_label.setEnabled(enabled)
            threshold_input.setEnabled(enabled)
            sec_label.setEnabled(enabled)
           
        # Connect checkbox to the toggle function
        apply_checkbox.toggled.connect(toggle_threshold_row)
       
        # Set initial enabled state
        toggle_threshold_row()
       
        # Layout arrangement: checkbox, then threshold controls
        non_config_layout.addWidget(apply_checkbox)
        non_config_layout.addSpacing(20)  # Add padding between checkbox and threshold controls
        non_config_layout.addWidget(threshold_label)
        non_config_layout.addWidget(threshold_input)
        non_config_layout.addWidget(sec_label)
        non_config_layout.addStretch()
        non_config_group.setLayout(non_config_layout)
        non_config_group.setFixedWidth(500)
       
       
        # Add to threshold section
        threshold_vbox.addWidget(non_config_group)
       
        # Regular threshold configuration
        threshold_fl = QFormLayout()
        threshold_entries = []
        for threshold in data.get('threshold-config', []):
            enabled = threshold.get('enabled', True)
            row, apps, thresh, enable_cb = self._create_threshold_row(data.get('ecu-type'), threshold.get('Applications', ''), threshold.get('Threshold', ''), idx, enabled)
            threshold_fl.addRow(row)
            threshold_entries.append((row, apps, thresh, enable_cb))
        add_threshold_btn = QPushButton('Add Threshold Config')
        add_threshold_btn.setFocusPolicy(Qt.NoFocus)
        add_threshold_btn.clicked.connect(lambda _, i=idx: [self.add_threshold_row(data.get('ecu-type'), i), self.validate_all_fields(), gb.content_changed()])
        threshold_vbox.addLayout(threshold_fl)
        threshold_vbox.addWidget(add_threshold_btn, alignment=Qt.AlignLeft)
        self.threshold_group.setLayout(threshold_vbox)

        vbox.addWidget(self.threshold_group)
        vbox.addWidget(startup_group)
       
        # Set the content widget to the scroll area
        scroll_area.setWidget(content_widget)
       
        # Create a container layout for the scroll area
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(scroll_area)
       
        # Set the container layout as the content layout for the collapsible group box
        gb.setContentLayout(container_layout)
       
        # Connect the removed signal to handle restore functionality
        gb.removed.connect(self.handle_group_removed)
       
        self.startup_group_list.append(startup_group)
        self.widgets['ecu-config'].append({
            'ecu_type': data.get('ecu-type'),
            'startup_layout': startup_fl,
            'startup': startup_entries,
            'threshold_layout': threshold_fl,
            'threshold': threshold_entries,
            'add_startup_btn': add_startup_btn,
            'add_threshold_btn': add_threshold_btn,
            'apply_checkbox': apply_checkbox,
            'nc_threshold_input': threshold_input
        })
        return gb

    def _get_ecu_family_and_type(self, ecu_type):
        """Map ECU index to family and type for application selection"""
        ecu_mapping = {
            'PADAS': ('PADAS', 'RCAR'),  # PADAS-RCAR
            'RCAR': ('ELITE', 'RCAR'),  # ELITE-RCAR  
            'SoC0': ('ELITE', 'SoC0'),  # ELITE-SoC0
            'SoC1': ('ELITE', 'SoC1')   # ELITE-SoC1
        }
        return ecu_mapping.get(ecu_type, (None, None))
   
    def _get_widget_text(self, widget):
        """Get text from either QLineEdit or ApplicationSelectorWidget"""
        if hasattr(widget, 'get_text'):
            return widget.get_text()
        elif hasattr(widget, 'text'):
            return widget.text()
        else:
            return ''
   
    def _set_widget_style(self, widget, style):
        """Set style for either QLineEdit or ApplicationSelectorWidget"""
        if hasattr(widget, 'text_field'):
            widget.text_field.setStyleSheet(style)
        else:
            widget.setStyleSheet(style)

    def _create_startup_row(self, ecu_type, type_val, apps_val, ecu_idx, enabled=True):
        row = QWidget()
        main_layout = QHBoxLayout(); row.setLayout(main_layout)
       
        # Enable/Disable checkbox at the start
        enable_cb = QCheckBox()
        enable_cb.setChecked(enabled)
       
        # Left side - form layout for type and apps
        left_widget = QWidget()
        left_form = QFormLayout(left_widget)
        left_form.setContentsMargins(0, 0, 0, 0)
       
        # Apps row - using custom application selector widget
        ecu_family, ecu_type = self._get_ecu_family_and_type(ecu_type)
        apps = ApplicationSelectorWidget(
            parent=self,
            ecu_family=ecu_family,
            ecu_type=ecu_type,
            ecu_idx=ecu_idx,
            placeholder_text='App1, App2'
        )
       
        # Create application count label
        def count_applications(text):
            """Count non-empty comma-separated values"""
            if not text or not text.strip():
                return 0
            apps_list = [app.strip() for app in text.split(',') if app.strip()]
            return len(apps_list)
       
        count_label = QLabel(f"Configured Application Count: {count_applications(apps_val)}")
        count_label.setStyleSheet("color: #666666; font-size: 11px;")
       
        # Update count when text changes
        def update_count_and_validation(text):
            count = count_applications(text)
            count_label.setText(f"Configured Application Count: {count}")
            self.validate_all_fields()
           
        apps.set_text(apps_val)
        apps.text_field.textChanged.connect(update_count_and_validation)

        # Type row with count label at the end
        dd = QComboBox(); dd.addItems(["Sequential", "Parallel"])
        dd.setFixedWidth(150)  # Set fixed width to 150 pixels
        idx = dd.findText(type_val)
        dd.setCurrentIndex(idx if idx != -1 else 0)
       
        type_row = QWidget()
        type_hl = QHBoxLayout(type_row)
        type_hl.setContentsMargins(0, 0, 0, 0)
        type_hl.addWidget(dd)
        type_hl.addStretch()  # Push count label to the right
        type_hl.addWidget(count_label)

        apps_row = QWidget()
        apps_hl = QHBoxLayout(apps_row)
        apps_hl.setContentsMargins(0, 0, 0, 0)
        apps_hl.addWidget(apps)
       
        left_form.addRow(QLabel('Order Type'), type_row)
        left_form.addRow(QLabel('Applications'), apps_row)

        rem = QPushButton('Remove')
        rem.setFocusPolicy(Qt.NoFocus)
        rem.clicked.connect(lambda _, i=ecu_idx, r=row: [self.remove_startup_row(i, r), self.validate_all_fields(), self._notify_content_changed(i)])
       
        main_layout.addWidget(enable_cb, alignment=Qt.AlignVCenter)
        main_layout.addWidget(left_widget)
        main_layout.addWidget(rem, alignment=Qt.AlignVCenter)
       
        enable_cb.clicked.connect(lambda: [self.validate_all_fields(), left_widget.setEnabled(enable_cb.isChecked())])
       
        # Set initial enabled state
        left_widget.setEnabled(enabled)
       
        return row, dd, apps, rem, enable_cb

    def _create_threshold_row(self, ecu_type, apps_val, threshold_val, ecu_idx, enabled=True):
        row = QWidget()
        main_layout = QHBoxLayout(); row.setLayout(main_layout)
       
        # Enable/Disable checkbox at the start
        enable_cb = QCheckBox()
        enable_cb.setChecked(enabled)
        enable_cb.clicked.connect(lambda: self.validate_all_fields())
       
        # Left side - form layout for apps and threshold
        left_widget = QWidget()
        left_form = QFormLayout(left_widget)
        left_form.setContentsMargins(0, 0, 0, 0)
       
        # Applications row - using custom application selector widget
        ecu_family, ecu_type = self._get_ecu_family_and_type(ecu_type)
        apps = ApplicationSelectorWidget(
            parent=self,
            ecu_family=ecu_family,
            ecu_type=ecu_type,
            ecu_idx=ecu_idx,
            placeholder_text='App1, App2, App3'
        )
       
        # Create application count label
        def count_applications(text):
            """Count non-empty comma-separated values"""
            if not text or not text.strip():
                return 0
            apps_list = [app.strip() for app in text.split(',') if app.strip()]
            return len(apps_list)
       
        count_label = QLabel(f"Configured Application Count: {count_applications(apps_val)}")
        count_label.setStyleSheet("color: #666666; font-size: 11px;")
       
        # Update count when text changes
        def update_count_and_validation(text):
            count = count_applications(text)
            count_label.setText(f"Configured Application Count: {count}")
            self.validate_all_fields()
           
        apps.set_text(apps_val)
        apps.text_field.textChanged.connect(update_count_and_validation)

        apps_row = QWidget()
        apps_hl = QHBoxLayout(apps_row)
        apps_hl.setContentsMargins(0, 0, 0, 0)
        apps_hl.addWidget(apps)
       
        # Threshold row with count label at the end
        thresh = QLineEdit(str(threshold_val))
        thresh.setPlaceholderText('5')
        thresh.setValidator(CustomIntValidator(1))
        thresh.setFixedWidth(80)
        thresh.textChanged.connect(lambda text: self.validate_all_fields())
       
        thresh_row = QWidget()
        thresh_hl = QHBoxLayout(thresh_row)
        thresh_hl.setContentsMargins(0, 0, 0, 0)
        thresh_hl.addWidget(thresh)
        thresh_hl.addWidget(QLabel('[Int: 1~ (sec)]'))
        thresh_hl.addStretch()  # Push count label to the right
        thresh_hl.addWidget(count_label)

        left_form.addRow(QLabel('Threshold'), thresh_row)
        left_form.addRow(QLabel('Applications'), apps_row)

        # Right side - Remove button (centered vertically)
        rem = QPushButton('Remove')
        rem.setFocusPolicy(Qt.NoFocus)
        rem.clicked.connect(lambda _, i=ecu_idx, r=row: [self.remove_threshold_row(i, r), self.validate_all_fields(), self._notify_content_changed(i)])
       
        main_layout.addWidget(enable_cb, alignment=Qt.AlignVCenter)
        main_layout.addWidget(left_widget)
        main_layout.addWidget(rem, alignment=Qt.AlignVCenter)
       
        enable_cb.clicked.connect(lambda: [self.validate_all_fields(), left_widget.setEnabled(enable_cb.isChecked())])
       
        # Set initial enabled state
        left_widget.setEnabled(enabled)
       
        return row, apps, thresh, enable_cb

    def validate_all_fields(self):
        enabled = True
        self.ecu_error_list = [False, False, False, False]
        self.ecu_block_list_selection_map = {
            0: self.isPadas and self.isRCAR,
            1: self.isElite and self.isRCAR,
            2: self.isElite and self.isSOC0,
            3: self.isElite and self.isSOC1
        }
        for ecu_idx, ecu_name in enumerate(['PADAS_RCAR', 'ELITE_RCAR', 'ELITE_SoC0', 'ELITE_SoC1']):
            if self.ecu_block_list_selection_map[ecu_idx] and self.is_any_ecu_selected_flag:
                le = self.widgets[f'IG-ON to QNX startup time {ecu_name}'][0]
                text = le.text()
                if not text or len(text) == 0:
                    enabled = False
                    self._set_widget_style(le, 'border: 1px solid red;')
                else:
                    self._set_widget_style(le, 'border: 0px;')
                    
        for key in ['DLT-Viewer Log Capture Time', 'Iterations', 'Power ON-OFF Delay']:
            if key in ['DLT-Viewer Log Capture Time', 'Power ON-OFF Delay', 'Iterations'] and self.widgets['Pre-Generated Logs'].isChecked():
                continue
            text = self.widgets[key][0].text()
            if not text or len(text) == 0:
                enabled = False
                break
            if key == 'DLT-Viewer Log Capture Time':
                if not (self.pre_gen_logs_cb.isChecked() or (text and 1 <= int(text))):
                    enabled = False
            elif key == 'Power ON-OFF Delay':
                if not (self.pre_gen_logs_cb.isChecked() or (text and 1 <= int(text))):
                    enabled = False
            elif key == 'Iterations':
                if not (self.pre_gen_logs_cb.isChecked() or (text and 1 <= int(text))):
                    enabled = False
        if not self.widgets['Pre-Generated Logs'].isChecked():
            path_cb = self.widgets['windows.Is Environment Path Set']
            path_le = self.widgets['windows.DLT-Viewer Installed Path']
            if not path_cb.isChecked() and (not path_le.text() or len(path_le.text()) == 0 or path_le.text().startswith(' ') or path_le.text().endswith(' ')):
                enabled = False
        is_partially_filled = not enabled
        for i in range(4):
            if self.ecu_block_list[i].disabled or not self.ecu_block_list_selection_map[i]:
                continue
            enable_checkbox=self.widgets['ecu-config'][i]['apply_checkbox']
            threshold_input=self.widgets['ecu-config'][i]['nc_threshold_input']
            if enable_checkbox.isChecked() and (not threshold_input.text() or len(threshold_input.text()) == 0 or not threshold_input.text().isdigit() or not (1 <= int(threshold_input.text()))):
                self._set_widget_style(threshold_input, 'border: 1px solid red;')
                enabled = False
                self.ecu_error_list[i] = True
            else:
                self._set_widget_style(threshold_input, 'border: 0px;')
            seen_apps = dict()
            for idx, entry in enumerate(self.widgets['ecu-config'][i]['startup']):
                text = self._get_widget_text(entry[2])
                if entry[4].isChecked() and self.widgets['Startup Order Application Registration'].isChecked() and text and len(text) > 0:
                    for app in text.split(','):
                        if app.strip():
                            if app.strip() in seen_apps:
                                seen_apps[app.strip()] += 1
                            else:
                                seen_apps[app.strip()] = 1
                
            for idx, entry in enumerate(self.widgets['ecu-config'][i]['startup']):
                text = self._get_widget_text(entry[2])
                if entry[4].isChecked() and self.widgets['Startup Order Application Registration'].isChecked() and (not text or len(text) == 0 or text.startswith(' ') or text.endswith(' ')):
                    self._set_widget_style(entry[2], 'border: 1px solid red;')
                    enabled = False
                    self.ecu_error_list[i] = True
                elif len([app.strip() for app in text.split(',')]) != len(set([app.strip() for app in text.split(',')])):
                    self._set_widget_style(entry[2], 'border: 1px solid red;')
                    enabled = False
                    self.ecu_error_list[i] = True
                elif entry[4].isChecked() and self.widgets['Startup Order Application Registration'].isChecked() and max([seen_apps[common_app] for common_app in set(seen_apps.keys()).intersection(set([app.strip() for app in text.split(',')]))]) > 1:
                    self._set_widget_style(entry[2], 'border: 1px solid red;')
                    enabled = False
                    self.ecu_error_list[i] = True
                else:
                    self._set_widget_style(entry[2], 'border: 0px;')
            for entry in self.widgets['ecu-config'][i]['threshold']:
                apps_text = self._get_widget_text(entry[1])
                if entry[3].isChecked() and (not apps_text or len(apps_text) == 0 or apps_text.startswith(' ') or apps_text.endswith(' ')):
                    self._set_widget_style(entry[1], 'border: 1px solid red;')
                    enabled = False
                    self.ecu_error_list[i] = True
                else:
                    self._set_widget_style(entry[1], 'border: 0px;')
                threshold_text = self._get_widget_text(entry[2])
                if entry[3].isChecked() and (not threshold_text or len(threshold_text) == 0 or not threshold_text.isdigit() or not (1 <= int(threshold_text))):
                    self._set_widget_style(entry[2], 'border: 1px solid red;')
                else:
                    self._set_widget_style(entry[2], 'border: 0px;')
        startup_order_group = self.widgets['Startup Order Application Registration']
        if startup_order_group.isChecked():
            if self.ecu_block_list_selection_map[0] and not self.ecu_block_list[0].disabled:
                if len(self.widgets['ecu-config'][0]['startup']) == 0:
                    enabled=False
                    self.ecu_error_list[0] = True
                else:
                    for entry in self.widgets['ecu-config'][0]['startup']:
                        text = self._get_widget_text(entry[2])
                        if (not text or len(text) == 0) and entry[4].isChecked():
                            enabled = False
                            self.ecu_error_list[0] = True
                            break
            if self.ecu_block_list_selection_map[1] and not self.ecu_block_list[1].disabled:
                if len(self.widgets['ecu-config'][1]['startup']) == 0:
                    enabled=False
                    self.ecu_error_list[1] = True
                else:
                    for entry in self.widgets['ecu-config'][1]['startup']:
                        text = self._get_widget_text(entry[2])
                        if (not text or len(text) == 0) and entry[4].isChecked():
                            enabled = False
                            self.ecu_error_list[1] = True
                            break
            if self.ecu_block_list_selection_map[2] and not self.ecu_block_list[2].disabled:
                if len(self.widgets['ecu-config'][2]['startup']) == 0:
                    enabled=False
                    self.ecu_error_list[2] = True
                else:
                    for entry in self.widgets['ecu-config'][2]['startup']:
                        text = self._get_widget_text(entry[2])
                        if (not text or len(text) == 0) and entry[4].isChecked():
                            enabled = False
                            self.ecu_error_list[2] = True
                            break
            if self.ecu_block_list_selection_map[3] and not self.ecu_block_list[3].disabled:
                if len(self.widgets['ecu-config'][3]['startup']) == 0:
                    enabled=False
                    self.ecu_error_list[3] = True
                else:
                    for entry in self.widgets['ecu-config'][3]['startup']:
                        text = self._get_widget_text(entry[2])
                        if (not text or len(text) == 0) and entry[4].isChecked():
                            enabled = False
                            self.ecu_error_list[3] = True
                            break
        if self.ecu_block_list_selection_map[0] and not self.ecu_block_list[0].disabled:
            # Check threshold entries for RCAR-PADAS
            for entry in self.widgets['ecu-config'][0]['threshold']:
                apps_text = self._get_widget_text(entry[1])
                threshold_text = self._get_widget_text(entry[2])
                if (not apps_text or len(apps_text) == 0 or not threshold_text or len(threshold_text) == 0) and entry[3].isChecked():
                    enabled = False
                    self.ecu_error_list[0] = True
                    break
        if self.ecu_block_list_selection_map[1] and not self.ecu_block_list[1].disabled:
            # Check threshold entries for RCAR
            for entry in self.widgets['ecu-config'][1]['threshold']:
                apps_text = self._get_widget_text(entry[1])
                threshold_text = self._get_widget_text(entry[2])
                if (not apps_text or len(apps_text) == 0 or not threshold_text or len(threshold_text) == 0) and entry[3].isChecked():
                    enabled = False
                    self.ecu_error_list[1] = True
                    break
        if self.ecu_block_list_selection_map[2] and not self.ecu_block_list[2].disabled:
            # Check threshold entries for SoC0
            for entry in self.widgets['ecu-config'][2]['threshold']:
                apps_text = self._get_widget_text(entry[1])
                threshold_text = self._get_widget_text(entry[2])
                if (not apps_text or len(apps_text) == 0 or not threshold_text or len(threshold_text) == 0) and entry[3].isChecked():
                    enabled = False
                    self.ecu_error_list[2] = True
                    break
        if self.ecu_block_list_selection_map[3] and not self.ecu_block_list[3].disabled:
            # Check threshold entries for SoC1
            for entry in self.widgets['ecu-config'][3]['threshold']:
                apps_text = self._get_widget_text(entry[1])
                threshold_text = self._get_widget_text(entry[2])
                if (not apps_text or len(apps_text) == 0 or not threshold_text or len(threshold_text) == 0) and entry[3].isChecked():
                    enabled = False
                    self.ecu_error_list[3] = True
                    break
        for i in range(4):
            self.update_ecu_block_styles(self.ecu_block_list[i], self.ecu_error_list[i])

        self.ok_btn.setEnabled(False if self.main_window.is_test_in_progress and self.is_checked else True)
        print(f"Validation result - ECU block list map: {self.ecu_block_list_selection_map}, ECU error list: {self.ecu_error_list}), is_partially_filled: {is_partially_filled}")
        return not is_partially_filled and any((
            not self.ecu_error_list[0] and self.ecu_block_list_selection_map[0],
            not self.ecu_error_list[1] and self.ecu_block_list_selection_map[1],
            not self.ecu_error_list[2] and self.ecu_block_list_selection_map[2],
            not self.ecu_error_list[3] and self.ecu_block_list_selection_map[3]
        ))
       
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
            (self.is_any_ecu_selected_flag and self.is_checked and not ecu_conditions.get(ecu_gb.title, True))
        )
       
        # Apply appropriate border style
        border_style = '1px solid red' if should_have_red_border else '1px solid #999999'
        ecu_gb.setStyleSheet(f"{ecu_gb.styleSheet()}CollapsibleGroupBox{{border: {border_style};}}")

    def _notify_content_changed(self, ecu_idx):
        """Notify the corresponding ECU block that content has changed."""
        if ecu_idx < len(self.ecu_block_list):
            self.ecu_block_list[ecu_idx].content_changed()

    def add_startup_row(self, ecu_type, idx):
        # self.ok_btn.setDisabled(False)
        entry = self.widgets['ecu-config'][idx]
        row, dd, apps, rem, enable_cb = self._create_startup_row(ecu_type, '', '', idx)
        entry['startup_layout'].addRow(row)
        entry['startup'].append((row, dd, apps, rem, enable_cb))
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

    def add_threshold_row(self, ecu_type, idx):
        entry = self.widgets['ecu-config'][idx]
        row, apps, thresh, enable_cb = self._create_threshold_row(ecu_type, '', '', idx)
        entry['threshold_layout'].addRow(row)
        entry['threshold'].append((row, apps, thresh, enable_cb))
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
        # Determine starting directory based on current path in line_edit
        current_path = line_edit.text().strip()
        if current_path and os.path.exists(current_path):
            # If the path itself is a directory, use it
            start_dir = current_path
        else:
            # Default to C drive if path is empty or invalid
            start_dir = 'C:\\'
       
        path, _ = QFileDialog.getOpenFileName(self, 'Select dlt-viewer executable', start_dir, 'Executable Files (*.exe)')
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
        """Open the Application_Input_List_for_Startup_Time.xlsx file"""
        app_input_path = self.app_input_file_path
       
        # Check if the file exists
        if not app_input_path.exists():
            print(f"Application_Input_List_for_Startup_Time.xlsx not found at: {app_input_path}")
            return
       
        # Store the file path for cleanup later
        self.excel_file_path = str(app_input_path)
       
        # Open the Excel file with the default application
        try:
            if platform.system() == "Windows":
                os.startfile(app_input_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", app_input_path])
            else:  # Linux and other Unix-like systems
                subprocess.run(["xdg-open", app_input_path])
        except Exception as e:
            print(f"Error opening Application_Input_List_for_Startup_Time.xlsx: {e}")
   
    def close_opened_excel_files(self):
        """Close the specific Excel file if it's open"""
        if not self.excel_file_path:
            return
           
        try:
            # Try to use Windows COM API to close the specific Excel file
            import win32com.client
            xl = win32com.client.GetActiveObject("Excel.Application")
           
            # Check how many workbooks are currently open
            workbook_count = xl.Workbooks.Count
           
            # Look for our specific file and close it
            for wb in xl.Workbooks:
                if wb.FullName.lower() == self.excel_file_path.lower():
                    wb.Close(SaveChanges=False)
                    print(f"Closed Excel file: {self.excel_file_path}")
                   
                    # If this was the only workbook, quit Excel entirely
                    if workbook_count == 1:
                        xl.Quit()
                        print("Closed Excel application (was the last workbook)")
                    break
                   
        except Exception as e:
            # If COM approach fails, silently continue (Excel might not be running or file not open)
            print(f"Could not close Excel file via COM: {e}")
            pass
   
    def check_app_input_file(self):
        """Check if Application_Input_List_for_Startup_Time.xlsx exists"""
        return self.app_input_file_path.exists()
   
    def update_app_input_button(self):
        """Update the Application Input List button appearance based on file presence"""
        if not hasattr(self, 'app_input_btn'):
            return
           
        file_exists = self.check_app_input_file()
       
        # Create tooltip text
        if file_exists:
            tooltip_lines = ["Application_Input_List_for_Startup_Time.xlsx found - Click to open", ""]
           
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
            tooltip_text = "Application_Input_List_for_Startup_Time.xlsx not found in current directory"
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
        """Parse the Application_Input_List_for_Startup_Time.xlsx file and extract applications by ECU type"""
        if not self.check_app_input_file():
            print("Application_Input_List_for_Startup_Time.xlsx not found, cannot parse applications")
            return None
       
        try:
            # Load the Excel workbook
            workbook = openpyxl.load_workbook(self.app_input_file_path)
            worksheet = workbook.active
           
            # Initialize the applications dictionary
            applications = {
                'ELITE': {
                    'RCAR': [],
                    'SOC0': [],
                    'SOC1': []
                },
                'PADAS': {
                    'RCAR': []
                }
            }
           
            # Column mapping according to the Excel structure
            # Column B = ELITE RCAR, Column C = ELITE SoC0, Column D = ELITE SoC1, Column E = PADAS RCAR
            column_mapping = {
                'B': ('ELITE', 'RCAR'),
                'C': ('ELITE', 'SOC0'),
                'D': ('ELITE', 'SOC1'),
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
            #print("Parsed Application Input List:")
            #for ecu_family, ecu_types in applications.items():
                #for ecu_type, apps in ecu_types.items():
                    #if apps:
                        #print(f"  {ecu_family} {ecu_type}: {apps}")
           
            return applications
           
        except Exception as e:
            print(f"Error parsing Application_Input_List_for_Startup_Time.xlsx: {e}")
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
        #print("Refreshing Application Input List...")
        self.parse_application_input_list()
       
        # Refresh all ApplicationSelectorWidget instances
        if hasattr(self, 'widgets') and 'ecu-config' in self.widgets:
            for ecu_config in self.widgets['ecu-config']:
                # Refresh startup entries
                for entry in ecu_config['startup']:
                    if len(entry) >= 3 and hasattr(entry[2], 'refresh_applications'):
                        entry[2].refresh_applications()
               
                # Refresh threshold entries  
                for entry in ecu_config['threshold']:
                    if len(entry) >= 2 and hasattr(entry[1], 'refresh_applications'):
                        entry[1].refresh_applications()

    def save_config(self):
        data = {}
        for key in ['DLT-Viewer Log Capture Time', 'Iterations', 'Power ON-OFF Delay']:
            w = self.widgets[key][0]
            # print(w.text())
            if w.text() and len(w.text())>0:
                data[key] = int(w.text())
        
        # Save IG-ON to QNX startup time values
        for ecu_name in ['PADAS_RCAR', 'ELITE_RCAR', 'ELITE_SoC0', 'ELITE_SoC1']:
            key = f'IG-ON to QNX startup time {ecu_name}'
            if key in self.widgets:
                w = self.widgets[key][0]
                if w.text() and len(w.text()) > 0:
                    data[key] = float(w.text())
        
        data['Startup Order Application Registration'] = self.widgets['Startup Order Application Registration'].isChecked()
        # data['Application Registration'] = self.widgets['Application Registration'].isChecked()
        data['Startup Order Judgement'] = self.widgets['Startup Order Judgement'].isChecked()
        data['Missing Judgement'] = self.widgets['Missing Judgement'].isChecked()
        data['Unexpected Judgement'] = self.widgets['Unexpected Judgement'].isChecked()
        data['Pre-Generated Logs'] = self.widgets['Pre-Generated Logs'].isChecked()
        data['windows'] = {
            'Is Environment Path Set': self.widgets['windows.Is Environment Path Set'].isChecked(),
            'DLT-Viewer Installed Path': self.widgets['windows.DLT-Viewer Installed Path'].text()
        }
        ec = []
        for idx, item in enumerate(self.widgets['ecu-config']):
            title = self.ecu_map.get(self.ecu_block_list[idx].title, self.ecu_block_list[idx].title)
            ec_item = {'ecu-type': title, 'startup-order': [], 'threshold-config': [], 'enabled': not self.ecu_block_list[idx].disabled}
            if self.ecu_block_list[idx].disabled:
                continue
            for entry in item['startup']:
                # entry is (row, dd, apps, rem, enable_cb)
                _, dd, apps, _, enable_cb = entry
                ec_item['startup-order'].append({
                    'Order Type': dd.currentText(),
                    'Applications': self._get_widget_text(apps),
                    'enabled': enable_cb.isChecked()
                })
            for entry in item['threshold']:
                # entry is (row, apps, thresh, enable_cb)
                _, apps, thresh, enable_cb = entry
                threshold_text = self._get_widget_text(thresh)
                if threshold_text:  # Only save if threshold value is provided
                    ec_item['threshold-config'].append({
                        'Applications': self._get_widget_text(apps),
                        'Threshold': int(threshold_text),
                        'enabled': enable_cb.isChecked()
                    })
           
            # Save non-configured application settings
            apply_checkbox = item['apply_checkbox']
            threshold_input = item['nc_threshold_input']

            if apply_checkbox and threshold_input:
                non_config_settings = {
                    'apply': apply_checkbox.isChecked(),
                    'threshold': int(threshold_input.text()) if threshold_input.text() else 5
                }
                ec_item['non-configured-settings'] = non_config_settings
           
            ec.append(ec_item)
           
        validation_map = {
            "PADAS": ("PADAS", "RCAR"),
            "RCAR": ("Elite", "RCAR"),
            "SoC0": ("Elite", "SoC0"),
            "SoC1": ("Elite", "SoC1"),
        }
        for idx, block in enumerate(self.ecu_block_list):
            # if block.disabled:
            #     continue  # Skip disabled blocks
           
            self.ecu_block_list_selection_map = {i: i==idx for i in range(4)}
            self.validate_all_fields()

            # Get mapped title if available
            title = self.ecu_map.get(block.title, block.title)
            group, key = validation_map[title]
            self.ecu_selection[group][key] = not block.disabled and not self.ecu_error_list[idx]
            py_logger.info(f"Enabled ECU: {title} {group}-{key} {self.ecu_selection[group][key]}")
       
        self.ecu_block_list_selection_map = {
            0: self.isPadas and self.isRCAR,
            1: self.isElite and self.isRCAR,
            2: self.isElite and self.isSOC0,
            3: self.isElite and self.isSOC1
        }
        self.validate_all_fields()
 
        # py_logger.info(f'self.ecu_selection: {self.ecu_selection}')
 
        data['ecu-config'] = ec
        data['ECU_setting'] = self.ecu_selection
        data["is_all_fields_valid"] = self.validate_all_fields()
        try:
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=4)

            self.accept()
        except Exception as e:
            print(f'Failed to save config: {e}')

    def closeEvent(self, event):
        """Handle dialog close event to cleanup Excel processes"""
        self.close_opened_excel_files()
        self.pdf_process = close_pdf_process(self.pdf_process)
        super().closeEvent(event)
   
    def reject(self):
        """Handle dialog cancel to cleanup Excel processes"""
        self.close_opened_excel_files()
        self.pdf_process = close_pdf_process(self.pdf_process)
        super().reject()
   
    def done(self, result):
        """Handle dialog completion to cleanup Excel processes"""
        self.close_opened_excel_files()
        self.pdf_process = close_pdf_process(self.pdf_process)
        super().done(result)