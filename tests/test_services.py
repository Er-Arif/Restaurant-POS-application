from __future__ import annotations

import os
import unittest
from datetime import date, timedelta
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from license_generator import create_license
from pos_system.config import app_config
from pos_system.database.bootstrap import initialize_database
from pos_system.database.session import SessionLocal, engine, session_scope
from pos_system.models.entities import Category, LicenseRecord, MenuItem, Order, OrderItem, Payment, RestaurantSettings, Table, User
from pos_system.models.enums import UserRole
from pos_system.services.auth_service import AuthService
from pos_system.services.license_service import LicenseService
from pos_system.services.menu_service import MenuService
from pos_system.services.order_service import OrderService
from pos_system.services.payment_service import PaymentService
from pos_system.services.print_service import PrintService
from pos_system.services.report_service import ReportService
from pos_system.services.settings_service import SettingsService
from pos_system.services.table_service import TableService


class ServiceTests(unittest.TestCase):
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
        if app_config.RECEIPT_PREVIEW_FILE.exists():
            app_config.RECEIPT_PREVIEW_FILE.unlink()

    def test_password_hashing_login(self):
        auth = AuthService()
        username = f"user_{id(self)}"
        auth.create_user(username, "pass123", UserRole.STAFF)
        session_user = auth.login(username, "pass123")
        self.assertEqual(session_user.username, username)

    def test_order_pricing_and_payment(self):
        auth = AuthService()
        settings = SettingsService()
        menu = MenuService()
        tables = TableService()
        orders = OrderService()
        payments = PaymentService()

        username = f"cashier_{id(self)}"
        user = auth.create_user(username, "pass123", UserRole.ADMIN)
        settings.save_settings(
            {
                "restaurant_name": "Test Cafe",
                "gst_percent": 5,
                "default_discount_amount": 10,
                "default_service_charge_amount": 20,
                "setup_complete": True,
            }
        )
        table_rows = tables.initialize_tables(2, "T")
        category = menu.save_category("Food", "Main food")
        item = menu.save_menu_item(
            {
                "category_id": category["id"],
                "name": "Paneer Wrap",
                "description": "Test",
                "price": 100,
                "is_available": True,
            }
        )
        order = orders.open_table_order(table_rows[0]["id"], user["id"])
        order = orders.add_item(order["id"], item["id"], qty=2)
        self.assertAlmostEqual(order["subtotal"], 200.0, places=2)
        payment = payments.settle(order["id"], "cash", 500)
        self.assertAlmostEqual(payment["change_returned"], 279.5, places=2)

    def test_license_activation_and_validation(self):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        app_config.BUNDLED_PUBLIC_KEY.write_bytes(public_bytes)
        temp_dir = app_config.project_root() / ".runtime" / "test_keys"
        temp_dir.mkdir(parents=True, exist_ok=True)
        private_path = temp_dir / "private.pem"
        private_path.write_bytes(private_bytes)
        service = LicenseService()
        key = create_license(
            private_key_path=private_path,
            hardware_id=service.get_hardware_fingerprint(),
            license_type="trial",
            expiry_date=(date.today() + timedelta(days=7)).isoformat(),
        )
        result = service.activate(key)
        self.assertTrue(result.success)
        validated = service.validate_installed_license()
        self.assertTrue(validated.success)

    def test_report_export(self):
        auth = AuthService()
        settings = SettingsService()
        menu = MenuService()
        tables = TableService()
        orders = OrderService()
        payments = PaymentService()
        username = f"reporter_{id(self)}"
        user = auth.create_user(username, "pass123", UserRole.ADMIN)
        settings.save_settings({"restaurant_name": "Export Cafe", "gst_percent": 5, "setup_complete": True})
        table_rows = tables.initialize_tables(1, "T")
        category = menu.save_category("Drinks")
        item = menu.save_menu_item({"category_id": category["id"], "name": "Tea", "description": "", "price": 50, "is_available": True})
        order = orders.open_table_order(table_rows[0]["id"], user["id"])
        order = orders.add_item(order["id"], item["id"], qty=1)
        payments.settle(order["id"], "upi", 50)
        report_service = ReportService()
        filename = report_service.export_orders_csv(
            {"start_date": date.today() - timedelta(days=1), "end_date": date.today() + timedelta(days=1)}
        )
        self.assertTrue(Path(filename).exists())

    def test_receipt_archive_save(self):
        print_service = PrintService()
        order = {
            "order_number": "T1-20260408101010",
            "table_name": "T1",
            "created_by_username": "admin",
            "subtotal": 330,
            "discount_amount": 0,
            "service_charge_amount": 0,
            "gst_amount": 0,
            "grand_total": 330,
            "items": [
                {"name": "Butter Chicken", "quantity": 1, "line_total": 250},
                {"name": "Naan", "quantity": 2, "line_total": 80},
            ],
            "payments": [
                {"method": "cash", "amount_received": 500, "change_returned": 170},
            ],
        }
        settings = {
            "restaurant_name": "Test Cafe",
            "address": "Main Road",
            "phone": "1234567890",
            "gst_number": "GST123",
            "currency_symbol": "?",
            "receipt_footer": "Thank you!",
        }
        message = print_service.print_receipt(order, settings)
        archived_receipts = list(app_config.RECEIPTS_DIR.glob("receipt_T1-20260408101010_*.txt"))
        self.assertTrue(app_config.RECEIPT_PREVIEW_FILE.exists())
        self.assertEqual(len(archived_receipts), 1)
        self.assertIn("Archived copy saved to", message)

    def test_receipt_pdf_save(self):
        print_service = PrintService()
        order = {
            "order_number": "T2-20260408121212",
            "table_name": "T2",
            "created_by_username": "staff",
            "subtotal": 200,
            "discount_amount": 10,
            "service_charge_amount": 20,
            "gst_amount": 10.5,
            "grand_total": 220.5,
            "items": [
                {"name": "Fried Rice", "quantity": 1, "line_total": 200},
            ],
            "payments": [
                {"method": "upi", "amount_received": 220.5, "change_returned": 0},
            ],
        }
        settings = {
            "restaurant_name": "PDF Cafe",
            "address": "Main Road",
            "phone": "1234567890",
            "gst_number": "GST123",
            "currency_symbol": "?",
            "receipt_footer": "Thank you!",
        }
        pdf_path = print_service.save_receipt_pdf(order, settings)
        archived_receipts = list(app_config.RECEIPTS_DIR.glob("receipt_T2-20260408121212_*.txt"))
        self.assertTrue(app_config.RECEIPT_PREVIEW_FILE.exists())
        self.assertEqual(len(archived_receipts), 1)
        self.assertTrue(pdf_path.exists())
        self.assertGreater(pdf_path.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
