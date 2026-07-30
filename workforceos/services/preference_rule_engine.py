"""Deterministic preference rule processing for WorkforceOS allocation."""

from __future__ import annotations

from typing import Any, Callable

from frappe import _

from workforceos.services.competency_service import CompetencyService

PreferenceApplier = Callable[
	[list[dict[str, Any]], dict[str, Any], dict[str, Any]],
	tuple[list[dict[str, Any]], dict[str, Any] | None],
]


class PreferenceRuleEngine:
	"""Apply configurable preference rules to eligible allocation candidates."""

	def select_candidates(
		self,
		candidates: list[dict[str, Any]],
		preference_rules: list[dict[str, Any]],
		context: dict[str, Any] | None = None,
	) -> dict[str, Any]:
		"""Filter and rank candidates using active preference rules."""
		context = context or {}
		working_candidates = list(candidates)
		applied_rules: list[dict[str, Any]] = []
		preference_steps: list[dict[str, Any]] = []

		for rule in preference_rules:
			applier = PREFERENCE_APPLIERS.get(rule.get("rule_code"))
			if not applier:
				continue

			before_names = {candidate["employee"]["name"] for candidate in working_candidates}
			working_candidates, application = applier(working_candidates, rule, context)
			after_names = {candidate["employee"]["name"] for candidate in working_candidates}

			if application:
				applied_rules.append(application)
				preference_steps.append(
					{
						"rule_code": rule.get("rule_code"),
						"rule_name": rule.get("rule_name"),
						"message": application.get("message"),
						"before_names": list(before_names),
						"after_names": list(after_names),
					}
				)

		ranked_candidates = CompetencyService.rank_candidates_by_priority(working_candidates)
		return {
			"candidates": ranked_candidates,
			"applied_preference_rules": applied_rules,
			"preference_steps": preference_steps,
		}


def _apply_prefer_certified_competency(
	candidates: list[dict[str, Any]],
	rule: dict[str, Any],
	context: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
	"""Prefer employees whose matched competency is certified."""
	del context
	certified_candidates = [
		candidate
		for candidate in candidates
		if (candidate.get("matched_competency") or {}).get("certified")
	]
	if not certified_candidates:
		return candidates, None

	if len(certified_candidates) == len(candidates):
		return certified_candidates, {
			"rule_code": rule.get("rule_code"),
			"rule_name": rule.get("rule_name"),
			"message": _("All eligible employees already had certified matching competencies."),
		}

	return certified_candidates, {
		"rule_code": rule.get("rule_code"),
		"rule_name": rule.get("rule_name"),
		"message": _("Selected certified employees over non-certified employees."),
	}


PREFERENCE_APPLIERS: dict[str, PreferenceApplier] = {
	"prefer_certified_competency": _apply_prefer_certified_competency,
}


def build_selection_reason(
	applied_preference_rules: list[dict[str, Any]],
	candidate: dict[str, Any],
) -> str:
	"""Build a human-readable allocation selection reason."""
	reasons: list[str] = []
	for rule in applied_preference_rules:
		reasons.append(_("Applied Preference Rule: {0}").format(rule.get("rule_name") or rule.get("rule_code")))
		if rule.get("message"):
			reasons.append(rule["message"])

	matched = candidate.get("matched_competency") or {}
	if matched.get("priority") is not None:
		reasons.append(
			_("Selected using Competency Priority {0} and Employee ID tie-breaker.").format(
				matched.get("priority")
			)
		)
	else:
		reasons.append(_("Selected using Competency Priority and Employee ID tie-breaker."))

	return " ".join(reasons)
