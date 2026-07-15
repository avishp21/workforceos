# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import getdate


def execute(filters: dict[str, Any] | None = None):
	"""Return columns and data for the Allocation Run Summary report."""
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns() -> list[dict[str, Any]]:
	"""Define report columns."""
	return [
		{
			"label": _("Run Name"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Allocation Run",
			"width": 150,
		},
		{
			"label": _("Allocation Date"),
			"fieldname": "allocation_date",
			"fieldtype": "Date",
			"width": 120,
		},
		{
			"label": _("Shift"),
			"fieldname": "shift",
			"fieldtype": "Link",
			"options": "Shift",
			"width": 140,
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"label": _("Required"),
			"fieldname": "total_required",
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"label": _("Allocated"),
			"fieldname": "total_allocated",
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"label": _("Shortage"),
			"fieldname": "total_shortage",
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"label": _("Assignments Created"),
			"fieldname": "assignments_created",
			"fieldtype": "Int",
			"width": 150,
		},
		{
			"label": _("Execution Time"),
			"fieldname": "execution_time_seconds",
			"fieldtype": "Float",
			"width": 120,
		},
		{
			"label": _("Started On"),
			"fieldname": "started_on",
			"fieldtype": "Datetime",
			"width": 160,
		},
		{
			"label": _("Completed On"),
			"fieldname": "completed_on",
			"fieldtype": "Datetime",
			"width": 160,
		},
	]


def get_data(filters: dict[str, Any]) -> list[dict[str, Any]]:
	"""Fetch allocation run history for the selected filters."""
	conditions = ["ar.docstatus < 2"]
	values: dict[str, Any] = {}

	if filters.get("date"):
		conditions.append("ar.allocation_date = %(allocation_date)s")
		values["allocation_date"] = getdate(filters["date"])

	if filters.get("shift"):
		conditions.append("ar.shift = %(shift)s")
		values["shift"] = filters["shift"]

	if filters.get("status"):
		conditions.append("ar.status = %(status)s")
		values["status"] = filters["status"]

	return frappe.db.sql(
		f"""
		SELECT
			ar.name,
			COALESCE(ar.run_name, ar.name) AS run_name,
			ar.allocation_date,
			ar.shift,
			ar.status,
			ar.total_required,
			ar.total_allocated,
			ar.total_shortage,
			ar.assignments_created,
			ar.execution_time_seconds,
			ar.started_on,
			ar.completed_on
		FROM `tabAllocation Run` ar
		WHERE {" AND ".join(conditions)}
		ORDER BY ar.started_on DESC, ar.creation DESC
		""",
		values,
		as_dict=True,
	)
