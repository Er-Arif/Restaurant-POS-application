from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import QApplication

from pos_system.config.app_config import DEV_BYPASS_ENV
from pos_system.controllers.app_controller import AppController
from pos_system.ui.theme import APP_STYLESHEET


DEV_FLAGS = {"--dev", "--dev-bypass-license", "--bypass-license"}


def main() -> None:
    argv = list(sys.argv)
    if any(flag in argv for flag in DEV_FLAGS):
        os.environ[DEV_BYPASS_ENV] = "1"
        argv = [arg for arg in argv if arg not in DEV_FLAGS]
    app = QApplication(argv)
    app.setStyleSheet(APP_STYLESHEET)
    controller = AppController(app)
    controller.start()
    sys.exit(app.exec())
