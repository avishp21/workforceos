# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import getdate, today

from workforceos.utils.report_helpers import (
	append_competency_filters,
	competency_count_select,
	primary_competency_join,
)


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
			"label": _("Primary Designation"),
			"fieldname": "primary_designation",
			"fieldtype": "Link",
			"options": "Workforce Designation",
			"width": 160,
		},
		{
			"label": _("Primary Skill"),
			"fieldname": "primary_skill",
			"fieldtype": "Link",
			"options": "Skill",
			"width": 140,
		},
		{
			"label": _("Total Competencies"),
			"fieldname": "total_competencies",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": _("Matched Competency"),
			"fieldname": "matched_competency",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": _("Matched Designation"),
			"fieldname": "matched_designation",
			"fieldtype": "Link",
			"options": "Workforce Designation",
			"width": 160,
		},
		{
			"label": _("Matched Skill"),
			"fieldname": "matched_skill",
			"fieldtype": "Link",
			"options": "Skill",
			"width": 140,
		},
		{
			"label": _("Certified"),
			"fieldname": "matched_certified",
			"fieldtype": "Check",
			"width": 90,
		},
		{
			"label": _("Competency Priority"),
			"fieldname": "matched_competency_priority",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": _("Applied Preference Rules"),
			"fieldname": "applied_preference_rules",
			"fieldtype": "Small Text",
			"width": 220,
		},
		{
			"label": _("Selection Reason"),
			"fieldname": "selection_reason",
			"fieldtype": "Small Text",
			"width": 260,
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
	}

	for filter_key, (column, value_key) in filter_map.items():
		if filters.get(filter_key):
			conditions.append(f"{column} = %({value_key})s")
			values[value_key] = filters[filter_key]

	append_competency_filters(conditions, filters)

	if filters.get("certified") not in (None, ""):
		values["certified"] = int(filters.get("certified"))

	return frappe.db.sql(
		f"""
		SELECT
			emp.employee_id,
			emp.employee_name,
			emp.contractor,
			primary_comp.designation AS primary_designation,
			primary_comp.skill AS primary_skill,
			{competency_count_select("emp")},
			ea.matched_competency,
			ea.matched_designation,
			ea.matched_skill,
			ea.matched_competency_priority,
			ea.matched_certified,
			ea.applied_preference_rules,
			ea.selection_reason,
			ea.production_line,
			ea.assignment_status,
			ea.assignment_type,
			ea.allocation_run,
			ea.assigned_on
		FROM `tabEmployee Assignment` ea
		INNER JOIN `tabWorkforce Employee` emp ON emp.name = ea.employee
		{primary_competency_join("emp")}
		WHERE {" AND ".join(conditions)}
		ORDER BY ea.production_line ASC, emp.employee_name ASC
		""",
		values,
		as_dict=True,
	)
