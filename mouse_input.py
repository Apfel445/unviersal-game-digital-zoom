
from pynput import mouse

class MouseInput:
    def __init__(self, main_window):
        self.main_window = main_window
        self.listener = None

    def start_listening(self):
        self.listener = mouse.Listener(on_click=self.on_click)
        self.listener.start()

    def on_click(self, x, y, button, pressed):
        if pressed:
            self.main_window.handle_mouse_press(button)

    def stop_listening(self):
        """Stops the mouse listener thread"""
        if self.listener:
            self.listener.stop()
            # Don't join, it can block and we want a swift exit

