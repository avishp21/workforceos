"""Workforce allocation orchestration service for WorkforceOS."""

from __future__ import annotations

import traceback
from datetime import date
from time import perf_counter
from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now

from workforceos.services.allocation_run_dashboard_service import (
	apply_dashboard_metrics,
	enrich_execution_stats,
)
from workforceos.services.employee_allocation_evaluation_service import (
	EmployeeAllocationEvaluationService,
	EvaluationRunStats,
	PendingEmployeeEvaluation,
	attach_selection_reasons,
)
from workforceos.services.competency_service import CompetencyService
from workforceos.services.preference_rule_engine import PreferenceRuleEngine
from workforceos.services.rule_engine import RuleEngine
from workforceos.utils.exceptions import AllocationError


class AllocationService:
	"""Orchestrates end-to-end workforce allocation."""

	def __init__(self) -> None:
		"""Initialize allocation dependencies."""
		self.rule_engine = RuleEngine()
		self.evaluation_service = EmployeeAllocationEvaluationService(self.rule_engine)
		self.preference_rule_engine = PreferenceRuleEngine()

	def allocate(self, allocation_date: str | date, shift: str) -> Document:
		"""Run workforce allocation for a date and shift.

		Args:
			allocation_date: Business date for allocation.
			shift: Shift identifier.

		Returns:
			The Allocation Run document.
		"""
		allocation_date = getdate(allocation_date)
		if not shift:
			frappe.throw(_("Shift is required"))

		run = self._create_allocation_run(allocation_date, shift)
		started_at = perf_counter()

		try:
			result = self._execute_allocation(run, allocation_date, shift)
			summary = self._build_summary(run, allocation_date, shift, result)
			run._allocation_summary = summary
			self._finalize_success(run, result, started_at)
		except Exception:
			self._finalize_failure(run, started_at)
		finally:
			frappe.db.commit()

		return run

	def allocate_workforce(
		self,
		target_date: date,
		plan_id: str | None = None,
		options: dict[str, Any] | None = None,
	) -> Document:
		"""Backward-compatible wrapper for allocation execution."""
		shift = (options or {}).get("shift")
		if not shift:
			frappe.throw(_("Shift is required in allocation options"))
		return self.allocate(target_date, shift)

	def get_allocation(self, target_date: date, allocation_id: str | None = None) -> Document | None:
		"""Retrieve an allocation run."""
		if allocation_id:
			if not frappe.db.exists("Allocation Run", allocation_id):
				return None
			return frappe.get_doc("Allocation Run", allocation_id)

		name = frappe.db.get_value(
			"Allocation Run",
			{"allocation_date": target_date},
			"name",
			order_by="creation desc",
		)
		return frappe.get_doc("Allocation Run", name) if name else None

	def reallocate(
		self,
		target_date: date,
		overrides: list[dict[str, Any]] | None = None,
		reason: str | None = None,
	) -> Document:
		"""Re-run allocation for a date using the provided shift override."""
		shift = (overrides or [{}])[0].get("shift") if overrides else None
		if not shift:
			frappe.throw(_("Shift is required for reallocation"))
		return self.allocate(target_date, shift)

	def get_allocation_status(self, allocation_id: str) -> dict[str, Any]:
		"""Return the current status of an allocation run."""
		run = frappe.get_doc("Allocation Run", allocation_id)
		return {
			"name": run.name,
			"status": run.status,
			"assignments_created": run.assignments_created,
			"total_shortage": run.total_shortage,
		}

	def cancel_allocation(self, allocation_id: str, reason: str | None = None) -> dict[str, Any]:
		"""Cancel an in-progress allocation run."""
		run = frappe.get_doc("Allocation Run", allocation_id)
		run.status = "Failed"
		if reason:
			run.remarks = reason
		run.completed_on = now()
		run.save(ignore_permissions=True)
		frappe.db.commit()
		return {"name": run.name, "status": run.status}

	def _create_allocation_run(self, allocation_date: date, shift: str) -> Document:
		"""Create and persist a new allocation run."""
		run = frappe.get_doc(
			{
				"doctype": "Allocation Run",
				"allocation_date": allocation_date,
				"shift": shift,
				"status": "Running",
				"started_on": now(),
			}
		)
		run.insert(ignore_permissions=True)
		frappe.db.commit()
		return run

	def _execute_allocation(self, run: Document, allocation_date: date, shift: str) -> dict[str, int]:
		"""Execute the allocation workflow."""
		plans = self._get_daily_line_plans(allocation_date, shift)
		if not plans:
			raise AllocationError(
				_("No Daily Line Plans found for {0} and shift {1}").format(allocation_date, shift)
			)

		attendance_map = self._get_attendance_map(allocation_date, shift)
		employee_map = self._get_employee_map(attendance_map.keys())
		rules = self.rule_engine.load_enabled_rules()
		eligibility_rules = [rule for rule in rules if rule.rule_category == "Eligibility"]
		validation_rules = [rule for rule in rules if rule.rule_category == "Validation"]
		preference_rules = [rule for rule in rules if rule.rule_category == "Preference"]

		stats = {
			"total_required": 0,
			"total_allocated": 0,
			"assignments_created": 0,
			"lines_processed": 0,
		}
		self.evaluation_service.stats = EvaluationRunStats()
		line_summaries: dict[str, dict[str, Any]] = {}
		assigned_employees: set[str] = set()

		for plan in plans:
			stats["lines_processed"] += 1
			production_line = plan.line
			line_summary = line_summaries.setdefault(
				production_line,
				{
					"line": production_line,
					"line_label": self._get_line_label(production_line),
					"required": 0,
					"allocated": 0,
				},
			)

			for requirement in plan.requirements:
				required_manpower = requirement.required_manpower or 0
				stats["total_required"] += required_manpower
				line_summary["required"] += required_manpower
				selected = self._select_employees(
					run=run,
					plan=plan,
					requirement=requirement,
					production_line=production_line,
					line_label=line_summary["line_label"],
					shift=shift,
					allocation_date=allocation_date,
					attendance_map=attendance_map,
					employee_map=employee_map,
					eligibility_rules=eligibility_rules,
					validation_rules=validation_rules,
					preference_rules=preference_rules,
					assigned_employees=assigned_employees,
					required_manpower=required_manpower,
				)

				for candidate in selected:
					self._create_assignment(
						run=run,
						allocation_date=allocation_date,
						shift=shift,
						employee=candidate["employee"]["name"],
						production_line=production_line,
						matched_competency=candidate.get("matched_competency"),
						selection_reason=candidate.get("allocation_selection_reason"),
						applied_preference_rules=candidate.get("applied_preference_rules"),
					)
					self._mark_attendance_allocated(
						attendance_name=candidate["attendance"]["name"],
						production_line=production_line,
					)
					assigned_employees.add(candidate["employee"]["name"])
					stats["total_allocated"] += 1
					stats["assignments_created"] += 1
					line_summary["allocated"] += 1

		stats["total_shortage"] = stats["total_required"] - stats["total_allocated"]
		enrich_execution_stats(stats, plans)
		stats["line_summaries"] = sorted(
			line_summaries.values(),
			key=lambda item: item["line_label"],
		)
		stats["evaluation_metrics"] = {
			"employees_evaluated": self.evaluation_service.stats.evaluated,
			"employees_allocated": self.evaluation_service.stats.allocated,
			"employees_rejected": self.evaluation_service.stats.rejected,
			"employees_skipped": self.evaluation_service.stats.skipped,
			"certified_allocations": self.evaluation_service.stats.certified_allocations,
			"non_certified_allocations": self.evaluation_service.stats.non_certified_allocations,
		}
		stats["unallocated_employees"] = self._get_unallocated_employees(
			attendance_map=attendance_map,
			employee_map=employee_map,
			assigned_employees=assigned_employees,
			plans=plans,
			shift=shift,
			allocation_date=allocation_date,
			eligibility_rules=eligibility_rules,
			validation_rules=validation_rules,
		)
		return stats

	def _get_daily_line_plans(self, allocation_date: date, shift: str) -> list[Document]:
		"""Load daily line plans for the allocation context."""
		plan_names = frappe.get_all(
			"Daily Line Plan",
			filters={"date": allocation_date, "shift": shift},
			pluck="name",
		)
		return [frappe.get_doc("Daily Line Plan", name) for name in plan_names]

	def _get_attendance_map(self, allocation_date: date, shift: str) -> dict[str, dict[str, Any]]:
		"""Load unallocated attendance records keyed by employee."""
		records = frappe.get_all(
			"Workforce Attendance",
			filters={
				"attendance_date": allocation_date,
				"shift": shift,
				"is_allocated": 0,
			},
			fields=["name", "employee", "status", "shift", "is_allocated"],
		)
		return {record.employee: record for record in records}

	def _get_employee_map(self, employee_names: set[str]) -> dict[str, dict[str, Any]]:
		"""Load workforce employees keyed by name."""
		if not employee_names:
			return {}

		employees = frappe.get_all(
			"Workforce Employee",
			filters={"name": ["in", list(employee_names)]},
			fields=["name", "employee_name", "employee_id", "default_line", "default_shift", "status"],
		)
		employee_map = {employee.name: employee for employee in employees}
		CompetencyService.attach_competencies_to_employees(employee_map)
		return employee_map

	def _select_employees(
		self,
		run: Document,
		plan: Document,
		requirement: Document,
		production_line: str,
		line_label: str,
		shift: str,
		allocation_date: date,
		attendance_map: dict[str, dict[str, Any]],
		employee_map: dict[str, dict[str, Any]],
		eligibility_rules: list[dict[str, Any]],
		validation_rules: list[dict[str, Any]],
		preference_rules: list[dict[str, Any]],
		assigned_employees: set[str],
		required_manpower: int,
	) -> list[dict[str, Any]]:
		"""Select employees for a manpower requirement using deterministic ranking."""
		del line_label
		candidates = []
		pending_evaluations: list[PendingEmployeeEvaluation] = []

		for employee_name, attendance in attendance_map.items():
			employee = employee_map.get(employee_name)
			if not employee:
				continue

			skip_reason = self._get_employee_skip_reason(
				employee=employee,
				employee_name=employee_name,
				attendance=attendance,
				assigned_employees=assigned_employees,
				allocation_date=allocation_date,
				shift=shift,
			)
			if skip_reason:
				self.evaluation_service.log_skipped_employee(
					allocation_run=run.name,
					employee=employee,
					production_line=production_line,
					reason=skip_reason,
				)
				continue

			context = {
				"employee": employee,
				"attendance": attendance,
				"requirement": requirement,
				"production_line": production_line,
				"shift": shift,
				"allocation_date": allocation_date,
				"assigned_employees": assigned_employees,
			}
			CompetencyService.enrich_rule_context(context)

			evaluation = self.evaluation_service.evaluate_employee_for_requirement(
				allocation_run=run.name,
				employee=employee,
				production_line=production_line,
				eligibility_rules=eligibility_rules,
				validation_rules=validation_rules,
				context=context,
			)

			if evaluation.get("pending"):
				pending_evaluations.append(evaluation["pending"])

			if evaluation["eligible"]:
				candidates.append(
					{
						"employee": employee,
						"attendance": attendance,
						"matched_competency": context.get("matched_competency"),
						"competency_selection_reason": context.get("competency_selection_reason"),
					}
				)

		selection_context = {
			"requirement": requirement,
			"production_line": production_line,
			"shift": shift,
			"allocation_date": allocation_date,
		}
		selection_result = self.preference_rule_engine.select_candidates(
			candidates=candidates,
			preference_rules=preference_rules,
			context=selection_context,
		)
		ranked_candidates = selection_result["candidates"]
		applied_preference_rules = selection_result["applied_preference_rules"]
		selected = ranked_candidates[:required_manpower]
		for candidate in selected:
			candidate["applied_preference_rules"] = applied_preference_rules
		attach_selection_reasons(selected, applied_preference_rules)
		selected_names = {candidate["employee"]["name"] for candidate in selected}
		self.evaluation_service.finalize_requirement_evaluations(
			allocation_run=run.name,
			production_line=production_line,
			pending_evaluations=pending_evaluations,
			preference_rules=preference_rules,
			selection_result=selection_result,
			selected_employee_names=selected_names,
		)
		return selected

	def _get_employee_skip_reason(
		self,
		employee: dict[str, Any],
		employee_name: str,
		attendance: dict[str, Any] | None,
		assigned_employees: set[str],
		allocation_date: date,
		shift: str,
	) -> str | None:
		"""Return a skip reason when rule evaluation should not run."""
		if employee_name in assigned_employees:
			return _("Already Assigned")

		if self._has_existing_assignment(employee_name, allocation_date, shift):
			return _("Already Assigned")

		if employee.get("status") == "Suspended":
			return _("Suspended Employee")

		if employee.get("status") != "Active":
			return _("Inactive Employee")

		if not attendance:
			return _("Attendance Missing")

		if attendance.get("status") not in ("Present", "Late", "Half Day"):
			return _("Attendance Missing")

		return None

	def _create_assignment(
		self,
		run: Document,
		allocation_date: date,
		shift: str,
		employee: str,
		production_line: str,
		matched_competency: dict[str, Any] | None = None,
		selection_reason: str | None = None,
		applied_preference_rules: list[dict[str, Any]] | None = None,
	) -> Document:
		"""Create an employee assignment for the allocation run."""
		matched_competency = matched_competency or {}
		log_fields = CompetencyService.build_matched_competency_log_fields(
			matched_competency,
			selection_reason=selection_reason,
			applied_preference_rules=applied_preference_rules,
		)
		assignment = frappe.get_doc(
			{
				"doctype": "Employee Assignment",
				"allocation_run": run.name,
				"assignment_date": allocation_date,
				"shift": shift,
				"employee": employee,
				"production_line": production_line,
				"assignment_status": "Assigned",
				"assignment_type": "Auto",
				"matched_competency": log_fields.get("matched_competency"),
				"matched_designation": log_fields.get("matched_designation"),
				"matched_skill": log_fields.get("matched_skill"),
				"matched_competency_priority": log_fields.get("matched_competency_priority"),
				"matched_certified": log_fields.get("matched_certified"),
				"applied_preference_rules": log_fields.get("applied_preference_rules"),
				"selection_reason": log_fields.get("selection_reason"),
			}
		)
		assignment.insert(ignore_permissions=True)
		return assignment

	def _mark_attendance_allocated(self, attendance_name: str, production_line: str) -> None:
		"""Mark attendance as allocated to a production line."""
		attendance = frappe.get_doc("Workforce Attendance", attendance_name)
		attendance.is_allocated = 1
		attendance.allocated_line = production_line
		attendance.save(ignore_permissions=True)

	def _finalize_success(self, run: Document, stats: dict[str, int], started_at: float) -> None:
		"""Update allocation run after successful execution."""
		execution_time_seconds = round(perf_counter() - started_at, 2)
		apply_dashboard_metrics(run, stats, execution_time_seconds)
		run.status = "Completed"
		run.completed_on = now()
		run.save(ignore_permissions=True)

	def _finalize_failure(self, run: Document, started_at: float) -> None:
		"""Update allocation run after a failed execution."""
		run.status = "Failed"
		run.completed_on = now()
		run.execution_time_seconds = round(perf_counter() - started_at, 2)
		run.error_log = traceback.format_exc()
		run.save(ignore_permissions=True)

	def _build_summary(
		self,
		run: Document,
		allocation_date: date,
		shift: str,
		result: dict[str, Any],
	) -> dict[str, Any]:
		"""Build a structured allocation summary for display."""
		return {
			"run": run.run_name or run.name,
			"date": str(allocation_date),
			"shift": shift,
			"required": result.get("total_required", 0),
			"allocated": result.get("total_allocated", 0),
			"shortage": result.get("total_shortage", 0),
			"lines": result.get("line_summaries", []),
			"unallocated_employees": result.get("unallocated_employees", []),
		}

	def _get_line_label(self, production_line: str) -> str:
		"""Return a display label for a production line."""
		return (
			frappe.db.get_value("Production Line", production_line, "line_name")
			or production_line
		)

	def _get_unallocated_employees(
		self,
		attendance_map: dict[str, dict[str, Any]],
		employee_map: dict[str, dict[str, Any]],
		assigned_employees: set[str],
		plans: list[Document],
		shift: str,
		allocation_date: date,
		eligibility_rules: list[dict[str, Any]],
		validation_rules: list[dict[str, Any]],
	) -> list[dict[str, str]]:
		"""Identify present employees who were not allocated and why."""
		unallocated = []

		for employee_name, attendance in attendance_map.items():
			if employee_name in assigned_employees:
				continue
			if attendance.status not in ("Present", "Late", "Half Day"):
				continue

			employee = employee_map.get(employee_name)
			if not employee:
				continue

			reason = self._get_unallocation_reason(
				employee=employee,
				attendance=attendance,
				plans=plans,
				shift=shift,
				allocation_date=allocation_date,
				assigned_employees=assigned_employees,
				eligibility_rules=eligibility_rules,
				validation_rules=validation_rules,
			)
			unallocated.append(
				{
					"employee": employee.get("employee_name") or employee_name,
					"reason": reason,
				}
			)

		return sorted(unallocated, key=lambda item: item["employee"])

	def _get_unallocation_reason(
		self,
		employee: dict[str, Any],
		attendance: dict[str, Any],
		plans: list[Document],
		shift: str,
		allocation_date: date,
		assigned_employees: set[str],
		eligibility_rules: list[dict[str, Any]],
		validation_rules: list[dict[str, Any]],
	) -> str:
		"""Determine why an employee could not be allocated."""
		if self._has_existing_assignment(employee["name"], allocation_date, shift):
			return _("Already Assigned")

		reasons: list[str] = []
		for plan in plans:
			for requirement in plan.requirements:
				context = {
					"employee": employee,
					"attendance": attendance,
					"requirement": requirement,
					"production_line": plan.line,
					"shift": shift,
					"allocation_date": allocation_date,
					"assigned_employees": assigned_employees,
				}
				CompetencyService.enrich_rule_context(context)
				reason = self._get_first_rule_failure(
					context,
					eligibility_rules + validation_rules,
				)
				if reason:
					reasons.append(reason)

		if reasons:
			return reasons[0]

		return _("No matching requirement")

	def _has_existing_assignment(self, employee: str, allocation_date: date, shift: str) -> bool:
		"""Return whether the employee already has an assignment for the date and shift."""
		return bool(
			frappe.db.exists(
				"Employee Assignment",
				{
					"employee": employee,
					"assignment_date": allocation_date,
					"shift": shift,
					"assignment_status": ["in", ["Assigned", "Reassigned"]],
				},
			)
		)

	def _get_first_rule_failure(
		self,
		context: dict[str, Any],
		rules: list[dict[str, Any]],
	) -> str | None:
		"""Return the first friendly failure reason for a rule evaluation context."""
		for rule in rules:
			result = self.rule_engine._evaluate_rule(rule, context)
			if result["passed"]:
				continue
			return self._friendly_rule_reason(result["rule_code"], result.get("message"))

		return None

	def _friendly_rule_reason(self, rule_code: str, message: str | None = None) -> str:
		"""Map rule codes to user-friendly allocation summary reasons."""
		reason_map = {
			"competency_match": _("Competency mismatch"),
			"skill_match": _("Competency mismatch"),
			"designation_match": _("Competency mismatch"),
			"duplicate_assignment": _("Already Assigned"),
			"employee_active": message or _("Inactive"),
			"attendance_present": _("Not Present"),
			"shift_match": _("Shift mismatch"),
			"demo_block_inactive": _("Inactive"),
		}
		return reason_map.get(rule_code) or message or _("Not eligible")
