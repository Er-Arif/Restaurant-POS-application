from __future__ import annotations

from datetime import UTC, date, datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QListWidgetItem, QMessageBox, QTableWidgetItem
from pos_system.models.enums import UserRole
from pos_system.services.print_service import PrintService
from pos_system.utils.formatting import money_text


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
        session_user=None,
        print_service=None,
    ):
        self.window = window
        self.auth_service = auth_service
        self.settings_service = settings_service
        self.menu_service = menu_service
        self.order_service = order_service
        self.report_service = report_service
        self.backup_service = backup_service
        self.table_service = table_service
        self.session_user = session_user
        self.print_service = print_service or PrintService()
        self.selected_category_id = None
        self.selected_item_id = None
        self.selected_user_id = None
        self.selected_order_id = None
        self.category_create_mode = True
        self.user_create_mode = True
        self.all_orders = []
        self.filtered_orders = []
        self._bind()

    def _bind(self) -> None:
        self.window.overview_refresh_button.clicked.connect(self.refresh_overview)
        self.window.save_category_button.clicked.connect(self.save_category)
        self.window.clear_category_button.clicked.connect(self.clear_category_form)
        self.window.toggle_category_button.clicked.connect(self.toggle_category_active)
        self.window.delete_category_button.clicked.connect(self.delete_category)
        self.window.category_list.itemClicked.connect(self.on_category_selected)
        self.window.save_item_button.clicked.connect(self.save_item)
        self.window.clear_item_button.clicked.connect(self.clear_item_form)
        self.window.toggle_item_button.clicked.connect(self.toggle_item_availability)
        self.window.delete_item_button.clicked.connect(self.delete_item)
        self.window.menu_items_table.itemSelectionChanged.connect(self.on_item_selected)
        self.window.save_user_button.clicked.connect(self.save_user)
        self.window.clear_user_button.clicked.connect(self.clear_user_form)
        self.window.users_table.itemSelectionChanged.connect(self.on_user_selected)
        self.window.order_status_filter.currentIndexChanged.connect(self.refresh_orders)
        self.window.order_search.textChanged.connect(self.apply_order_filters)
        self.window.orders_table.itemSelectionChanged.connect(self.on_order_selected)
        self.window.refresh_orders_button.clicked.connect(self.refresh_orders)
        self.window.cancel_order_button.clicked.connect(self.cancel_selected_order)
        self.window.print_order_receipt_button.clicked.connect(self.print_selected_order_receipt)
        self.window.save_order_pdf_button.clicked.connect(self.save_selected_order_pdf)
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
        self.refresh_overview()
        self.clear_category_form()
        self.clear_item_form()
        self.clear_user_form()

    def refresh_overview(self) -> None:
        settings = self.settings_service.get_settings()
        orders = self.order_service.list_orders()
        currency = settings.get("currency_symbol") or "?"
        today = datetime.now().astimezone().date()

        def order_local_date(order: dict) -> date:
            created_at = order["created_at"]
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            return created_at.astimezone().date()

        today_orders = [order for order in orders if order_local_date(order) == today]
        paid_today = [order for order in today_orders if order["status"] == "paid"]
        cancelled_today = [order for order in today_orders if order["status"] == "cancelled"]
        open_orders = [order for order in orders if order["status"] == "open"]
        revenue_today = sum(order["grand_total"] for order in paid_today)
        average_bill = revenue_today / len(paid_today) if paid_today else 0
        open_tables = len({order["table_id"] for order in open_orders})

        restaurant_name = settings.get("restaurant_name") or "Restaurant"
        self.window.brand_label.setText(f"{restaurant_name} Admin Dashboard")
        self.window.overview_headline.setText(f"{restaurant_name} overview for {today.isoformat()}")
        self.window.overview_summary.setText("A simple live summary of today's business and the latest order activity.")

        self.window.overview_sales_today_value.setText(money_text(revenue_today, currency))
        self.window.overview_sales_today_meta.setText(f"{len(paid_today)} paid order(s) today")
        self.window.overview_orders_today_value.setText(str(len(today_orders)))
        self.window.overview_orders_today_meta.setText("Today's open, paid, and cancelled orders")
        self.window.overview_average_bill_value.setText(money_text(average_bill, currency))
        self.window.overview_average_bill_meta.setText("Average from today's paid bills")
        self.window.overview_open_tables_value.setText(str(open_tables))
        self.window.overview_open_tables_meta.setText("Tables with an active ticket right now")
        self.window.overview_paid_orders_value.setText(str(len(paid_today)))
        self.window.overview_paid_orders_meta.setText("Paid orders completed today")
        self.window.overview_cancelled_orders_value.setText(str(len(cancelled_today)))
        self.window.overview_cancelled_orders_meta.setText("Orders cancelled today")

        recent_orders = orders[:5]
        self.window.overview_recent_orders.setRowCount(len(recent_orders))
        for row, order in enumerate(recent_orders):
            values = [
                order["order_number"],
                order["table_name"],
                order["status"].title(),
                money_text(order["grand_total"], currency),
                order_local_date(order).isoformat(),
            ]
            for column, value in enumerate(values):
                self.window.overview_recent_orders.setItem(row, column, QTableWidgetItem(str(value)))

    def refresh_categories(self) -> None:
        categories = self.menu_service.list_categories()
        self.window.category_list.clear()
        self.window.item_category_combo.clear()
        for category in categories:
            label = category["name"] if category["is_active"] else f"{category['name']} (Archived)"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, category["id"])
            item.setToolTip(category["description"])
            self.window.category_list.addItem(item)
            self.window.item_category_combo.addItem(label, category["id"])
        self._update_category_buttons()

    def save_category(self) -> None:
        try:
            category_id = None if self.category_create_mode else self.selected_category_id
            category = self.menu_service.save_category(
                name=self.window.category_name.text(),
                description=self.window.category_description.toPlainText(),
                category_id=category_id,
            )
            self.selected_category_id = category["id"]
            self.category_create_mode = False
            self.refresh_categories()
            self.refresh_overview()
            self._select_category_in_list(category["id"])
            message = "Category added successfully." if category_id is None else "Category updated successfully."
            QMessageBox.information(self.window, "Category Saved", message)
        except Exception as exc:
            QMessageBox.warning(self.window, "Category Error", str(exc))

    def on_category_selected(self, item) -> None:
        self.selected_category_id = item.data(Qt.UserRole)
        self.category_create_mode = False
        self.window.category_name.setText(item.text().replace(" (Archived)", ""))
        self.window.category_description.setPlainText(item.toolTip())
        self._update_category_buttons()

    def clear_category_form(self) -> None:
        self.selected_category_id = None
        self.category_create_mode = True
        self.window.category_name.clear()
        self.window.category_description.clear()
        self.window.category_list.clearSelection()
        self._update_category_buttons()
        self.window.category_name.setFocus()

    def toggle_category_active(self) -> None:
        if not self.selected_category_id:
            QMessageBox.warning(self.window, "No Category", "Select a category first.")
            return
        category = next((row for row in self.menu_service.list_categories() if row["id"] == self.selected_category_id), None)
        if not category:
            QMessageBox.warning(self.window, "Category Error", "Category not found.")
            return
        target_active = not category["is_active"]
        action_text = "restore" if target_active else "archive"
        answer = QMessageBox.question(self.window, "Confirm Category Update", f"Do you want to {action_text} category '{category['name']}'?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.menu_service.set_category_active(category["id"], target_active)
            self.refresh_categories()
            self.refresh_menu_items()
            self.refresh_overview()
            self._select_category_in_list(category["id"])
            QMessageBox.information(self.window, "Category Updated", "Category status updated successfully.")
        except Exception as exc:
            QMessageBox.warning(self.window, "Category Error", str(exc))

    def delete_category(self) -> None:
        if not self.selected_category_id:
            QMessageBox.warning(self.window, "No Category", "Select a category first.")
            return
        category_name = self.window.category_name.text().strip() or "this category"
        answer = QMessageBox.question(self.window, "Delete Category", f"Delete '{category_name}' permanently? This only works when the category has no menu items.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.menu_service.delete_category(self.selected_category_id)
            self.refresh_categories()
            self.refresh_overview()
            self.clear_category_form()
            QMessageBox.information(self.window, "Category Deleted", "Category deleted successfully.")
        except Exception as exc:
            QMessageBox.warning(self.window, "Delete Error", str(exc))

    def refresh_menu_items(self) -> None:
        items = self.menu_service.list_menu_items()
        table = self.window.menu_items_table
        table.setRowCount(len(items))
        for row, item in enumerate(items):
            availability = "Yes" if item["is_available"] else "No"
            if not item["category_is_active"]:
                availability += " | Archived Category"
            values = [item["id"], item["name"], item["category_name"], f"{item['price']:.2f}", availability]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                if column == 0:
                    cell.setData(Qt.UserRole, item["id"])
                table.setItem(row, column, cell)
        self._update_item_buttons()

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
            self.refresh_overview()
            self._select_item_in_table(item["id"])
            QMessageBox.information(self.window, "Menu Item Saved", "Menu item saved successfully.")
        except Exception as exc:
            QMessageBox.warning(self.window, "Menu Item Error", str(exc))

    def on_item_selected(self) -> None:
        selected = self.window.menu_items_table.selectedItems()
        if not selected:
            self.selected_item_id = None
            self._update_item_buttons()
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
        self._update_item_buttons(full_item)

    def clear_item_form(self) -> None:
        self.selected_item_id = None
        self.window.item_name.clear()
        self.window.item_description.clear()
        self.window.item_price.setValue(0)
        self.window.item_available.setChecked(True)
        self.window.menu_items_table.clearSelection()
        self._update_item_buttons()

    def toggle_item_availability(self) -> None:
        if not self.selected_item_id:
            QMessageBox.warning(self.window, "No Item", "Select a menu item first.")
            return
        item = next((row for row in self.menu_service.list_menu_items() if row["id"] == self.selected_item_id), None)
        if not item:
            QMessageBox.warning(self.window, "Menu Item Error", "Menu item not found.")
            return
        target_available = not item["is_available"]
        action_text = "mark available" if target_available else "mark unavailable"
        answer = QMessageBox.question(self.window, "Confirm Item Update", f"Do you want to {action_text} '{item['name']}'?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.menu_service.set_menu_item_availability(item["id"], target_available)
            self.refresh_menu_items()
            self.refresh_overview()
            self._select_item_in_table(item["id"])
            QMessageBox.information(self.window, "Menu Item Updated", "Menu item availability updated successfully.")
        except Exception as exc:
            QMessageBox.warning(self.window, "Menu Item Error", str(exc))

    def delete_item(self) -> None:
        if not self.selected_item_id:
            QMessageBox.warning(self.window, "No Item", "Select a menu item first.")
            return
        item_name = self.window.item_name.text().strip() or "this item"
        answer = QMessageBox.question(self.window, "Delete Menu Item", f"Delete '{item_name}' permanently? Sold items cannot be deleted and should be marked unavailable instead.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.menu_service.delete_menu_item(self.selected_item_id)
            self.refresh_menu_items()
            self.refresh_overview()
            self.clear_item_form()
            QMessageBox.information(self.window, "Menu Item Deleted", "Menu item deleted successfully.")
        except Exception as exc:
            QMessageBox.warning(self.window, "Delete Error", str(exc))

    def refresh_users(self) -> None:
        users = self.auth_service.list_users()
        table = self.window.users_table
        table.setRowCount(len(users))
        for row, user in enumerate(users):
            values = [user["id"], user["full_name"], user["username"], user["role"], "Yes" if user["is_active"] else "No"]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                if column == 0:
                    cell.setData(Qt.UserRole, user["id"])
                table.setItem(row, column, cell)
        self._update_user_buttons()

    def save_user(self) -> None:
        try:
            self._require_admin_password_confirmation()
            payload = {
                "full_name": self.window.user_full_name.text(),
                "username": self.window.user_username.text(),
                "password": self.window.user_password.text(),
                "role": UserRole(self.window.user_role.currentText()),
                "is_active": self.window.user_active.isChecked(),
            }
            if self.user_create_mode:
                self.auth_service.create_user(
                    full_name=payload["full_name"],
                    username=payload["username"],
                    password=payload["password"],
                    role=payload["role"],
                    is_active=payload["is_active"],
                )
                message = "New user created successfully."
            else:
                self.auth_service.update_user(
                    user_id=self.selected_user_id,
                    full_name=payload["full_name"],
                    username=payload["username"],
                    role=payload["role"],
                    is_active=payload["is_active"],
                    password=payload["password"],
                )
                message = "User updated successfully."
            self.refresh_users()
            self.refresh_overview()
            self.clear_user_form()
            QMessageBox.information(self.window, "User Saved", message)
        except Exception as exc:
            QMessageBox.warning(self.window, "User Error", str(exc))

    def on_user_selected(self) -> None:
        selected = self.window.users_table.selectedItems()
        if not selected:
            self.clear_user_form()
            return
        row = selected[0].row()
        self.selected_user_id = self.window.users_table.item(row, 0).data(Qt.UserRole)
        self.user_create_mode = False
        self.window.user_full_name.setText(self.window.users_table.item(row, 1).text())
        self.window.user_username.setText(self.window.users_table.item(row, 2).text())
        self.window.user_role.setCurrentText(self.window.users_table.item(row, 3).text())
        self.window.user_active.setChecked(self.window.users_table.item(row, 4).text() == "Yes")
        self.window.user_password.clear()
        self.window.user_password.setPlaceholderText("Leave blank to keep the current password")
        self._update_user_buttons()

    def clear_user_form(self) -> None:
        self.selected_user_id = None
        self.user_create_mode = True
        self.window.user_full_name.clear()
        self.window.user_username.clear()
        self.window.user_password.clear()
        self.window.user_password.setPlaceholderText("Required for a new user")
        self.window.user_role.setCurrentIndex(0)
        self.window.user_active.setChecked(True)
        self.window.user_admin_password.clear()
        self.window.users_table.clearSelection()
        self._update_user_buttons()

    def _require_admin_password_confirmation(self) -> None:
        if not self.session_user:
            raise ValueError("Admin verification is unavailable in this context.")
        admin_password = self.window.user_admin_password.text()
        if not admin_password:
            raise ValueError("Enter your admin password to confirm this user change.")
        if not self.auth_service.verify_user_password(self.session_user.user_id, admin_password):
            raise ValueError("Admin password is incorrect.")
        if self.user_create_mode and not self.window.user_password.text():
            raise ValueError("Password is required for a new user.")

    def _update_user_buttons(self) -> None:
        self.window.save_user_button.setText("Create User" if self.user_create_mode else "Update User")

    def refresh_orders(self) -> None:
        status = self.window.order_status_filter.currentText()
        self.all_orders = self.order_service.list_orders(None if status == "all" else status)
        self.apply_order_filters(preserve_selection=False)
        self.refresh_overview()

    def apply_order_filters(self, preserve_selection: bool = True) -> None:
        search_text = self.window.order_search.text().strip().lower()
        previous_order_id = self.selected_order_id if preserve_selection else None
        if search_text:
            self.filtered_orders = [
                order for order in self.all_orders if self._order_matches_search(order, search_text)
            ]
        else:
            self.filtered_orders = list(self.all_orders)
        table = self.window.orders_table
        table.setRowCount(len(self.filtered_orders))
        for row, order in enumerate(self.filtered_orders):
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
        selected = False
        if previous_order_id is not None:
            for row, order in enumerate(self.filtered_orders):
                if order["id"] == previous_order_id:
                    table.selectRow(row)
                    selected = True
                    break
        if not selected:
            self.selected_order_id = None
            self.clear_order_detail()
        self.update_order_action_state()

    def on_order_selected(self) -> None:
        order = self.get_selected_order()
        if not order:
            self.selected_order_id = None
            self.clear_order_detail()
            self.update_order_action_state()
            return
        self.selected_order_id = order["id"]
        self.render_order_detail(order)
        self.update_order_action_state()

    def cancel_selected_order(self) -> None:
        order = self.get_selected_order()
        if not order:
            QMessageBox.warning(self.window, "No Selection", "Select an order first.")
            return
        if order["status"] == "paid":
            QMessageBox.warning(self.window, "Action Blocked", "Paid orders cannot be cancelled from the admin panel.")
            return
        answer = QMessageBox.question(
            self.window,
            "Confirm Cancellation",
            f"Cancel order {order['order_number']} for table {order['table_name']}?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.order_service.cancel_order(order["id"])
            self.refresh_orders()
            QMessageBox.information(self.window, "Order Cancelled", "Order cancelled successfully.")
        except Exception as exc:
            QMessageBox.warning(self.window, "Cancel Error", str(exc))

    def print_selected_order_receipt(self) -> None:
        order = self.get_selected_order()
        if not order:
            QMessageBox.warning(self.window, "No Selection", "Select an order first.")
            return
        if order["status"] != "paid":
            QMessageBox.warning(self.window, "Receipt Unavailable", "Only paid orders can be printed as receipts.")
            return
        try:
            message = self.print_service.print_receipt_dialog(order, self.settings_service.get_settings(), self.window)
            QMessageBox.information(self.window, "Receipt", message)
        except Exception as exc:
            QMessageBox.warning(self.window, "Print Error", str(exc))

    def save_selected_order_pdf(self) -> None:
        order = self.get_selected_order()
        if not order:
            QMessageBox.warning(self.window, "No Selection", "Select an order first.")
            return
        if order["status"] != "paid":
            QMessageBox.warning(self.window, "Receipt Unavailable", "Only paid orders can be exported as receipt PDFs.")
            return
        try:
            pdf_path = self.print_service.save_receipt_pdf(order, self.settings_service.get_settings())
            QMessageBox.information(self.window, "Receipt PDF Saved", f"Receipt PDF saved to {pdf_path}")
        except Exception as exc:
            QMessageBox.warning(self.window, "PDF Error", str(exc))

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
            self.refresh_overview()
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
            self.refresh_overview()
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
            self.refresh_overview()
            self.window.backup_status.setText("Backup restored. Restart the application to refresh live data.")
        except Exception as exc:
            QMessageBox.warning(self.window, "Restore Error", str(exc))

    def get_selected_order(self):
        selected = self.window.orders_table.selectedItems()
        if not selected:
            return None
        order_id = self.window.orders_table.item(selected[0].row(), 0).data(Qt.UserRole)
        return next((order for order in self.filtered_orders if order["id"] == order_id), None)

    def render_order_detail(self, order: dict) -> None:
        currency = self.settings_service.get_settings().get("currency_symbol") or "?"
        summary_lines = [
            f"Order #: {order['order_number']}",
            f"Table: {order['table_name']}",
            f"Cashier: {order['created_by_username']}",
            f"Status: {order['status'].title()}",
            f"Created: {order['created_at'].strftime('%Y-%m-%d %H:%M')}",
            f"Subtotal: {money_text(order['subtotal'], currency)}",
            f"Discount: {money_text(order['discount_amount'], currency)}",
            f"Service Charge: {money_text(order['service_charge_amount'], currency)}",
            f"GST: {money_text(order['gst_amount'], currency)}",
            f"Grand Total: {money_text(order['grand_total'], currency)}",
        ]
        self.window.order_detail_summary.setText("\n".join(summary_lines))
        self.window.order_detail_items.setRowCount(len(order["items"]))
        for row, item in enumerate(order["items"]):
            values = [item["name"], item["quantity"], money_text(item["unit_price"], currency), money_text(item["line_total"], currency)]
            for column, value in enumerate(values):
                self.window.order_detail_items.setItem(row, column, QTableWidgetItem(str(value)))
        if order["payments"]:
            payment_lines = []
            for payment in order["payments"]:
                payment_lines.append(
                    f"{payment['created_at'].strftime('%Y-%m-%d %H:%M')} | {payment['method'].upper()} | Paid {money_text(payment['paid_amount'], currency)} | Received {money_text(payment['amount_received'], currency)} | Change {money_text(payment['change_returned'], currency)}"
                )
            self.window.order_detail_payments.setPlainText("\n".join(payment_lines))
        else:
            self.window.order_detail_payments.setPlainText("No payments recorded yet.")

    def clear_order_detail(self) -> None:
        self.window.order_detail_summary.setText("Select an order to view details.")
        self.window.order_detail_items.setRowCount(0)
        self.window.order_detail_payments.setPlainText("")

    def update_order_action_state(self) -> None:
        order = self.get_selected_order()
        has_order = order is not None
        is_paid = bool(order and order["status"] == "paid")
        can_cancel = bool(order and order["status"] != "paid")
        self.window.cancel_order_button.setEnabled(can_cancel)
        self.window.print_order_receipt_button.setEnabled(is_paid)
        self.window.save_order_pdf_button.setEnabled(is_paid)
        if not has_order:
            self.window.cancel_order_button.setEnabled(False)

    def _update_category_buttons(self) -> None:
        category = next((row for row in self.menu_service.list_categories() if row["id"] == self.selected_category_id), None)
        has_category = category is not None
        self.window.toggle_category_button.setEnabled(has_category)
        self.window.delete_category_button.setEnabled(has_category)
        self.window.save_category_button.setText("Add Category" if self.category_create_mode else "Update Category")
        self.window.toggle_category_button.setText("Restore Category" if category and not category["is_active"] else "Archive Category")

    def _update_item_buttons(self, item: dict | None = None) -> None:
        if item is None and self.selected_item_id:
            item = next((row for row in self.menu_service.list_menu_items() if row["id"] == self.selected_item_id), None)
        has_item = item is not None
        self.window.toggle_item_button.setEnabled(has_item)
        self.window.delete_item_button.setEnabled(has_item)
        self.window.toggle_item_button.setText("Mark Available" if item and not item["is_available"] else "Mark Unavailable")

    def _select_category_in_list(self, category_id: int) -> None:
        for index in range(self.window.category_list.count()):
            item = self.window.category_list.item(index)
            if item.data(Qt.UserRole) == category_id:
                self.window.category_list.setCurrentItem(item)
                self.on_category_selected(item)
                return

    def _select_item_in_table(self, item_id: int) -> None:
        for row in range(self.window.menu_items_table.rowCount()):
            cell = self.window.menu_items_table.item(row, 0)
            if cell and cell.data(Qt.UserRole) == item_id:
                self.window.menu_items_table.selectRow(row)
                self.on_item_selected()
                return

    @staticmethod
    def _order_matches_search(order: dict, search_text: str) -> bool:
        haystack = " ".join(
            [
                str(order["order_number"]),
                str(order["table_name"]),
                str(order["created_by_username"]),
                str(order["status"]),
            ]
        ).lower()
        return search_text in haystack




















