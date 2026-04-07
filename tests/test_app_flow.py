from __future__ import annotations

import os
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from license_generator import create_license, generate_keypair  # noqa: E402
from pos_system.config import app_config  # noqa: E402
from pos_system.controllers.admin_controller import AdminController  # noqa: E402
from pos_system.controllers.app_controller import AppController  # noqa: E402
from pos_system.controllers.pos_controller import PosController  # noqa: E402
from pos_system.database.bootstrap import initialize_database  # noqa: E402
from pos_system.database.session import SessionLocal, engine, session_scope  # noqa: E402
from pos_system.models.entities import Category, LicenseRecord, MenuItem, Order, OrderItem, Payment, RestaurantSettings, Table, User  # noqa: E402
from pos_system.models.enums import StartupStatus, UserRole  # noqa: E402
from pos_system.services.auth_service import AuthService  # noqa: E402
from pos_system.services.backup_service import BackupService  # noqa: E402
from pos_system.services.license_service import LicenseService  # noqa: E402
from pos_system.services.menu_service import MenuService  # noqa: E402
from pos_system.services.order_service import OrderService  # noqa: E402
from pos_system.services.payment_service import PaymentService  # noqa: E402
from pos_system.services.print_service import PrintService  # noqa: E402
from pos_system.services.report_service import ReportService  # noqa: E402
from pos_system.services.settings_service import SettingsService  # noqa: E402
from pos_system.services.table_service import TableService  # noqa: E402
from pos_system.ui.screens import AdminDashboardWindow, PosWindow  # noqa: E402


class AppFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        initialize_database()

    @classmethod
    def tearDownClass(cls):
        SessionLocal.remove()
        engine.dispose()

    def setUp(self):
        SessionLocal.remove()
        with session_scope() as session:
            for model in (Payment, OrderItem, Order, MenuItem, Category, Table, LicenseRecord, RestaurantSettings, User):
                session.query(model).delete()
        for path in app_config.RECEIPTS_DIR.glob("receipt_*.txt"):
            path.unlink()
        for path in app_config.RECEIPTS_DIR.glob("receipt_*.pdf"):
            path.unlink()
        for path in app_config.BACKUP_DIR.glob("*.db"):
            path.unlink()
        if app_config.RECEIPT_PREVIEW_FILE.exists():
            app_config.RECEIPT_PREVIEW_FILE.unlink()
        if app_config.LICENSE_FILE.exists():
            app_config.LICENSE_FILE.unlink()
        os.environ.pop(app_config.DEV_BYPASS_ENV, None)
        key_dir = app_config.project_root() / ".runtime" / "flow_keys"
        key_dir.mkdir(parents=True, exist_ok=True)
        self.private_key_path = key_dir / "private.pem"
        self.public_key_path = app_config.BUNDLED_PUBLIC_KEY
        generate_keypair(self.private_key_path, self.public_key_path)

    def _activate_license(self) -> None:
        service = LicenseService()
        license_key = create_license(
            private_key_path=self.private_key_path,
            hardware_id=service.get_hardware_fingerprint(),
            license_type="trial",
            expiry_date=(date.today() + timedelta(days=14)).isoformat(),
        )
        result = service.activate(license_key)
        self.assertTrue(result.success)

    def _seed_ready_state(self):
        self._activate_license()
        settings = SettingsService()
        auth = AuthService()
        tables = TableService()
        menu = MenuService()
        settings.save_settings(
            {
                "restaurant_name": "Flow Cafe",
                "address": "1 Test Street",
                "phone": "9999999999",
                "gst_number": "GSTFLOW",
                "currency_symbol": "?",
                "receipt_footer": "See you soon",
                "gst_percent": 5,
                "default_discount_amount": 0,
                "default_service_charge_amount": 0,
                "setup_complete": True,
            }
        )
        admin = auth.create_user("adminflow", "pass123", UserRole.ADMIN)
        staff = auth.create_user("staffflow", "pass123", UserRole.STAFF)
        table_rows = tables.initialize_tables(2, "T")
        category = menu.save_category("Main")
        item = menu.save_menu_item({"category_id": category["id"], "name": "Burger", "description": "", "price": 150, "is_available": True})
        return {"admin": admin, "staff": staff, "tables": table_rows, "item": item}

    def test_startup_state_transitions(self):
        service = LicenseService()
        self.assertEqual(service.validate_startup().status, StartupStatus.NEEDS_ACTIVATION)
        self._activate_license()
        self.assertEqual(service.validate_startup().status, StartupStatus.NEEDS_SETUP)
        AuthService().create_user("starter", "pass123", UserRole.ADMIN)
        self.assertEqual(service.validate_startup().status, StartupStatus.READY)

    def test_developer_bypass_skips_activation(self):
        os.environ[app_config.DEV_BYPASS_ENV] = "1"
        controller = AppController(self.app)
        controller.prepare_developer_bypass()
        service = LicenseService()
        self.assertEqual(service.validate_startup().status, StartupStatus.READY)
        session_user = AuthService().login("arif", "arif123")
        self.assertEqual(session_user.username, "arif")
        self.assertEqual(session_user.role, UserRole.ADMIN)

    def test_inactive_user_cannot_login(self):
        auth = AuthService()
        auth.create_user("inactive", "pass123", UserRole.STAFF, is_active=False)
        with self.assertRaisesRegex(ValueError, "inactive"):
            auth.login("inactive", "pass123")

    def test_cancel_order_before_payment(self):
        seeded = self._seed_ready_state()
        order_service = OrderService()
        order = order_service.open_table_order(seeded["tables"][0]["id"], seeded["admin"]["id"])
        cancelled = order_service.cancel_order(order["id"])
        self.assertEqual(cancelled["status"], "cancelled")

    def test_backup_and_restore_round_trip(self):
        self._seed_ready_state()
        settings_service = SettingsService()
        backup_service = BackupService()
        settings_service.save_settings({"restaurant_name": "Before Backup", "setup_complete": True})
        backup_path = backup_service.create_backup()
        self.assertTrue(Path(backup_path).exists())
        settings_service.save_settings({"restaurant_name": "After Backup", "setup_complete": True})
        backup_service.restore_backup(backup_path)
        SessionLocal.remove()
        restored_name = settings_service.get_settings()["restaurant_name"]
        self.assertEqual(restored_name, "Before Backup")

    @patch.object(QMessageBox, "information")
    @patch.object(QMessageBox, "warning")
    def test_admin_controller_happy_path(self, mock_warning, mock_info):
        self._activate_license()
        SettingsService().save_settings({"restaurant_name": "Admin Cafe", "setup_complete": True})
        AuthService().create_user("admin", "pass123", UserRole.ADMIN)

        window = AdminDashboardWindow()
        controller = AdminController(
            window=window,
            auth_service=AuthService(),
            settings_service=SettingsService(),
            menu_service=MenuService(),
            order_service=OrderService(),
            report_service=ReportService(),
            backup_service=BackupService(),
            table_service=TableService(),
        )
        controller.load()

        window.category_name.setText("Starters")
        window.category_description.setPlainText("Snacks")
        controller.save_category()
        self.assertEqual(len(MenuService().list_categories()), 1)

        window.item_category_combo.setCurrentIndex(0)
        window.item_name.setText("Soup")
        window.item_description.setPlainText("Hot")
        window.item_price.setValue(120)
        controller.save_item()
        self.assertEqual(len(MenuService().list_menu_items()), 1)

        window.user_username.setText("staff1")
        window.user_password.setText("pass123")
        window.user_role.setCurrentText("staff")
        controller.save_user()
        self.assertEqual(len(AuthService().list_users()), 2)

        window.settings_restaurant_name.setText("Admin Cafe Updated")
        controller.save_settings()
        self.assertEqual(SettingsService().get_settings()["restaurant_name"], "Admin Cafe Updated")
        self.assertFalse(mock_warning.called)

    @patch.object(QMessageBox, "information")
    @patch.object(QMessageBox, "warning")
    def test_staff_pos_flow(self, mock_warning, mock_info):
        self._seed_ready_state()
        session_user = AuthService().login("staffflow", "pass123")
        window = PosWindow()
        controller = PosController(
            window=window,
            session_user=session_user,
            settings_service=SettingsService(),
            menu_service=MenuService(),
            table_service=TableService(),
            order_service=OrderService(),
            payment_service=PaymentService(),
            print_service=PrintService(),
        )
        controller.load()

        table_item = window.table_list.item(0)
        controller.on_table_selected(table_item)
        menu_item_widget = window.item_list.item(0)
        controller.add_selected_item(menu_item_widget)
        window.payment_method.setCurrentText("cash")
        window.amount_received.setValue(200)
        controller.take_payment()

        paid_orders = OrderService().list_orders("paid")
        self.assertEqual(len(paid_orders), 1)
        self.assertIsNotNone(controller.last_completed_order)
        self.assertTrue(app_config.RECEIPT_PREVIEW_FILE.exists())
        self.assertGreaterEqual(len(list(app_config.RECEIPTS_DIR.glob("receipt_*.txt"))), 1)
        self.assertGreaterEqual(len(list(app_config.RECEIPTS_DIR.glob("receipt_*.pdf"))), 1)

        controller.print_service.print_receipt_dialog = Mock(return_value="Receipt sent")
        controller.reprint_receipt()
        controller.print_service.print_receipt_dialog.assert_called_once()

        controller.export_receipt_pdf()
        self.assertGreaterEqual(mock_info.call_count, 2)
        self.assertFalse(mock_warning.called)


if __name__ == "__main__":
    unittest.main()

