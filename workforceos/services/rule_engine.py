"""Configurable business rule engine for WorkforceOS."""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _

RULE_CATEGORIES = ("Eligibility", "Preference", "Validation")


class RuleEngine:
	"""Evaluates configurable business rules across workforce workflows."""

	def load_enabled_rules(self) -> list[dict[str, Any]]:
		"""Load enabled allocation rules ordered by priority.

		Returns:
			Active allocation rules sorted by ascending priority.
		"""
		return frappe.get_all(
			"Allocation Rule",
			filters={"is_enabled": 1},
			fields=["name", "rule_name", "rule_code", "rule_category", "priority", "score", "description"],
			order_by="priority asc",
		)

	def load_rules(self, rule_set: str | None = None, scope: str | None = None) -> list[dict[str, Any]]:
		"""Load active rules for allocation.

		Args:
			rule_set: Unused placeholder for future rule sets.
			scope: Optional rule category filter.

		Returns:
			A list of active rule definitions.
		"""
		rules = self.load_enabled_rules()
		if scope:
			return [rule for rule in rules if rule.rule_category == scope]
		return rules

	def evaluate_rules(self, context: dict[str, Any], scope: str) -> dict[str, Any]:
		"""Evaluate all applicable rules for a given context.

		Args:
			context: Evaluation context including entities and parameters.
			scope: Rule category to evaluate.

		Returns:
			Rule evaluation results including pass/fail outcomes.
		"""
		results = []
		for rule in self.load_rules(scope=scope):
			outcome = self._evaluate_rule(rule, context)
			results.append(outcome)

		passed = all(result["passed"] for result in results) if results else True
		return {"passed": passed, "results": results}

	def validate_rule(self, rule: dict[str, Any]) -> bool:
		"""Validate a single rule definition."""
		return bool(rule.get("rule_code")) and rule.get("rule_category") in RULE_CATEGORIES

	def get_rule_violations(self, context: dict[str, Any], scope: str) -> list[dict[str, Any]]:
		"""Return rule violations for a context without halting execution."""
		evaluation = self.evaluate_rules(context, scope)
		return [result for result in evaluation["results"] if not result["passed"]]

	def explain_rule_outcome(self, rule_code: str, context: dict[str, Any]) -> dict[str, Any]:
		"""Explain why a specific rule passed or failed."""
		rule = frappe.db.get_value(
			"Allocation Rule",
			{"rule_code": rule_code},
			["name", "rule_name", "rule_code", "rule_category", "priority", "score", "description"],
			as_dict=True,
		)
		if not rule:
			frappe.throw(_("Allocation Rule {0} was not found").format(rule_code))
		return self._evaluate_rule(rule, context)

	def is_eligible(self, rule: dict[str, Any], context: dict[str, Any]) -> bool:
		"""Return whether a candidate passes an eligibility rule."""
		result = self._evaluate_rule(rule, context)
		return result["passed"]

	def is_valid(self, rule: dict[str, Any], context: dict[str, Any]) -> bool:
		"""Return whether a candidate passes a validation rule."""
		result = self._evaluate_rule(rule, context)
		return result["passed"]

	def get_preference_score(self, rule: dict[str, Any], context: dict[str, Any]) -> int:
		"""Return preference score contribution for a candidate."""
		result = self._evaluate_rule(rule, context)
		return result.get("score", 0) if result["passed"] else 0

	def score_candidate(self, preference_rules: list[dict[str, Any]], context: dict[str, Any]) -> int:
		"""Calculate total preference score for a candidate."""
		return sum(self.get_preference_score(rule, context) for rule in preference_rules)

	def _evaluate_rule(self, rule: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
		"""Evaluate a single rule against the provided context."""
		rule_code = rule["rule_code"]
		evaluator = RULE_EVALUATORS.get(rule_code)

		if not evaluator:
			return {
				"rule_code": rule_code,
				"rule_name": rule.get("rule_name"),
				"rule_category": rule.get("rule_category"),
				"passed": True,
				"score": 0,
				"message": _("No evaluator implemented for rule {0}").format(rule_code),
			}

		passed, score, message = evaluator(context, rule)
		return {
			"rule_code": rule_code,
			"rule_name": rule.get("rule_name"),
			"rule_category": rule.get("rule_category"),
			"passed": passed,
			"score": score,
			"message": message,
		}


def _employee_active(context: dict[str, Any], rule: dict[str, Any]) -> tuple[bool, int, str]:
	employee = context.get("employee") or {}
	passed = employee.get("status") == "Active"
	return passed, 0, _("Inactive Employee") if not passed else ""


def _attendance_present(context: dict[str, Any], rule: dict[str, Any]) -> tuple[bool, int, str]:
	attendance = context.get("attendance") or {}
	if not attendance:
		return False, 0, _("Attendance Missing")
	passed = attendance.get("status") in ("Present", "Late", "Half Day")
	return passed, 0, _("Attendance Missing") if not passed else ""


def _shift_match(context: dict[str, Any], rule: dict[str, Any]) -> tuple[bool, int, str]:
	attendance = context.get("attendance") or {}
	shift = context.get("shift")
	passed = attendance.get("shift") == shift
	return passed, 0, _("Shift mismatch") if not passed else ""


def _designation_match(context: dict[str, Any], rule: dict[str, Any]) -> tuple[bool, int, str]:
	employee = context.get("employee") or {}
	requirement = context.get("requirement") or {}
	if not requirement.get("designation"):
		return True, 0, ""
	passed = employee.get("designation") == requirement.get("designation")
	if passed:
		return True, 0, ""
	return (
		False,
		0,
		_("Employee designation is {0}\nRequired designation is {1}").format(
			employee.get("designation") or _("Not set"),
			requirement.get("designation"),
		),
	)


def _skill_match(context: dict[str, Any], rule: dict[str, Any]) -> tuple[bool, int, str]:
	employee = context.get("employee") or {}
	requirement = context.get("requirement") or {}
	if not requirement.get("skill"):
		return True, 0, ""
	passed = employee.get("skill") == requirement.get("skill")
	if passed:
		return True, 0, ""
	return (
		False,
		0,
		_("Employee skill is {0}\nRequired skill is {1}").format(
			employee.get("skill") or _("Not set"),
			requirement.get("skill"),
		),
	)


def _duplicate_assignment(context: dict[str, Any], rule: dict[str, Any]) -> tuple[bool, int, str]:
	employee_name = (context.get("employee") or {}).get("name")
	assigned_employees = context.get("assigned_employees") or set()
	passed = employee_name not in assigned_employees
	return passed, 0, _("Already Assigned") if not passed else ""


def _prefer_default_line(context: dict[str, Any], rule: dict[str, Any]) -> tuple[bool, int, str]:
	employee = context.get("employee") or {}
	production_line = context.get("production_line")
	if employee.get("default_line") == production_line:
		return True, rule.get("score") or 0, ""
	return True, 0, ""


RULE_EVALUATORS = {
	"employee_active": _employee_active,
	"attendance_present": _attendance_present,
	"shift_match": _shift_match,
	"designation_match": _designation_match,
	"skill_match": _skill_match,
	"duplicate_assignment": _duplicate_assignment,
	"prefer_default_line": _prefer_default_line,
}
