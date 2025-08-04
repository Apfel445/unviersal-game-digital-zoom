import json
import os
from typing import Dict, Any

class Config:
    """Global configuration manager with automatic syncing"""
    
    # Global instance
    _instance = None
    
    # Default configuration values
    DEFAULT_CONFIG = {
        "hotkey": "ctrl+alt+z",
        "update_rate": 60,
        "box_width": 200,
        "box_height": 100,
        "zoom_level": 2.5,
        "show_crosshair": True,
        "border_color": "#FF0000",
        "border_width": 2,
        "follow_mouse": True,
        "snap_to_center": False,
        # Advanced settings
        "interpolation_mode": "nearest",  # nearest, linear, cubic
        "capture_quality": "high",  # low, medium, high
        "overlay_opacity": 0.99,
        "enable_smooth_movement": True,
        "enable_auto_hide": False,
        "auto_hide_delay": 3.0,  # seconds
        "enable_sound_feedback": False,
        "enable_visual_feedback": True,
        "crosshair_color": "#00FF00",
        "crosshair_size": 20,
        "crosshair_thickness": 2,
        "enable_center_dot": True,
        "enable_border_glow": False,
        "border_glow_color": "#FFFF00",
        "enable_capture_region_highlight": False,
        "highlight_color": "#FF00FF",
        "enable_performance_mode": True,
        "enable_debug_mode": False
    }
    
    def __new__(cls, config_file: str = "magnifier_config.json"):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_file: str = "magnifier_config.json"):
        if self._initialized:
            return
        
        self.config_file = config_file
        self.settings = self.load_config()
        self._initialized = True
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                config = self.DEFAULT_CONFIG.copy()
                config.update(loaded_config)
                return config
            except (json.JSONDecodeError, IOError):
                print(f"Error loading config, using defaults")
                return self.DEFAULT_CONFIG.copy()
        else:
            return self.DEFAULT_CONFIG.copy()
    
    def save_config(self) -> bool:
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            return True
        except IOError as e:
            print(f"Error saving config: {e}")
            return False
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value and save immediately"""
        self.settings[key] = value
        self.save_config()
    
    def update(self, new_settings: Dict[str, Any]):
        """Update multiple settings at once and save immediately"""
        self.settings.update(new_settings)
        self.save_config()
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        self.settings = self.DEFAULT_CONFIG.copy()
        self.save_config()
    
    # Convenience properties for common settings
    @property
    def hotkey(self) -> str:
        return self.get("hotkey")
    
    @hotkey.setter
    def hotkey(self, value: str):
        self.set("hotkey", value)
    
    @property
    def update_rate(self) -> int:
        return self.get("update_rate", 60)
    
    @update_rate.setter
    def update_rate(self, value: int):
        self.set("update_rate", value)
    
    @property
    def box_width(self) -> int:
        return self.get("box_width", 200)
    
    @box_width.setter
    def box_width(self, value: int):
        self.set("box_width", value)
    
    @property
    def box_height(self) -> int:
        return self.get("box_height", 100)
    
    @box_height.setter
    def box_height(self, value: int):
        self.set("box_height", value)
    
    @property
    def zoom_level(self) -> float:
        return self.get("zoom_level", 2.5)
    
    @zoom_level.setter
    def zoom_level(self, value: float):
        self.set("zoom_level", value)
    
    @property
    def show_crosshair(self) -> bool:
        return self.get("show_crosshair", True)
    
    @show_crosshair.setter
    def show_crosshair(self, value: bool):
        self.set("show_crosshair", value)
    
    @property
    def follow_mouse(self) -> bool:
        return self.get("follow_mouse", True)
    
    @follow_mouse.setter
    def follow_mouse(self, value: bool):
        self.set("follow_mouse", value)
    
    @property
    def border_color(self) -> str:
        return self.get("border_color", "#FF0000")
    
    @border_color.setter
    def border_color(self, value: str):
        self.set("border_color", value)
    
    @property
    def border_width(self) -> int:
        return self.get("border_width", 2)
    
    @border_width.setter
    def border_width(self, value: int):
        self.set("border_width", value)
    
    @property
    def crosshair_color(self) -> str:
        return self.get("crosshair_color", "#00FF00")
    
    @crosshair_color.setter
    def crosshair_color(self, value: str):
        self.set("crosshair_color", value)
    
    @property
    def crosshair_size(self) -> int:
        return self.get("crosshair_size", 20)
    
    @crosshair_size.setter
    def crosshair_size(self, value: int):
        self.set("crosshair_size", value)
    
    @property
    def crosshair_thickness(self) -> int:
        return self.get("crosshair_thickness", 2)
    
    @crosshair_thickness.setter
    def crosshair_thickness(self, value: int):
        self.set("crosshair_thickness", value)
    
    @property
    def enable_center_dot(self) -> bool:
        return self.get("enable_center_dot", True)
    
    @enable_center_dot.setter
    def enable_center_dot(self, value: bool):
        self.set("enable_center_dot", value)
    
    @property
    def enable_performance_mode(self) -> bool:
        return self.get("enable_performance_mode", True)
    
    @enable_performance_mode.setter
    def enable_performance_mode(self, value: bool):
        self.set("enable_performance_mode", value)
    
    @property
    def interpolation_mode(self) -> str:
        return self.get("interpolation_mode", "nearest")
    
    @interpolation_mode.setter
    def interpolation_mode(self, value: str):
        self.set("interpolation_mode", value)
    
    @property
    def overlay_opacity(self) -> float:
        return self.get("overlay_opacity", 0.99)
    
    @overlay_opacity.setter
    def overlay_opacity(self, value: float):
        self.set("overlay_opacity", value)