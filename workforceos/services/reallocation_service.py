"""Supervisor reallocation workflow for WorkforceOS."""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import now

from workforceos.services.competency_service import CompetencyService
from workforceos.services.rule_engine import RuleEngine


class ReallocationService:
	"""Validate and persist manual employee reallocations."""

	def __init__(self, rule_engine: RuleEngine | None = None) -> None:
		self.rule_engine = rule_engine or RuleEngine()

	def get_current_allocations(self, allocation_run: str) -> list[dict[str, Any]]:
		"""Return active assignments for an allocation run."""
		frappe.has_permission("Employee Assignment", "read", throw=True)
		rows = frappe.get_all(
			"Employee Assignment",
			filters={
				"allocation_run": allocation_run,
				"assignment_status": ["in", ["Assigned", "Reassigned"]],
			},
			fields=[
				"name",
				"employee",
				"production_line",
				"matched_competency",
				"matched_certified",
				"assignment_status",
			],
			order_by="production_line asc, employee asc",
		)
		for row in rows:
			row["employee_name"] = frappe.db.get_value(
				"Workforce Employee", row.employee, "employee_name"
			) or row.employee
		return rows

	def get_workstations_for_line(
		self,
		allocation_run: str,
		production_line: str,
	) -> list[dict[str, Any]]:
		"""Return workstation options from the daily line plan for a production line."""
		run = frappe.get_doc("Allocation Run", allocation_run)
		plan_name = frappe.db.get_value(
			"Daily Line Plan",
			{
				"date": run.allocation_date,
				"shift": run.shift,
				"line": production_line,
			},
			"name",
		)
		if not plan_name:
			return []

		plan = frappe.get_doc("Daily Line Plan", plan_name)
		options: list[dict[str, Any]] = []
		for requirement in plan.requirements:
			designation = requirement.designation
			skill = requirement.skill
			label = CompetencyService.format_matched_competency(
				{"designation": designation, "skill": skill}
			)
			options.append(
				{
					"value": f"{designation}|{skill}",
					"label": label,
					"designation": designation,
					"skill": skill,
				}
			)
		return options

	def reallocate(
		self,
		assignment_name: str,
		to_production_line: str,
		reason: str,
		comments: str | None = None,
		to_workstation: str | None = None,
	) -> dict[str, Any]:
		"""Validate and apply a production-line reallocation (MVP)."""
		frappe.has_permission("Employee Assignment", "write", throw=True)
		frappe.has_permission("Employee Reallocation", "create", throw=True)

		assignment = frappe.get_doc("Employee Assignment", assignment_name)
		if not to_production_line:
			frappe.throw(_("New Production Line is required"))

		if to_workstation:
			designation, skill = self._parse_workstation_key(to_workstation)
		else:
			designation = assignment.matched_designation
			skill = assignment.matched_skill

		if not designation and not skill:
			frappe.throw(_("Assignment has no matched competency to validate"))

		validation = self._validate_reallocation(
			assignment=assignment,
			to_production_line=to_production_line,
			designation=designation,
			skill=skill,
		)
		if not validation["passed"]:
			return {
				"success": False,
				"message": validation["message"],
			}

		from_line = assignment.production_line
		matched_competency_label = assignment.matched_competency or CompetencyService.format_matched_competency(
			{
				"designation": assignment.matched_designation,
				"skill": assignment.matched_skill,
			}
		)

		reallocation = frappe.get_doc(
			{
				"doctype": "Employee Reallocation",
				"allocation_run": assignment.allocation_run,
				"employee_assignment": assignment.name,
				"assignment_date": assignment.assignment_date,
				"shift": assignment.shift,
				"employee": assignment.employee,
				"employee_name": frappe.db.get_value(
					"Workforce Employee", assignment.employee, "employee_name"
				),
				"from_production_line": from_line,
				"to_production_line": to_production_line,
				"matched_competency": matched_competency_label,
				"reason": reason,
				"comments": comments,
				"validation_passed": 1,
				"validation_message": validation["message"],
				"reallocated_by": frappe.session.user,
				"reallocated_on": now(),
			}
		)
		reallocation.insert(ignore_permissions=True)

		assignment.production_line = to_production_line
		assignment.selection_reason = _("Manual reallocation to {0}: {1}").format(
			to_production_line,
			reason,
		)
		assignment.assignment_status = "Reassigned"
		assignment.assignment_type = "Manual"
		assignment.remarks = comments or assignment.remarks
		assignment.save(ignore_permissions=True)

		self._update_attendance_line(assignment)
		frappe.db.commit()

		return {
			"success": True,
			"message": _("Employee reallocated to {0}").format(to_production_line),
			"reallocation": reallocation.name,
			"assignment": assignment.name,
		}

	def _validate_reallocation(
		self,
		assignment: frappe.model.document.Document,
		to_production_line: str,
		designation: str,
		skill: str,
	) -> dict[str, Any]:
		employee_rows = frappe.get_all(
			"Workforce Employee",
			filters={"name": assignment.employee},
			fields=["name", "employee_name", "status"],
		)
		if not employee_rows:
			frappe.throw(_("Employee {0} was not found").format(assignment.employee))
		employee_map = {row.name: dict(row) for row in employee_rows}
		CompetencyService.attach_competencies_to_employees(employee_map)
		employee_dict = employee_map[assignment.employee]

		attendance = frappe.db.get_value(
			"Workforce Attendance",
			{
				"employee": assignment.employee,
				"attendance_date": assignment.assignment_date,
				"shift": assignment.shift,
			},
			["name", "status", "shift"],
			as_dict=True,
		)

		requirement = frappe._dict({"designation": designation, "skill": skill})
		assigned_employees = set(
			frappe.get_all(
				"Employee Assignment",
				filters={
					"assignment_date": assignment.assignment_date,
					"shift": assignment.shift,
					"assignment_status": ["in", ["Assigned", "Reassigned"]],
					"name": ["!=", assignment.name],
				},
				pluck="employee",
			)
		)

		context = {
			"employee": employee_dict,
			"attendance": attendance or {},
			"requirement": requirement,
			"production_line": to_production_line,
			"shift": assignment.shift,
			"allocation_date": assignment.assignment_date,
			"assigned_employees": assigned_employees,
		}
		CompetencyService.enrich_rule_context(context)

		rules = self.rule_engine.load_enabled_rules()
		eligibility = [rule for rule in rules if rule.rule_category == "Eligibility"]
		validation = [rule for rule in rules if rule.rule_category == "Validation"]

		for rule in eligibility + validation:
			outcome = self.rule_engine._evaluate_rule(rule, context)
			if not outcome["passed"]:
				return {
					"passed": False,
					"message": outcome.get("message")
					or outcome.get("rule_name")
					or _("Reallocation validation failed"),
					"matched_competency": context.get("matched_competency"),
				}

		return {
			"passed": True,
			"message": _("All allocation rules passed"),
			"matched_competency": context.get("matched_competency"),
		}

	def _parse_workstation_key(self, workstation_key: str) -> tuple[str, str]:
		if not workstation_key:
			return "", ""
		if "|" in workstation_key:
			designation, skill = workstation_key.split("|", 1)
			return designation, skill
		return "", workstation_key

	def _update_attendance_line(self, assignment: frappe.model.document.Document) -> None:
		attendance_name = frappe.db.get_value(
			"Workforce Attendance",
			{
				"employee": assignment.employee,
				"attendance_date": assignment.assignment_date,
				"shift": assignment.shift,
			},
			"name",
		)
		if not attendance_name:
			return
		frappe.db.set_value(
			"Workforce Attendance",
			attendance_name,
			"allocated_line",
			assignment.production_line,
		)
