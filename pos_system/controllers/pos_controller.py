from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem, QMessageBox, QTableWidgetItem


class PosController:
    def __init__(self, window, session_user, settings_service, menu_service, table_service, order_service, payment_service, print_service):
        self.window = window
        self.session_user = session_user
        self.settings_service = settings_service
        self.menu_service = menu_service
        self.table_service = table_service
        self.order_service = order_service
        self.payment_service = payment_service
        self.print_service = print_service
        self.selected_table_id = None
        self.current_order = None
        self.last_completed_order = None
        self._bind()

    def _bind(self) -> None:
        self.window.table_list.itemClicked.connect(self.on_table_selected)
        self.window.category_filter.currentIndexChanged.connect(self.refresh_menu_items)
        self.window.item_list.itemDoubleClicked.connect(self.add_selected_item)
        self.window.remove_item_button.clicked.connect(self.remove_selected_item)
        self.window.apply_adjustments_button.clicked.connect(self.apply_adjustments)
        self.window.pay_button.clicked.connect(self.take_payment)
        self.window.print_button.clicked.connect(self.reprint_receipt)
        self.window.save_pdf_button.clicked.connect(self.export_receipt_pdf)

    def load(self) -> None:
        self.window.user_label.setText(f"Signed in as {self.session_user.username} ({self.session_user.role.value})")
        self.refresh_tables()
        self.refresh_categories()
        self.refresh_menu_items()
        settings = self.settings_service.get_settings()
        self.window.discount_spin.setValue(settings["default_discount_amount"])
        self.window.service_charge_spin.setValue(settings["default_service_charge_amount"])

    def refresh_tables(self) -> None:
        self.window.table_list.clear()
        orders_by_table = {order["table_id"]: order for order in self.order_service.list_orders("open")}
        for table in self.table_service.list_tables():
            label = table["name"]
            if table["id"] in orders_by_table:
                label += " (Open)"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, table["id"])
            self.window.table_list.addItem(item)

    def refresh_categories(self) -> None:
        self.window.category_filter.clear()
        self.window.category_filter.addItem("All Categories", None)
        for category in self.menu_service.list_categories():
            self.window.category_filter.addItem(category["name"], category["id"])

    def refresh_menu_items(self) -> None:
        self.window.item_list.clear()
        category_id = self.window.category_filter.currentData()
        for item in self.menu_service.list_menu_items(category_id=category_id, only_available=True):
            widget_item = QListWidgetItem(f"{item['name']} - {item['price']:.2f}")
            widget_item.setData(Qt.UserRole, item["id"])
            self.window.item_list.addItem(widget_item)

    def on_table_selected(self, item) -> None:
        self.selected_table_id = item.data(Qt.UserRole)
        self.current_order = self.order_service.open_table_order(self.selected_table_id, self.session_user.user_id)
        self._render_order()

    def add_selected_item(self, item) -> None:
        if not self.current_order:
            QMessageBox.warning(self.window, "Select Table", "Select a table before adding items.")
            return
        try:
            self.current_order = self.order_service.add_item(self.current_order["id"], item.data(Qt.UserRole), qty=1)
            self._render_order()
            self.refresh_tables()
        except Exception as exc:
            QMessageBox.warning(self.window, "Add Item Error", str(exc))

    def remove_selected_item(self) -> None:
        if not self.current_order:
            return
        selected = self.window.order_items_table.selectedItems()
        if not selected:
            QMessageBox.warning(self.window, "No Selection", "Select an order item to remove.")
            return
        order_item_id = self.window.order_items_table.item(selected[0].row(), 0).data(Qt.UserRole)
        try:
            self.current_order = self.order_service.remove_order_item(self.current_order["id"], order_item_id)
            self._render_order()
        except Exception as exc:
            QMessageBox.warning(self.window, "Remove Error", str(exc))

    def apply_adjustments(self) -> None:
        if not self.current_order:
            return
        try:
            self.current_order = self.order_service.update_adjustments(
                self.current_order["id"],
                self.window.discount_spin.value(),
                self.window.service_charge_spin.value(),
            )
            self._render_order()
        except Exception as exc:
            QMessageBox.warning(self.window, "Adjustment Error", str(exc))

    def take_payment(self) -> None:
        if not self.current_order:
            return
        try:
            self.apply_adjustments()
            self.payment_service.settle(
                self.current_order["id"],
                self.window.payment_method.currentText(),
                self.window.amount_received.value(),
            )
            completed_order = self.order_service.get_order(self.current_order["id"])
            settings = self.settings_service.get_settings()
            pdf_path = self.print_service.save_receipt_pdf(completed_order, settings)
            self.last_completed_order = completed_order
            QMessageBox.information(
                self.window,
                "Payment Complete",
                f"Payment saved. Receipt PDF saved to {pdf_path}. Use Print Receipt to choose a printer or Microsoft Print to PDF.",
            )
            self.current_order = None
            self.selected_table_id = None
            self._clear_ticket()
            self.refresh_tables()
        except Exception as exc:
            QMessageBox.warning(self.window, "Payment Error", str(exc))

    def reprint_receipt(self) -> None:
        order = self._receipt_order()
        if not order:
            QMessageBox.warning(self.window, "No Receipt", "Complete a sale or load an order first.")
            return
        try:
            message = self.print_service.print_receipt_dialog(order, self.settings_service.get_settings(), self.window)
            QMessageBox.information(self.window, "Receipt", message)
        except Exception as exc:
            QMessageBox.warning(self.window, "Print Error", str(exc))

    def export_receipt_pdf(self) -> None:
        order = self._receipt_order()
        if not order:
            QMessageBox.warning(self.window, "No Receipt", "Complete a sale or load an order first.")
            return
        try:
            pdf_path = self.print_service.save_receipt_pdf(order, self.settings_service.get_settings())
            QMessageBox.information(self.window, "Receipt PDF Saved", f"Receipt PDF saved to {pdf_path}")
        except Exception as exc:
            QMessageBox.warning(self.window, "PDF Error", str(exc))

    def _receipt_order(self):
        return self.current_order or self.last_completed_order

    def _render_order(self) -> None:
        if not self.current_order:
            self._clear_ticket()
            return
        self.window.order_meta.setText(
            f"Order {self.current_order['order_number']} | Table {self.current_order['table_name']} | Status {self.current_order['status']}"
        )
        table = self.window.order_items_table
        table.setRowCount(len(self.current_order["items"]))
        for row, item in enumerate(self.current_order["items"]):
            values = [item["id"], item["name"], item["quantity"], f"{item['line_total']:.2f}"]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                if column == 0:
                    cell.setData(Qt.UserRole, item["id"])
                table.setItem(row, column, cell)
        self.window.discount_spin.setValue(self.current_order["discount_amount"])
        self.window.service_charge_spin.setValue(self.current_order["service_charge_amount"])
        self.window.totals_label.setText(
            (
                f"Subtotal: {self.current_order['subtotal']:.2f}\n"
                f"Discount: {self.current_order['discount_amount']:.2f}\n"
                f"Service Charge: {self.current_order['service_charge_amount']:.2f}\n"
                f"GST ({self.current_order['gst_percent']:.2f}%): {self.current_order['gst_amount']:.2f}\n"
                f"Grand Total: {self.current_order['grand_total']:.2f}"
            )
        )

    def _clear_ticket(self) -> None:
        self.window.order_meta.setText("Select a table to begin.")
        self.window.order_items_table.setRowCount(0)
        self.window.totals_label.setText("")
