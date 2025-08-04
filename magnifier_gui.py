import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QSpinBox, QDoubleSpinBox, QCheckBox, QFrame,
                             QDialog, QComboBox, QSlider, QColorDialog, QTabWidget,
                             QGroupBox, QGridLayout, QLineEdit, QMessageBox)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage, QFont, QPainter, QPen, QColor
from typing import Optional
import threading
import keyboard
from pynput import mouse
from mouse_input import MouseInput

import win32gui
import win32con

class TransparentOverlay(QWidget):
    """
    A completely transparent, non-interactive overlay window.
    This window will pass all mouse events through to the window below it.
    """
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

    def showEvent(self, event):
        """
        When the window is shown, apply the transparent window style.
        """
        super().showEvent(event)
        hwnd = self.winId()
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        style |= win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)

class MagnifierOverlay(TransparentOverlay):
    """Simple magnifier overlay window"""
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.is_active = False
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the overlay UI as a separate layer that won't be captured"""
        self.setWindowTitle("Screen Magnifier")
        
        # Set window opacity from config
        opacity = self.config.get("overlay_opacity", 0.99)
        self.setWindowOpacity(opacity)
        self.setStyleSheet("background-color: black;")
        
        # Windows-specific: Try to exclude window from screen capture
        self._apply_windows_capture_exclusion()
        
        # Create label for image display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.image_label)
        self.setLayout(layout)
        
        self.hide()
    
    def update_display(self, image: Optional[np.ndarray]):
        """Update the magnifier display"""
        if image is None:
            return
        
        # Convert BGR to RGB for Qt
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        
        # Create QImage and QPixmap
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        
        # Update label
        self.image_label.setPixmap(pixmap)
        
        # Resize window to fit content plus border
        border_width = self.config.get("border_width", 2)
        self.resize(pixmap.width() + border_width * 2, pixmap.height() + border_width * 2)
        
        # Position image label with border space
        self.image_label.setGeometry(border_width, border_width, pixmap.width(), pixmap.height())
    
    def paintEvent(self, event):
        """Draw border around the overlay"""
        super().paintEvent(event)
        
        painter = QPainter(self)
        pen = QPen(QColor(self.config.get("border_color", "#FF0000")))
        pen.setWidth(self.config.get("border_width", 2))
        painter.setPen(pen)
        
        # Draw border
        border_width = self.config.get("border_width", 2)
        rect = self.rect().adjusted(border_width//2, border_width//2, -border_width//2, -border_width//2)
        painter.drawRect(rect)
    
    def keyPressEvent(self, event):
        """Handle escape key to hide magnifier"""
        if event.key() == Qt.Key_Escape:
            self.hide_magnifier()
        else:
            super().keyPressEvent(event)
    
    def show_magnifier(self):
        """Show the magnifier"""
        self.is_active = True
        self.show()
        # Apply Windows capture exclusion after window is shown and has a handle
        self._apply_windows_capture_exclusion()
    
    def hide_magnifier(self):
        """Hide the magnifier instantly"""
        self.is_active = False
        self.hide()
        self.current_image = None
    
    def _apply_windows_capture_exclusion(self):
        """Apply Windows-specific exclusion from screen capture"""
        try:
            import platform
            if platform.system() == "Windows":
                # Try to use Windows API to exclude from capture
                import ctypes
                from ctypes import wintypes
                
                # Get window handle
                hwnd = int(self.winId())
                
                # SetWindowDisplayAffinity with WDA_EXCLUDEFROMCAPTURE
                WDA_EXCLUDEFROMCAPTURE = 0x00000011
                user32 = ctypes.WinDLL("user32", use_last_error=True)
                user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
                user32.SetWindowDisplayAffinity.restype = wintypes.BOOL
                
                result = user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
                if not result:
                    self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        except Exception as e:
            self.setAttribute(Qt.WA_TransparentForMouseEvents, True)


class MagnifierControlPanel(QWidget):
    
    settings_changed = pyqtSignal(dict)
    toggle_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    snap_to_center_requested = pyqtSignal()
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setup_ui()
        self.load_settings()
        self.mouse_input = MouseInput(self)
        self.mouse_input.start_listening()
        
    def setup_ui(self):
        """Setup the control panel UI"""
        self.setWindowTitle("Screen Magnifier Control")
        self.setFixedSize(350, 500)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        
        # Main layout
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Title
        title = QLabel("Screen Magnifier")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(title)
        
                # Hotkey binding section
        hotkey_frame = QFrame()
        hotkey_frame.setFrameStyle(QFrame.Box)
        hotkey_layout = QVBoxLayout()
        
        hotkey_title = QLabel("Hotkey Binding")
        hotkey_title.setFont(QFont("Arial", 10, QFont.Bold))
        hotkey_layout.addWidget(hotkey_title)
        
        hotkey_row = QHBoxLayout()
        self.hotkey_display = QLabel(self.config.get("hotkey"))
        self.hotkey_display.setStyleSheet("border: 1px solid gray; padding: 5px; background: #f0f0f0;")
        self.hotkey_display.setAlignment(Qt.AlignCenter)
        hotkey_row.addWidget(self.hotkey_display)
        
        self.change_hotkey_btn = QPushButton("Change")
        self.change_hotkey_btn.clicked.connect(self.change_hotkey)
        hotkey_row.addWidget(self.change_hotkey_btn)
        
        hotkey_layout.addLayout(hotkey_row)
        hotkey_frame.setLayout(hotkey_layout)
        layout.addWidget(hotkey_frame)

        # Status frame
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.Box)
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("Status: OFF")
        self.status_label.setFont(QFont("Arial", 10))
        status_layout.addWidget(self.status_label)
        
        self.toggle_btn = QPushButton("START")
        self.toggle_btn.setMinimumHeight(30)
        self.toggle_btn.clicked.connect(self.toggle_magnifier)
        status_layout.addWidget(self.toggle_btn)
        
        status_frame.setLayout(status_layout)
        layout.addWidget(status_frame)
        
        # Settings frame
        settings_frame = QFrame()
        settings_frame.setFrameStyle(QFrame.Box)
        settings_layout = QVBoxLayout()
        
        # Zoom level
        zoom_layout = QHBoxLayout()
        zoom_layout.addWidget(QLabel("Zoom Level:"))
        self.zoom_spin = QDoubleSpinBox()
        self.zoom_spin.setRange(1.0, 10.0)
        self.zoom_spin.setSingleStep(0.1)
        self.zoom_spin.setSuffix("x")
        # Use editingFinished to reduce constant updates while dragging
        self.zoom_spin.editingFinished.connect(self.on_zoom_level_changed)
        zoom_layout.addWidget(self.zoom_spin)
        settings_layout.addLayout(zoom_layout)
        
        # Box size
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Capture Size:"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(50, 1000)
        self.width_spin.setSuffix(" px")
        self.width_spin.editingFinished.connect(self.on_box_width_changed)
        size_layout.addWidget(self.width_spin)
        
        size_layout.addWidget(QLabel("x"))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(50, 1000)
        self.height_spin.setSuffix(" px")
        self.height_spin.editingFinished.connect(self.on_box_height_changed)
        size_layout.addWidget(self.height_spin)
        settings_layout.addLayout(size_layout)

        # Update rate
        rate_layout = QHBoxLayout()
        rate_layout.addWidget(QLabel("Update Rate:"))
        self.rate_spin = QSpinBox()
        self.rate_spin.setRange(15, 120)  # Better minimum for performance
        self.rate_spin.setSuffix(" FPS")
        self.rate_spin.editingFinished.connect(self.on_update_rate_changed)
        rate_layout.addWidget(self.rate_spin)
        settings_layout.addLayout(rate_layout)
        
        # Crosshair
        self.crosshair_check = QCheckBox("Show Crosshair")
        self.crosshair_check.stateChanged.connect(self.on_show_crosshair_changed)
        settings_layout.addWidget(self.crosshair_check)
        
        # Position mode
        position_layout = QHBoxLayout()
        self.follow_mouse_check = QCheckBox("Follow Mouse")
        self.follow_mouse_check.stateChanged.connect(self.on_follow_mouse_changed)
        position_layout.addWidget(self.follow_mouse_check)
        
        self.center_btn = QPushButton("Snap to Center")
        self.center_btn.clicked.connect(self.snap_to_center)
        position_layout.addWidget(self.center_btn)
        settings_layout.addLayout(position_layout)
        
        settings_frame.setLayout(settings_layout)
        layout.addWidget(settings_frame)
        
        # Advanced settings button
        advanced_layout = QHBoxLayout()
        self.advanced_btn = QPushButton("Advanced Settings")
        self.advanced_btn.clicked.connect(self.show_advanced_settings)
        advanced_layout.addWidget(self.advanced_btn)
        
        layout.addLayout(advanced_layout)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.minimize_btn = QPushButton("Minimize")
        self.minimize_btn.clicked.connect(self.showMinimized)
        button_layout.addWidget(self.minimize_btn)
        
        self.quit_btn = QPushButton("Quit")
        self.quit_btn.clicked.connect(self.quit_requested.emit)
        button_layout.addWidget(self.quit_btn)
        
        layout.addLayout(button_layout)
        
        # Info label
        info_label = QLabel(f"Hotkey: {self.config.get('hotkey')}\nPress ESC to hide magnifier")
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setFont(QFont("Arial", 8))
        info_label.setStyleSheet("color: gray;")
        layout.addWidget(info_label)
        
        self.setLayout(layout)
        
        # Initialize advanced settings dialog
        self.advanced_dialog = None
    
    def change_hotkey(self):
        """Open hotkey recording dialog"""
        dialog = UnifiedHotkeyRecorderDialog(self.config.hotkey, self)
        if dialog.exec_() == QDialog.Accepted:
            new_hotkey = dialog.get_hotkey()
            self.hotkey_display.setText(new_hotkey)
            self.config.hotkey = new_hotkey
            # Emit settings changed to update hotkeys in main app
            self.settings_changed.emit({"hotkey": new_hotkey})

    
    def on_advanced_settings_changed(self, new_settings: dict):
        """Handle settings changes from the advanced dialog and update the UI."""
        self.load_settings()
        self.settings_changed.emit(new_settings)

    def show_advanced_settings(self):
        """Show advanced settings dialog"""
        if not self.advanced_dialog:
            self.advanced_dialog = AdvancedSettingsDialog(self.config, self)
            self.advanced_dialog.settings_changed.connect(self.on_advanced_settings_changed)

        self.advanced_dialog.show()
        self.advanced_dialog.raise_()
        self.advanced_dialog.activateWindow()
    
    def load_settings(self):
        """Load current settings into UI"""
        self.zoom_spin.setValue(self.config.zoom_level)
        self.width_spin.setValue(self.config.box_width)
        self.height_spin.setValue(self.config.box_height)
        self.crosshair_check.setChecked(self.config.show_crosshair)
        self.rate_spin.setValue(self.config.update_rate)
        self.follow_mouse_check.setChecked(self.config.follow_mouse)
    
    def on_zoom_level_changed(self):
        """Handle zoom level spin box change."""
        self.config.zoom_level = self.zoom_spin.value()
        self.settings_changed.emit({"zoom_level": self.config.zoom_level})
    
    def on_box_width_changed(self):
        """Handle box width spin box change."""
        self.config.box_width = self.width_spin.value()
        self.settings_changed.emit({"box_width": self.config.box_width})

    def on_box_height_changed(self):
        """Handle box height spin box change."""
        self.config.box_height = self.height_spin.value()
        self.settings_changed.emit({"box_height": self.config.box_height})

    def on_update_rate_changed(self):
        """Handle update rate spin box change."""
        self.config.update_rate = self.rate_spin.value()
        self.settings_changed.emit({"update_rate": self.config.update_rate})

    def on_show_crosshair_changed(self, state):
        """Handle show crosshair checkbox change."""
        self.config.show_crosshair = self.crosshair_check.isChecked()
        self.settings_changed.emit({"show_crosshair": self.config.show_crosshair})

    def on_follow_mouse_changed(self, state):
        """Handle follow mouse checkbox change and update button state."""
        self.config.follow_mouse = self.follow_mouse_check.isChecked()
        self.settings_changed.emit({"follow_mouse": self.config.follow_mouse})
        # Enable/disable snap to center button based on follow mouse setting
        if self.follow_mouse_check.isChecked():
            self.center_btn.setText("Snap to Center")
            self.center_btn.setEnabled(False)  # Disabled when following mouse
        else:
            self.center_btn.setText("Snap to Center")
            self.center_btn.setEnabled(True)   # Enabled when not following mouse

    def snap_to_center(self):
        """Request snap to center"""
        self.snap_to_center_requested.emit()
    
    def toggle_magnifier(self):
        """Toggle magnifier and update UI"""
        self.toggle_requested.emit()
    
    def update_status(self, is_active: bool):
        """Update the status display"""
        if is_active:
            self.status_label.setText("Status: ON")
            self.toggle_btn.setText("STOP")
            self.toggle_btn.setStyleSheet("background-color: #ff4444;")
        else:
            self.status_label.setText("Status: OFF")
            self.toggle_btn.setText("START")
            self.toggle_btn.setStyleSheet("background-color: #44ff44;")
    
    def closeEvent(self, event):
        """Override close event to terminate the program"""
        event.ignore() # Prevent default close
        self.quit_requested.emit() # Emit signal to main app to quit

    def handle_mouse_press(self, button):
        """Handle mouse press events"""
        if str(button) == self.config.hotkey:
            self.toggle_requested.emit()


class UnifiedHotkeyRecorderDialog(QDialog):
    """Dialog for recording custom hotkeys"""
    
    def __init__(self, current_hotkey: str, parent=None):
        super().__init__(parent)
        self.current_hotkey = current_hotkey
        self.recorded_hotkey = current_hotkey
        self.setup_ui()
        self.mouse_listener = None
        
    def setup_ui(self):
        """Setup the hotkey recorder UI"""
        self.setWindowTitle("Record Hotkey")
        self.setFixedSize(300, 150)
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel("Press any key combination or click a mouse button...")
        instructions.setAlignment(Qt.AlignCenter)
        layout.addWidget(instructions)
        
        # Current hotkey display
        self.hotkey_label = QLabel(f"Current: {self.current_hotkey}")
        self.hotkey_label.setAlignment(Qt.AlignCenter)
        self.hotkey_label.setStyleSheet("font-weight: bold; color: blue;")
        layout.addWidget(self.hotkey_label)
        
        # Recording status
        self.status_label = QLabel("Click 'Start Recording' to begin")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.record_btn = QPushButton("Start Recording")
        self.record_btn.clicked.connect(self.start_recording)
        button_layout.addWidget(self.record_btn)
        
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setEnabled(False)
        button_layout.addWidget(self.ok_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        self.recording = False
        self.recording_thread = None
    
    def start_recording(self):
        """Start recording hotkey"""
        if not self.recording:
            self.recording = True
            self.record_btn.setText("Recording...")
            self.record_btn.setEnabled(False)
            self.status_label.setText("Press any key combination or click a mouse button...")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")

            # Start recording in separate threads
            self.mouse_listener = mouse.Listener(on_click=self.on_click)
            self.mouse_listener.start()
            self.recording_thread = threading.Thread(target=self._record_hotkey, daemon=True)
            self.recording_thread.start()
    
    def _record_hotkey(self):
        """Record hotkey in background thread"""
        try:
            # Wait for key combination
            event = keyboard.read_event()
            if event.event_type == keyboard.KEY_DOWN:
                if self.mouse_listener:
                    self.mouse_listener.stop()
                # Get the key combination
                keys = []
                if keyboard.is_pressed('ctrl'):
                    keys.append('ctrl')
                if keyboard.is_pressed('alt'):
                    keys.append('alt')
                if keyboard.is_pressed('shift'):
                    keys.append('shift')
                if keyboard.is_pressed('win'):
                    keys.append('win')
                
                # Add the main key
                if event.name and event.name not in ['ctrl', 'alt', 'shift', 'win']:
                    keys.append(event.name)
                
                if keys:
                    self.recorded_hotkey = '+'.join(keys)
                    # Update UI in main thread
                    self.status_label.setText(f"Recorded: {self.recorded_hotkey}")
                    self.status_label.setStyleSheet("color: green; font-weight: bold;")
                    self.hotkey_label.setText(f"New: {self.recorded_hotkey}")
                    self.ok_btn.setEnabled(True)
                    self.record_btn.setText("Record Again")
                    self.record_btn.setEnabled(True)
                    self.recording = False
        except Exception as e:
            print(f"Error recording hotkey: {e}")
            self.recording = False

    def on_click(self, x, y, button, pressed):
        """Handle mouse click events"""
        if pressed:
            self.recorded_hotkey = str(button)
            self.hotkey_label.setText(f"New: {self.recorded_hotkey}")
            self.ok_btn.setEnabled(True)
            self.record_btn.setText("Record Again")
            self.record_btn.setEnabled(True)
            self.recording = False
            if self.mouse_listener:
                self.mouse_listener.stop()

    
    def get_hotkey(self) -> str:
        """Get the recorded hotkey"""
        return self.recorded_hotkey




class AdvancedSettingsDialog(QDialog):
    """Advanced settings dialog with tabs"""
    
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        """Setup the advanced settings UI"""
        self.setWindowTitle("Advanced Settings")
        self.setFixedSize(500, 600)
        self.setModal(False)
        
        layout = QVBoxLayout()
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Performance tab
        self.performance_tab = self.create_performance_tab()
        self.tab_widget.addTab(self.performance_tab, "Performance")
        
        # Visual tab
        self.visual_tab = self.create_visual_tab()
        self.tab_widget.addTab(self.visual_tab, "Visual")
        
        # Crosshair tab
        self.crosshair_tab = self.create_crosshair_tab()
        self.tab_widget.addTab(self.crosshair_tab, "Crosshair")
        
        # Behavior tab
        self.behavior_tab = self.create_behavior_tab()
        self.tab_widget.addTab(self.behavior_tab, "Behavior")
        
        layout.addWidget(self.tab_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # self.apply_btn = QPushButton("Apply")
        # self.apply_btn.clicked.connect(self.apply_settings)
        # button_layout.addWidget(self.apply_btn)
        
        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(self.reset_btn)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def create_performance_tab(self):
        """Create performance settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Interpolation mode
        interpolation_group = QGroupBox("Image Quality")
        interpolation_layout = QGridLayout()
        
        interpolation_layout.addWidget(QLabel("Interpolation Mode:"), 0, 0)
        self.interpolation_combo = QComboBox()
        self.interpolation_combo.addItems(["nearest", "linear", "cubic"])
        self.interpolation_combo.currentTextChanged.connect(self.on_interpolation_mode_changed)
        interpolation_layout.addWidget(self.interpolation_combo, 0, 1)
        
        interpolation_layout.addWidget(QLabel("Capture Quality:"), 1, 0)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["low", "medium", "high"])
        self.quality_combo.currentTextChanged.connect(self.on_capture_quality_changed)
        interpolation_layout.addWidget(self.quality_combo, 1, 1)
        
        interpolation_group.setLayout(interpolation_layout)
        layout.addWidget(interpolation_group)
        
        # Performance options
        performance_group = QGroupBox("Performance Options")
        performance_layout = QVBoxLayout()
        
        self.performance_mode_check = QCheckBox("Enable Performance Mode")
        self.performance_mode_check.stateChanged.connect(self.on_performance_mode_changed)
        performance_layout.addWidget(self.performance_mode_check)
        
        self.smooth_movement_check = QCheckBox("Enable Smooth Movement")
        self.smooth_movement_check.stateChanged.connect(self.on_smooth_movement_changed)
        performance_layout.addWidget(self.smooth_movement_check)
        
        self.debug_mode_check = QCheckBox("Enable Debug Mode")
        self.debug_mode_check.stateChanged.connect(self.on_debug_mode_changed)
        performance_layout.addWidget(self.debug_mode_check)
        
        performance_group.setLayout(performance_layout)
        layout.addWidget(performance_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_visual_tab(self):
        """Create visual settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Overlay settings
        overlay_group = QGroupBox("Overlay Settings")
        overlay_layout = QGridLayout()
        
        overlay_layout.addWidget(QLabel("Opacity:"), 0, 0)
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(50, 100)
        self.opacity_slider.valueChanged.connect(self.on_overlay_opacity_changed)
        overlay_layout.addWidget(self.opacity_slider, 0, 1)
        
        self.opacity_label = QLabel("99%")
        overlay_layout.addWidget(self.opacity_label, 0, 2)
        
        overlay_layout.addWidget(QLabel("Border Color:"), 1, 0)
        self.border_color_btn = QPushButton("Choose Color")
        self.border_color_btn.clicked.connect(self.on_border_color_changed)
        overlay_layout.addWidget(self.border_color_btn, 1, 1)
        
        self.border_glow_check = QCheckBox("Enable Border Glow")
        self.border_glow_check.stateChanged.connect(self.on_enable_border_glow_changed)
        overlay_layout.addWidget(self.border_glow_check, 2, 0, 1, 2)
        
        overlay_group.setLayout(overlay_layout)
        layout.addWidget(overlay_group)
        
        # Visual feedback
        feedback_group = QGroupBox("Visual Feedback")
        feedback_layout = QVBoxLayout()
        
        self.visual_feedback_check = QCheckBox("Enable Visual Feedback")
        self.visual_feedback_check.stateChanged.connect(self.on_enable_visual_feedback_changed)
        feedback_layout.addWidget(self.visual_feedback_check)
        
        self.capture_highlight_check = QCheckBox("Highlight Capture Region")
        self.capture_highlight_check.stateChanged.connect(self.on_enable_capture_region_highlight_changed)
        feedback_layout.addWidget(self.capture_highlight_check)
        
        feedback_group.setLayout(feedback_layout)
        layout.addWidget(feedback_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_crosshair_tab(self):
        """Create crosshair settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Crosshair settings
        crosshair_group = QGroupBox("Crosshair Settings")
        crosshair_layout = QGridLayout()
        
        crosshair_layout.addWidget(QLabel("Color:"), 0, 0)
        self.crosshair_color_btn = QPushButton("Choose Color")
        self.crosshair_color_btn.clicked.connect(self.on_crosshair_color_changed)
        crosshair_layout.addWidget(self.crosshair_color_btn, 0, 1)
        
        crosshair_layout.addWidget(QLabel("Size:"), 1, 0)
        self.crosshair_size_spin = QSpinBox()
        self.crosshair_size_spin.setRange(5, 50)
        self.crosshair_size_spin.valueChanged.connect(self.on_crosshair_size_changed)
        crosshair_layout.addWidget(self.crosshair_size_spin, 1, 1)
        
        crosshair_layout.addWidget(QLabel("Thickness:"), 2, 0)
        self.crosshair_thickness_spin = QSpinBox()
        self.crosshair_thickness_spin.setRange(1, 5)
        self.crosshair_thickness_spin.valueChanged.connect(self.on_crosshair_thickness_changed)
        crosshair_layout.addWidget(self.crosshair_thickness_spin, 2, 1)
        
        self.center_dot_check = QCheckBox("Show Center Dot")
        self.center_dot_check.stateChanged.connect(self.on_enable_center_dot_changed)
        crosshair_layout.addWidget(self.center_dot_check, 3, 0, 1, 2)
        
        crosshair_group.setLayout(crosshair_layout)
        layout.addWidget(crosshair_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_behavior_tab(self):
        """Create behavior settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Auto-hide settings
        autohide_group = QGroupBox("Auto-Hide Settings")
        autohide_layout = QGridLayout()
        
        self.auto_hide_check = QCheckBox("Enable Auto-Hide")
        self.auto_hide_check.stateChanged.connect(self.on_enable_auto_hide_changed)
        autohide_layout.addWidget(self.auto_hide_check, 0, 0, 1, 2)
        
        autohide_layout.addWidget(QLabel("Delay (seconds):"), 1, 0)
        self.auto_hide_delay_spin = QDoubleSpinBox()
        self.auto_hide_delay_spin.setRange(1.0, 10.0)
        self.auto_hide_delay_spin.setSingleStep(0.5)
        self.auto_hide_delay_spin.valueChanged.connect(self.on_auto_hide_delay_changed)
        autohide_layout.addWidget(self.auto_hide_delay_spin, 1, 1)
        
        autohide_group.setLayout(autohide_layout)
        layout.addWidget(autohide_group)
        
        # Sound feedback
        sound_group = QGroupBox("Sound Feedback")
        sound_layout = QVBoxLayout()
        
        self.sound_feedback_check = QCheckBox("Enable Sound Feedback")
        self.sound_feedback_check.stateChanged.connect(self.on_enable_sound_feedback_changed)
        sound_layout.addWidget(self.sound_feedback_check)
        
        sound_group.setLayout(sound_layout)
        layout.addWidget(sound_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def load_settings(self):
        """Load current settings into UI"""
        # Performance settings
        self.interpolation_combo.setCurrentText(self.config.get("interpolation_mode", "nearest"))
        self.quality_combo.setCurrentText(self.config.get("capture_quality", "high"))
        self.performance_mode_check.setChecked(self.config.get("enable_performance_mode", False))
        self.smooth_movement_check.setChecked(self.config.get("enable_smooth_movement", True))
        self.debug_mode_check.setChecked(self.config.get("enable_debug_mode", False))
        
        # Visual settings
        opacity = int(self.config.get("overlay_opacity", 0.99) * 100)
        self.opacity_slider.setValue(opacity)
        self.opacity_label.setText(f"{opacity}%")
        self.border_glow_check.setChecked(self.config.get("enable_border_glow", False))
        self.visual_feedback_check.setChecked(self.config.get("enable_visual_feedback", True))
        self.capture_highlight_check.setChecked(self.config.get("enable_capture_region_highlight", False))
        
        # Crosshair settings
        self.crosshair_size_spin.setValue(self.config.get("crosshair_size", 20))
        self.crosshair_thickness_spin.setValue(self.config.get("crosshair_thickness", 2))
        self.center_dot_check.setChecked(self.config.get("enable_center_dot", True))
        
        # Behavior settings
        self.auto_hide_check.setChecked(self.config.get("enable_auto_hide", False))
        self.auto_hide_delay_spin.setValue(self.config.get("auto_hide_delay", 3.0))
        self.sound_feedback_check.setChecked(self.config.get("enable_sound_feedback", False))
    
    def on_setting_changed(self):
        """Handle setting changes"""
        self.on_advanced_setting_changed()
    
    def on_overlay_opacity_changed(self, value: int):
        """Handle overlay opacity slider change."""
        self.config.overlay_opacity = value / 100.0
        self.opacity_label.setText(f"{value}%")
        self.settings_changed.emit({"overlay_opacity": self.config.overlay_opacity})

    def on_border_color_changed(self):
        """Handle border color button click."""
        color = QColorDialog.getColor(QColor(self.config.border_color), self)
        if color.isValid():
            self.config.border_color = color.name()
            self.settings_changed.emit({"border_color": self.config.border_color})

    def on_enable_border_glow_changed(self, state: int):
        """Handle enable border glow checkbox change."""
        self.config.enable_border_glow = self.border_glow_check.isChecked()
        self.settings_changed.emit({"enable_border_glow": self.config.enable_border_glow})

    def on_enable_visual_feedback_changed(self, state: int):
        """Handle enable visual feedback checkbox change."""
        self.config.enable_visual_feedback = self.visual_feedback_check.isChecked()
        self.settings_changed.emit({"enable_visual_feedback": self.config.enable_visual_feedback})

    def on_enable_capture_region_highlight_changed(self, state: int):
        """Handle enable capture region highlight checkbox change."""
        self.config.enable_capture_region_highlight = self.capture_highlight_check.isChecked()
        self.settings_changed.emit({"enable_capture_region_highlight": self.config.enable_capture_region_highlight})

    def on_crosshair_color_changed(self):
        """Handle crosshair color button click."""
        color = QColorDialog.getColor(QColor(self.config.crosshair_color), self)
        if color.isValid():
            self.config.crosshair_color = color.name()
            self.settings_changed.emit({"crosshair_color": self.config.crosshair_color})

    def on_crosshair_size_changed(self, value: int):
        """Handle crosshair size spin box change."""
        self.config.crosshair_size = value
        self.settings_changed.emit({"crosshair_size": self.config.crosshair_size})

    def on_crosshair_thickness_changed(self, value: int):
        """Handle crosshair thickness spin box change."""
        self.config.crosshair_thickness = value
        self.settings_changed.emit({"crosshair_thickness": self.config.crosshair_thickness})

    def on_enable_center_dot_changed(self, state: int):
        """Handle enable center dot checkbox change."""
        self.config.enable_center_dot = self.center_dot_check.isChecked()
        self.settings_changed.emit({"enable_center_dot": self.config.enable_center_dot})

    def on_enable_auto_hide_changed(self, state: int):
        """Handle enable auto hide checkbox change."""
        self.config.enable_auto_hide = self.auto_hide_check.isChecked()
        self.settings_changed.emit({"enable_auto_hide": self.config.enable_auto_hide})

    def on_auto_hide_delay_changed(self, value: float):
        """Handle auto hide delay spin box change."""
        self.config.auto_hide_delay = value
        self.settings_changed.emit({"auto_hide_delay": self.config.auto_hide_delay})

    def on_enable_sound_feedback_changed(self, state: int):
        """Handle enable sound feedback checkbox change."""
        self.config.enable_sound_feedback = self.sound_feedback_check.isChecked()
        self.settings_changed.emit({"enable_sound_feedback": self.config.enable_sound_feedback})
    
    def on_interpolation_mode_changed(self, text: str):
        """Handle interpolation mode change."""
        self.config.interpolation_mode = text
        self.settings_changed.emit({"interpolation_mode": text})
    
    def on_capture_quality_changed(self, text: str):
        """Handle capture quality change."""
        self.config.capture_quality = text
        self.settings_changed.emit({"capture_quality": text})
    
    def on_performance_mode_changed(self, state: int):
        """Handle performance mode checkbox change."""
        self.config.enable_performance_mode = self.performance_mode_check.isChecked()
        self.settings_changed.emit({"enable_performance_mode": self.config.enable_performance_mode})

    def on_smooth_movement_changed(self, state: int):
        """Handle smooth movement checkbox change."""
        self.config.enable_smooth_movement = self.smooth_movement_check.isChecked()
        self.settings_changed.emit({"enable_smooth_movement": self.config.enable_smooth_movement})

    def on_debug_mode_changed(self, state: int):
        """Handle debug mode checkbox change."""
        self.config.enable_debug_mode = self.debug_mode_check.isChecked()
        self.settings_changed.emit({"enable_debug_mode": self.config.enable_debug_mode})
    
    def reset_to_defaults(self):
        """Reset all settings to defaults, save, and notify"""
        reply = QMessageBox.question(self, "Reset Settings",
                                   "Are you sure you want to reset all advanced settings to defaults?",
                                   QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            # Use the config method to reset, which also saves
            self.config.reset_to_defaults()
            self.load_settings()
            # Emit a signal with all default settings so main app updates
            self.settings_changed.emit(self.config.DEFAULT_CONFIG.copy())
            QMessageBox.information(self, "Settings Reset", "All settings have been reset to defaults!")