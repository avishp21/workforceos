# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe


def execute() -> None:
	"""Remove the deprecated Operations workspace from the desk."""
	if not frappe.db.exists("DocType", "Workspace"):
		return

	if frappe.db.exists("Workspace", "Operations"):
		frappe.delete_doc("Workspace", "Operations", force=True, ignore_permissions=True)

	frappe.db.commit()
