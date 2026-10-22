# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe


def execute() -> None:
	"""Send desk users to WorkforceOS instead of the missing Home workspace."""
	if not frappe.db.exists("Workspace", "WorkforceOS"):
		return

	users = frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User"},
		pluck="name",
	)
	for user in users:
		current = frappe.db.get_value("User", user, "default_workspace")
		if current in (None, "", "Home"):
			frappe.db.set_value(
				"User", user, "default_workspace", "WorkforceOS", update_modified=False
			)

	frappe.db.commit()
