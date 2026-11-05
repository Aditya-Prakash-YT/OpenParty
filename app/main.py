"""OpenParty application entry point and screen-flow coordinator."""

import os
import sys
import traceback

from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QStackedWidget

import errors
from deps import check_dependencies, run_setup_installer
from gui.create_party import CreatePartyWidget
from gui.download import DownloadWidget
from gui.home import HomeWidget
from gui.join_party import JoinPartyWidget
from gui.launch import LaunchWidget
from logger import launcher_logger
from theme import apply_theme


class MainWindow(QMainWindow):
    """Connect screens and coordinate the create, join, download, and launch flows."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenParty")
        self.setMinimumSize(640, 560)
        self.resize(760, 660)
        launcher_logger.info("Starting OpenParty UI")

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        self._build_screens()
        self._check_cli_arguments()

    def _build_screens(self):
        self.menu_widget = HomeWidget()
        self.menu_widget.create_requested.connect(self.show_create_party)
        self.menu_widget.join_requested.connect(self.show_join_party)
        self.menu_widget.help_requested.connect(self._show_how_it_works)
        self.menu_widget.logs_requested.connect(errors.open_log_folder)
        self.menu_widget.setup_requested.connect(self._on_run_setup)
        self.stacked_widget.addWidget(self.menu_widget)

        self.create_party_widget = CreatePartyWidget()
        self.create_party_widget.back_requested.connect(self.show_main_menu)
        self.create_party_widget.party_start_requested.connect(self.start_hosted_party)
        self.stacked_widget.addWidget(self.create_party_widget)

        self.join_party_widget = JoinPartyWidget()
        self.join_party_widget.back_requested.connect(self.show_main_menu)
        self.join_party_widget.party_loaded.connect(self.start_party)
        self.stacked_widget.addWidget(self.join_party_widget)

        self.download_widget = DownloadWidget()
        self.download_widget.cancel_requested.connect(self.show_main_menu)
        self.download_widget.download_complete.connect(self.on_download_complete)
        self.stacked_widget.addWidget(self.download_widget)

        self.launch_widget = LaunchWidget()
        self.launch_widget.back_requested.connect(self.show_main_menu)
        self.stacked_widget.addWidget(self.launch_widget)

    def _check_cli_arguments(self):
        if len(sys.argv) <= 1:
            return
        arg_path = sys.argv[1].strip('"\'')
        if os.path.isfile(arg_path) and arg_path.lower().endswith(".oparty"):
            launcher_logger.info("Opening party file from command line: %s", arg_path)
            self.show_join_party()
            self.join_party_widget.load_file(arg_path)

    def _on_run_setup(self):
        if run_setup_installer():
            QMessageBox.information(
                self,
                "Setup Started",
                "OpenParty setup has been launched.\n"
                "Please accept the Administrator prompt to install missing components.\n"
                "When complete, click 'Check Again'.",
            )
        else:
            QMessageBox.warning(
                self,
                "Setup Not Found",
                "Could not find setup.cmd.\nPlease run setup\\setup.cmd manually.",
            )

    def _show_how_it_works(self):
        QMessageBox.information(
            self,
            "How OpenParty Works",
            "OpenParty synchronizes video playback in three steps:\n\n"
            "1. Host creates a party:\n"
            "   Select a video file or enter a magnet link. OpenParty generates an .oparty configuration file.\n\n"
            "2. Share with guests:\n"
            "   Send the .oparty file to your participants.\n\n"
            "3. Guests join and watch:\n"
            "   Guests open the file in OpenParty. The video downloads and VLC opens automatically in synchronized playback.",
        )

    def show_main_menu(self):
        self.menu_widget.refresh_dependencies()
        self.stacked_widget.setCurrentWidget(self.menu_widget)

    def show_create_party(self):
        self.stacked_widget.setCurrentWidget(self.create_party_widget)

    def show_join_party(self):
        self.stacked_widget.setCurrentWidget(self.join_party_widget)

    def _require_dependencies(self) -> bool:
        dependencies = check_dependencies()
        missing = [name.capitalize() for name, present in dependencies.items() if not present]
        if not missing:
            return True

        QMessageBox.warning(
            self,
            "Missing Components",
            "Cannot start playback because the following components are missing:\n"
            f"{', '.join(missing)}\n\n"
            "Please run setup\\setup.cmd, then click 'Check Again' on the main menu.",
        )
        self.show_main_menu()
        return False

    def start_party(self, config):
        if not self._require_dependencies():
            return
        launcher_logger.info("Starting party: %s", config.party.name)
        self.stacked_widget.setCurrentWidget(self.download_widget)
        self.download_widget.start_download(config)

    def start_hosted_party(self, config, local_media_path: str = ""):
        if not self._require_dependencies():
            return
        launcher_logger.info("Host launching party: %s", config.party.name)
        if local_media_path and os.path.isfile(local_media_path):
            self.stacked_widget.setCurrentWidget(self.launch_widget)
            self.launch_widget.start_launch(config, local_media_path, is_host=True)
            return

        self.stacked_widget.setCurrentWidget(self.download_widget)
        self.download_widget.start_download(config)

    def on_download_complete(self, media_path):
        self.stacked_widget.setCurrentWidget(self.launch_widget)
        self.launch_widget.start_launch(
            self.download_widget.config,
            media_path,
            p2p_manager=self.download_widget.manager,
            p2p_gid=self.download_widget.gid,
        )

    def closeEvent(self, event):
        try:
            from torrent_creator import SeederManager

            SeederManager.stop_seeding()
        except Exception:
            launcher_logger.exception("Failed to stop torrent seeder during shutdown")
        if self.download_widget:
            try:
                self.download_widget._cleanup()
            except Exception:
                launcher_logger.exception("Failed to stop download engine during shutdown")
        event.accept()


def global_exception_handler(exc_type, exc_value, exc_tb):
    """Log unexpected exceptions and show a readable message when possible."""
    msg = errors.log_and_format(
        "An unexpected error occurred.",
        str(exc_value),
        "Please restart OpenParty. If this persists, click View Logs to see details.",
        exc=exc_value,
    )
    launcher_logger.critical("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
    try:
        QMessageBox.critical(None, "OpenParty - Error", msg)
    except Exception:
        pass


if __name__ == "__main__":
    sys.excepthook = global_exception_handler
    app = QApplication(sys.argv)
    apply_theme(app)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
