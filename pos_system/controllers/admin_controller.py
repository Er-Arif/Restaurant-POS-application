from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QListWidgetItem, QMessageBox, QTableWidgetItem

from pos_system.models.enums import UserRole


class AdminController:
    def __init__(
        self,
        window,
        auth_service,
        settings_service,
        menu_service,
        order_service,
        report_service,
        backup_service,
        table_service,
    ):
        self.window = window
        self.auth_service = auth_service
        self.settings_service = settings_service
        self.menu_service = menu_service
        self.order_service = order_service
        self.report_service = report_service
        self.backup_service = backup_service
        self.table_service = table_service
        self.selected_category_id = None
        self.selected_item_id = None
        self.selected_user_id = None
        self._bind()

    def _bind(self) -> None:
        self.window.save_category_button.clicked.connect(self.save_category)
        self.window.category_list.itemClicked.connect(self.on_category_selected)
        self.window.save_item_button.clicked.connect(self.save_item)
        self.window.menu_items_table.itemSelectionChanged.connect(self.on_item_selected)
        self.window.save_user_button.clicked.connect(self.save_user)
        self.window.users_table.itemSelectionChanged.connect(self.on_user_selected)
        self.window.refresh_orders_button.clicked.connect(self.refresh_orders)
        self.window.cancel_order_button.clicked.connect(self.cancel_selected_order)
        self.window.refresh_report_button.clicked.connect(self.refresh_report_summary)
        self.window.export_csv_button.clicked.connect(self.export_report_csv)
        self.window.save_settings_button.clicked.connect(self.save_settings)
        self.window.settings_logo_browse.clicked.connect(self.window.choose_settings_logo)
        self.window.create_backup_button.clicked.connect(self.create_backup)
        self.window.restore_backup_button.clicked.connect(self.restore_backup)

    def load(self) -> None:
        self.refresh_categories()
        self.refresh_menu_items()
        self.refresh_users()
        self.refresh_orders()
        self.refresh_report_summary()
        self.refresh_settings()
        self.refresh_backups()
        settings = self.settings_service.get_settings()
        name = settings.get("restaurant_name") or "Restaurant"
        self.window.brand_label.setText(f"{name} Admin Dashboard")
        self.window.overview_summary.setText(
            "Use this dashboard to manage menu items, users, billing defaults, reports, and backups."
        )

    def refresh_categories(self) -> None:
        categories = self.menu_service.list_categories()
        self.window.category_list.clear()
        self.window.item_category_combo.clear()
        for category in categories:
            item = QListWidgetItem(category["name"])
            item.setData(Qt.UserRole, category["id"])
            item.setToolTip(category["description"])
            self.window.category_list.addItem(item)
            self.window.item_category_combo.addItem(category["name"], category["id"])

    def save_category(self) -> None:
        try:
            category = self.menu_service.save_category(
                name=self.window.category_name.text(),
                description=self.window.category_description.toPlainText(),
                category_id=self.selected_category_id,
            )
            self.selected_category_id = category["id"]
            self.refresh_categories()
            QMessageBox.information(self.window, "Category Saved", "Category saved successfully.")
        except Exception as exc:
            QMessageBox.warning(self.window, "Category Error", str(exc))

    def on_category_selected(self, item) -> None:
        self.selected_category_id = item.data(Qt.UserRole)
        self.window.category_name.setText(item.text())
        self.window.category_description.setPlainText(item.toolTip())

    def refresh_menu_items(self) -> None:
        items = self.menu_service.list_menu_items()
        table = self.window.menu_items_table
        table.setRowCount(len(items))
        for row, item in enumerate(items):
            values = [item["id"], item["name"], item["category_name"], f"{item['price']:.2f}", "Yes" if item["is_available"] else "No"]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                if column == 0:
                    cell.setData(Qt.UserRole, item["id"])
                table.setItem(row, column, cell)

    def save_item(self) -> None:
        try:
            category_id = self.window.item_category_combo.currentData()
            if category_id is None:
                raise ValueError("Create a category first.")
            item = self.menu_service.save_menu_item(
                {
                    "category_id": category_id,
                    "name": self.window.item_name.text(),
                    "description": self.window.item_description.toPlainText(),
                    "price": self.window.item_price.value(),
                    "is_available": self.window.item_available.isChecked(),
                },
                item_id=self.selected_item_id,
            )
            self.selected_item_id = item["id"]
            self.refresh_menu_items()
            QMessageBox.information(self.window, "Menu Item Saved", "Menu item saved successfully.")
        except Exception as exc:
            QMessageBox.warning(self.window, "Menu Item Error", str(exc))

    def on_item_selected(self) -> None:
        selected = self.window.menu_items_table.selectedItems()
        if not selected:
            return
        item_id = self.window.menu_items_table.item(selected[0].row(), 0).data(Qt.UserRole)
        full_item = next((item for item in self.menu_service.list_menu_items() if item["id"] == item_id), None)
        if not full_item:
            return
        self.selected_item_id = full_item["id"]
        index = self.window.item_category_combo.findData(full_item["category_id"])
        self.window.item_category_combo.setCurrentIndex(index)
        self.window.item_name.setText(full_item["name"])
        self.window.item_description.setPlainText(full_item["description"])
        self.window.item_price.setValue(full_item["price"])
        self.window.item_available.setChecked(full_item["is_available"])

    def refresh_users(self) -> None:
        users = self.auth_service.list_users()
        table = self.window.users_table
        table.setRowCount(len(users))
        for row, user in enumerate(users):
            values = [user["id"], user["username"], user["role"], "Yes" if user["is_active"] else "No"]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                if column == 0:
                    cell.setData(Qt.UserRole, user["id"])
                table.setItem(row, column, cell)

    def save_user(self) -> None:
        try:
            payload = {
                "username": self.window.user_username.text(),
                "password": self.window.user_password.text(),
                "role": UserRole(self.window.user_role.currentText()),
                "is_active": self.window.user_active.isChecked(),
            }
            if self.selected_user_id:
                self.auth_service.update_user(
                    user_id=self.selected_user_id,
                    username=payload["username"],
                    role=payload["role"],
                    is_active=payload["is_active"],
                    password=payload["password"],
                )
            else:
                self.auth_service.create_user(
                    username=payload["username"],
                    password=payload["password"],
                    role=payload["role"],
                    is_active=payload["is_active"],
                )
            self.refresh_users()
            QMessageBox.information(self.window, "User Saved", "User saved successfully.")
        except Exception as exc:
            QMessageBox.warning(self.window, "User Error", str(exc))

    def on_user_selected(self) -> None:
        selected = self.window.users_table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        self.selected_user_id = self.window.users_table.item(row, 0).data(Qt.UserRole)
        self.window.user_username.setText(self.window.users_table.item(row, 1).text())
        self.window.user_role.setCurrentText(self.window.users_table.item(row, 2).text())
        self.window.user_active.setChecked(self.window.users_table.item(row, 3).text() == "Yes")

    def refresh_orders(self) -> None:
        status = self.window.order_status_filter.currentText()
        orders = self.order_service.list_orders(None if status == "all" else status)
        table = self.window.orders_table
        table.setRowCount(len(orders))
        for row, order in enumerate(orders):
            values = [
                order["id"],
                order["order_number"],
                order["table_name"],
                order["created_by_username"],
                order["status"],
                f"{order['subtotal']:.2f}",
                f"{order['grand_total']:.2f}",
                order["created_at"].strftime("%Y-%m-%d %H:%M"),
            ]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                if column == 0:
                    cell.setData(Qt.UserRole, order["id"])
                table.setItem(row, column, cell)

    def cancel_selected_order(self) -> None:
        selected = self.window.orders_table.selectedItems()
        if not selected:
            QMessageBox.warning(self.window, "No Selection", "Select an order first.")
            return
        order_id = self.window.orders_table.item(selected[0].row(), 0).data(Qt.UserRole)
        try:
            self.order_service.cancel_order(order_id)
            self.refresh_orders()
            QMessageBox.information(self.window, "Order Cancelled", "Order cancelled successfully.")
        except Exception as exc:
            QMessageBox.warning(self.window, "Cancel Error", str(exc))

    def refresh_report_summary(self) -> None:
        summary = self.report_service.sales_summary(
            self.window.report_start.date().toPython(),
            self.window.report_end.date().toPython(),
        )
        self.window.report_summary.setText(
            (
                f"Orders: {summary.order_count}\n"
                f"Revenue: {summary.total_revenue:.2f}\n"
                f"Cash: {summary.cash_revenue:.2f}\n"
                f"UPI: {summary.upi_revenue:.2f}"
            )
        )

    def export_report_csv(self) -> None:
        try:
            filename = self.report_service.export_orders_csv(
                {
                    "start_date": self.window.report_start.date().toPython(),
                    "end_date": self.window.report_end.date().toPython(),
                }
            )
            QMessageBox.information(self.window, "CSV Exported", f"Report exported to:\n{filename}")
        except Exception as exc:
            QMessageBox.warning(self.window, "Export Error", str(exc))

    def refresh_settings(self) -> None:
        settings = self.settings_service.get_settings()
        self.window.settings_restaurant_name.setText(settings["restaurant_name"])
        self.window.settings_address.setPlainText(settings["address"])
        self.window.settings_phone.setText(settings["phone"])
        self.window.settings_gst_number.setText(settings["gst_number"])
        self.window.settings_currency.setText(settings["currency_symbol"])
        self.window.settings_gst_percent.setValue(settings["gst_percent"])
        self.window.settings_discount.setValue(settings["default_discount_amount"])
        self.window.settings_service_charge.setValue(settings["default_service_charge_amount"])
        self.window.settings_receipt_footer.setPlainText(settings["receipt_footer"])
        self.window.settings_logo_path.setText(settings["logo_path"])

    def save_settings(self) -> None:
        try:
            self.settings_service.save_settings(
                {
                    "restaurant_name": self.window.settings_restaurant_name.text(),
                    "address": self.window.settings_address.toPlainText(),
                    "phone": self.window.settings_phone.text(),
                    "gst_number": self.window.settings_gst_number.text(),
                    "currency_symbol": self.window.settings_currency.text(),
                    "gst_percent": self.window.settings_gst_percent.value(),
                    "default_discount_amount": self.window.settings_discount.value(),
                    "default_service_charge_amount": self.window.settings_service_charge.value(),
                    "receipt_footer": self.window.settings_receipt_footer.toPlainText(),
                    "logo_source_path": self.window.settings_logo_path.text(),
                    "setup_complete": True,
                }
            )
            self.refresh_settings()
            QMessageBox.information(self.window, "Settings Saved", "Settings updated successfully.")
        except Exception as exc:
            QMessageBox.warning(self.window, "Settings Error", str(exc))

    def refresh_backups(self) -> None:
        self.window.backup_list.clear()
        for path in self.backup_service.list_backups():
            self.window.backup_list.addItem(path)

    def create_backup(self) -> None:
        try:
            backup_path = self.backup_service.create_backup()
            self.refresh_backups()
            self.window.backup_status.setText(f"Backup created: {backup_path}")
        except Exception as exc:
            QMessageBox.warning(self.window, "Backup Error", str(exc))

    def restore_backup(self) -> None:
        selected = self.window.selected_backup_path()
        if not selected:
            selected, _ = QFileDialog.getOpenFileName(self.window, "Select Backup", "", "Database (*.db)")
        if not selected:
            return
        try:
            self.backup_service.restore_backup(selected)
            self.refresh_backups()
            self.window.backup_status.setText("Backup restored. Restart the application to refresh live data.")
        except Exception as exc:
            QMessageBox.warning(self.window, "Restore Error", str(exc))
