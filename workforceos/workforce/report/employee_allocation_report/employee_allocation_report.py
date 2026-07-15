# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import getdate, today


def execute(filters: dict[str, Any] | None = None):
	"""Return columns and data for the Employee Allocation Report."""
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns() -> list[dict[str, Any]]:
	"""Define report columns."""
	return [
		{
			"label": _("Employee ID"),
			"fieldname": "employee_id",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Employee Name"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("Contractor"),
			"fieldname": "contractor",
			"fieldtype": "Link",
			"options": "Contractor",
			"width": 160,
		},
		{
			"label": _("Designation"),
			"fieldname": "designation",
			"fieldtype": "Link",
			"options": "Workforce Designation",
			"width": 160,
		},
		{
			"label": _("Skill"),
			"fieldname": "skill",
			"fieldtype": "Link",
			"options": "Skill",
			"width": 140,
		},
		{
			"label": _("Production Line"),
			"fieldname": "production_line",
			"fieldtype": "Link",
			"options": "Production Line",
			"width": 160,
		},
		{
			"label": _("Assignment Status"),
			"fieldname": "assignment_status",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": _("Assignment Type"),
			"fieldname": "assignment_type",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Allocation Run"),
			"fieldname": "allocation_run",
			"fieldtype": "Link",
			"options": "Allocation Run",
			"width": 150,
		},
		{
			"label": _("Assigned On"),
			"fieldname": "assigned_on",
			"fieldtype": "Datetime",
			"width": 160,
		},
	]


def get_data(filters: dict[str, Any]) -> list[dict[str, Any]]:
	"""Fetch employee allocation rows for the selected filters."""
	allocation_date = filters.get("allocation_date") or today()
	conditions = ["ea.docstatus < 2", "ea.assignment_date = %(allocation_date)s"]
	values: dict[str, Any] = {"allocation_date": getdate(allocation_date)}

	filter_map = {
		"shift": ("ea.shift", "shift"),
		"production_line": ("ea.production_line", "production_line"),
		"contractor": ("emp.contractor", "contractor"),
		"skill": ("emp.skill", "skill"),
		"designation": ("emp.designation", "designation"),
	}

	for filter_key, (column, value_key) in filter_map.items():
		if filters.get(filter_key):
			conditions.append(f"{column} = %({value_key})s")
			values[value_key] = filters[filter_key]

	return frappe.db.sql(
		f"""
		SELECT
			emp.employee_id,
			emp.employee_name,
			emp.contractor,
			emp.designation,
			emp.skill,
			ea.production_line,
			ea.assignment_status,
			ea.assignment_type,
			ea.allocation_run,
			ea.assigned_on
		FROM `tabEmployee Assignment` ea
		INNER JOIN `tabWorkforce Employee` emp ON emp.name = ea.employee
		WHERE {" AND ".join(conditions)}
		ORDER BY ea.production_line ASC, emp.employee_name ASC
		""",
		values,
		as_dict=True,
	)
