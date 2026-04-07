from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pos_system.config.app_config import RECEIPTS_DIR, RECEIPT_PREVIEW_FILE
from pos_system.utils.formatting import money_text

try:
    import win32print
except ImportError:  # pragma: no cover
    win32print = None


class PrintService:
    def print_receipt(self, order: dict, settings: dict) -> str:
        content = self.render_receipt(order, settings)
        archived_path = self.save_receipt_copy(order, content)
        if win32print is None:
            return f"Printer driver unavailable. Receipt preview saved to {RECEIPT_PREVIEW_FILE}. Archived copy saved to {archived_path}."
        try:
            printer_name = win32print.GetDefaultPrinter()
            handle = win32print.OpenPrinter(printer_name)
        except Exception:
            return f"Default printer unavailable. Receipt preview saved to {RECEIPT_PREVIEW_FILE}. Archived copy saved to {archived_path}."
        try:
            win32print.StartDocPrinter(handle, 1, ("Restaurant Receipt", None, "RAW"))
            win32print.StartPagePrinter(handle)
            win32print.WritePrinter(handle, content.encode("utf-8"))
            win32print.EndPagePrinter(handle)
            win32print.EndDocPrinter(handle)
            return f"Receipt sent to {printer_name}. Archived copy saved to {archived_path}."
        finally:
            win32print.ClosePrinter(handle)

    def render_receipt(self, order: dict, settings: dict) -> str:
        currency = settings.get("currency_symbol", "₹")
        lines = [
            settings.get("restaurant_name", "Restaurant POS"),
            settings.get("address", ""),
            f"Phone: {settings.get('phone', '')}",
            f"GST: {settings.get('gst_number', '')}",
            "-" * 36,
            f"Order: {order['order_number']}",
            f"Table: {order['table_name']}",
            f"Cashier: {order['created_by_username']}",
            "-" * 36,
        ]
        for item in order["items"]:
            lines.append(f"{item['name']} x{item['quantity']} {money_text(item['line_total'], currency)}")
        lines.extend(
            [
                "-" * 36,
                f"Subtotal: {money_text(order['subtotal'], currency)}",
                f"Discount: {money_text(order['discount_amount'], currency)}",
                f"Service: {money_text(order['service_charge_amount'], currency)}",
                f"GST: {money_text(order['gst_amount'], currency)}",
                f"Total: {money_text(order['grand_total'], currency)}",
            ]
        )
        if order["payments"]:
            payment = order["payments"][0]
            lines.extend(
                [
                    f"Paid via: {payment['method'].upper()}",
                    f"Received: {money_text(payment['amount_received'], currency)}",
                    f"Change: {money_text(payment['change_returned'], currency)}",
                ]
            )
        footer = settings.get("receipt_footer", "").strip()
        if footer:
            lines.extend(["-" * 36, footer])
        receipt_text = "\n".join(lines) + "\n"
        RECEIPT_PREVIEW_FILE.write_text(receipt_text, encoding="utf-8")
        return receipt_text

    def save_receipt_copy(self, order: dict, receipt_text: str) -> Path:
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        safe_order_number = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in order["order_number"])
        filename = RECEIPTS_DIR / f"receipt_{safe_order_number}_{timestamp}.txt"
        filename.write_text(receipt_text, encoding="utf-8")
        return filename
