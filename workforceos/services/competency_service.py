"""Competency matrix helpers for WorkforceOS."""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _


class CompetencyService:
	"""Load, match, and deterministically rank employee competencies."""

	@staticmethod
	def load_competencies_for_employees(employee_names: list[str]) -> dict[str, list[dict[str, Any]]]:
		"""Return competencies grouped by Workforce Employee name."""
		if not employee_names:
			return {}

		rows = frappe.get_all(
			"Employee Competency",
			filters={"parent": ["in", employee_names], "parenttype": "Workforce Employee"},
			fields=["parent", "designation", "skill", "priority", "certified", "remarks"],
			order_by="priority asc",
		)

		grouped: dict[str, list[dict[str, Any]]] = {name: [] for name in employee_names}
		for row in rows:
			grouped.setdefault(row.parent, []).append(CompetencyService.serialize_competency(row))

		for competencies in grouped.values():
			competencies.sort(key=CompetencyService._competency_sort_key)

		return grouped

	@staticmethod
	def attach_competencies_to_employees(employee_map: dict[str, dict[str, Any]]) -> None:
		"""Mutate employee dicts in-place with competencies and primary competency."""
		if not employee_map:
			return

		competency_map = CompetencyService.load_competencies_for_employees(list(employee_map.keys()))
		for employee_name, employee in employee_map.items():
			competencies = competency_map.get(employee_name, [])
			employee["competencies"] = competencies
			employee["primary_competency"] = CompetencyService.get_primary_competency(competencies)

	@staticmethod
	def enrich_rule_context(context: dict[str, Any]) -> dict[str, Any]:
		"""Attach matched competency used for rule evaluation and allocation."""
		employee = context.get("employee") or {}
		requirement = context.get("requirement")
		matched, competency_reason = CompetencyService.resolve_matched_competency_with_reason(
			employee,
			requirement,
		)
		context["matched_competency"] = matched
		context["competency_selection_reason"] = competency_reason
		return context

	@staticmethod
	def get_requirement_fields(requirement: Any) -> tuple[str | None, str | None]:
		"""Return designation and skill from a requirement document or mapping."""
		if not requirement:
			return None, None
		designation = getattr(requirement, "designation", None) or requirement.get("designation")
		skill = getattr(requirement, "skill", None) or requirement.get("skill")
		return designation, skill

	@staticmethod
	def serialize_competency(row: dict[str, Any] | Any) -> dict[str, Any]:
		"""Normalize a competency row for APIs and allocation context."""
		if isinstance(row, dict):
			data = row
		elif callable(getattr(row, "as_dict", None)):
			data = row.as_dict()
		else:
			data = dict(row)

		return {
			"designation": data.get("designation"),
			"skill": data.get("skill"),
			"priority": data.get("priority") or 1,
			"certified": cint(data.get("certified")),
			"remarks": data.get("remarks"),
		}

	@staticmethod
	def get_primary_competency(competencies: list[dict[str, Any]]) -> dict[str, Any] | None:
		"""Return the lowest priority-number competency."""
		if not competencies:
			return None
		return min(competencies, key=CompetencyService._competency_sort_key)

	@staticmethod
	def find_matching_competencies(
		competencies: list[dict[str, Any]],
		designation: str | None,
		skill: str | None,
	) -> list[dict[str, Any]]:
		"""Return competencies matching a designation and skill requirement."""
		matches: list[dict[str, Any]] = []
		for competency in competencies:
			if designation and competency.get("designation") != designation:
				continue
			if skill and competency.get("skill") != skill:
				continue
			matches.append(competency)

		return sorted(matches, key=CompetencyService._competency_sort_key)

	@staticmethod
	def has_certified_competency_match(
		competencies: list[dict[str, Any]],
		designation: str | None,
		skill: str | None,
	) -> bool:
		"""Return whether any matching competency is certified."""
		return any(
			competency.get("certified")
			for competency in CompetencyService.find_matching_competencies(competencies, designation, skill)
		)

	@staticmethod
	def select_best_competency(
		competencies: list[dict[str, Any]],
		designation: str | None,
		skill: str | None,
	) -> dict[str, Any] | None:
		"""Select the best competency using certified preference and priority."""
		matches = CompetencyService.find_matching_competencies(competencies, designation, skill)
		if not matches:
			return None

		certified_matches = [competency for competency in matches if competency.get("certified")]
		pool = certified_matches if certified_matches else matches
		return min(pool, key=CompetencyService._competency_sort_key)

	@staticmethod
	def resolve_matched_competency(employee: dict[str, Any], requirement: Any) -> dict[str, Any] | None:
		"""Resolve the competency used for allocation."""
		matched, _reason = CompetencyService.resolve_matched_competency_with_reason(employee, requirement)
		return matched

	@staticmethod
	def resolve_matched_competency_with_reason(
		employee: dict[str, Any],
		requirement: Any,
	) -> tuple[dict[str, Any] | None, str]:
		"""Resolve the matched competency and explain why it was selected."""
		competencies = employee.get("competencies") or []
		designation, skill = CompetencyService.get_requirement_fields(requirement)
		matches = CompetencyService.find_matching_competencies(competencies, designation, skill)
		if not matches:
			return None, _("No matching competency found")

		matched = CompetencyService.select_best_competency(competencies, designation, skill)
		if not matched:
			return None, _("No matching competency found")

		if matched.get("certified"):
			return matched, _("Matched certified competency with Priority {0}").format(matched.get("priority"))

		if CompetencyService.has_certified_competency_match(competencies, designation, skill):
			return matched, _("Matched competency with Priority {0}").format(matched.get("priority"))

		return matched, _("Matched competency with Priority {0}; no certified competency was available").format(
			matched.get("priority")
		)

	@staticmethod
	def has_competency_match(employee: dict[str, Any], requirement: Any) -> bool:
		"""Return whether the employee has any competency for the requirement pair."""
		competencies = employee.get("competencies") or []
		designation, skill = CompetencyService.get_requirement_fields(requirement)
		if not designation and not skill:
			return bool(competencies)
		return bool(CompetencyService.find_matching_competencies(competencies, designation, skill))

	@staticmethod
	def get_candidate_sort_key(candidate: dict[str, Any]) -> tuple[Any, ...]:
		"""Deterministic tie-breaker key after preference rules are applied."""
		matched = candidate.get("matched_competency") or {}
		employee = candidate.get("employee") or {}
		priority = matched.get("priority") or 9999
		employee_id = (employee.get("employee_id") or employee.get("name") or "").upper()
		employee_name = employee.get("employee_name") or ""
		return (priority, employee_id, employee_name)

	@staticmethod
	def rank_candidates_by_priority(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
		"""Sort candidates by competency priority and deterministic tie-breakers."""
		return sorted(candidates, key=CompetencyService.get_candidate_sort_key)

	@staticmethod
	def rank_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
		"""Backward-compatible alias for priority-based candidate ranking."""
		return CompetencyService.rank_candidates_by_priority(candidates)

	@staticmethod
	def format_matched_competency(matched: dict[str, Any] | None) -> str:
		"""Return a display label for a matched competency."""
		if not matched:
			return ""
		designation = matched.get("designation") or _("Not set")
		skill = matched.get("skill") or _("Not set")
		return f"{designation} / {skill}"

	@staticmethod
	def employee_has_competency(
		competencies: list[dict[str, Any]],
		designation: str,
		skill: str,
	) -> bool:
		"""Return whether an employee has the given designation + skill pair."""
		return bool(CompetencyService.find_matching_competencies(competencies, designation, skill))

	@staticmethod
	def build_employee_api_payload(employee_doc: Any) -> dict[str, Any]:
		"""Serialize a Workforce Employee for API responses."""
		competencies = [
			CompetencyService.serialize_competency(row) for row in employee_doc.get("competencies", [])
		]
		competencies.sort(key=CompetencyService._competency_sort_key)
		primary = CompetencyService.get_primary_competency(competencies)

		return {
			"employee": employee_doc.name,
			"employee_id": employee_doc.employee_id,
			"employee_name": employee_doc.employee_name,
			"primary_competency": primary,
			"competencies": competencies,
			"total_competencies": len(competencies),
		}

	@staticmethod
	def build_matched_competency_log_fields(
		matched: dict[str, Any] | None,
		selection_reason: str | None = None,
		applied_preference_rules: list[dict[str, Any]] | None = None,
	) -> dict[str, Any]:
		"""Return Allocation Decision Log fields for a matched competency."""
		matched = matched or {}
		applied_rules = applied_preference_rules or []
		return {
			"matched_competency": CompetencyService.format_matched_competency(matched),
			"matched_designation": matched.get("designation"),
			"matched_skill": matched.get("skill"),
			"matched_competency_priority": matched.get("priority"),
			"matched_certified": matched.get("certified"),
			"applied_preference_rules": CompetencyService.format_applied_preference_rules(applied_rules),
			"selection_reason": selection_reason,
		}

	@staticmethod
	def format_applied_preference_rules(applied_rules: list[dict[str, Any]]) -> str:
		"""Serialize applied preference rules for decision logs."""
		if not applied_rules:
			return ""
		return "; ".join(
			f"{rule.get('rule_name') or rule.get('rule_code')}: {rule.get('message') or ''}".strip(": ")
			for rule in applied_rules
		)

	@staticmethod
	def _competency_sort_key(competency: dict[str, Any]) -> tuple[Any, ...]:
		return (
			competency.get("priority") or 9999,
			competency.get("designation") or "",
			competency.get("skill") or "",
		)


def cint(value: Any) -> int:
	"""Safe integer conversion for competency flags."""
	try:
		return int(value or 0)
	except (TypeError, ValueError):
		return 0
