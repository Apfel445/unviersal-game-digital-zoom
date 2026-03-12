import mss
import numpy as np
import cv2
from PyQt5.QtGui import QCursor
from typing import Tuple, Optional

class ScreenCapture:
    """Simplified screen capture for magnifier"""

    # Map interpolation mode strings to OpenCV constants once at class level
    # to avoid rebuilding this dict on every call to scale_image().
    _INTERPOLATION_MAP = {
        "nearest": cv2.INTER_NEAREST,
        "linear": cv2.INTER_LINEAR,
        "cubic": cv2.INTER_CUBIC,
    }

    def __init__(self):
        self.sct = mss.mss()
        self.monitors = self.sct.monitors
        # Cache hex color strings → BGR tuples to avoid re-parsing every frame.
        self._color_cache: dict[str, tuple[int, int, int]] = {}
    
    def cleanup(self):
        """Clean up screen capture resources"""
        if hasattr(self, 'sct') and self.sct:
            self.sct.close()
    
    def get_cursor_position(self) -> Tuple[int, int]:
        """Get current cursor position"""
        cursor_pos = QCursor.pos()
        return cursor_pos.x(), cursor_pos.y()
    
    def capture_around_cursor(self, box_width: int, box_height: int) -> Optional[np.ndarray]:
        """Capture screen region around cursor with boundary checking and anti-self-capture"""
        try:
            cursor_x, cursor_y = self.get_cursor_position()
            
            # Calculate capture area centered on cursor
            half_width = box_width // 2
            half_height = box_height // 2
            
            left = cursor_x - half_width
            top = cursor_y - half_height
            
            # Find which monitor contains the cursor for boundary checking
            monitor = self.get_monitor_containing_point(cursor_x, cursor_y)
            if monitor:
                # Clamp capture region to monitor bounds to prevent issues
                left = max(monitor["left"], min(left, monitor["left"] + monitor["width"] - box_width))
                top = max(monitor["top"], min(top, monitor["top"] + monitor["height"] - box_height))
            
            # Ensure we have valid dimensions
            if box_width <= 0 or box_height <= 0:
                return None
            
            # Create capture region with exact coordinates
            region = {
                "left": int(left),
                "top": int(top),
                "width": int(box_width),
                "height": int(box_height)
            }
            
            # Capture the screen region with optimized settings
            screenshot = self.sct.grab(region)
            
            # Convert to numpy array (BGRA -> BGR) with optimized conversion
            img = np.array(screenshot, dtype=np.uint8)
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            
            return img
        except Exception as e:
            print(f"Error capturing screen: {e}")
            return None
    
    def get_monitor_containing_point(self, x: int, y: int) -> Optional[dict]:
        """Find which monitor contains the given point"""
        for monitor in self.monitors[1:]:  # Skip the "All in One" monitor at index 0
            if (monitor["left"] <= x < monitor["left"] + monitor["width"] and
                monitor["top"] <= y < monitor["top"] + monitor["height"]):
                return monitor
        return None
    
    def scale_image(self, image: np.ndarray, zoom_level: float, interpolation_mode: str = "nearest") -> np.ndarray:
        """Scale image using specified interpolation mode with performance optimizations"""
        if image is None:
            return None
        
        # Skip scaling if zoom level is 1.0 (no change needed).
        # Return the original reference; add_crosshair() will copy it if needed.
        if abs(zoom_level - 1.0) < 0.01:
            return image
        
        height, width = image.shape[:2]
        new_width = int(width * zoom_level)
        new_height = int(height * zoom_level)
        
        # Map interpolation mode to OpenCV constant using the class-level constant.
        interpolation = self._INTERPOLATION_MAP.get(interpolation_mode, cv2.INTER_NEAREST)
        
        # Use optimized resize for better performance
        scaled = cv2.resize(image, (new_width, new_height), interpolation=interpolation)
        return scaled
    
    def add_crosshair(self, image: np.ndarray, config: dict = None) -> np.ndarray:
        """Add crosshair to center of image with configurable settings"""
        if image is None:
            return image
        
        if config is None:
            config = {}
        
        image_copy = image.copy()
        h, w = image_copy.shape[:2]
        center_x, center_y = w // 2, h // 2
        
        # Get crosshair settings from config or use defaults
        crosshair_size = config.get("crosshair_size", 20)
        crosshair_thickness = config.get("crosshair_thickness", 2)
        crosshair_color = config.get("crosshair_color", "#00FF00")
        enable_center_dot = config.get("enable_center_dot", True)
        
        # Convert hex color to BGR, using the cache to avoid re-parsing every frame.
        if crosshair_color not in self._color_cache:
            color_hex = crosshair_color.lstrip('#')
            color_rgb = tuple(int(color_hex[i:i+2], 16) for i in (0, 2, 4))
            self._color_cache[crosshair_color] = (color_rgb[2], color_rgb[1], color_rgb[0])
        color_bgr = self._color_cache[crosshair_color]
        
        # Limit crosshair size to image bounds
        crosshair_size = min(crosshair_size, min(w, h) // 4)
        
        # Draw crosshair lines
        cv2.line(image_copy, 
                (center_x - crosshair_size, center_y), 
                (center_x + crosshair_size, center_y), 
                color_bgr, crosshair_thickness)
        cv2.line(image_copy, 
                (center_x, center_y - crosshair_size), 
                (center_x, center_y + crosshair_size), 
                color_bgr, crosshair_thickness)
        
        # Add center dot if enabled
        if enable_center_dot:
            dot_radius = max(1, crosshair_thickness // 2)
            cv2.circle(image_copy, (center_x, center_y), dot_radius, color_bgr, -1)
        
        return image_copy
    
    def get_monitor_center(self) -> Tuple[int, int]:
        """Get the center coordinates of the primary monitor"""
        # Use the first monitor (index 0 is 'All in One', index 1 is primary)
        primary = self.monitors[1] if len(self.monitors) > 1 else self.monitors[0]
        center_x = primary["left"] + primary["width"] // 2
        center_y = primary["top"] + primary["height"] // 2
        return center_x, center_y

    def is_fullscreen(self) -> bool:
        """Check if the foreground window is fullscreen"""
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            
            # Get screen resolution
            screen_width = user32.GetSystemMetrics(0)
            screen_height = user32.GetSystemMetrics(1)
            
            # Check if window size matches screen size
            return (rect.left == 0 and rect.top == 0 and
                    rect.right == screen_width and rect.bottom == screen_height)
        except Exception:
            return False