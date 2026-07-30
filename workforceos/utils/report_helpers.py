"""Shared helpers for WorkforceOS script reports."""

from __future__ import annotations

from typing import Any


def append_competency_filters(
	conditions: list[str],
	filters: dict[str, Any],
	employee_alias: str = "emp",
) -> None:
	"""Append designation/skill filters against the competency matrix."""
	if filters.get("designation"):
		conditions.append(
			f"""
			EXISTS (
				SELECT 1
				FROM `tabEmployee Competency` ec_designation
				WHERE ec_designation.parent = {employee_alias}.name
					AND ec_designation.parenttype = 'Workforce Employee'
					AND ec_designation.designation = %(designation)s
			)
			"""
		)

	if filters.get("skill"):
		conditions.append(
			f"""
			EXISTS (
				SELECT 1
				FROM `tabEmployee Competency` ec_skill
				WHERE ec_skill.parent = {employee_alias}.name
					AND ec_skill.parenttype = 'Workforce Employee'
					AND ec_skill.skill = %(skill)s
			)
			"""
		)

	if filters.get("certified") not in (None, ""):
		conditions.append(
			f"""
			EXISTS (
				SELECT 1
				FROM `tabEmployee Competency` ec_certified
				WHERE ec_certified.parent = {employee_alias}.name
					AND ec_certified.parenttype = 'Workforce Employee'
					AND ec_certified.certified = %(certified)s
			)
			"""
		)


def primary_competency_join(employee_alias: str = "emp") -> str:
	"""SQL join for each employee's primary (lowest priority) competency."""
	return f"""
	LEFT JOIN `tabEmployee Competency` primary_comp
		ON primary_comp.parent = {employee_alias}.name
		AND primary_comp.parenttype = 'Workforce Employee'
		AND primary_comp.priority = (
			SELECT MIN(ec_min.priority)
			FROM `tabEmployee Competency` ec_min
			WHERE ec_min.parent = {employee_alias}.name
				AND ec_min.parenttype = 'Workforce Employee'
		)
	"""


def competency_count_select(employee_alias: str = "emp") -> str:
	"""SQL expression for total competencies per employee."""
	return f"""(
		SELECT COUNT(*)
		FROM `tabEmployee Competency` ec_count
		WHERE ec_count.parent = {employee_alias}.name
			AND ec_count.parenttype = 'Workforce Employee'
	) AS total_competencies"""
