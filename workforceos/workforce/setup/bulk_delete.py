# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

"""Bulk delete utility for WorkforceOS doctypes."""

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _

# FK-safe delete order (dependents first).
BULK_DELETE_DOCTYPES = [
	"Employee Assignment",
	"Allocation Decision Log",
	"Allocation Run",
	"Workforce Attendance",
	"Daily Line Plan",
	"Workforce Employee",
	"Allocation Rule",
	"Skill",
	"Workforce Designation",
	"Shift",
	"Production Line",
	"Contractor",
]


def get_bulk_delete_options() -> list[dict[str, Any]]:
	"""Return WorkforceOS doctypes available for bulk delete with current counts."""
	options = []
	for doctype in BULK_DELETE_DOCTYPES:
		options.append(
			{
				"doctype": doctype,
				"count": frappe.db.count(doctype),
			}
		)
	return options


def bulk_delete(doctypes: list[str] | str | None = None) -> dict[str, int]:
	"""Delete all documents for selected WorkforceOS doctypes."""
	selected = _normalize_doctypes(doctypes)
	deleted: dict[str, int] = {}

	for doctype in BULK_DELETE_DOCTYPES:
		if doctype not in selected:
			continue
		deleted[doctype] = _delete_all(doctype)

	frappe.db.commit()
	return deleted


def _normalize_doctypes(doctypes: list[str] | str | None) -> set[str]:
	if doctypes is None or doctypes == "":
		frappe.throw(_("Select at least one DocType."))

	if isinstance(doctypes, str):
		doctypes = json.loads(doctypes) if doctypes.strip().startswith("[") else [doctypes]

	if not isinstance(doctypes, (list, tuple, set)):
		frappe.throw(_("DocTypes must be a list."))

	selected = {str(item).strip() for item in doctypes if str(item).strip()}
	invalid = selected - set(BULK_DELETE_DOCTYPES)
	if invalid:
		frappe.throw(_("Invalid DocTypes: {0}").format(", ".join(sorted(invalid))))
	if not selected:
		frappe.throw(_("Select at least one DocType."))
	return selected


def _delete_all(doctype: str) -> int:
	names = frappe.get_all(doctype, pluck="name")
	deleted = 0
	for name in names:
		if frappe.db.exists(doctype, name):
			frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)
			deleted += 1
	return deleted
