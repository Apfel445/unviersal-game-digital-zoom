#!/usr/bin/env python3
"""
Simple Global Screen Magnifier - Cleaned up version
A lightweight screen magnifier with GSautoclicker-style GUI
"""

import sys
import time
import signal
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtCore import QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QCursor
import keyboard
import threading

from config import Config
from screen_capture import ScreenCapture
from magnifier_gui import MagnifierOverlay, MagnifierControlPanel


import logging

logging.basicConfig(filename='magnifier.log', level=logging.ERROR)

class HotkeyThread(QThread):
    """
    A separate thread to handle global hotkey detection without blocking the main GUI.
    Uses the 'keyboard' library to listen for key presses system-wide.
    This thread is designed to be stopped and started anew on hotkey changes.
    """
    
    hotkey_pressed = pyqtSignal()
    
    def __init__(self, hotkeys: list):
        """
        Initializes the hotkey thread.
        Args:
            hotkeys: A list of keyboard hotkey strings to listen for.
        """
        super().__init__()
        self.hotkeys = hotkeys
        self.running = True
        self._handlers = []

    def run(self):
        """
        Registers the hotkeys and enters a loop to keep the thread alive.
        """
        try:
            for hotkey in self.hotkeys:
                handler = keyboard.add_hotkey(hotkey, self.on_hotkey_pressed)
                self._handlers.append(handler)
            
            while self.running:
                time.sleep(0.1)
                
        except (ValueError, ImportError, NotImplementedError) as e:
            logging.error(f"Error setting up keyboard hotkeys: {e}")
            # Silently fail if hotkeys can't be set (e.g., no permissions)
        finally:
            self._cleanup()

    def on_hotkey_pressed(self):
        """
        Callback for when a hotkey is pressed. Emits a signal to the main thread.
        """
        if self.running:
            self.hotkey_pressed.emit()

    def _cleanup(self):
        """Unregister all hotkeys managed by this thread."""
        for handler in self._handlers:
            keyboard.remove_hotkey(handler)
        self._handlers.clear()

    def stop(self):
        """
        Stops the hotkey listener thread gracefully.
        """
        self.running = False
        # Do not wait() here to avoid blocking the GUI thread.
        # The thread will exit naturally when `run` completes its loop.


class ScreenMagnifierApp:
    """Main application class for the screen magnifier"""
    
    def __init__(self):
        """
        Initializes the main application.
        Sets up the GUI, signal handlers, hotkeys, and timers.
        """
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Initialize components
        self.config = Config()
        self.screen_capture = ScreenCapture()
        
        # GUI components
        self.magnifier_overlay = MagnifierOverlay(self.config)
        self.control_panel = MagnifierControlPanel(self.config)
        
        # System tray
        self.setup_system_tray()
        
        # Hotkey thread
        self.hotkey_thread = None
        self.setup_hotkey()
        
        # Update timer for real-time magnification
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_magnifier)
        
        # Connect signals from the control panel to the main application
        self.control_panel.settings_changed.connect(self.on_settings_changed)
        self.control_panel.toggle_requested.connect(self.toggle_magnifier)
        self.control_panel.quit_requested.connect(self.quit_application)
        self.control_panel.snap_to_center_requested.connect(self.snap_to_center)
        
        # Fixed position for snap to center mode
        self.fixed_position = None
        
        # Show control panel
        self.control_panel.show()
        
        print("Screen Magnifier started!")
        print(f"Hotkey: {self.config.hotkey}")
        
        # Initialize the update rate after config is fully loaded
        self.on_settings_changed({"update_rate": self.config.update_rate})
    
    def signal_handler(self, sig, frame):
        """Handle Ctrl+C and other signals"""
        print(f"\nReceived signal {sig}. Shutting down...")
        self.quit_application()

    def setup_system_tray(self):
        """Setup system tray icon and menu"""
        self.tray_icon = QSystemTrayIcon()
        
        # Create simple icon
        pixmap = QPixmap(16, 16)
        pixmap.fill()
        icon = QIcon(pixmap)
        self.tray_icon.setIcon(icon)
        
        # Create context menu
        tray_menu = QMenu()
        
        # Show control panel action
        show_action = QAction("Show Control Panel", self.app)
        show_action.triggered.connect(self.show_control_panel)
        tray_menu.addAction(show_action)
        
        # Toggle action
        self.toggle_action = QAction("Toggle Magnifier", self.app)
        self.toggle_action.triggered.connect(self.toggle_magnifier)
        tray_menu.addAction(self.toggle_action)
        
        tray_menu.addSeparator()
        
        # Quit action
        quit_action = QAction("Quit", self.app)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        # Handle tray icon activation
        self.tray_icon.activated.connect(self.on_tray_activated)
    
    def setup_hotkey(self):
        """
        Sets up the global hotkey listener.
        Creates a new HotkeyThread and starts it.
        """
        if self.hotkey_thread:
            self.hotkey_thread.stop()
        
        hotkeys = [self.config.hotkey]
        
        # The keyboard library only handles keyboard hotkeys, so we filter out mouse buttons.
        keyboard_hotkeys = [hk for hk in hotkeys if not hk.startswith("Button.")]
        
        self.hotkey_thread = HotkeyThread(keyboard_hotkeys)
        self.hotkey_thread.hotkey_pressed.connect(self.toggle_magnifier)
        self.hotkey_thread.start()
    
    def toggle_magnifier(self):
        """
        Toggles the magnifier on or off.
        This method is called when a hotkey is pressed.
        """
        if self.magnifier_overlay.is_active:
            self.stop_magnification()
        else:
            self.start_magnification()
        
        # Update control panel status
        self.control_panel.update_status(self.magnifier_overlay.is_active)
    
    def start_magnification(self):
        """Start the magnification process"""
        self.magnifier_overlay.show_magnifier()
        # Use the configured update rate directly
        interval = 1000 // self.config.update_rate
        self.update_timer.setInterval(interval)
        self.update_timer.start()
    
    def stop_magnification(self):
        """Stop the magnification process with minimal overhead"""
        # Stop timer immediately
        self.update_timer.stop()
        
        # Hide overlay instantly
        self.magnifier_overlay.hide_magnifier()
    
    def update_magnifier(self):
        """
        This is the main loop for the magnifier.
        It captures the screen, scales the image, and updates the overlay.
        """
        if not self.magnifier_overlay.is_active:
            return
        
        # Get current settings using properties
        box_width = self.config.box_width
        box_height = self.config.box_height
        zoom_level = self.config.zoom_level
        show_crosshair = self.config.show_crosshair
        follow_mouse = self.config.follow_mouse
        
        # Capture and process image
        captured_image = self.capture_screen_data(box_width, box_height)
        
        if captured_image is not None:
            self.update_display_layer(captured_image, zoom_level, show_crosshair, follow_mouse)
    
    def capture_screen_data(self, box_width: int, box_height: int):
        """LAYER 1: Pure screen capture system - completely independent of overlay"""
        # This system operates in complete isolation from the display layer
        # It simply captures the screen around the cursor position
        # No knowledge of overlay, no hiding/showing, no interference checking
        return self.screen_capture.capture_around_cursor(box_width, box_height)
    
    def update_display_layer(self, raw_image, zoom_level: float, show_crosshair: bool, follow_mouse: bool):
        """LAYER 2: Pure display system - handles the isolated overlay window"""
        # Get advanced settings using properties
        interpolation_mode = self.config.interpolation_mode
        
        # Scale the image FIRST (without crosshair)
        scaled_image = self.screen_capture.scale_image(raw_image, zoom_level, interpolation_mode)
        
        # Add crosshair AFTER scaling so it stays normal size on top
        if show_crosshair:
            # Get crosshair settings from config using properties
            crosshair_config = {
                "crosshair_size": self.config.crosshair_size,
                "crosshair_thickness": self.config.crosshair_thickness,
                "crosshair_color": self.config.crosshair_color,
                "enable_center_dot": self.config.enable_center_dot
            }
            scaled_image = self.screen_capture.add_crosshair(scaled_image, crosshair_config)
        
        # Update the isolated overlay display
        self.magnifier_overlay.update_display(scaled_image)
        
        # Position the overlay (no interference checking needed due to layer separation)
        self.position_overlay_cleanly(follow_mouse)
    
    def position_overlay_cleanly(self, follow_mouse: bool):
        """Position the overlay efficiently"""
        if follow_mouse:
            cursor_pos = QCursor.pos()
            overlay_width = self.magnifier_overlay.width()
            overlay_height = self.magnifier_overlay.height()
            new_x = cursor_pos.x() - overlay_width // 2
            new_y = cursor_pos.y() - overlay_height // 2
            self.magnifier_overlay.move(new_x, new_y)
        else:
            if self.fixed_position is None:
                self.snap_to_center()
    
    def snap_to_center(self):
        """Snap magnifier to center of monitor"""
        center_x, center_y = self.screen_capture.get_monitor_center()
        overlay_width = self.magnifier_overlay.width()
        overlay_height = self.magnifier_overlay.height()
        
        # Center the overlay on the monitor
        new_x = center_x - overlay_width // 2
        new_y = center_y - overlay_height // 2
        
        # Keep on screen
        screen_geometry = self.app.primaryScreen().geometry()
        new_x = max(0, min(new_x, screen_geometry.width() - overlay_width))
        new_y = max(0, min(new_y, screen_geometry.height() - overlay_height))
        
        # Update fixed position and move overlay
        self.fixed_position = (new_x, new_y)
        if self.magnifier_overlay.is_active:
            self.magnifier_overlay.move(new_x, new_y)
        
        # Set follow_mouse to False and update the UI
        self.config.follow_mouse = False
        self.control_panel.load_settings()
        print("Magnifier snapped to center")
    
    def show_control_panel(self):
        """Show the control panel"""
        self.control_panel.show()
        self.control_panel.raise_()
        self.control_panel.activateWindow()
    
    def on_settings_changed(self, new_settings: dict):
        """Handle settings changes"""
        self.config.update(new_settings)

        # Force the control panel to reload its widgets to reflect the new state
        self.control_panel.load_settings()
        
        # Update hotkeys if hotkey settings changed
        if "hotkey" in new_settings:
            self.setup_hotkey()
        
        if "update_rate" in new_settings:
            # Ensure the timer interval is immediately updated if the update_rate changes
            self.update_timer.setInterval(1000 // self.config.update_rate)
        
        if "follow_mouse" in new_settings:
            if new_settings["follow_mouse"]:
                self.fixed_position = None
                print("Switched to follow mouse mode")
            else:
                print("Switched to fixed position mode")
        
        print("Settings updated!")
    
    def on_tray_activated(self, reason):
        """Handle system tray icon activation"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_control_panel()
    
    def quit_application(self):
        """Quit the application"""
        print("Shutting down...")
        
        # Stop hotkey thread
        if self.hotkey_thread:
            self.hotkey_thread.stop()
        
        # Stop timers
        self.update_timer.stop()
        
        # Clean up screen capture
        if hasattr(self, 'screen_capture'):
            self.screen_capture.cleanup()
        
        # Hide windows
        self.magnifier_overlay.hide()
        self.control_panel.hide()
        
        # Hide system tray
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
        
        # Quit application
        self.app.quit()
        sys.exit(0)
    
    def run(self):
        """Run the application"""
        return self.app.exec_()


def run_magnifier_app():
    """Main entry point"""
    try:
        app = ScreenMagnifierApp()
        
        # Timer to allow Ctrl+C to work
        timer = QTimer()
        timer.start(500)
        timer.timeout.connect(lambda: None)
        
        return app.run()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(run_magnifier_app())