from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QToolButton, QFrame, QSizePolicy, QPushButton, QLabel
from PyQt5.QtCore import Qt, QPropertyAnimation, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QFont


class CollapsibleGroupBox(QFrame):
    """A clean, collapsible group box with remove functionality."""
    
    removed = pyqtSignal(object)  # Signal emitted when the remove button is clicked, passes self reference
    
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.title_map = {
            "PADAS": "PADAS_RCAR",
            "RCAR": "ELITE_RCAR",
            "SoC0": "ELITE_SoC0",
            "SoC1": "ELITE_SoC1"
        }
        self.title = self.title_map.get(title, title)  # Store title for restoration
        self.parent_layout = None  # Will store reference to parent layout
        self.layout_index = -1  # Will store position in parent layout
        self.disabled = False  # Flag to indicate if the group box is disabled
        
        # Set frame style and size policy
        self.setFrameStyle(QFrame.StyledPanel)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # Remove background styling to not interfere with content
        self.setStyleSheet("""
            CollapsibleGroupBox {
                border: 1px solid #ddd;
                border-radius: 6px;
                background: transparent;
            }
        """)
        
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create header
        self.create_header(self.title)
        
        # Create content area
        self.content_area = QFrame()
        self.content_area.setStyleSheet("")  # No styling to preserve original content appearance
        self.content_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.main_layout.addWidget(self.content_area)
        
        # Animation
        self.toggle_animation = QPropertyAnimation(self.content_area, b"maximumHeight")
        self.toggle_animation.setDuration(200)
        
        self.collapsed = True  # Start collapsed
        self.expanded_height = 0  # Will be set when content is added
        
        # Set initial collapsed state
        self.content_area.setMaximumHeight(0)
        
        # Timer for delayed height calculation
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.recalculate_height)
        
    def create_header(self, title):
        """Create a clean header with title, toggle and remove buttons."""
        header_frame = QFrame()
        header_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        header_frame.setFixedHeight(36)  # Set a fixed height for the header
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: none;
                border-radius: 6px 6px 0px 0px;
                padding: 0px;
            }
        """)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 8, 8, 8)
        header_layout.setSpacing(8)
        
        # Title
        self.title_label = QLabel(title)
        # font = QFont()
        # font.setWeight(200)
        # font.setPixelSize(13)
        # self.title_label.setFont(font)
        self.title_label.setStyleSheet("color: #2c3e50; background: transparent; font-weight: 500; font-size: 9pt;")
        
        # Toggle button
        self.toggle_button = QToolButton()
        self.toggle_button.setFocusPolicy(Qt.NoFocus)
        self.toggle_button.setText("+")  # Plus sign when collapsed
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)  # Start collapsed
        self.toggle_button.setFixedSize(20, 20)
        self.toggle_button.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                color: #2c3e50;
                font-weight: bold;
                font-size: 12px;
            }
            QToolButton:hover {
                background-color: #ecf0f1;
                border-color: #95a5a6;
            }
            QToolButton:pressed {
                background-color: #d5dbdb;
            }
        """)
        self.toggle_button.setToolTip("Collapse/Expand")
        
        # Remove button  
        self.remove_button = QPushButton("×")
        self.remove_button.setFocusPolicy(Qt.NoFocus)
        self.remove_button.setFixedSize(20, 20)
        self.remove_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                color: #e74c3c;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #fadbd8;
                border-color: #e74c3c;
            }
            QPushButton:pressed {
                background-color: #f5b7b1;
            }
        """)
        self.remove_button.setToolTip("Remove this section")
        
        # Add to layout
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.toggle_button)
        header_layout.addWidget(self.remove_button)
        
        self.main_layout.addWidget(header_frame)
        
        # Connect signals
        self.toggle_button.clicked.connect(self.toggle_collapsed)
        self.remove_button.clicked.connect(self.hide_group)
        
    def setContentLayout(self, layout):
        """Set the layout for the collapsible content without modifying its styling."""
        # Clear existing layout if any
        if self.content_area.layout():
            old_layout = self.content_area.layout()
            while old_layout.count():
                child = old_layout.takeAt(0)
                if child.widget():
                    child.widget().setParent(None)
        
        # Set the layout directly without any wrapper or modifications
        self.content_area.setLayout(layout)
        
        # Force layout activation and geometry updates
        layout.activate()
        self.content_area.updateGeometry()
        
        # Get the proper size hint after everything is laid out
        self.content_area.adjustSize()
        content_size = self.content_area.sizeHint()
        self.expanded_height = max(content_size.height(), self.content_area.minimumSizeHint().height())
        
        # Set maximum height based on collapsed state
        if self.collapsed:
            self.content_area.setMaximumHeight(0)
        else:
            self.content_area.setMaximumHeight(self.expanded_height)
            
            # Force a layout update on the parent
        if self.parent():
            self.parent().updateGeometry()
            
    def recalculate_height(self):
        """Recalculate the expanded height when content changes."""
        if self.content_area.layout():
            self.content_area.layout().activate()
            self.content_area.updateGeometry()
            self.content_area.adjustSize()
            
            content_size = self.content_area.sizeHint()
            self.expanded_height = max(content_size.height(), self.content_area.minimumSizeHint().height())
            
            # If currently expanded, update the maximum height
            if not self.collapsed:
                self.content_area.setMaximumHeight(self.expanded_height)
                
    def content_changed(self):
        """Call this method when content is dynamically added/removed."""
        # Use timer to delay height calculation to allow layout to settle
        self.resize_timer.start(50)
        
    def toggle_collapsed(self):
        """Toggle the collapsed state of the group box."""
        checked = self.toggle_button.isChecked()
        
        # Update button text
        self.toggle_button.setText("−" if checked else "+")
        
        if checked:
            # Expanding - recalculate height first
            self.recalculate_height()
            self.toggle_animation.setStartValue(0)
            target_height = max(self.expanded_height, 100)  # Minimum height
            self.toggle_animation.setEndValue(target_height)
            self.collapsed = False
        else:
            # Collapsing
            current_height = self.content_area.height()
            self.toggle_animation.setStartValue(current_height)
            self.toggle_animation.setEndValue(0)
            self.collapsed = True
        
        # Connect animation finished signal to update geometry
        self.toggle_animation.finished.connect(self.updateGeometry)
        self.toggle_animation.start()
        
    def hide_group(self):
        """Hide the group box and emit removed signal with self reference."""
        # Store layout information before hiding
        if self.parent():
            parent_widget = self.parent()
            if hasattr(parent_widget, 'layout') and parent_widget.layout():
                self.parent_layout = parent_widget.layout()
                # Find our position in the layout
                for i in range(self.parent_layout.count()):
                    if self.parent_layout.itemAt(i).widget() == self:
                        self.layout_index = i
                        break
        
        self.setVisible(False)
        self.disabled = True
        self.removed.emit(self)  # Pass self reference
        
    def show_group(self):
        """Show the group box again."""
        self.setVisible(True)
        self.disabled = False
        
    def create_restore_button(self):
        """Create a restore button that can bring back this group box."""
        restore_btn = QPushButton(f"Add {self.title} Configuration")
        restore_btn.setFocusPolicy(Qt.NoFocus)
        restore_btn.setFixedHeight(36)  # Same height as group box header
        restore_btn.setStyleSheet("""
            QPushButton {
                background-color: #e8f4fd;
                border: 2px solid #3498db;
                border-radius: 6px;
                color: #2980b9;
                font-weight: bold;
                font-size: 12px;
                text-align: center;
                padding-left: 12px;
            }
            QPushButton:hover {
                background-color: #d6eaf8;
                border-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #aed6f1;
            }
        """)
        restore_btn.setToolTip(f"Click to add {self.title} configuration")
        
        # Connect restore functionality
        restore_btn.clicked.connect(lambda: self.restore_group(restore_btn))
        
        return restore_btn
        
    def restore_group(self, restore_button):
        """Restore the group box and remove the restore button."""
        if self.parent_layout and self.layout_index >= 0:
            # Remove the restore button
            self.parent_layout.removeWidget(restore_button)
            restore_button.deleteLater()
            
            # Insert the group box back at its original position
            self.parent_layout.insertWidget(self.layout_index, self)
            self.show_group()
        
    def sizeHint(self):
        """Return the size hint based on collapsed state."""
        if self.collapsed:
            # When collapsed, only return the header height
            return QSize(super().sizeHint().width(), 36)
        else:
            # When expanded, return the full size
            return super().sizeHint()
        
    def setCollapsed(self, collapsed):
        """Programmatically set the collapsed state."""
        if collapsed != self.collapsed:
            self.toggle_button.setChecked(not collapsed)
            self.toggle_collapsed()
            self.toggle_collapsed()
    def disableRemoveButton(self, disabled):
        """Programmatically set the remove button state."""
        if disabled:
            self.remove_button.setStyleSheet("""
                QPushButton {
                    background: lightgray;
                    border: 1px solid #bdc3c7;
                    border-radius: 3px;
                    color: gray;
                    font-weight: bold;
                    font-size: 14px;
                }
            """)
        self.remove_button.setDisabled(disabled)
