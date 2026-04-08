from __future__ import annotations

import base64
import os
import unittest
from datetime import UTC, date, datetime, timedelta
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
        self.assertAlmostEqual(order["discount_percent"], 10.0, places=2)
        self.assertAlmostEqual(order["service_charge_percent"], 20.0, places=2)
        self.assertAlmostEqual(order["discount_amount"], 20.0, places=2)
        self.assertAlmostEqual(order["service_charge_amount"], 36.0, places=2)
        self.assertAlmostEqual(order["grand_total"], 226.8, places=2)
        payment = payments.settle(order["id"], "cash", 500)
        self.assertAlmostEqual(payment["paid_amount"], 227.0, places=2)
        self.assertAlmostEqual(payment["change_returned"], 273.0, places=2)

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
        order = orders.add_item(order["id"], item["id"], qty=2)
        payments.settle(order["id"], "upi", 200)
        report_service = ReportService()
        summary = report_service.sales_summary(date.today() - timedelta(days=1), date.today() + timedelta(days=1))
        self.assertEqual(summary.order_count, 1)
        self.assertEqual(summary.top_items[0][0], "Tea")
        self.assertEqual(summary.top_items[0][1], 2)
        self.assertEqual(len(summary.recent_orders), 1)
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

    def test_receipt_html_includes_logo_image_when_configured(self):
        logo_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a6xQAAAAASUVORK5CYII="
        )
        logo_path = app_config.LOGO_DIR / "test_logo.png"
        logo_path.write_bytes(logo_bytes)
        print_service = PrintService()
        html = print_service.render_receipt_html(
            {
                "order_number": "PREVIEW-LOGO",
                "table_name": "T1",
                "created_by_username": "arif",
                "created_at": datetime(2026, 4, 9, 14, 30, tzinfo=UTC),
                "subtotal": 100,
                "discount_amount": 0,
                "service_charge_amount": 0,
                "gst_amount": 5,
                "grand_total": 105,
                "items": [{"name": "Tea", "quantity": 1, "line_total": 100}],
                "payments": [],
            },
            {
                "restaurant_name": "Logo Cafe",
                "address": "Road 1",
                "phone": "123",
                "currency_symbol": "?",
                "receipt_footer": "Thanks",
                "logo_path": str(logo_path),
            },
        )
        self.assertIn("<img src=", html)
        self.assertIn("Logo Cafe", html)

    def test_receipt_layout_uses_admin_settings(self):
        settings_service = SettingsService()
        print_service = PrintService()
        saved = settings_service.save_settings(
            {
                "restaurant_name": "Design Cafe",
                "address": "42 Market Road",
                "phone": "9999999999",
                "gst_number": "GST-DESIGN",
                "currency_symbol": "?",
                "receipt_footer": "Come back soon!",
                "setup_complete": True,
            }
        )
        self.assertEqual(saved["restaurant_name"], "Design Cafe")
        self.assertEqual(saved["receipt_footer"], "Come back soon!")

        receipt_text = print_service.render_receipt(
            {
                "order_number": "PREVIEW-42",
                "table_name": "T9",
                "created_by_username": "arif",
                "subtotal": 100,
                "discount_amount": 5,
                "service_charge_amount": 10,
                "gst_amount": 5.25,
                "grand_total": 110.25,
                "items": [{"name": "Coffee", "quantity": 2, "line_total": 100}],
                "payments": [{"method": "upi", "amount_received": 110.25, "change_returned": 0}],
            },
            settings_service.get_settings(),
        )
        self.assertIn("Design Cafe", receipt_text)
        self.assertIn("42 Market Road", receipt_text)
        self.assertIn("Phone: 9999999999", receipt_text)
        self.assertIn("Order: PREVIEW-42", receipt_text)
        self.assertIn("Table: T9", receipt_text)
        self.assertIn("Cashier: arif", receipt_text)
        self.assertIn("Date: 2026-04-09", receipt_text)
        self.assertIn("Come back soon!", receipt_text)
        self.assertIn("Powered by", receipt_text)



if __name__ == "__main__":
    unittest.main()
