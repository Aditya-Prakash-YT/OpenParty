# OpenParty v1.0 — Developer Guide

OpenParty is a decentralized watch party orchestrator built in Python (PySide6). Its core philosophy is split-architecture: the application itself never installs dependencies, runs as Administrator, or manipulates system state. Instead, a static Windows batch script (`setup/setup.cmd`) handles all privileged environment configuration.

## Architecture Overview

- **`setup/setup.cmd`**: Handles UAC elevation, winget installations (VLC, Syncplay, aria2c), and registers the `.oparty` file extension in the Windows Registry.
- **`app/main.py`**: The entrypoint for the PySide6 UI. Uses a `QStackedWidget` to manage screens.
- **`app/config/`**: JSON parsing and validation layer (`loader.py`). Strongly typed using Python Dataclasses to represent `.oparty` files.
- **`app/downloader/`**: An asynchronous JSON-RPC client (`aria2.py`) bridging Python to a detached `aria2c` process. It dynamically binds to open ports and generates random secret tokens.
- **`app/gui/`**: Individual screen logic (Create, Join, Download, Launch) and the `error_panel.py` abstraction.
- **`app/deps.py`**: Passive dependency detection. Uses the Windows Registry and `shutil.which()` to find installed executables.

## Building and Packaging

OpenParty is packaged using PyInstaller. 

**Prerequisites:**
1. Install Python 3.12+.
2. Run `pip install -r app/requirements.txt` (which includes PyInstaller).

**Build Command:**
Run the following from the repository root:
```cmd
pyinstaller --noconsole --onefile --name OpenParty --clean app/main.py
```

The resulting standalone executable will be located at `dist/OpenParty.exe`.

## How to Extend OpenParty

### Adding a new UI screen
1. Create your widget class in `app/gui/`.
2. Instantiate it in `MainWindow.__init__` (`app/main.py`).
3. Add it to `self.stacked_widget`.
4. Connect its signals to transitions in `MainWindow` (e.g., `self.my_widget.back_requested.connect(self.show_main_menu)`).

### Extending the `.oparty` JSON schema
1. Update `app/config/loader.py` dataclasses (e.g., `MediaSource`).
2. Add your new field and write a `_validate_*` method in the dataclass if strict validation is needed.
3. Update `test_loader.py` with cases for valid and invalid inputs of your new field.

### Error Handling
Never use naked `QMessageBox.critical()`.
1. Add a descriptive helper method to `app/errors.py` that formats the Problem, Likely cause, and Suggested fix.
2. In your UI class, include `ErrorPanel` and call `self.error_panel.show_error(msg)` to display it non-intrusively with built-in retry functionality.
