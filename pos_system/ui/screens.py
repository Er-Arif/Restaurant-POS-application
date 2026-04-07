from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from pos_system.models.enums import PaymentMethod, UserRole



class MoneySpinBox(QDoubleSpinBox):
    def focusInEvent(self, event):
        super().focusInEvent(event)
        line_edit = self.lineEdit()
        if line_edit is not None:
            line_edit.selectAll()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        line_edit = self.lineEdit()
        if line_edit is not None:
            line_edit.selectAll()


class ActivationScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Activate POS")
        layout = QVBoxLayout(self)
        title = QLabel("Offline License Activation")
        title.setStyleSheet("font-size: 20pt; font-weight: 700;")
        self.hardware_value = QLabel("")
        self.hardware_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.license_input = QTextEdit()
        self.license_input.setPlaceholderText("Paste the encrypted license key here")
        self.feedback_label = QLabel("")
        self.activate_button = QPushButton("Validate & Activate")
        layout.addWidget(title)
        layout.addWidget(QLabel("Hardware Fingerprint"))
        layout.addWidget(self.hardware_value)
        layout.addWidget(QLabel("License Key"))
        layout.addWidget(self.license_input)
        layout.addWidget(self.feedback_label)
        layout.addWidget(self.activate_button)
        layout.addStretch(1)
        self.resize(720, 500)


class SetupWizardScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Initial Setup Wizard")
        outer = QVBoxLayout(self)
        title = QLabel("First-Time Restaurant Setup")
        title.setStyleSheet("font-size: 20pt; font-weight: 700;")
        outer.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)

        admin_box = QGroupBox("Admin Account")
        admin_form = QFormLayout(admin_box)
        self.admin_username = QLineEdit()
        self.admin_password = QLineEdit()
        self.admin_password.setEchoMode(QLineEdit.Password)
        self.admin_confirm_password = QLineEdit()
        self.admin_confirm_password.setEchoMode(QLineEdit.Password)
        admin_form.addRow("Username", self.admin_username)
        admin_form.addRow("Password", self.admin_password)
        admin_form.addRow("Confirm Password", self.admin_confirm_password)

        restaurant_box = QGroupBox("Restaurant Branding")
        restaurant_form = QFormLayout(restaurant_box)
        self.restaurant_name = QLineEdit()
        self.address = QTextEdit()
        self.phone = QLineEdit()
        self.gst_number = QLineEdit()
        self.currency_symbol = QLineEdit("?")
        self.receipt_footer = QTextEdit()
        self.logo_path = QLineEdit()
        self.logo_browse = QPushButton("Browse Logo")
        logo_row = QWidget()
        logo_layout = QHBoxLayout(logo_row)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.addWidget(self.logo_path)
        logo_layout.addWidget(self.logo_browse)
        restaurant_form.addRow("Restaurant Name", self.restaurant_name)
        restaurant_form.addRow("Address", self.address)
        restaurant_form.addRow("Phone", self.phone)
        restaurant_form.addRow("GST Number", self.gst_number)
        restaurant_form.addRow("Currency", self.currency_symbol)
        restaurant_form.addRow("Receipt Footer", self.receipt_footer)
        restaurant_form.addRow("Logo", logo_row)

        billing_box = QGroupBox("Billing Defaults")
        billing_form = QFormLayout(billing_box)
        self.gst_percent = MoneySpinBox()
        self.gst_percent.setMaximum(100)
        self.gst_percent.setDecimals(2)
        self.discount_amount = MoneySpinBox()
        self.discount_amount.setMaximum(100000)
        self.discount_amount.setDecimals(2)
        self.service_charge = MoneySpinBox()
        self.service_charge.setMaximum(100000)
        self.service_charge.setDecimals(2)
        billing_form.addRow("GST %", self.gst_percent)
        billing_form.addRow("Default Discount", self.discount_amount)
        billing_form.addRow("Service Charge", self.service_charge)

        tables_box = QGroupBox("Table Setup")
        tables_form = QFormLayout(tables_box)
        self.table_count = QSpinBox()
        self.table_count.setRange(1, 200)
        self.table_count.setValue(10)
        self.table_prefix = QLineEdit("T")
        tables_form.addRow("Number of Tables", self.table_count)
        tables_form.addRow("Table Prefix", self.table_prefix)

        self.feedback_label = QLabel("")
        self.create_button = QPushButton("Create Admin & Finish Setup")

        content_layout.addWidget(admin_box)
        content_layout.addWidget(restaurant_box)
        content_layout.addWidget(billing_box)
        content_layout.addWidget(tables_box)
        content_layout.addWidget(self.feedback_label)
        content_layout.addWidget(self.create_button)
        content_layout.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll)
        self.resize(800, 720)

    def choose_logo(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Select Logo", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if filename:
            self.logo_path.setText(filename)


class LoginScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Restaurant POS Login")
        layout = QVBoxLayout(self)
        title = QLabel("Restaurant POS Login")
        title.setStyleSheet("font-size: 20pt; font-weight: 700;")
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.feedback_label = QLabel("")
        self.login_button = QPushButton("Login")
        form = QFormLayout()
        form.addRow("Username", self.username)
        form.addRow("Password", self.password)
        layout.addWidget(title)
        layout.addLayout(form)
        layout.addWidget(self.feedback_label)
        layout.addWidget(self.login_button)
        layout.addStretch(1)
        self.resize(420, 260)


class AdminDashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Admin Dashboard")
        container = QWidget()
        root = QVBoxLayout(container)

        header = QHBoxLayout()
        self.brand_label = QLabel("Admin Dashboard")
        self.brand_label.setStyleSheet("font-size: 20pt; font-weight: 700;")
        self.open_pos_button = QPushButton("Open POS")
        self.logout_button = QPushButton("Logout")
        header.addWidget(self.brand_label)
        header.addStretch(1)
        header.addWidget(self.open_pos_button)
        header.addWidget(self.logout_button)
        root.addLayout(header)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs)
        self.setCentralWidget(container)

        self.overview_tab = QWidget()
        overview_layout = QVBoxLayout(self.overview_tab)

        hero_box = QGroupBox("Business Snapshot")
        hero_layout = QVBoxLayout(hero_box)
        self.overview_headline = QLabel("Today's business at a glance")
        self.overview_headline.setStyleSheet("font-size: 18pt; font-weight: 700;")
        self.overview_summary = QLabel("")
        self.overview_summary.setWordWrap(True)
        hero_layout.addWidget(self.overview_headline)
        hero_layout.addWidget(self.overview_summary)
        overview_layout.addWidget(hero_box)

        metrics_layout = QGridLayout()
        sales_card, self.overview_sales_today_value, self.overview_sales_today_meta = self._build_metric_card("Sales Today")
        orders_card, self.overview_orders_today_value, self.overview_orders_today_meta = self._build_metric_card("Orders Today")
        average_card, self.overview_average_bill_value, self.overview_average_bill_meta = self._build_metric_card("Average Bill")
        open_card, self.overview_open_tables_value, self.overview_open_tables_meta = self._build_metric_card("Open Tables")
        paid_card, self.overview_paid_orders_value, self.overview_paid_orders_meta = self._build_metric_card("Paid Orders")
        cancelled_card, self.overview_cancelled_orders_value, self.overview_cancelled_orders_meta = self._build_metric_card("Cancelled Orders")
        metrics_layout.addWidget(sales_card, 0, 0)
        metrics_layout.addWidget(orders_card, 0, 1)
        metrics_layout.addWidget(average_card, 0, 2)
        metrics_layout.addWidget(open_card, 1, 0)
        metrics_layout.addWidget(paid_card, 1, 1)
        metrics_layout.addWidget(cancelled_card, 1, 2)
        overview_layout.addLayout(metrics_layout)

        actions_box = QGroupBox("Quick Actions")
        actions_layout = QGridLayout(actions_box)
        self.overview_refresh_button = QPushButton("Refresh Dashboard")
        self.overview_menu_button = QPushButton("Manage Menu")
        self.overview_users_button = QPushButton("Manage Users")
        self.overview_orders_button = QPushButton("Review Orders")
        self.overview_reports_button = QPushButton("Open Reports")
        self.overview_backup_button = QPushButton("Create Backup")
        actions_layout.addWidget(self.overview_refresh_button, 0, 0)
        actions_layout.addWidget(self.overview_menu_button, 0, 1)
        actions_layout.addWidget(self.overview_users_button, 0, 2)
        actions_layout.addWidget(self.overview_orders_button, 1, 0)
        actions_layout.addWidget(self.overview_reports_button, 1, 1)
        actions_layout.addWidget(self.overview_backup_button, 1, 2)
        overview_layout.addWidget(actions_box)

        lower_layout = QHBoxLayout()

        recent_orders_box = QGroupBox("Recent Orders")
        recent_orders_layout = QVBoxLayout(recent_orders_box)
        self.overview_recent_orders = QTableWidget(0, 5)
        self.overview_recent_orders.setHorizontalHeaderLabels(["Order #", "Table", "Status", "Total", "Created"])
        self.overview_recent_orders.horizontalHeader().setStretchLastSection(True)
        recent_orders_layout.addWidget(self.overview_recent_orders)
        lower_layout.addWidget(recent_orders_box, 2)

        side_layout = QVBoxLayout()
        operations_box = QGroupBox("Operations")
        operations_layout = QVBoxLayout(operations_box)
        self.overview_operations_summary = QLabel("")
        self.overview_operations_summary.setWordWrap(True)
        operations_layout.addWidget(self.overview_operations_summary)
        side_layout.addWidget(operations_box)

        alerts_box = QGroupBox("Attention Needed")
        alerts_layout = QVBoxLayout(alerts_box)
        self.overview_alerts_summary = QLabel("")
        self.overview_alerts_summary.setWordWrap(True)
        alerts_layout.addWidget(self.overview_alerts_summary)
        side_layout.addWidget(alerts_box)

        top_items_box = QGroupBox("Top Items")
        top_items_layout = QVBoxLayout(top_items_box)
        self.overview_top_items_summary = QLabel("")
        self.overview_top_items_summary.setWordWrap(True)
        top_items_layout.addWidget(self.overview_top_items_summary)
        side_layout.addWidget(top_items_box)
        side_layout.addStretch(1)

        lower_layout.addLayout(side_layout, 1)
        overview_layout.addLayout(lower_layout)
        self.tabs.addTab(self.overview_tab, "Overview")

        self.menu_tab = QWidget()
        menu_layout = QHBoxLayout(self.menu_tab)
        category_box = QGroupBox("Categories")
        category_layout = QVBoxLayout(category_box)
        self.category_name = QLineEdit()
        self.category_description = QTextEdit()
        self.category_list = QListWidget()
        self.save_category_button = QPushButton("Save Category")
        self.clear_category_button = QPushButton("New Category")
        self.toggle_category_button = QPushButton("Archive Category")
        self.delete_category_button = QPushButton("Delete Category")
        category_actions = QHBoxLayout()
        category_actions.addWidget(self.save_category_button)
        category_actions.addWidget(self.clear_category_button)
        category_actions.addWidget(self.toggle_category_button)
        category_actions.addWidget(self.delete_category_button)
        category_layout.addWidget(QLabel("Name"))
        category_layout.addWidget(self.category_name)
        category_layout.addWidget(QLabel("Description"))
        category_layout.addWidget(self.category_description)
        category_layout.addLayout(category_actions)
        category_layout.addWidget(self.category_list)

        item_box = QGroupBox("Menu Items")
        item_layout = QVBoxLayout(item_box)
        form = QFormLayout()
        self.item_category_combo = QComboBox()
        self.item_name = QLineEdit()
        self.item_description = QTextEdit()
        self.item_price = MoneySpinBox()
        self.item_price.setMaximum(100000)
        self.item_price.setDecimals(2)
        self.item_available = QCheckBox("Available")
        self.item_available.setChecked(True)
        form.addRow("Category", self.item_category_combo)
        form.addRow("Item Name", self.item_name)
        form.addRow("Description", self.item_description)
        form.addRow("Price", self.item_price)
        form.addRow("", self.item_available)
        self.save_item_button = QPushButton("Save Item")
        self.clear_item_button = QPushButton("New Item")
        self.toggle_item_button = QPushButton("Mark Unavailable")
        self.delete_item_button = QPushButton("Delete Item")
        item_actions = QHBoxLayout()
        item_actions.addWidget(self.save_item_button)
        item_actions.addWidget(self.clear_item_button)
        item_actions.addWidget(self.toggle_item_button)
        item_actions.addWidget(self.delete_item_button)
        self.menu_items_table = QTableWidget(0, 5)
        self.menu_items_table.setHorizontalHeaderLabels(["ID", "Name", "Category", "Price", "Available"])
        self.menu_items_table.horizontalHeader().setStretchLastSection(True)
        item_layout.addLayout(form)
        item_layout.addLayout(item_actions)
        item_layout.addWidget(self.menu_items_table)

        menu_layout.addWidget(category_box, 1)
        menu_layout.addWidget(item_box, 2)
        self.tabs.addTab(self.menu_tab, "Menu")

        self.users_tab = QWidget()
        users_layout = QVBoxLayout(self.users_tab)
        users_form = QFormLayout()
        self.user_full_name = QLineEdit()
        self.user_username = QLineEdit()
        self.user_password = QLineEdit()
        self.user_password.setEchoMode(QLineEdit.Password)
        self.user_password.setPlaceholderText("Required for a new user")
        self.user_role = QComboBox()
        self.user_role.addItems([role.value for role in UserRole])
        self.user_active = QCheckBox("Active")
        self.user_active.setChecked(True)
        self.user_admin_password = QLineEdit()
        self.user_admin_password.setEchoMode(QLineEdit.Password)
        self.user_admin_password.setPlaceholderText("Enter your admin password to confirm changes")
        users_form.addRow("Full Name", self.user_full_name)
        users_form.addRow("Username", self.user_username)
        users_form.addRow("Password / Reset", self.user_password)
        users_form.addRow("Role", self.user_role)
        users_form.addRow("", self.user_active)
        users_form.addRow("Admin Password", self.user_admin_password)
        self.save_user_button = QPushButton("Create User")
        self.clear_user_button = QPushButton("Add New User")
        user_actions = QHBoxLayout()
        user_actions.addWidget(self.save_user_button)
        user_actions.addWidget(self.clear_user_button)
        self.users_table = QTableWidget(0, 5)
        self.users_table.setHorizontalHeaderLabels(["ID", "Full Name", "Username", "Role", "Active"])
        self.users_table.horizontalHeader().setStretchLastSection(True)
        self.users_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.users_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.users_table.setSelectionMode(QAbstractItemView.SingleSelection)
        users_layout.addLayout(users_form)
        users_layout.addLayout(user_actions)
        users_layout.addWidget(self.users_table)
        self.tabs.addTab(self.users_tab, "Users")

        self.orders_tab = QWidget()
        orders_layout = QVBoxLayout(self.orders_tab)
        orders_header = QHBoxLayout()
        self.order_status_filter = QComboBox()
        self.order_status_filter.addItems(["all", "open", "paid", "cancelled"])
        self.order_search = QLineEdit()
        self.order_search.setPlaceholderText("Search by order #, table, cashier, or status")
        self.refresh_orders_button = QPushButton("Refresh Orders")
        self.cancel_order_button = QPushButton("Cancel Selected Order")
        self.print_order_receipt_button = QPushButton("Print Selected Receipt")
        self.save_order_pdf_button = QPushButton("Save Selected Receipt PDF")
        orders_header.addWidget(QLabel("Status"))
        orders_header.addWidget(self.order_status_filter)
        orders_header.addWidget(QLabel("Search"))
        orders_header.addWidget(self.order_search)
        orders_header.addWidget(self.refresh_orders_button)
        orders_header.addWidget(self.cancel_order_button)
        orders_header.addWidget(self.print_order_receipt_button)
        orders_header.addWidget(self.save_order_pdf_button)
        orders_header.addStretch(1)
        orders_body = QHBoxLayout()
        self.orders_table = QTableWidget(0, 8)
        self.orders_table.setHorizontalHeaderLabels(
            ["ID", "Order #", "Table", "User", "Status", "Subtotal", "Total", "Created At"]
        )
        self.orders_table.horizontalHeader().setStretchLastSection(True)
        order_detail_box = QGroupBox("Order Details")
        order_detail_layout = QVBoxLayout(order_detail_box)
        self.order_detail_summary = QLabel("Select an order to view details.")
        self.order_detail_summary.setWordWrap(True)
        self.order_detail_items = QTableWidget(0, 4)
        self.order_detail_items.setHorizontalHeaderLabels(["Item", "Qty", "Unit", "Line Total"])
        self.order_detail_items.horizontalHeader().setStretchLastSection(True)
        self.order_detail_payments = QPlainTextEdit()
        self.order_detail_payments.setReadOnly(True)
        order_detail_layout.addWidget(self.order_detail_summary)
        order_detail_layout.addWidget(self.order_detail_items)
        order_detail_layout.addWidget(QLabel("Payments"))
        order_detail_layout.addWidget(self.order_detail_payments)
        orders_layout.addLayout(orders_header)
        orders_body.addWidget(self.orders_table, 2)
        orders_body.addWidget(order_detail_box, 1)
        orders_layout.addLayout(orders_body)
        self.tabs.addTab(self.orders_tab, "Orders")

        self.reports_tab = QWidget()
        reports_layout = QVBoxLayout(self.reports_tab)
        reports_controls = QHBoxLayout()
        self.report_start = QDateEdit()
        self.report_start.setCalendarPopup(True)
        self.report_start.setDate(date.today())
        self.report_end = QDateEdit()
        self.report_end.setCalendarPopup(True)
        self.report_end.setDate(date.today())
        self.refresh_report_button = QPushButton("Refresh Summary")
        self.export_csv_button = QPushButton("Export CSV")
        reports_controls.addWidget(QLabel("From"))
        reports_controls.addWidget(self.report_start)
        reports_controls.addWidget(QLabel("To"))
        reports_controls.addWidget(self.report_end)
        reports_controls.addWidget(self.refresh_report_button)
        reports_controls.addWidget(self.export_csv_button)
        reports_controls.addStretch(1)
        self.report_summary = QLabel("")
        self.report_summary.setWordWrap(True)
        reports_layout.addLayout(reports_controls)
        reports_layout.addWidget(self.report_summary)
        reports_layout.addStretch(1)
        self.tabs.addTab(self.reports_tab, "Reports")

        self.settings_tab = QWidget()
        settings_layout = QVBoxLayout(self.settings_tab)
        settings_form = QFormLayout()
        self.settings_restaurant_name = QLineEdit()
        self.settings_address = QTextEdit()
        self.settings_phone = QLineEdit()
        self.settings_gst_number = QLineEdit()
        self.settings_currency = QLineEdit("?")
        self.settings_gst_percent = MoneySpinBox()
        self.settings_gst_percent.setMaximum(100)
        self.settings_gst_percent.setDecimals(2)
        self.settings_discount = MoneySpinBox()
        self.settings_discount.setMaximum(100000)
        self.settings_discount.setDecimals(2)
        self.settings_service_charge = MoneySpinBox()
        self.settings_service_charge.setMaximum(100000)
        self.settings_service_charge.setDecimals(2)
        self.settings_receipt_footer = QTextEdit()
        self.settings_logo_path = QLineEdit()
        self.settings_logo_browse = QPushButton("Browse Logo")
        settings_logo_row = QWidget()
        settings_logo_layout = QHBoxLayout(settings_logo_row)
        settings_logo_layout.setContentsMargins(0, 0, 0, 0)
        settings_logo_layout.addWidget(self.settings_logo_path)
        settings_logo_layout.addWidget(self.settings_logo_browse)
        settings_form.addRow("Restaurant Name", self.settings_restaurant_name)
        settings_form.addRow("Address", self.settings_address)
        settings_form.addRow("Phone", self.settings_phone)
        settings_form.addRow("GST Number", self.settings_gst_number)
        settings_form.addRow("Currency", self.settings_currency)
        settings_form.addRow("GST %", self.settings_gst_percent)
        settings_form.addRow("Default Discount", self.settings_discount)
        settings_form.addRow("Service Charge", self.settings_service_charge)
        settings_form.addRow("Receipt Footer", self.settings_receipt_footer)
        settings_form.addRow("Logo", settings_logo_row)
        self.save_settings_button = QPushButton("Save Settings")
        settings_layout.addLayout(settings_form)
        settings_layout.addWidget(self.save_settings_button)
        self.tabs.addTab(self.settings_tab, "Settings")

        self.backup_tab = QWidget()
        backup_layout = QVBoxLayout(self.backup_tab)
        backup_buttons = QHBoxLayout()
        self.create_backup_button = QPushButton("Create Backup")
        self.restore_backup_button = QPushButton("Restore Backup")
        backup_buttons.addWidget(self.create_backup_button)
        backup_buttons.addWidget(self.restore_backup_button)
        backup_buttons.addStretch(1)
        self.backup_list = QListWidget()
        self.backup_status = QLabel("")
        backup_layout.addLayout(backup_buttons)
        backup_layout.addWidget(self.backup_list)
        backup_layout.addWidget(self.backup_status)
        self.tabs.addTab(self.backup_tab, "Backups")
        self.resize(1200, 800)

    def choose_settings_logo(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Select Logo", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if filename:
            self.settings_logo_path.setText(filename)

    def selected_backup_path(self) -> str:
        item = self.backup_list.currentItem()
        return item.text() if item else ""

    @staticmethod
    def _build_metric_card(title: str):
        card = QFrame()
        card.setStyleSheet("QFrame { background: white; border: 1px solid #d7cfc2; border-radius: 12px; }")
        layout = QVBoxLayout(card)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 10pt; color: #52606d; font-weight: 600;")
        value_label = QLabel("0")
        value_label.setStyleSheet("font-size: 24pt; font-weight: 700; color: #165b47;")
        meta_label = QLabel("")
        meta_label.setWordWrap(True)
        meta_label.setStyleSheet("color: #52606d;")
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addWidget(meta_label)
        layout.addStretch(1)
        return card, value_label, meta_label


class PosWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("POS Terminal")
        central = QWidget()
        root = QHBoxLayout(central)
        self.setCentralWidget(central)

        left_box = QGroupBox("Tables")
        left_layout = QVBoxLayout(left_box)
        self.table_list = QListWidget()
        left_layout.addWidget(self.table_list)

        middle_box = QGroupBox("Menu")
        middle_layout = QVBoxLayout(middle_box)
        self.category_filter = QComboBox()
        self.item_list = QListWidget()
        middle_layout.addWidget(self.category_filter)
        middle_layout.addWidget(self.item_list)

        right_box = QGroupBox("Active Ticket")
        right_layout = QVBoxLayout(right_box)
        self.user_label = QLabel("")
        self.order_meta = QLabel("Select a table to begin.")
        self.order_items_table = QTableWidget(0, 4)
        self.order_items_table.setHorizontalHeaderLabels(["ID", "Item", "Qty", "Line Total"])
        self.order_items_table.horizontalHeader().setStretchLastSection(True)
        adjustment_form = QFormLayout()
        self.discount_spin = MoneySpinBox()
        self.discount_spin.setMaximum(100000)
        self.discount_spin.setDecimals(2)
        self.service_charge_spin = MoneySpinBox()
        self.service_charge_spin.setMaximum(100000)
        self.service_charge_spin.setDecimals(2)
        adjustment_form.addRow("Discount", self.discount_spin)
        adjustment_form.addRow("Service Charge", self.service_charge_spin)
        payment_row = QHBoxLayout()
        self.payment_method = QComboBox()
        self.payment_method.addItems([method.value for method in PaymentMethod])
        self.amount_received = MoneySpinBox()
        self.amount_received.setMaximum(1000000)
        self.amount_received.setDecimals(2)
        payment_row.addWidget(QLabel("Method"))
        payment_row.addWidget(self.payment_method)
        payment_row.addWidget(QLabel("Received"))
        payment_row.addWidget(self.amount_received)
        self.totals_label = QLabel("")
        self.remove_item_button = QPushButton("Remove Selected Item")
        self.apply_adjustments_button = QPushButton("Apply Charges")
        self.pay_button = QPushButton("Take Payment")
        self.print_button = QPushButton("Print Receipt")
        self.save_pdf_button = QPushButton("Save Receipt PDF")
        self.logout_button = QPushButton("Logout")
        right_layout.addWidget(self.user_label)
        right_layout.addWidget(self.order_meta)
        right_layout.addWidget(self.order_items_table)
        right_layout.addLayout(adjustment_form)
        right_layout.addLayout(payment_row)
        right_layout.addWidget(self.totals_label)
        right_layout.addWidget(self.remove_item_button)
        right_layout.addWidget(self.apply_adjustments_button)
        right_layout.addWidget(self.pay_button)
        right_layout.addWidget(self.print_button)
        right_layout.addWidget(self.save_pdf_button)
        right_layout.addWidget(self.logout_button)
        right_layout.addStretch(1)

        root.addWidget(left_box, 1)
        root.addWidget(middle_box, 1)
        root.addWidget(right_box, 2)
        self.resize(1280, 800)

    @staticmethod
    def show_message(parent, title: str, text: str) -> None:
        QMessageBox.information(parent, title, text)

















