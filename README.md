# Simple Global Screen Magnifier

A lightweight and customizable screen magnifier application with a graphical user interface. This tool provides real-time magnification of your screen, useful for detailed work, presentations, or accessibility.

## Features

*   **Global Screen Magnification**: Magnifies a portion of the screen around the cursor or a fixed position.
*   **Customizable Zoom Level**: Adjust the magnification level to suit your needs.
*   **Adjustable Capture Size**: Define the width and height of the area captured for magnification.
*   **Configurable Update Rate (FPS)**: Control the refresh rate of the magnified view for optimal performance or smoothness.
*   **Hotkey Support**: Toggle the magnifier on/off using a customizable keyboard hotkey or mouse button.
*   **Follow Mouse/Fixed Position**: The magnifier can either follow your mouse cursor dynamically or snap to a fixed position on the screen (e.g., center).
*   **Customizable Crosshair**: Option to display a crosshair in the magnified view, with adjustable size, thickness, color, and a center dot.
*   **Intuitive Control Panel (GUI)**: A user-friendly graphical interface to manage all settings and controls.
*   **System Tray Integration**: Quick access to common actions like showing/hiding the control panel, toggling the magnifier, and quitting the application from the system tray.
*   **Advanced Settings**: Extensive customization options including:
    *   **Performance**: Image interpolation mode, capture quality, performance mode, smooth movement, debug mode.
    *   **Visual**: Overlay opacity, border color and glow, visual feedback, capture region highlight.
*   **Transparent Overlay**: The magnifier window is designed to be non-interactive, allowing mouse events to pass through to underlying applications.

## Installation and Running

This application is built with Python and requires a few dependencies. For Windows users, a convenient batch script is provided for installation and execution.

### Prerequisites

*   Python 3.7+ (Download from [python.org](https://www.python.org/))

### Steps

1.  **Clone the repository** (if you haven't already):
    ```bash
    git clone https://github.com/your-username/SimpleGlobalScreenMagnifier.git
    cd SimpleGlobalScreenMagnifier
    ```
    *(Note: Replace `https://github.com/your-username/SimpleGlobalScreenMagnifier.git` with the actual repository URL)*

2.  **Run the installation script**:
    On Windows, simply double-click the `install_and_run.bat` file. This script will:
    *   Check for Python installation.
    *   Install all necessary Python packages listed in `requirements.txt` using `pip`.
    *   Launch the magnifier application.

    Alternatively, you can run the commands manually in your terminal:

    ```bash
    # (Optional) Create and activate a virtual environment
    python -m venv venv
    .\venv\Scripts\activate   # On Windows
    # source venv/bin/activate  # On macOS/Linux

    pip install -r requirements.txt
    python run_magnifier.py
    ```

## How to Use

1.  **Launch the application**: Run `install_and_run.bat` or `python run_magnifier.py`. The Control Panel will appear, and a system tray icon will be visible.
2.  **Toggle Magnifier**:
    *   Use the configured **Hotkey** (default is usually `Alt+Z` or `Button.x2` depending on configuration - check your `config.py` or Control Panel).
    *   Click the "START"/"STOP" button in the Control Panel.
    *   Right-click the system tray icon and select "Toggle Magnifier".
3.  **Adjust Settings**: Use the Control Panel to change zoom level, capture size, update rate, crosshair visibility, and other advanced settings.
4.  **Positioning**:
    *   **Follow Mouse**: Keep the "Follow Mouse" checkbox enabled in the Control Panel for the magnifier to follow your cursor.
    *   **Fixed Position**: Uncheck "Follow Mouse" and click "Snap to Center" to place the magnifier at the center of your primary monitor.
5.  **Hide/Show Control Panel**:
    *   Right-click the system tray icon and select "Show Control Panel".
    *   Double-click the system tray icon.
6.  **Quit Application**:
    *   Click the "Quit" button in the Control Panel.
    *   Right-click the system tray icon and select "Quit".
    *   Press `Ctrl+C` in the terminal where the application was launched.
    *   Press `ESC` while the magnifier overlay is active to hide it instantly.

## Configuration

Settings are stored and can be adjusted via the `magnifier_config.json` file or directly through the Control Panel. The `config.py` file defines default settings and handles loading/saving.

## Contributing

Contributions are welcome! Please feel free to open issues or submit pull requests.

## License

This project is open-source and available under the [License Name or Link to License File].
