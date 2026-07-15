# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import flt, getdate, today


def execute(filters: dict[str, Any] | None = None):
	"""Return columns and data for the Line Manpower Summary report."""
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns() -> list[dict[str, Any]]:
	"""Define report columns."""
	return [
		{
			"label": _("Production Line"),
			"fieldname": "production_line",
			"fieldtype": "Link",
			"options": "Production Line",
			"width": 200,
		},
		{
			"label": _("Required Manpower"),
			"fieldname": "required_manpower",
			"fieldtype": "Int",
			"width": 150,
		},
		{
			"label": _("Allocated Manpower"),
			"fieldname": "allocated_manpower",
			"fieldtype": "Int",
			"width": 150,
		},
		{
			"label": _("Shortage"),
			"fieldname": "shortage",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": _("Excess"),
			"fieldname": "excess",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": _("Completion %"),
			"fieldname": "completion_pct",
			"fieldtype": "Percent",
			"width": 130,
		},
	]


def get_data(filters: dict[str, Any]) -> list[dict[str, Any]]:
	"""Build line-wise manpower summary rows."""
	allocation_date = getdate(filters.get("allocation_date") or today())
	shift = filters.get("shift")

	required_by_line = _get_required_manpower(allocation_date, shift)
	allocated_by_line = _get_allocated_manpower(allocation_date, shift)
	lines = _get_sorted_lines(set(required_by_line) | set(allocated_by_line))

	rows = []
	total_required = 0
	total_allocated = 0

	for line in lines:
		required = required_by_line.get(line, 0)
		allocated = allocated_by_line.get(line, 0)
		shortage = max(required - allocated, 0)
		excess = max(allocated - required, 0)
		completion_pct = _get_completion_pct(required, allocated)

		rows.append(
			{
				"production_line": line,
				"required_manpower": required,
				"allocated_manpower": allocated,
				"shortage": shortage,
				"excess": excess,
				"completion_pct": completion_pct,
			}
		)
		total_required += required
		total_allocated += allocated

	if rows:
		rows.append(
			{
				"production_line": _("Total"),
				"required_manpower": total_required,
				"allocated_manpower": total_allocated,
				"shortage": max(total_required - total_allocated, 0),
				"excess": max(total_allocated - total_required, 0),
				"completion_pct": _get_completion_pct(total_required, total_allocated),
				"is_total_row": 1,
			}
		)

	return rows


def _get_required_manpower(allocation_date, shift: str | None) -> dict[str, int]:
	"""Sum required manpower from daily line plans by production line."""
	conditions = ["dlp.docstatus < 2", "dlp.date = %(allocation_date)s"]
	values: dict[str, Any] = {"allocation_date": allocation_date}

	if shift:
		conditions.append("dlp.shift = %(shift)s")
		values["shift"] = shift

	records = frappe.db.sql(
		f"""
		SELECT
			dlp.line AS production_line,
			COALESCE(SUM(dlr.required_manpower), 0) AS required_manpower
		FROM `tabDaily Line Plan` dlp
		INNER JOIN `tabDaily Line Requirement` dlr ON dlr.parent = dlp.name
		WHERE {" AND ".join(conditions)}
		GROUP BY dlp.line
		""",
		values,
		as_dict=True,
	)
	return {record.production_line: int(record.required_manpower) for record in records}


def _get_allocated_manpower(allocation_date, shift: str | None) -> dict[str, int]:
	"""Count employee assignments by production line."""
	conditions = [
		"ea.docstatus < 2",
		"ea.assignment_date = %(allocation_date)s",
		"ea.assignment_status != 'Cancelled'",
	]
	values: dict[str, Any] = {"allocation_date": allocation_date}

	if shift:
		conditions.append("ea.shift = %(shift)s")
		values["shift"] = shift

	records = frappe.db.sql(
		f"""
		SELECT
			ea.production_line,
			COUNT(ea.name) AS allocated_manpower
		FROM `tabEmployee Assignment` ea
		WHERE {" AND ".join(conditions)}
		GROUP BY ea.production_line
		""",
		values,
		as_dict=True,
	)
	return {record.production_line: int(record.allocated_manpower) for record in records}


def _get_sorted_lines(lines: set[str]) -> list[str]:
	"""Return production lines ordered alphabetically by line name."""
	if not lines:
		return []

	line_names = frappe.db.sql(
		"""
		SELECT name, line_name
		FROM `tabProduction Line`
		WHERE name IN %(lines)s
		ORDER BY line_name ASC, name ASC
		""",
		{"lines": list(lines)},
		as_dict=True,
	)
	known_lines = {record.name for record in line_names}
	sorted_lines = [record.name for record in line_names]
	sorted_lines.extend(sorted(lines - known_lines))
	return sorted_lines


def _get_completion_pct(required: int, allocated: int) -> float:
	"""Calculate completion percentage for a line."""
	if required > 0:
		return flt(allocated / required * 100, 2)
	if allocated > 0:
		return 100.0
	return 0.0
