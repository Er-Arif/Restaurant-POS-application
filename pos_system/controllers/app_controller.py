from __future__ import annotations

from PySide6.QtWidgets import QApplication

from pos_system.config.app_config import developer_license_bypass_enabled
from pos_system.controllers.admin_controller import AdminController
from pos_system.controllers.pos_controller import PosController
from pos_system.database.bootstrap import initialize_database
from pos_system.models.enums import StartupStatus, UserRole
from pos_system.services.auth_service import AuthService
from pos_system.services.backup_service import BackupService
from pos_system.services.license_service import LicenseService
from pos_system.services.menu_service import MenuService
from pos_system.services.order_service import OrderService
from pos_system.services.payment_service import PaymentService
from pos_system.services.print_service import PrintService
from pos_system.services.report_service import ReportService
from pos_system.services.settings_service import SettingsService
from pos_system.services.table_service import TableService
from pos_system.ui.screens import ActivationScreen, AdminDashboardWindow, LoginScreen, PosWindow, SetupWizardScreen


class AppController:
    DEV_ADMIN_USERNAME = "arif"
    DEV_ADMIN_PASSWORD = "arif123"

    def __init__(self, app: QApplication):
        self.app = app
        initialize_database()
        self.license_service = LicenseService()
        self.auth_service = AuthService()
        self.settings_service = SettingsService()
        self.menu_service = MenuService()
        self.table_service = TableService()
        self.order_service = OrderService()
        self.payment_service = PaymentService()
        self.report_service = ReportService()
        self.backup_service = BackupService()
        self.print_service = PrintService()

        self.activation_screen = None
        self.setup_screen = None
        self.login_screen = None
        self.admin_window = None
        self.pos_window = None

    def start(self) -> None:
        if developer_license_bypass_enabled():
            self.prepare_developer_bypass()
        state = self.license_service.validate_startup()
        if state.status == StartupStatus.NEEDS_ACTIVATION:
            self.show_activation()
        elif state.status == StartupStatus.NEEDS_SETUP:
            self.show_setup()
        else:
            self.show_login()

    def show_activation(self) -> None:
        self.close_current_windows()
        screen = ActivationScreen()
        screen.hardware_value.setText(self.license_service.get_hardware_fingerprint())
        screen.activate_button.clicked.connect(lambda: self.activate_license(screen))
        self.activation_screen = screen
        screen.show()

    def activate_license(self, screen: ActivationScreen) -> None:
        try:
            result = self.license_service.activate(screen.license_input.toPlainText())
            screen.feedback_label.setText(result.message)
            self.show_setup()
        except Exception as exc:
            screen.feedback_label.setText(str(exc))

    def show_setup(self) -> None:
        self.close_current_windows()
        screen = SetupWizardScreen()
        screen.logo_browse.clicked.connect(screen.choose_logo)
        screen.create_button.clicked.connect(lambda: self.complete_setup(screen))
        self.setup_screen = screen
        screen.show()

    def complete_setup(self, screen: SetupWizardScreen) -> None:
        try:
            if screen.admin_password.text() != screen.admin_confirm_password.text():
                raise ValueError("Passwords do not match.")
            self.settings_service.save_settings(
                {
                    "restaurant_name": screen.restaurant_name.text(),
                    "address": screen.address.toPlainText(),
                    "phone": screen.phone.text(),
                    "gst_number": screen.gst_number.text(),
                    "currency_symbol": screen.currency_symbol.text(),
                    "receipt_footer": screen.receipt_footer.toPlainText(),
                    "gst_percent": screen.gst_percent.value(),
                    "default_discount_amount": screen.discount_amount.value(),
                    "default_service_charge_amount": screen.service_charge.value(),
                    "logo_source_path": screen.logo_path.text(),
                    "setup_complete": True,
                }
            )
            self.auth_service.create_user(
                username=screen.admin_username.text(),
                password=screen.admin_password.text(),
                role=UserRole.ADMIN,
                is_active=True,
            )
            self.table_service.initialize_tables(screen.table_count.value(), screen.table_prefix.text() or "T")
            self.seed_default_categories()
            self.show_login()
        except Exception as exc:
            screen.feedback_label.setText(str(exc))

    def show_login(self) -> None:
        self.close_current_windows()
        screen = LoginScreen()
        if developer_license_bypass_enabled():
            screen.username.setText(self.DEV_ADMIN_USERNAME)
            screen.password.setText(self.DEV_ADMIN_PASSWORD)
            screen.feedback_label.setText("Developer bypass enabled. Use the prefilled admin login.")
        screen.login_button.clicked.connect(lambda: self.login(screen))
        self.login_screen = screen
        screen.show()

    def login(self, screen: LoginScreen) -> None:
        try:
            user = self.auth_service.login(screen.username.text(), screen.password.text())
            if user.role == UserRole.ADMIN:
                self.show_admin(user)
            else:
                self.show_pos(user)
        except Exception as exc:
            screen.feedback_label.setText(str(exc))

    def show_admin(self, session_user) -> None:
        self.close_current_windows()
        window = AdminDashboardWindow()
        controller = AdminController(
            window=window,
            auth_service=self.auth_service,
            settings_service=self.settings_service,
            menu_service=self.menu_service,
            order_service=self.order_service,
            report_service=self.report_service,
            backup_service=self.backup_service,
            table_service=self.table_service,
        )
        controller.load()
        window.logout_button.clicked.connect(self.show_login)
        window.open_pos_button.clicked.connect(lambda: self.show_pos(session_user))
        self.admin_window = window
        self.admin_controller = controller
        window.show()

    def show_pos(self, session_user) -> None:
        self.close_current_windows()
        window = PosWindow()
        controller = PosController(
            window=window,
            session_user=session_user,
            settings_service=self.settings_service,
            menu_service=self.menu_service,
            table_service=self.table_service,
            order_service=self.order_service,
            payment_service=self.payment_service,
            print_service=self.print_service,
        )
        controller.load()
        window.logout_button.clicked.connect(self.show_login)
        self.pos_window = window
        self.pos_controller = controller
        window.show()

    def close_current_windows(self) -> None:
        for attr in ("activation_screen", "setup_screen", "login_screen", "admin_window", "pos_window"):
            window = getattr(self, attr, None)
            if window:
                window.close()
                setattr(self, attr, None)

    def seed_default_categories(self) -> None:
        if self.menu_service.list_categories():
            return
        for name in ("Starters", "Main Course", "Beverages", "Desserts"):
            self.menu_service.save_category(name=name, description=f"Default {name.lower()} category")

    def prepare_developer_bypass(self) -> None:
        self.settings_service.save_settings(
            {
                "restaurant_name": "Developer POS",
                "address": "Local Development Mode",
                "phone": "",
                "gst_number": "",
                "currency_symbol": "?",
                "receipt_footer": "Developer testing build",
                "gst_percent": 0,
                "default_discount_amount": 0,
                "default_service_charge_amount": 0,
                "setup_complete": True,
            }
        )
        existing_user = next((user for user in self.auth_service.list_users() if user["username"] == self.DEV_ADMIN_USERNAME), None)
        if existing_user:
            self.auth_service.update_user(
                user_id=existing_user["id"],
                username=self.DEV_ADMIN_USERNAME,
                role=UserRole.ADMIN,
                is_active=True,
                password=self.DEV_ADMIN_PASSWORD,
            )
        else:
            self.auth_service.create_user(
                username=self.DEV_ADMIN_USERNAME,
                password=self.DEV_ADMIN_PASSWORD,
                role=UserRole.ADMIN,
                is_active=True,
            )
        if not self.table_service.list_tables():
            self.table_service.initialize_tables(10, "T")
        self.seed_default_categories()
