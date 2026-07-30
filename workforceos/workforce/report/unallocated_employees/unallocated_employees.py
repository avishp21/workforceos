# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import getdate, today

from workforceos.services.competency_service import CompetencyService
from workforceos.services.rule_engine import RuleEngine
from workforceos.utils.report_helpers import append_competency_filters, primary_competency_join, competency_count_select


def execute(filters: dict[str, Any] | None = None):
	"""Return columns and data for the Unallocated Employees report."""
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
			"label": _("Attendance Status"),
			"fieldname": "attendance_status",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": _("Reason"),
			"fieldname": "reason",
			"fieldtype": "Data",
			"width": 180,
		},
	]


def get_data(filters: dict[str, Any]) -> list[dict[str, Any]]:
	"""Fetch present employees without assignments for the selected filters."""
	report_date = getdate(filters.get("date") or today())
	conditions = [
		"wa.docstatus < 2",
		"wa.attendance_date = %(report_date)s",
		"wa.status = 'Present'",
		"ea.name IS NULL",
	]
	values: dict[str, Any] = {"report_date": report_date}

	filter_map = {
		"shift": ("wa.shift", "shift"),
		"contractor": ("emp.contractor", "contractor"),
	}

	for filter_key, (column, value_key) in filter_map.items():
		if filters.get(filter_key):
			conditions.append(f"{column} = %({value_key})s")
			values[value_key] = filters[filter_key]

	append_competency_filters(conditions, filters)

	if filters.get("certified") not in (None, ""):
		values["certified"] = int(filters.get("certified"))

	rows = frappe.db.sql(
		f"""
		SELECT
			emp.name AS employee,
			emp.employee_id,
			emp.employee_name,
			emp.contractor,
			primary_comp.designation AS primary_designation,
			primary_comp.skill AS primary_skill,
			{competency_count_select("emp")},
			wa.status AS attendance_status,
			wa.shift,
			wa.attendance_date
		FROM `tabWorkforce Attendance` wa
		INNER JOIN `tabWorkforce Employee` emp ON emp.name = wa.employee
		{primary_competency_join("emp")}
		LEFT JOIN `tabEmployee Assignment` ea
			ON ea.employee = wa.employee
			AND ea.assignment_date = wa.attendance_date
			AND ea.shift = wa.shift
			AND ea.docstatus < 2
			AND ea.assignment_status != 'Cancelled'
		WHERE {" AND ".join(conditions)}
		ORDER BY emp.contractor ASC, emp.employee_name ASC
		""",
		values,
		as_dict=True,
	)

	context = _build_reason_context(report_date, filters.get("shift"))
	competency_map = CompetencyService.load_competencies_for_employees([row.employee for row in rows])
	for row in rows:
		competencies = competency_map.get(row.employee, [])
		row["competencies"] = competencies
		row["reason"] = _get_unallocated_reason(row, context, competencies)

	return rows


def _build_reason_context(report_date, shift: str | None) -> dict[str, Any]:
	"""Prepare shared context for reason evaluation."""
	plan_filters: dict[str, Any] = {"date": report_date}
	if shift:
		plan_filters["shift"] = shift

	plan_names = frappe.get_all("Daily Line Plan", filters=plan_filters, pluck="name")
	plans = [frappe.get_doc("Daily Line Plan", name) for name in plan_names]

	rule_engine = RuleEngine()
	rules = rule_engine.load_enabled_rules()

	return {
		"plans": plans,
		"shift": shift,
		"report_date": report_date,
		"eligibility_rules": [rule for rule in rules if rule.rule_category == "Eligibility"],
		"validation_rules": [rule for rule in rules if rule.rule_category == "Validation"],
		"rule_engine": rule_engine,
		"assigned_employees": _get_assigned_employees(report_date, shift),
	}


def _get_assigned_employees(report_date, shift: str | None) -> set[str]:
	"""Return employees already assigned for the date and shift."""
	assignment_filters: dict[str, Any] = {
		"assignment_date": report_date,
		"assignment_status": ["!=", "Cancelled"],
	}
	if shift:
		assignment_filters["shift"] = shift

	return set(
		frappe.get_all(
			"Employee Assignment",
			filters=assignment_filters,
			pluck="employee",
		)
	)


def _get_unallocated_reason(
	row: dict[str, Any],
	context: dict[str, Any],
	competencies: list[dict[str, Any]],
) -> str:
	"""Determine why a present employee was not allocated."""
	log_reason = _get_reason_from_decision_logs(row, context)
	if log_reason:
		return log_reason

	evaluated_reason = _get_reason_from_rule_evaluation(row, context)
	if evaluated_reason:
		return evaluated_reason

	return _("Not Allocated")


def _get_reason_from_decision_logs(row: dict[str, Any], context: dict[str, Any]) -> str | None:
	"""Read the most relevant reason from employee allocation evaluations."""
	run_filters: dict[str, Any] = {"allocation_date": context["report_date"]}
	if context.get("shift"):
		run_filters["shift"] = context["shift"]

	run_names = frappe.get_all(
		"Allocation Run",
		filters=run_filters,
		pluck="name",
		order_by="creation desc",
	)
	if not run_names:
		return None

	evaluations = frappe.get_all(
		"Employee Allocation Evaluation",
		filters={
			"employee": row["employee"],
			"allocation_run": ["in", run_names],
		},
		fields=["final_decision", "selection_reason", "evaluation_status"],
		order_by="creation desc",
	)
	if not evaluations:
		return _get_reason_from_legacy_decision_logs(row, context)

	for evaluation in evaluations:
		if evaluation.final_decision == "Allocated":
			continue
		if evaluation.final_decision == "Skipped":
			return evaluation.selection_reason or _("Already Assigned")
		reason = (evaluation.selection_reason or "").lower()
		if "manpower limit" in reason or "no matching" in reason:
			return _("No Requirement")
		if evaluation.selection_reason:
			return evaluation.selection_reason

	return None


def _get_reason_from_legacy_decision_logs(row: dict[str, Any], context: dict[str, Any]) -> str | None:
	"""Fallback for allocation runs that still used Allocation Decision Log."""
	run_filters: dict[str, Any] = {"allocation_date": context["report_date"]}
	if context.get("shift"):
		run_filters["shift"] = context["shift"]

	run_names = frappe.get_all(
		"Allocation Run",
		filters=run_filters,
		pluck="name",
		order_by="creation desc",
	)
	if not run_names:
		return None

	log_filters = {
		"employee": row["employee"],
		"allocation_run": ["in", run_names],
	}
	logs = frappe.get_all(
		"Allocation Decision Log",
		filters=log_filters,
		fields=["rule_code", "reason", "decision", "result"],
		order_by="evaluated_on desc",
	)
	if not logs:
		return None

	for log in logs:
		if log.rule_code == "final_decision":
			if "manpower limit" in (log.reason or "").lower():
				return _("No Requirement")
			continue

		normalized = _normalize_reason(log.rule_code, log.reason)
		if normalized:
			return normalized

	for log in logs:
		normalized = _normalize_reason(log.rule_code, log.reason)
		if normalized:
			return normalized

	return None


def _get_reason_from_rule_evaluation(row: dict[str, Any], context: dict[str, Any]) -> str | None:
	"""Evaluate allocation rules to infer an unallocated reason."""
	employee = {
		"name": row["employee"],
		"employee_name": row["employee_name"],
		"competencies": competencies,
		"status": frappe.db.get_value("Workforce Employee", row["employee"], "status"),
	}
	attendance = {
		"status": row["attendance_status"],
		"shift": row["shift"],
	}
	assigned_employees = context["assigned_employees"]

	if row["employee"] in assigned_employees:
		return _("Already Assigned")

	if not context["plans"]:
		return _("No Requirement")

	rule_engine = context["rule_engine"]
	rules = context["eligibility_rules"] + context["validation_rules"]
	reasons: list[str] = []

	for plan in context["plans"]:
		for requirement in plan.requirements:
			eval_context = {
				"employee": employee,
				"attendance": attendance,
				"requirement": requirement,
				"production_line": plan.line,
				"shift": context.get("shift") or row["shift"],
				"allocation_date": context["report_date"],
				"assigned_employees": assigned_employees,
			}
			CompetencyService.enrich_rule_context(eval_context)
			for rule in rules:
				result = rule_engine._evaluate_rule(rule, eval_context)
				if result["passed"]:
					continue
				normalized = _normalize_reason(result["rule_code"], result.get("message"))
				if normalized:
					reasons.append(normalized)
				break

	if reasons:
		return reasons[0]

	return _("No Requirement")


def _normalize_reason(rule_code: str | None, reason: str | None = None) -> str | None:
	"""Map rule outcomes to report reason labels."""
	reason_map = {
		"competency_match": _("Competency Mismatch"),
		"skill_match": _("Competency Mismatch"),
		"designation_match": _("Competency Mismatch"),
		"shift_match": _("Shift Mismatch"),
		"duplicate_assignment": _("Already Assigned"),
		"employee_skip": _("Already Assigned"),
		"final_decision": None,
	}

	if rule_code in reason_map and reason_map[rule_code]:
		return reason_map[rule_code]

	reason_text = (reason or "").lower()
	if "already assigned" in reason_text:
		return _("Already Assigned")
	if "skill" in reason_text:
		return _("Skill Mismatch")
	if "shift" in reason_text:
		return _("Shift Mismatch")
	if "no matching requirement" in reason_text or "manpower limit" in reason_text:
		return _("No Requirement")

	if rule_code and rule_code not in ("final_decision", "employee_skip"):
		return _("Unknown")

	return None
