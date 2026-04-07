from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from pos_system.controllers.app_controller import AppController
from pos_system.ui.theme import APP_STYLESHEET


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)
    controller = AppController(app)
    controller.start()
    sys.exit(app.exec())
