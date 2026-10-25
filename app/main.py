import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                               QHBoxLayout, QWidget, QLabel, QStackedWidget, QFrame,
                               QMessageBox, QCommandLinkButton, QStyle)
from PySide6.QtCore import Qt, QSize
from logger import launcher_logger
from deps import check_dependencies, run_setup_installer
from gui.create_party import CreatePartyWidget
from gui.join_party import JoinPartyWidget
from gui.download import DownloadWidget
from gui.launch import LaunchWidget
import errors

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenParty")
        self.setMinimumSize(620, 520)
        self.resize(650, 560)
        
        launcher_logger.info("Starting OpenParty UI")
        
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        # 1. Main Menu Screen
        self.menu_widget = QWidget()
        self.menu_layout = QVBoxLayout(self.menu_widget)
        self.menu_layout.setContentsMargins(36, 28, 36, 24)
        self.menu_layout.setSpacing(16)
        
        # Header Box
        header_box = QVBoxLayout()
        header_box.setSpacing(4)
        
        self.title = QLabel("OpenParty")
        self.title.setStyleSheet("font-size: 26px; font-weight: 700; color: #0f172a;")
        self.title.setAlignment(Qt.AlignCenter)
        header_box.addWidget(self.title)
        
        self.subtitle = QLabel("Synchronized movie playback for watch parties.")
        self.subtitle.setStyleSheet("font-size: 13px; color: #475569;")
        self.subtitle.setAlignment(Qt.AlignCenter)
        header_box.addWidget(self.subtitle)
        
        self.menu_layout.addLayout(header_box)
        
        # Dependency Status Container
        self.dep_container = QWidget()
        self.dep_layout = QVBoxLayout(self.dep_container)
        self.dep_layout.setContentsMargins(0, 0, 0, 0)
        self.menu_layout.addWidget(self.dep_container)
        
        # Action Links Container (Windows Native Command Link Buttons)
        self.action_container = QWidget()
        self.action_layout = QVBoxLayout(self.action_container)
        self.action_layout.setContentsMargins(0, 10, 0, 10)
        self.action_layout.setSpacing(12)
        
        # Command Link 1: Join Party
        self.btn_join = QCommandLinkButton(
            "Join a Watch Party",
            "Open a party invite file (.oparty) or paste invite data from a friend."
        )
        self.btn_join.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.btn_join.setIconSize(QSize(24, 24))
        self.btn_join.setCursor(Qt.PointingHandCursor)
        self.btn_join.setStyleSheet(
            "QCommandLinkButton { padding: 12px 16px; border: 1px solid #cbd5e1; border-radius: 6px; background-color: #ffffff; }"
            "QCommandLinkButton:hover { background-color: #f8fafc; border-color: #94a3b8; }"
        )
        self.btn_join.clicked.connect(self.show_join_party)
        self.action_layout.addWidget(self.btn_join)
        
        # Command Link 2: Host Party
        self.btn_create = QCommandLinkButton(
            "Host a Watch Party",
            "Select a local video file or enter a magnet link to invite friends."
        )
        self.btn_create.setIcon(self.style().standardIcon(QStyle.SP_FileDialogStart))
        self.btn_create.setIconSize(QSize(24, 24))
        self.btn_create.setCursor(Qt.PointingHandCursor)
        self.btn_create.setStyleSheet(
            "QCommandLinkButton { padding: 12px 16px; border: 1px solid #cbd5e1; border-radius: 6px; background-color: #ffffff; }"
            "QCommandLinkButton:hover { background-color: #f8fafc; border-color: #94a3b8; }"
        )
        self.btn_create.clicked.connect(self.show_create_party)
        self.action_layout.addWidget(self.btn_create)
        
        self.menu_layout.addWidget(self.action_container)
        self.menu_layout.addStretch()
        
        # Footer Bar
        footer = QHBoxLayout()
        self.btn_help = QPushButton("How It Works")
        self.btn_help.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxInformation))
        self.btn_help.setFlat(True)
        self.btn_help.setCursor(Qt.PointingHandCursor)
        self.btn_help.setStyleSheet("color: #475569; font-size: 12px; font-weight: 500;")
        self.btn_help.clicked.connect(self._show_how_it_works)
        footer.addWidget(self.btn_help)
        
        footer.addStretch()
        
        self.btn_logs = QPushButton("View Logs")
        self.btn_logs.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.btn_logs.setFlat(True)
        self.btn_logs.setCursor(Qt.PointingHandCursor)
        self.btn_logs.setStyleSheet("color: #475569; font-size: 12px; font-weight: 500;")
        self.btn_logs.clicked.connect(errors.open_log_folder)
        footer.addWidget(self.btn_logs)
        
        self.menu_layout.addLayout(footer)
        
        self.stacked_widget.addWidget(self.menu_widget)
        
        # 2. Create Party Screen
        self.create_party_widget = CreatePartyWidget()
        self.create_party_widget.back_requested.connect(self.show_main_menu)
        self.create_party_widget.party_start_requested.connect(self.start_hosted_party)
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
        
        # Check dependencies and update UI
        self.check_env()
        
        # CLI Argument handling (e.g. user double-clicked a .oparty file)
        self._check_cli_arguments()

    def _check_cli_arguments(self):
        if len(sys.argv) > 1:
            arg_path = sys.argv[1].strip('\"\'')
            if os.path.isfile(arg_path) and arg_path.lower().endswith(".oparty"):
                launcher_logger.info(f"Opening party file from command line: {arg_path}")
                self.show_join_party()
                self.join_party_widget.load_file(arg_path)

    def check_env(self):
        launcher_logger.info("Checking dependencies...")
        deps = check_dependencies()
        all_found = all(deps.values())
        
        # Clear previous dependency widgets
        for i in reversed(range(self.dep_layout.count())):
            item = self.dep_layout.itemAt(i)
            w = item.widget()
            if w:
                w.setParent(None)
            l = item.layout()
            if l:
                while l.count():
                    child = l.takeAt(0)
                    if child.widget():
                        child.widget().setParent(None)

        if all_found:
            launcher_logger.info("All dependencies found.")
            badge = QFrame()
            badge.setStyleSheet(
                "QFrame { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px 10px; }"
                "QLabel { color: #334155; font-size: 12px; font-weight: 500; border: none; background: transparent; }"
            )
            b_layout = QHBoxLayout(badge)
            b_layout.setContentsMargins(6, 4, 6, 4)
            b_layout.setSpacing(8)
            
            icon_lbl = QLabel()
            icon_lbl.setPixmap(self.style().standardIcon(QStyle.SP_DialogApplyButton).pixmap(14, 14))
            b_layout.addWidget(icon_lbl)
            
            lbl = QLabel("System check passed: VLC, Syncplay, and aria2c are ready.")
            b_layout.addWidget(lbl)
            b_layout.addStretch()
            self.dep_layout.addWidget(badge)
            
            self.btn_join.setEnabled(True)
            self.btn_create.setEnabled(True)
        else:
            launcher_logger.warning(f"Missing dependencies: {deps}")
            banner = QFrame()
            banner.setStyleSheet(
                "QFrame { background-color: #fffbeb; border: 1px solid #fde68a; border-radius: 6px; padding: 12px; }"
                "QLabel { border: none; background: transparent; }"
            )
            banner_layout = QVBoxLayout(banner)
            banner_layout.setSpacing(8)
            
            title_layout = QHBoxLayout()
            warn_icon = QLabel()
            warn_icon.setPixmap(self.style().standardIcon(QStyle.SP_MessageBoxWarning).pixmap(18, 18))
            title_layout.addWidget(warn_icon)
            
            title_lbl = QLabel("Required software components are missing:")
            title_lbl.setStyleSheet("font-weight: 600; color: #92400e; font-size: 13px;")
            title_layout.addWidget(title_lbl)
            title_layout.addStretch()
            banner_layout.addLayout(title_layout)
            
            tool_descs = {
                "vlc": "VLC Media Player (media playback)",
                "syncplay": "Syncplay (playback synchronization)",
                "aria2c": "aria2c (download engine)"
            }
            for name, found in deps.items():
                status_icon = self.style().standardIcon(QStyle.SP_DialogApplyButton if found else QStyle.SP_DialogCancelButton)
                icon_lbl = QLabel()
                icon_lbl.setPixmap(status_icon.pixmap(14, 14))
                
                desc = tool_descs.get(name, name.capitalize())
                desc_lbl = QLabel(desc)
                desc_lbl.setStyleSheet("font-size: 12px; color: #1e293b;")
                
                row = QHBoxLayout()
                row.setSpacing(6)
                row.addWidget(icon_lbl)
                row.addWidget(desc_lbl)
                row.addStretch()
                banner_layout.addLayout(row)
                
            btn_row = QHBoxLayout()
            btn_setup = QPushButton("Run Setup")
            btn_setup.setIcon(self.style().standardIcon(QStyle.SP_DesktopIcon))
            btn_setup.setCursor(Qt.PointingHandCursor)
            btn_setup.setStyleSheet(
                "QPushButton { background-color: #d97706; color: white; font-weight: 600; padding: 6px 14px; border-radius: 4px; border: none; }"
                "QPushButton:hover { background-color: #b45309; }"
            )
            btn_setup.clicked.connect(self._on_run_setup)
            
            btn_recheck = QPushButton("Check Again")
            btn_recheck.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
            btn_recheck.setCursor(Qt.PointingHandCursor)
            btn_recheck.setStyleSheet(
                "QPushButton { background-color: #ffffff; color: #1e293b; font-weight: 500; padding: 6px 14px; border: 1px solid #d1d5db; border-radius: 4px; }"
                "QPushButton:hover { background-color: #f3f4f6; }"
            )
            btn_recheck.clicked.connect(self.check_env)
            
            btn_row.addWidget(btn_setup)
            btn_row.addWidget(btn_recheck)
            btn_row.addStretch()
            banner_layout.addLayout(btn_row)
            
            self.dep_layout.addWidget(banner)
            
            self.btn_join.setEnabled(True)
            self.btn_create.setEnabled(True)

    def _on_run_setup(self):
        success = run_setup_installer()
        if success:
            QMessageBox.information(
                self, "Setup Started",
                "OpenParty setup has been launched.\n"
                "Please accept the Administrator prompt to install missing components.\n"
                "When complete, click 'Check Again'."
            )
        else:
            QMessageBox.warning(
                self, "Setup Not Found",
                "Could not find setup.cmd.\n"
                "Please run setup\\setup.cmd manually."
            )

    def _show_how_it_works(self):
        QMessageBox.information(
            self, "How OpenParty Works",
            "OpenParty synchronizes video playback in three steps:\n\n"
            "1. Host creates a party:\n"
            "   Select a video file or enter a magnet link. OpenParty generates an .oparty configuration file.\n\n"
            "2. Share with guests:\n"
            "   Send the .oparty file to your participants.\n\n"
            "3. Guests join and watch:\n"
            "   Guests open the file in OpenParty. The video downloads and VLC opens automatically in synchronized playback."
        )

    def show_main_menu(self):
        self.stacked_widget.setCurrentWidget(self.menu_widget)
        
    def show_create_party(self):
        self.stacked_widget.setCurrentWidget(self.create_party_widget)

    def show_join_party(self):
        self.stacked_widget.setCurrentWidget(self.join_party_widget)

    def start_party(self, config):
        deps = check_dependencies()
        if not all(deps.values()):
            missing = [k.capitalize() for k, v in deps.items() if not v]
            QMessageBox.warning(
                self, "Missing Components",
                f"Cannot start playback because the following components are missing:\n"
                f"{', '.join(missing)}\n\n"
                "Please click 'Run Setup' on the main menu to install them."
            )
            self.show_main_menu()
            return

        launcher_logger.info(f"Starting party: {config.party.name}")
        self.stacked_widget.setCurrentWidget(self.download_widget)
        self.download_widget.start_download(config)

    def start_hosted_party(self, config, local_media_path: str = ""):
        deps = check_dependencies()
        if not all(deps.values()):
            missing = [k.capitalize() for k, v in deps.items() if not v]
            QMessageBox.warning(
                self, "Missing Components",
                f"Cannot start playback because the following components are missing:\n"
                f"{', '.join(missing)}\n\n"
                "Please click 'Run Setup' on the main menu to install them."
            )
            self.show_main_menu()
            return

        launcher_logger.info(f"Host launching party: {config.party.name}")
        if local_media_path and os.path.isfile(local_media_path):
            self.stacked_widget.setCurrentWidget(self.launch_widget)
            self.launch_widget.start_launch(config, local_media_path)
        else:
            self.stacked_widget.setCurrentWidget(self.download_widget)
            self.download_widget.start_download(config)
        
    def on_download_complete(self, media_path):
        self.stacked_widget.setCurrentWidget(self.launch_widget)
        config = self.download_widget.config
        self.launch_widget.start_launch(config, media_path)

    def closeEvent(self, event):
        try:
            from torrent_creator import SeederManager
            SeederManager.stop_seeding()
        except Exception:
            pass
        if hasattr(self, 'download_widget') and self.download_widget:
            try:
                self.download_widget._cleanup()
            except Exception:
                pass
        event.accept()

def global_exception_handler(exc_type, exc_value, exc_tb):
    """Catch unhandled exceptions cleanly and log details."""
    import traceback
    msg = errors.log_and_format(
        "An unexpected error occurred.",
        str(exc_value),
        "Please restart OpenParty. If this persists, click View Logs to see details.",
        exc=exc_value
    )
    launcher_logger.critical("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
    try:
        QMessageBox.critical(None, "OpenParty - Error", msg)
    except Exception:
        pass

if __name__ == "__main__":
    sys.excepthook = global_exception_handler
    app = QApplication(sys.argv)
    
    app.setStyleSheet("""
        QWidget {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            color: #1e293b;
        }
        QLineEdit, QTextEdit {
            border: 1px solid #cbd5e1;
            border-radius: 4px;
            padding: 6px 10px;
            background-color: #ffffff;
            selection-background-color: #2563eb;
        }
        QLineEdit:focus, QTextEdit:focus {
            border: 1px solid #2563eb;
        }
        QPushButton {
            border-radius: 4px;
            padding: 6px 12px;
        }
        QScrollBar:vertical {
            border: none;
            background: #f1f5f9;
            width: 8px;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical {
            background: #cbd5e1;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical:hover {
            background: #94a3b8;
        }
    """)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
