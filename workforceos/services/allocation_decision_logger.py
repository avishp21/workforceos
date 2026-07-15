"""Allocation decision logging for WorkforceOS."""

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import now

from workforceos.services.rule_engine import RuleEngine

FINAL_DECISION_RULE_CODE = "final_decision"
SKIP_RULE_CODE = "employee_skip"


class AllocationDecisionLogger:
	"""Persists explainable allocation decisions for each rule evaluation."""

	def __init__(self, rule_engine: RuleEngine | None = None) -> None:
		self.rule_engine = rule_engine or RuleEngine()

	def log_skipped_employee(
		self,
		allocation_run: str,
		daily_line_plan: str,
		employee: str,
		requirement: Any,
		production_line: str,
		reason: str,
	) -> None:
		"""Log a skipped employee before rule evaluation begins."""
		self._create_log(
			allocation_run=allocation_run,
			daily_line_plan=daily_line_plan,
			employee=employee,
			requirement=requirement,
			production_line=production_line,
			rule=None,
			rule_code=SKIP_RULE_CODE,
			result="Skipped",
			score=0,
			decision="Skipped",
			reason=reason,
			details=None,
		)

	def evaluate_employee_for_requirement(
		self,
		allocation_run: str,
		daily_line_plan: str,
		employee: dict[str, Any],
		requirement: Any,
		production_line: str,
		eligibility_rules: list[dict[str, Any]],
		validation_rules: list[dict[str, Any]],
		preference_rules: list[dict[str, Any]],
		context: dict[str, Any],
	) -> dict[str, Any]:
		"""Evaluate rules for an employee and persist a log entry for each evaluation."""
		total_score = 0

		for rule in eligibility_rules:
			outcome = self._evaluate_and_log(
				allocation_run=allocation_run,
				daily_line_plan=daily_line_plan,
				employee=employee,
				requirement=requirement,
				production_line=production_line,
				rule=rule,
				context=context,
			)
			if not outcome["passed"]:
				return {
					"eligible": False,
					"score": 0,
					"failure_reason": outcome.get("reason") or outcome.get("message"),
					"employee_name": employee["name"],
				}

		for rule in validation_rules:
			outcome = self._evaluate_and_log(
				allocation_run=allocation_run,
				daily_line_plan=daily_line_plan,
				employee=employee,
				requirement=requirement,
				production_line=production_line,
				rule=rule,
				context=context,
			)
			if not outcome["passed"]:
				return {
					"eligible": False,
					"score": 0,
					"failure_reason": outcome.get("reason") or outcome.get("message"),
					"employee_name": employee["name"],
				}

		for rule in preference_rules:
			outcome = self._evaluate_and_log(
				allocation_run=allocation_run,
				daily_line_plan=daily_line_plan,
				employee=employee,
				requirement=requirement,
				production_line=production_line,
				rule=rule,
				context=context,
			)
			if outcome["passed"]:
				total_score += outcome.get("score", 0) or 0

		return {
			"eligible": True,
			"score": total_score,
			"failure_reason": "",
			"employee_name": employee["name"],
		}

	def finalize_requirement_decisions(
		self,
		allocation_run: str,
		daily_line_plan: str,
		requirement: Any,
		production_line: str,
		line_label: str,
		evaluations: list[dict[str, Any]],
		selected_employee_names: set[str],
	) -> None:
		"""Create final decision log entries for evaluated employees."""
		for evaluation in evaluations:
			if evaluation.get("skipped"):
				continue

			employee_name = evaluation["employee_name"]
			if evaluation["eligible"] and employee_name in selected_employee_names:
				self._log_final_decision(
					allocation_run=allocation_run,
					daily_line_plan=daily_line_plan,
					employee=employee_name,
					requirement=requirement,
					production_line=production_line,
					decision="Allocated",
					reason=_("Highest score for {0}").format(line_label),
					score=evaluation.get("score", 0),
				)
			elif evaluation["eligible"]:
				self._log_final_decision(
					allocation_run=allocation_run,
					daily_line_plan=daily_line_plan,
					employee=employee_name,
					requirement=requirement,
					production_line=production_line,
					decision="Rejected",
					reason=_("Not selected within manpower limit"),
					score=evaluation.get("score", 0),
				)

	def _evaluate_and_log(
		self,
		allocation_run: str,
		daily_line_plan: str,
		employee: dict[str, Any],
		requirement: Any,
		production_line: str,
		rule: dict[str, Any],
		context: dict[str, Any],
	) -> dict[str, Any]:
		"""Evaluate one rule and persist a decision log entry."""
		outcome = self.rule_engine._evaluate_rule(rule, context)
		passed = outcome["passed"]
		result = "Pass" if passed else "Fail"
		score = outcome.get("score", 0) if passed else 0
		decision = "Continue" if passed else "Rejected"
		reason = self._build_rule_reason(outcome)

		self._create_log(
			allocation_run=allocation_run,
			daily_line_plan=daily_line_plan,
			employee=employee["name"],
			requirement=requirement,
			production_line=production_line,
			rule=rule,
			rule_code=rule.get("rule_code"),
			result=result,
			score=score,
			decision=decision,
			reason=reason,
			details=json.dumps(outcome, default=str),
		)
		return {**outcome, "reason": reason}

	def _log_final_decision(
		self,
		allocation_run: str,
		daily_line_plan: str,
		employee: str,
		requirement: Any,
		production_line: str,
		decision: str,
		reason: str,
		score: int,
	) -> None:
		"""Persist the final allocation outcome for an employee."""
		self._create_log(
			allocation_run=allocation_run,
			daily_line_plan=daily_line_plan,
			employee=employee,
			requirement=requirement,
			production_line=production_line,
			rule=None,
			rule_code=FINAL_DECISION_RULE_CODE,
			result="Pass" if decision == "Allocated" else "Fail",
			score=score,
			decision=decision,
			reason=reason,
			details=None,
		)

	def _build_rule_reason(self, outcome: dict[str, Any]) -> str:
		"""Return a human-readable reason for a rule evaluation."""
		if outcome.get("passed"):
			return ""
		return outcome.get("message") or outcome.get("rule_name") or outcome.get("rule_code") or ""

	def _create_log(
		self,
		allocation_run: str,
		daily_line_plan: str,
		employee: str | None,
		requirement: Any,
		production_line: str,
		rule: dict[str, Any] | None,
		rule_code: str | None,
		result: str,
		score: int,
		decision: str,
		reason: str,
		details: str | None,
	) -> str:
		"""Insert an Allocation Decision Log record."""
		doc = frappe.get_doc(
			{
				"doctype": "Allocation Decision Log",
				"allocation_run": allocation_run,
				"daily_line_plan": daily_line_plan,
				"employee": employee,
				"production_line": production_line,
				"designation": getattr(requirement, "designation", None),
				"skill": getattr(requirement, "skill", None),
				"allocation_rule": rule.get("name") if rule else None,
				"rule_code": rule_code,
				"result": result,
				"score": score,
				"decision": decision,
				"reason": reason,
				"details": details,
				"evaluated_on": now(),
			}
		)
		doc.insert(ignore_permissions=True)
		return doc.name
