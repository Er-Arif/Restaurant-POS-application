APP_STYLESHEET = """
QWidget {
    background: #f6f3eb;
    color: #1f2933;
    font-family: "Segoe UI";
    font-size: 11pt;
}
QMainWindow, QDialog {
    background: #f6f3eb;
}
QPushButton {
    background: #165b47;
    color: white;
    border: none;
    border-radius: 10px;
    padding: 10px 16px;
    font-weight: 600;
}
QPushButton:hover {
    background: #1a7058;
}
QPushButton:disabled {
    background: #8aa89d;
}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateEdit, QDoubleSpinBox, QSpinBox, QListWidget, QTableWidget {
    background: white;
    border: 1px solid #d7cfc2;
    border-radius: 8px;
    padding: 6px;
}
QTabWidget::pane {
    border: 1px solid #d7cfc2;
    border-radius: 12px;
    background: #fffdf7;
}
QTabBar::tab {
    background: #e7dcc8;
    padding: 10px 16px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 4px;
}
QTabBar::tab:selected {
    background: #fffdf7;
}
QGroupBox {
    border: 1px solid #d7cfc2;
    border-radius: 12px;
    margin-top: 12px;
    padding-top: 14px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QHeaderView::section {
    background: #e7dcc8;
    padding: 8px;
    border: none;
    font-weight: 700;
}
"""
