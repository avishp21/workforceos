# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import json

import frappe


def execute() -> None:
	"""Sync the WorkforceOS workspace definition from the app JSON (without removing the source file)."""
	if not frappe.db.exists("DocType", "Workspace"):
		return

	workspace_path = frappe.get_app_path(
		"workforceos",
		"workforce",
		"workspace",
		"workforceos",
		"workforceos.json",
	)
	with open(workspace_path, encoding="utf-8") as handle:
		data = json.load(handle)

	workspace_name = data.get("name") or "WorkforceOS"
	if frappe.db.exists("Workspace", workspace_name):
		frappe.delete_doc("Workspace", workspace_name, force=True, ignore_permissions=True)

	frappe.get_doc(data).insert(ignore_permissions=True)
	frappe.db.commit()
