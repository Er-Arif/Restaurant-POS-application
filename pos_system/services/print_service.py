from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from pathlib import Path
from urllib.parse import quote

from PySide6.QtGui import QTextDocument
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import QDialog

from pos_system.config.app_config import APP_VENDOR, RECEIPTS_DIR, RECEIPT_PREVIEW_FILE
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

    def print_receipt_dialog(self, order: dict, settings: dict, parent=None) -> str:
        content = self.render_receipt(order, settings)
        archived_path = self.save_receipt_copy(order, content)
        printer = QPrinter(QPrinter.HighResolution)
        printer.setDocName(f"Receipt {order['order_number']}")
        dialog = QPrintDialog(printer, parent)
        if dialog.exec() != QDialog.Accepted:
            return f"Print cancelled. Receipt preview saved to {RECEIPT_PREVIEW_FILE}. Archived copy saved to {archived_path}."
        try:
            self._send_to_printer(self._build_document(self.render_receipt_html(order, settings), is_html=True), printer)
        except Exception as exc:
            return f"Unable to print receipt: {exc}. Receipt preview saved to {RECEIPT_PREVIEW_FILE}. Archived copy saved to {archived_path}."
        printer_name = printer.printerName() or "selected printer"
        return f"Receipt sent to {printer_name}. Archived copy saved to {archived_path}."

    def save_receipt_pdf(self, order: dict, settings: dict) -> Path:
        content = self.render_receipt(order, settings)
        self.save_receipt_copy(order, content)
        pdf_path = self._receipt_file_path(order, ".pdf")
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(str(pdf_path))
        printer.setDocName(f"Receipt {order['order_number']}")
        self._send_to_printer(self._build_document(self.render_receipt_html(order, settings), is_html=True), printer)
        return pdf_path

    def render_receipt(self, order: dict, settings: dict) -> str:
        currency = settings.get("currency_symbol", "?")
        divider = "-" * 36
        receipt_datetime_text = self._format_receipt_datetime(order)
        lines: list[str] = []

        restaurant_name = (settings.get("restaurant_name") or "Restaurant POS").strip()
        address = (settings.get("address") or "").strip()
        phone = (settings.get("phone") or "").strip()
        footer = (settings.get("receipt_footer") or "").strip()
        powered_by = f"Powered by {APP_VENDOR}"

        if restaurant_name:
            lines.append(restaurant_name)
        if address:
            lines.append(address)
        if phone:
            lines.append(f"Phone: {phone}")
        lines.extend(
            [
                divider,
                f"Order: {order['order_number']}",
                f"Table: {order['table_name']}",
                f"Cashier: {order['created_by_username']}",
                f"Date: {receipt_datetime_text}",
                divider,
            ]
        )
        for item in order["items"]:
            lines.append(f"{item['name']} x{item['quantity']} {money_text(item['line_total'], currency)}")
        lines.extend(
            [
                divider,
                f"Subtotal: {money_text(order['subtotal'], currency)}",
                f"Discount: {money_text(order['discount_amount'], currency)}",
                f"Service: {money_text(order['service_charge_amount'], currency)}",
                f"GST: {money_text(order['gst_amount'], currency)}",
                f"Total: {money_text(order['grand_total'], currency)}",
                "",
                divider,
            ]
        )
        if footer:
            lines.append(footer)
        lines.append(powered_by)
        receipt_text = "\n".join(lines) + "\n"
        RECEIPT_PREVIEW_FILE.write_text(receipt_text, encoding="utf-8")
        return receipt_text

    def render_receipt_html(self, order: dict, settings: dict) -> str:
        currency = settings.get("currency_symbol", "?")
        divider = escape("-" * 36)
        receipt_datetime_text = escape(self._format_receipt_datetime(order))
        logo_path = (settings.get("logo_path") or "").strip()
        restaurant_name = escape((settings.get("restaurant_name") or "Restaurant POS").strip())
        address = escape((settings.get("address") or "").strip())
        phone = escape((settings.get("phone") or "").strip())
        footer = escape((settings.get("receipt_footer") or "").strip())
        powered_by = escape(f"Powered by {APP_VENDOR}")

        top_lines: list[str] = []
        if logo_path and Path(logo_path).exists():
            top_lines.append(
                f"<div style='margin:0 0 2px 0; line-height:1;'><img src='{self._path_to_file_uri(logo_path)}' style='display:block; margin:0; max-height:34px; max-width:110px; width:auto; height:auto;' /></div>"
            )
        if restaurant_name:
            top_lines.append(f"<div style='margin:0;'>{restaurant_name}</div>")
        if address:
            top_lines.append(f"<div style='margin:0;'>{address}</div>")
        if phone:
            top_lines.append(f"<div style='margin:0;'>Phone: {phone}</div>")

        item_lines = "".join(
            f"<div>{escape(item['name'])} x{item['quantity']} {escape(money_text(item['line_total'], currency))}</div>"
            for item in order["items"]
        )

        footer_html = f"<div>{footer}</div>" if footer else ""
        return (
            "<div style='margin:0; padding:0; font-family: Consolas, Courier New, monospace; font-size: 10pt; line-height: 1.35;'>"
            "<div style='width:280px; margin:0 auto; padding:0;'>"
            f"<div style='margin:0; padding:0;'>{''.join(top_lines)}</div>"
            f"<div style='margin:0;'>{divider}</div>"
            f"<div style='margin:0;'>Order: {escape(order['order_number'])}</div>"
            f"<div style='margin:0;'>Table: {escape(order['table_name'])}</div>"
            f"<div style='margin:0;'>Cashier: {escape(order['created_by_username'])}</div>"
            f"<div style='margin:0;'>Date: {receipt_datetime_text}</div>"
            f"<div style='margin:0;'>{divider}</div>"
            f"{item_lines}"
            f"<div style='margin:0;'>{divider}</div>"
            f"<div style='margin:0;'>Subtotal: {escape(money_text(order['subtotal'], currency))}</div>"
            f"<div style='margin:0;'>Discount: {escape(money_text(order['discount_amount'], currency))}</div>"
            f"<div style='margin:0;'>Service: {escape(money_text(order['service_charge_amount'], currency))}</div>"
            f"<div style='margin:0;'>GST: {escape(money_text(order['gst_amount'], currency))}</div>"
            f"<div style='margin:0;'><strong>Total: {escape(money_text(order['grand_total'], currency))}</strong></div>"
            f"<div style='margin-top:6px;'>{divider}</div>"
            f"{footer_html}"
            f"<div style='margin:0;'>{powered_by}</div>"
            "</div>"
            "</div>"
        )

    def save_receipt_copy(self, order: dict, receipt_text: str) -> Path:
        filename = self._receipt_file_path(order, ".txt")
        filename.write_text(receipt_text, encoding="utf-8")
        return filename

    def _receipt_file_path(self, order: dict, suffix: str) -> Path:
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        safe_order_number = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in order["order_number"])
        return RECEIPTS_DIR / f"receipt_{safe_order_number}_{timestamp}{suffix}"

    def _build_document(self, content: str, *, is_html: bool = True) -> QTextDocument:
        document = QTextDocument()
        if is_html:
            document.setHtml(content)
        else:
            document.setHtml(f"<pre style='font-family: Consolas, Courier New, monospace; font-size: 10pt;'>{escape(content)}</pre>")
        return document

    def _send_to_printer(self, document: QTextDocument, printer: QPrinter) -> None:
        print_method = getattr(document, "print", None) or getattr(document, "print_", None)
        if print_method is None:
            raise RuntimeError("QTextDocument printing is unavailable in this Qt build.")
        print_method(printer)

    @staticmethod
    def _path_to_file_uri(path: str) -> str:
        resolved = Path(path).resolve().as_posix()
        return f"file:///{quote(resolved, safe='/:')}"

    @staticmethod
    def _format_receipt_datetime(order: dict) -> str:
        receipt_datetime = order.get("created_at")
        if isinstance(receipt_datetime, datetime):
            if receipt_datetime.tzinfo is None:
                receipt_datetime = receipt_datetime.replace(tzinfo=UTC)
            return receipt_datetime.astimezone().strftime("%Y-%m-%d %H:%M")
        return datetime.now(UTC).astimezone().strftime("%Y-%m-%d %H:%M")

