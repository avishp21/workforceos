# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe


def execute() -> None:
	"""Remove deprecated Authorized field data after DocType migration."""
	if not frappe.db.table_exists("tabEmployee Competency"):
		return

	if frappe.db.has_column("Employee Competency", "authorized"):
		frappe.db.sql("ALTER TABLE `tabEmployee Competency` DROP COLUMN `authorized`")

	frappe.db.commit()
