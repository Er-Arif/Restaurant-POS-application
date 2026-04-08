from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidgetItem, QMessageBox, QPushButton, QTableWidgetItem, QVBoxLayout, QWidget


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
        self.suppress_adjustment_autosave = False
        self.adjustment_timer = QTimer(self.window)
        self.adjustment_timer.setSingleShot(True)
        self.adjustment_timer.setInterval(450)
        self.cancel_shortcut = QShortcut(QKeySequence("F3"), self.window)
        self.pay_shortcut = QShortcut(QKeySequence("F4"), self.window)
        self._bind()

    def _bind(self) -> None:
        self.window.table_list.itemClicked.connect(self.on_table_selected)
        self.window.category_bar.itemClicked.connect(self.on_category_selected)
        self.window.menu_search.textChanged.connect(self.refresh_menu_items)
        self.window.discount_spin.valueChanged.connect(self.queue_adjustments)
        self.window.service_charge_spin.valueChanged.connect(self.queue_adjustments)
        self.window.discount_spin.editingFinished.connect(self.apply_adjustments_immediately)
        self.window.service_charge_spin.editingFinished.connect(self.apply_adjustments_immediately)
        self.adjustment_timer.timeout.connect(self.apply_adjustments)
        self.window.payment_method.currentTextChanged.connect(self.on_payment_method_changed)
        self.window.pay_button.clicked.connect(self.take_payment)
        self.window.cancel_order_button.clicked.connect(self.cancel_current_order)
        self.cancel_shortcut.activated.connect(self.cancel_current_order)
        self.pay_shortcut.activated.connect(self.take_payment)

    def load(self) -> None:
        self.window.user_label.setText(f"Signed in as {self.session_user.username} ({self.session_user.role.value})")
        self.refresh_tables()
        self.refresh_categories()
        self.refresh_menu_items()
        settings = self.settings_service.get_settings()
        self.window.discount_spin.setValue(settings["default_discount_amount"])
        self.window.service_charge_spin.setValue(settings["default_service_charge_amount"])
        self.on_payment_method_changed(self.window.payment_method.currentText())

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
        self.window.category_bar.clear()
        all_item = QListWidgetItem("All")
        all_item.setData(Qt.UserRole, None)
        self.window.category_bar.addItem(all_item)
        for category in self.menu_service.list_categories():
            item = QListWidgetItem(category["name"])
            item.setData(Qt.UserRole, category["id"])
            self.window.category_bar.addItem(item)
        if self.window.category_bar.count():
            self.window.category_bar.setCurrentRow(0)
        self.refresh_menu_items()

    def on_category_selected(self, item) -> None:
        if item is None:
            return
        self.refresh_menu_items()

    def refresh_menu_items(self) -> None:
        self.window.item_list.clear()
        selected_category = self.window.category_bar.currentItem()
        category_id = selected_category.data(Qt.UserRole) if selected_category else None
        search_text = self.window.menu_search.text().strip().lower()
        for item in self.menu_service.list_menu_items(category_id=category_id, only_available=True):
            if search_text and search_text not in item["name"].lower():
                continue
            list_item = QListWidgetItem()
            list_item.setData(Qt.UserRole, item["id"])
            row_widget = QWidget()
            row_widget.setStyleSheet("QWidget { background: white; border-radius: 18px; }")
            row_layout = QVBoxLayout(row_widget)
            row_layout.setContentsMargins(14, 14, 14, 14)
            row_layout.setSpacing(8)
            name_label = QLabel(item["name"])
            name_label.setStyleSheet("font-size: 15pt; font-weight: 700; color: #183153;")
            price_label = QLabel(f"Price: {item['price']:.2f}")
            price_label.setStyleSheet("font-size: 12pt; color: #52606d;")
            add_button = QPushButton("+ Add Item")
            add_button.setMinimumHeight(42)
            add_button.setStyleSheet("QPushButton { background: #165b47; color: white; border: none; border-radius: 12px; font-size: 12pt; font-weight: 700; padding: 8px 14px; } QPushButton:hover { background: #1d7158; }")
            add_button.clicked.connect(lambda _checked=False, menu_item_id=item["id"]: self.add_menu_item(menu_item_id))
            row_layout.addWidget(name_label)
            row_layout.addWidget(price_label)
            row_layout.addStretch(1)
            row_layout.addWidget(add_button)
            list_item.setSizeHint(row_widget.sizeHint())
            self.window.item_list.addItem(list_item)
            self.window.item_list.setItemWidget(list_item, row_widget)

    def on_table_selected(self, item) -> None:
        self.selected_table_id = item.data(Qt.UserRole)
        self.current_order = self.order_service.open_table_order(self.selected_table_id, self.session_user.user_id)
        self._render_order()

    def add_selected_item(self, item) -> None:
        if item is None:
            return
        self.add_menu_item(item.data(Qt.UserRole))

    def add_menu_item(self, menu_item_id: int) -> None:
        if not self.current_order:
            QMessageBox.warning(self.window, "Select Table", "Select a table before adding items.")
            return
        try:
            self.current_order = self.order_service.add_item(self.current_order["id"], menu_item_id, qty=1)
            self._render_order()
            self.refresh_tables()
        except Exception as exc:
            QMessageBox.warning(self.window, "Add Item Error", str(exc))

    def remove_order_item(self, order_item_id: int) -> None:
        if not self.current_order:
            return
        try:
            self.current_order = self.order_service.remove_order_item(self.current_order["id"], order_item_id)
            self._render_order()
            self.refresh_tables()
        except Exception as exc:
            QMessageBox.warning(self.window, "Remove Error", str(exc))

    def queue_adjustments(self) -> None:
        if self.suppress_adjustment_autosave or not self.current_order:
            return
        self.adjustment_timer.start()

    def apply_adjustments_immediately(self) -> None:
        if self.suppress_adjustment_autosave or not self.current_order:
            return
        self.adjustment_timer.stop()
        self.apply_adjustments()

    def apply_adjustments(self) -> None:
        if self.suppress_adjustment_autosave or not self.current_order:
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

    def on_payment_method_changed(self, method: str) -> None:
        is_cash = method == "cash"
        self.window.amount_received_label.setVisible(is_cash)
        self.window.amount_received.setVisible(is_cash)
        if not is_cash:
            self.window.amount_received.setValue(0)
        if self.current_order:
            self._update_totals_label()

    def take_payment(self) -> None:
        if not self.current_order:
            return
        try:
            self.apply_adjustments()
            payment = self.payment_service.settle(
                self.current_order["id"],
                self.window.payment_method.currentText(),
                self.window.amount_received.value(),
            )
            completed_order = self.order_service.get_order(self.current_order["id"])
            self.last_completed_order = completed_order
            self.show_receipt_preview(completed_order, payment)
            self.current_order = None
            self.selected_table_id = None
            self._clear_ticket()
            self.refresh_tables()
        except Exception as exc:
            QMessageBox.warning(self.window, "Payment Error", str(exc))

    def cancel_current_order(self) -> None:
        if not self.current_order:
            QMessageBox.warning(self.window, "No Open Order", "Select a table with an open order first.")
            return
        answer = QMessageBox.question(
            self.window,
            "Cancel Open Order",
            "Cancel this open order and free the table? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            cancelled_order = self.order_service.cancel_order(self.current_order["id"])
            self.current_order = None
            self.selected_table_id = None
            self._clear_ticket()
            self.refresh_tables()
            QMessageBox.information(
                self.window,
                "Order Cancelled",
                f"Order {cancelled_order['order_number']} has been cancelled and the table is now available.",
            )
        except Exception as exc:
            QMessageBox.warning(self.window, "Cancel Order Error", str(exc))

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

    def show_receipt_preview(self, order: dict, payment: dict | None = None) -> None:
        from pos_system.ui.screens import ReceiptPreviewDialog

        settings = self.settings_service.get_settings()
        receipt_text = self.print_service.render_receipt(order, settings)
        receipt_html = self.print_service.render_receipt_html(order, settings)
        dialog = ReceiptPreviewDialog(receipt_html, self.window, is_html=True)
        if payment:
            if payment["method"] == "cash":
                dialog.status_label.setText(
                    f"Payment saved. Cash rounded total: {payment['paid_amount']:.2f}. Change returned: {payment['change_returned']:.2f}."
                )
            else:
                dialog.status_label.setText(
                    f"Payment saved. {payment['method'].upper()} collected exactly: {payment['paid_amount']:.2f}."
                )

        def handle_print() -> None:
            message = self.print_service.print_receipt_dialog(order, settings, dialog)
            dialog.status_label.setText(message)

        def handle_pdf() -> None:
            pdf_path = self.print_service.save_receipt_pdf(order, settings)
            dialog.status_label.setText(f"Receipt PDF saved to {pdf_path}")

        dialog.print_button.clicked.connect(handle_print)
        dialog.save_pdf_button.clicked.connect(handle_pdf)
        dialog.close_button.clicked.connect(dialog.accept)
        dialog.exec()

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
        self._resize_order_table_columns()
        for row, item in enumerate(self.current_order["items"]):
            name_cell = QTableWidgetItem(item["name"])
            name_cell.setData(Qt.UserRole, item["id"])
            qty_cell = QTableWidgetItem(str(item["quantity"]))
            unit_cell = QTableWidgetItem(f"{item['unit_price']:.2f}")
            line_total_cell = QTableWidgetItem(f"{item['line_total']:.2f}")
            table.setItem(row, 0, name_cell)
            table.setItem(row, 1, qty_cell)
            table.setItem(row, 2, unit_cell)
            table.setItem(row, 3, line_total_cell)
            table.setCellWidget(row, 4, self._build_order_action_widget(item))
        self.suppress_adjustment_autosave = True
        self.window.discount_spin.setValue(self.current_order.get("discount_percent", 0))
        self.window.service_charge_spin.setValue(self.current_order.get("service_charge_percent", 0))
        self.suppress_adjustment_autosave = False
        self._update_totals_label()

    def _resize_order_table_columns(self) -> None:
        table = self.window.order_items_table
        viewport_width = table.viewport().width()
        if viewport_width <= 0:
            viewport_width = max(table.width() - table.verticalHeader().width() - 8, 520)
        qty_width = 64
        unit_width = 96
        total_width = 104
        action_width = 176
        padding = 12
        name_width = max(140, viewport_width - qty_width - unit_width - total_width - action_width - padding)
        table.setColumnWidth(0, name_width)
        table.setColumnWidth(1, qty_width)
        table.setColumnWidth(2, unit_width)
        table.setColumnWidth(3, total_width)
        table.setColumnWidth(4, action_width)
        table.horizontalScrollBar().setValue(0)
        QTimer.singleShot(0, self._resize_order_table_columns_once)

    def _resize_order_table_columns_once(self) -> None:
        table = self.window.order_items_table
        viewport_width = table.viewport().width()
        if viewport_width <= 0:
            return
        qty_width = 64
        unit_width = 96
        total_width = 104
        action_width = 176
        padding = 12
        name_width = max(140, viewport_width - qty_width - unit_width - total_width - action_width - padding)
        table.setColumnWidth(0, name_width)
        table.setColumnWidth(1, qty_width)
        table.setColumnWidth(2, unit_width)
        table.setColumnWidth(3, total_width)
        table.setColumnWidth(4, action_width)
        table.horizontalScrollBar().setValue(0)

    def _build_order_action_widget(self, item: dict) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(4)
        minus_button = QPushButton("- Remove")
        plus_button = QPushButton("+ Add")
        minus_button.setMinimumWidth(88)
        plus_button.setMinimumWidth(76)
        minus_button.clicked.connect(lambda _checked=False, order_item_id=item["id"]: self.remove_order_item(order_item_id))
        plus_button.clicked.connect(lambda _checked=False, menu_item_id=item["menu_item_id"]: self.add_menu_item(menu_item_id))
        layout.addWidget(minus_button)
        layout.addWidget(plus_button)
        return widget

    def _update_totals_label(self) -> None:
        if not self.current_order:
            self.window.totals_label.setText("")
            return
        payment_method = self.window.payment_method.currentText()
        cash_total = self.current_order.get("cash_round_total", self.current_order["grand_total"])
        lines = [
            f"Subtotal: {self.current_order['subtotal']:.2f}",
            f"Discount ({self.current_order.get('discount_percent', 0):.2f}%): {self.current_order['discount_amount']:.2f}",
            f"Service Charge ({self.current_order.get('service_charge_percent', 0):.2f}%): {self.current_order['service_charge_amount']:.2f}",
            f"GST ({self.current_order['gst_percent']:.2f}%): {self.current_order['gst_amount']:.2f}",
            f"Grand Total: {self.current_order['grand_total']:.2f}",
        ]
        if payment_method == "cash":
            lines.append(f"Cash Rounded Total: {cash_total:.2f}")
        self.window.totals_label.setText("\n".join(lines))

    def _clear_ticket(self) -> None:
        self.window.order_meta.setText("Select a table to begin.")
        self.adjustment_timer.stop()
        self.window.order_items_table.setRowCount(0)
        self.window.totals_label.setText("")
        self.suppress_adjustment_autosave = True
        self.window.discount_spin.setValue(0)
        self.window.service_charge_spin.setValue(0)
        self.window.amount_received.setValue(0)
        self.suppress_adjustment_autosave = False
