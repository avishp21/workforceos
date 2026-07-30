"""Persistence for employee allocation evaluations and rule audit trails."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

import frappe
from frappe import _
from frappe.utils import now

from workforceos.services.competency_service import CompetencyService
from workforceos.services.preference_rule_engine import build_selection_reason
from workforceos.services.rule_engine import RuleEngine


@dataclass
class EvaluationRunStats:
	"""Aggregated evaluation metrics for an allocation run."""

	evaluated: int = 0
	allocated: int = 0
	rejected: int = 0
	skipped: int = 0
	certified_allocations: int = 0
	non_certified_allocations: int = 0

	def register(self, doc_fields: dict[str, Any]) -> None:
		"""Update counters from a persisted evaluation document."""
		self.evaluated += 1
		decision = doc_fields.get("final_decision")
		if decision == "Allocated":
			self.allocated += 1
			if doc_fields.get("certified"):
				self.certified_allocations += 1
			else:
				self.non_certified_allocations += 1
		elif decision == "Rejected":
			self.rejected += 1
		elif decision == "Skipped":
			self.skipped += 1


@dataclass
class PendingEmployeeEvaluation:
	"""Eligible employee evaluation waiting for preference-rule finalization."""

	employee_name: str
	employee: dict[str, Any]
	context: dict[str, Any]
	rule_rows: list[dict[str, Any]] = field(default_factory=list)
	started_at: float = field(default_factory=perf_counter)


class EmployeeAllocationEvaluationService:
	"""Creates one Employee Allocation Evaluation per employee consideration."""

	def __init__(self, rule_engine: RuleEngine | None = None) -> None:
		self.rule_engine = rule_engine or RuleEngine()
		self.stats = EvaluationRunStats()

	def log_skipped_employee(
		self,
		allocation_run: str,
		employee: dict[str, Any],
		production_line: str,
		reason: str,
	) -> dict[str, Any]:
		"""Persist a skipped employee evaluation without rule execution."""
		started_at = perf_counter()
		doc_fields = self._build_base_fields(
			allocation_run=allocation_run,
			employee=employee,
			production_line=production_line,
			context={},
		)
		doc_fields.update(
			{
				"final_decision": "Skipped",
				"evaluation_status": "Completed",
				"selection_reason": reason,
				"rules_evaluated": 0,
				"execution_time_ms": round((perf_counter() - started_at) * 1000, 3),
				"rule_evaluations": [],
			}
		)
		self._insert_evaluation(doc_fields)
		return {"employee_name": employee["name"], "skipped": True, "eligible": False}

	def evaluate_employee_for_requirement(
		self,
		allocation_run: str,
		employee: dict[str, Any],
		production_line: str,
		eligibility_rules: list[dict[str, Any]],
		validation_rules: list[dict[str, Any]],
		context: dict[str, Any],
	) -> dict[str, Any]:
		"""Evaluate eligibility and validation rules with early exit."""
		started_at = perf_counter()
		rule_rows: list[dict[str, Any]] = []
		execution_order = 0

		for rule in eligibility_rules:
			execution_order, outcome = self._evaluate_rule_row(
				rule=rule,
				context=context,
				execution_order=execution_order,
				rule_rows=rule_rows,
			)
			if not outcome["passed"]:
				self._insert_evaluation(
					self._build_rejected_fields(
						allocation_run=allocation_run,
						employee=employee,
						production_line=production_line,
						context=context,
						rule_rows=rule_rows,
						started_at=started_at,
						selection_reason=outcome.get("reason") or outcome.get("message") or "",
						stopped_early=True,
					)
				)
				return {
					"eligible": False,
					"failure_reason": outcome.get("reason") or outcome.get("message"),
					"employee_name": employee["name"],
				}

		for rule in validation_rules:
			execution_order, outcome = self._evaluate_rule_row(
				rule=rule,
				context=context,
				execution_order=execution_order,
				rule_rows=rule_rows,
			)
			if not outcome["passed"]:
				self._insert_evaluation(
					self._build_rejected_fields(
						allocation_run=allocation_run,
						employee=employee,
						production_line=production_line,
						context=context,
						rule_rows=rule_rows,
						started_at=started_at,
						selection_reason=outcome.get("reason") or outcome.get("message") or "",
						stopped_early=True,
					)
				)
				return {
					"eligible": False,
					"failure_reason": outcome.get("reason") or outcome.get("message"),
					"employee_name": employee["name"],
				}

		return {
			"eligible": True,
			"failure_reason": "",
			"employee_name": employee["name"],
			"pending": PendingEmployeeEvaluation(
				employee_name=employee["name"],
				employee=employee,
				context=context,
				rule_rows=rule_rows,
				started_at=started_at,
			),
		}

	def finalize_requirement_evaluations(
		self,
		allocation_run: str,
		production_line: str,
		pending_evaluations: list[PendingEmployeeEvaluation],
		preference_rules: list[dict[str, Any]],
		selection_result: dict[str, Any],
		selected_employee_names: set[str],
	) -> None:
		"""Append preference rule rows and persist eligible employee evaluations."""
		ranked_candidates = selection_result.get("candidates") or []
		preference_steps = selection_result.get("preference_steps") or []
		final_pool_names = {candidate["employee"]["name"] for candidate in ranked_candidates}

		for pending in pending_evaluations:
			rule_rows = list(pending.rule_rows)
			execution_order = len(rule_rows)
			execution_order = self._append_preference_rule_rows(
				employee_name=pending.employee_name,
				preference_rules=preference_rules,
				preference_steps=preference_steps,
				rule_rows=rule_rows,
				execution_order=execution_order,
			)

			employee_name = pending.employee_name
			if employee_name in selected_employee_names:
				final_decision = "Allocated"
				candidate = next(
					(item for item in ranked_candidates if item["employee"]["name"] == employee_name),
					None,
				)
				selection_reason = (
					(candidate or {}).get("allocation_selection_reason")
					or pending.context.get("competency_selection_reason")
					or _("Selected using deterministic competency ranking")
				)
			elif employee_name not in final_pool_names:
				final_decision = "Rejected"
				selection_reason = self._preference_rejection_reason(
					employee_name=employee_name,
					preference_steps=preference_steps,
				)
			else:
				final_decision = "Rejected"
				selection_reason = _("Not selected within manpower limit")

			doc_fields = self._build_base_fields(
				allocation_run=allocation_run,
				employee=pending.employee,
				production_line=production_line,
				context=pending.context,
			)
			doc_fields.update(
				{
					"final_decision": final_decision,
					"evaluation_status": "Completed",
					"selection_reason": selection_reason,
					"rules_evaluated": len(rule_rows),
					"execution_time_ms": round((perf_counter() - pending.started_at) * 1000, 3),
					"rule_evaluations": rule_rows,
				}
			)
			self._insert_evaluation(doc_fields)

	def _evaluate_rule_row(
		self,
		rule: dict[str, Any],
		context: dict[str, Any],
		execution_order: int,
		rule_rows: list[dict[str, Any]],
	) -> tuple[int, dict[str, Any]]:
		rule_started_at = perf_counter()
		outcome = self.rule_engine._evaluate_rule(rule, context)
		execution_order += 1
		status = "Passed" if outcome["passed"] else "Failed"
		reason = "" if outcome["passed"] else self._build_rule_reason(outcome)
		rule_rows.append(
			{
				"execution_order": execution_order,
				"rule": rule.get("name"),
				"status": status,
				"reason": reason,
				"execution_time_ms": round((perf_counter() - rule_started_at) * 1000, 3),
				"evaluation_details": json.dumps(outcome, default=str),
			}
		)
		return execution_order, {**outcome, "reason": reason}

	def _append_preference_rule_rows(
		self,
		employee_name: str,
		preference_rules: list[dict[str, Any]],
		preference_steps: list[dict[str, Any]],
		rule_rows: list[dict[str, Any]],
		execution_order: int,
	) -> int:
		steps_by_code = {step.get("rule_code"): step for step in preference_steps}

		for rule in preference_rules:
			rule_code = rule.get("rule_code")
			step = steps_by_code.get(rule_code)
			if not step:
				continue

			execution_order += 1
			before_names = set(step.get("before_names") or [])
			after_names = set(step.get("after_names") or [])
			if employee_name in after_names:
				status = "Passed"
				reason = step.get("message") or ""
			elif employee_name in before_names:
				status = "Failed"
				reason = step.get("message") or _("Filtered by preference rule")
			else:
				status = "Skipped"
				reason = _("Rule not applicable to this employee")

			rule_rows.append(
				{
					"execution_order": execution_order,
					"rule": rule.get("name"),
					"status": status,
					"reason": reason,
					"execution_time_ms": 0,
					"evaluation_details": json.dumps(step, default=str),
				}
			)

		return execution_order

	def _preference_rejection_reason(
		self,
		employee_name: str,
		preference_steps: list[dict[str, Any]],
	) -> str:
		for step in reversed(preference_steps):
			before_names = set(step.get("before_names") or [])
			after_names = set(step.get("after_names") or [])
			if employee_name in before_names and employee_name not in after_names:
				return step.get("message") or _("Filtered by preference rule")
		return _("Not selected within manpower limit")

	def _build_rejected_fields(
		self,
		allocation_run: str,
		employee: dict[str, Any],
		production_line: str,
		context: dict[str, Any],
		rule_rows: list[dict[str, Any]],
		started_at: float,
		selection_reason: str,
		stopped_early: bool,
	) -> dict[str, Any]:
		doc_fields = self._build_base_fields(
			allocation_run=allocation_run,
			employee=employee,
			production_line=production_line,
			context=context,
		)
		doc_fields.update(
			{
				"final_decision": "Rejected",
				"evaluation_status": "Stopped Early" if stopped_early else "Completed",
				"selection_reason": selection_reason,
				"rules_evaluated": len(rule_rows),
				"execution_time_ms": round((perf_counter() - started_at) * 1000, 3),
				"rule_evaluations": rule_rows,
			}
		)
		return doc_fields

	def _build_base_fields(
		self,
		allocation_run: str,
		employee: dict[str, Any],
		production_line: str,
		context: dict[str, Any],
	) -> dict[str, Any]:
		matched = context.get("matched_competency") or {}
		log_fields = CompetencyService.build_matched_competency_log_fields(matched)
		return {
			"doctype": "Employee Allocation Evaluation",
			"allocation_run": allocation_run,
			"employee": employee.get("name"),
			"employee_name": employee.get("employee_name") or employee.get("name"),
			"production_line": production_line,
			"matched_competency": log_fields.get("matched_competency"),
			"certified": log_fields.get("matched_certified") or 0,
			"competency_priority": log_fields.get("matched_competency_priority"),
			"created_on": now(),
		}

	def _insert_evaluation(self, doc_fields: dict[str, Any]) -> str:
		doc = frappe.get_doc(doc_fields)
		doc.insert(ignore_permissions=True)
		self.stats.register(doc_fields)
		return doc.name

	@staticmethod
	def _build_rule_reason(outcome: dict[str, Any]) -> str:
		if outcome.get("passed"):
			return ""
		return outcome.get("message") or outcome.get("rule_name") or outcome.get("rule_code") or ""


def attach_selection_reasons(
	candidates: list[dict[str, Any]],
	applied_preference_rules: list[dict[str, Any]],
) -> None:
	"""Enrich selected candidates with allocation selection reasons."""
	for candidate in candidates:
		candidate["allocation_selection_reason"] = build_selection_reason(
			applied_preference_rules,
			candidate,
		)
