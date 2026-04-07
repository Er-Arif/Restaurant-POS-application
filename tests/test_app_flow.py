from __future__ import annotations

import os
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
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
        admin = auth.create_user("adminflow", "pass123", UserRole.ADMIN, full_name="Admin Flow")
        staff = auth.create_user("staffflow", "pass123", UserRole.STAFF, full_name="Staff Flow")
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
    def test_category_add_mode_requires_new_category_action(self, mock_warning, mock_info):
        self._activate_license()
        SettingsService().save_settings({"restaurant_name": "Category Cafe", "setup_complete": True})
        auth = AuthService()
        auth.create_user("admincat", "pass123", UserRole.ADMIN)

        window = AdminDashboardWindow()
        controller = AdminController(
            window=window,
            auth_service=auth,
            settings_service=SettingsService(),
            menu_service=MenuService(),
            order_service=OrderService(),
            report_service=ReportService(),
            backup_service=BackupService(),
            table_service=TableService(),
            session_user=auth.login("admincat", "pass123"),
        )
        controller.load()

        self.assertEqual(window.save_category_button.text(), "Add Category")
        window.category_name.setText("Starters")
        window.category_description.setPlainText("Snacks")
        controller.save_category()
        categories = MenuService().list_categories()
        self.assertEqual(len(categories), 1)
        self.assertEqual(categories[0]["name"], "Starters")
        self.assertEqual(window.save_category_button.text(), "Update Category")

        window.category_name.setText("Starters Updated")
        controller.save_category()
        categories = MenuService().list_categories()
        self.assertEqual(len(categories), 1)
        self.assertEqual(categories[0]["name"], "Starters Updated")

        controller.clear_category_form()
        self.assertEqual(window.save_category_button.text(), "Add Category")
        window.category_name.setText("Beverages")
        window.category_description.setPlainText("Drinks")
        controller.save_category()
        categories = MenuService().list_categories()
        self.assertEqual(len(categories), 2)
        self.assertFalse(mock_warning.called)

    @patch.object(QMessageBox, "warning")
    def test_user_management_requires_admin_password_and_supports_update(self, mock_warning):
        self._activate_license()
        SettingsService().save_settings({"restaurant_name": "Users Cafe", "setup_complete": True})
        auth = AuthService()
        auth.create_user("admin", "pass123", UserRole.ADMIN, full_name="Admin User")

        window = AdminDashboardWindow()
        controller = AdminController(
            window=window,
            auth_service=auth,
            settings_service=SettingsService(),
            menu_service=MenuService(),
            order_service=OrderService(),
            report_service=ReportService(),
            backup_service=BackupService(),
            table_service=TableService(),
            session_user=auth.login("admin", "pass123"),
        )
        controller.load()

        self.assertEqual(window.save_user_button.text(), "Create User")
        self.assertEqual(window.clear_user_button.text(), "Add New User")
        window.user_full_name.setText("Aman Khan")
        window.user_username.setText("aman")
        window.user_password.setText("pass123")
        window.user_role.setCurrentText("staff")
        controller.save_user()
        mock_warning.assert_called_once()
        self.assertIn("admin password", mock_warning.call_args.args[2].lower())
        self.assertEqual(len(auth.list_users()), 1)

        mock_warning.reset_mock()
        window.user_admin_password.setText("pass123")
        controller.save_user()
        users = auth.list_users()
        self.assertEqual(len(users), 2)
        created = next(user for user in users if user["username"] == "aman")
        self.assertEqual(created["full_name"], "Aman Khan")
        self.assertEqual(window.save_user_button.text(), "Create User")
        self.assertEqual(window.user_password.placeholderText(), "Required for a new user")

        for row in range(window.users_table.rowCount()):
            if window.users_table.item(row, 0).data(Qt.UserRole) == created["id"]:
                window.users_table.selectRow(row)
                break
        controller.on_user_selected()
        self.assertEqual(window.save_user_button.text(), "Update User")
        self.assertEqual(window.user_password.placeholderText(), "Leave blank to keep the current password")
        self.assertEqual(window.user_username.text(), "aman")

        window.user_username.setText("aman.staff")
        window.user_password.setText("newpass123")
        window.user_admin_password.setText("wrongpass")
        controller.save_user()
        mock_warning.assert_called_once()
        self.assertIn("incorrect", mock_warning.call_args.args[2].lower())

        mock_warning.reset_mock()
        window.user_admin_password.setText("pass123")
        controller.save_user()
        updated = next(user for user in auth.list_users() if user["id"] == created["id"])
        self.assertEqual(updated["username"], "aman.staff")
        self.assertEqual(auth.login("aman.staff", "newpass123").username, "aman.staff")

    @patch.object(QMessageBox, "information")
    @patch.object(QMessageBox, "warning")
    def test_admin_controller_happy_path(self, mock_warning, mock_info):
        self._activate_license()
        SettingsService().save_settings({"restaurant_name": "Admin Cafe", "setup_complete": True})
        auth = AuthService()
        auth.create_user("admin", "pass123", UserRole.ADMIN, full_name="Admin User")

        window = AdminDashboardWindow()
        controller = AdminController(
            window=window,
            auth_service=auth,
            settings_service=SettingsService(),
            menu_service=MenuService(),
            order_service=OrderService(),
            report_service=ReportService(),
            backup_service=BackupService(),
            table_service=TableService(),
            session_user=auth.login("admin", "pass123"),
        )
        controller.load()
        self.assertIn("Admin Cafe", window.overview_headline.text())
        self.assertEqual(window.overview_orders_today_value.text(), "0")
        window.overview_users_button.click()
        self.assertIs(window.tabs.currentWidget(), window.users_tab)

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

        window.user_full_name.setText("Staff One")
        window.user_username.setText("staff1")
        window.user_password.setText("pass123")
        window.user_role.setCurrentText("staff")
        window.user_admin_password.setText("pass123")
        controller.save_user()
        users = AuthService().list_users()
        self.assertEqual(len(users), 2)
        staff_user = next(user for user in users if user["username"] == "staff1")
        self.assertEqual(staff_user["full_name"], "Staff One")

        window.settings_restaurant_name.setText("Admin Cafe Updated")
        controller.save_settings()
        self.assertEqual(SettingsService().get_settings()["restaurant_name"], "Admin Cafe Updated")
        self.assertIn("Users:", window.overview_operations_summary.text())
        self.assertFalse(mock_warning.called)

    @patch.object(QMessageBox, "information")
    @patch.object(QMessageBox, "warning")
    @patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes)
    def test_admin_orders_panel_manager_flow(self, mock_question, mock_warning, mock_info):
        seeded = self._seed_ready_state()
        order_service = OrderService()
        payment_service = PaymentService()
        auth = AuthService()

        open_order = order_service.open_table_order(seeded["tables"][0]["id"], seeded["staff"]["id"])
        order_service.add_item(open_order["id"], seeded["item"]["id"], qty=1)
        paid_order = order_service.open_table_order(seeded["tables"][1]["id"], seeded["staff"]["id"])
        paid_order = order_service.add_item(paid_order["id"], seeded["item"]["id"], qty=1)
        payment_service.settle(paid_order["id"], "cash", 200)

        window = AdminDashboardWindow()
        controller = AdminController(
            window=window,
            auth_service=auth,
            settings_service=SettingsService(),
            menu_service=MenuService(),
            order_service=OrderService(),
            report_service=ReportService(),
            backup_service=BackupService(),
            table_service=TableService(),
            session_user=auth.login("adminflow", "pass123"),
        )
        controller.load()

        window.order_search.setText("T2")
        controller.apply_order_filters()
        self.assertEqual(window.orders_table.rowCount(), 1)
        window.orders_table.selectRow(0)
        controller.on_order_selected()
        self.assertIn("Order #:", window.order_detail_summary.text())
        self.assertIn("CASH", window.order_detail_payments.toPlainText())
        self.assertTrue(window.print_order_receipt_button.isEnabled())
        self.assertTrue(window.save_order_pdf_button.isEnabled())

        controller.print_service.print_receipt_dialog = Mock(return_value="Receipt sent")
        controller.print_service.save_receipt_pdf = Mock(return_value=Path("receipt.pdf"))
        controller.print_selected_order_receipt()
        controller.save_selected_order_pdf()
        controller.print_service.print_receipt_dialog.assert_called_once()
        controller.print_service.save_receipt_pdf.assert_called_once()

        window.order_search.setText("T1")
        controller.apply_order_filters()
        window.orders_table.selectRow(0)
        controller.on_order_selected()
        self.assertTrue(window.cancel_order_button.isEnabled())
        controller.cancel_selected_order()
        self.assertGreaterEqual(mock_info.call_count, 3)
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
