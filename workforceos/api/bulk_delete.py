"""Bulk delete API for WorkforceOS."""

from __future__ import annotations

import frappe

from workforceos.workforce.setup.bulk_delete import bulk_delete, get_bulk_delete_options


@frappe.whitelist()
def options() -> list[dict]:
	"""Return WorkforceOS doctypes and record counts for bulk delete."""
	frappe.only_for("System Manager")
	return get_bulk_delete_options()


@frappe.whitelist()
def delete(doctypes: str | list | None = None) -> dict:
	"""Bulk delete all records for selected WorkforceOS doctypes."""
	frappe.only_for("System Manager")
	return bulk_delete(doctypes)
