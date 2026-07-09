import sys
# pyrefly: ignore [missing-import]
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                               QWidget, QLabel, QStackedWidget)
# pyrefly: ignore [missing-import]
from PySide6.QtCore import Qt
from logger import launcher_logger
from deps import check_dependencies
from gui.create_party import CreatePartyWidget
from gui.join_party import JoinPartyWidget
from gui.download import DownloadWidget
from gui.launch import LaunchWidget
import errors

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenParty")
        self.setMinimumSize(500, 400)
        
        launcher_logger.info("Starting OpenParty UI")
        
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        # 1. Main Menu / Loading Screen
        self.menu_widget = QWidget()
        self.menu_layout = QVBoxLayout(self.menu_widget)
        
        self.title = QLabel("Welcome to OpenParty")
        self.title.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.title.setAlignment(Qt.AlignCenter)
        self.menu_layout.addWidget(self.title)
        
        self.stacked_widget.addWidget(self.menu_widget)
        
        # 2. Create Party Screen
        self.create_party_widget = CreatePartyWidget()
        self.create_party_widget.back_requested.connect(self.show_main_menu)
        self.stacked_widget.addWidget(self.create_party_widget)
        
        # 3. Join Party Screen
        self.join_party_widget = JoinPartyWidget()
        self.join_party_widget.back_requested.connect(self.show_main_menu)
        self.join_party_widget.party_loaded.connect(self.start_party)
        self.stacked_widget.addWidget(self.join_party_widget)
        
        # 4. Download Screen
        self.download_widget = DownloadWidget()
        self.download_widget.cancel_requested.connect(self.show_main_menu)
        self.download_widget.download_complete.connect(self.on_download_complete)
        self.stacked_widget.addWidget(self.download_widget)
        
        # 5. Launch Screen
        self.launch_widget = LaunchWidget()
        self.launch_widget.back_requested.connect(self.show_main_menu)
        self.stacked_widget.addWidget(self.launch_widget)
        
        # Run Environment Check
        self.check_env()

    def check_env(self):
        launcher_logger.info("Checking dependencies...")
        deps = check_dependencies()
        
        all_found = all(deps.values())
        
        if all_found:
            launcher_logger.info("All dependencies found.")
            self.setup_main_menu_buttons()
        else:
            launcher_logger.warning(f"Missing dependencies: {deps}")
            self.show_dependency_error(deps)

    def show_dependency_error(self, deps):
        check_layout = QVBoxLayout()
        for name, found in deps.items():
            icon = "✔" if found else "✘"
            color = "green" if found else "red"
            lbl = QLabel(f"<span style='color: {color};'>{icon}</span> {name.capitalize()}")
            lbl.setStyleSheet("font-size: 16px;")
            check_layout.addWidget(lbl)
            
        self.menu_layout.addLayout(check_layout)
        
        msg = QLabel("<b>Required software is missing. Please run setup.cmd and restart OpenParty.</b>")
        msg.setStyleSheet("font-size: 14px; margin-top: 20px;")
        msg.setWordWrap(True)
        self.menu_layout.addWidget(msg)
        self.menu_layout.addStretch()
        
    def setup_main_menu_buttons(self):
        self.btn_create = QPushButton("Create Party")
        self.btn_join = QPushButton("Join Party")
        
        self.btn_create.setMinimumHeight(40)
        self.btn_join.setMinimumHeight(40)
        
        self.btn_create.clicked.connect(self.show_create_party)
        self.btn_join.clicked.connect(self.show_join_party)
        
        self.menu_layout.addWidget(self.btn_create)
        self.menu_layout.addWidget(self.btn_join)
        
        self.btn_logs = QPushButton("View Logs")
        self.btn_logs.setMinimumHeight(30)
        self.btn_logs.clicked.connect(errors.open_log_folder)
        self.menu_layout.addStretch()
        self.menu_layout.addWidget(self.btn_logs)
        
    def show_main_menu(self):
        self.stacked_widget.setCurrentWidget(self.menu_widget)
        
    def show_create_party(self):
        self.stacked_widget.setCurrentWidget(self.create_party_widget)

    def show_join_party(self):
        self.stacked_widget.setCurrentWidget(self.join_party_widget)

    def start_party(self, config):
        launcher_logger.info(f"Starting party: {config.party.name}")
        self.stacked_widget.setCurrentWidget(self.download_widget)
        self.download_widget.start_download(config)
        
    def on_download_complete(self, media_path):
        self.stacked_widget.setCurrentWidget(self.launch_widget)
        # We need the config, which is stored in download_widget
        config = self.download_widget.config
        self.launch_widget.start_launch(config, media_path)

def global_exception_handler(exc_type, exc_value, exc_tb):
    """Catch unhandled exceptions so the app never shows a scary traceback."""
    import traceback
    msg = errors.log_and_format(
        "An unexpected error occurred.",
        str(exc_value),
        "Please restart OpenParty. If this keeps happening, check View Logs and report the issue.",
        exc=exc_value
    )
    launcher_logger.critical("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
    # Try to show a dialog if we can
    try:
        # pyrefly: ignore [missing-import]
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(None, "OpenParty — Unexpected Error", msg)
    except Exception:
        pass

if __name__ == "__main__":
    sys.excepthook = global_exception_handler
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
