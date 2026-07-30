"""Business dashboard metrics for Allocation Run documents."""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document


def apply_dashboard_metrics(
	run: Document,
	stats: dict[str, Any],
	execution_time_seconds: float,
) -> None:
	"""Persist dashboard metrics on the Allocation Run when execution completes."""
	total_required = stats.get("total_required") or 0
	total_allocated = stats.get("total_allocated") or 0
	metrics = stats.get("evaluation_metrics") or {}

	run.employees_evaluated = metrics.get("employees_evaluated", 0)
	run.employees_allocated = metrics.get("employees_allocated", 0)
	run.employees_rejected = metrics.get("employees_rejected", 0)
	run.employees_skipped = metrics.get("employees_skipped", 0)
	run.total_shortage = stats.get("total_shortage") or 0
	run.allocation_success_percent = _allocation_success_percent(total_required, total_allocated)
	run.execution_time_seconds = execution_time_seconds

	run.total_required = total_required
	run.total_allocated = total_allocated
	run.production_lines_processed = stats.get("production_lines_processed") or 0
	run.total_workstations = stats.get("total_workstations") or 0
	run.assignments_created = stats.get("assignments_created") or 0
	run.lines_processed = stats.get("lines_processed") or 0

	run.certified_allocations = metrics.get("certified_allocations", 0)
	run.non_certified_allocations = metrics.get("non_certified_allocations", 0)
	run.most_used_competency = _most_used_competency(run.name)
	run.rule_failure_summary = _rule_failure_summary(run.name)


def enrich_execution_stats(stats: dict[str, Any], plans: list[Any]) -> None:
	"""Add production planning counters used by the dashboard."""
	stats["production_lines_processed"] = len({plan.line for plan in plans})
	stats["total_workstations"] = sum(len(plan.requirements or []) for plan in plans)


def _allocation_success_percent(total_required: int, total_allocated: int) -> float:
	if not total_required:
		return 100.0 if total_allocated else 0.0
	return round((total_allocated / total_required) * 100, 2)


def _most_used_competency(allocation_run: str) -> str:
	rows = frappe.db.sql(
		"""
		SELECT matched_competency, COUNT(*) AS allocation_count
		FROM `tabEmployee Assignment`
		WHERE allocation_run = %s
			AND IFNULL(matched_competency, '') != ''
		GROUP BY matched_competency
		ORDER BY allocation_count DESC
		LIMIT 1
		""",
		allocation_run,
		as_dict=True,
	)
	if not rows:
		return ""
	return rows[0].matched_competency


def _rule_failure_summary(allocation_run: str) -> str:
	rows = frappe.db.sql(
		"""
		SELECT
			COALESCE(ar.rule_name, are.rule) AS rule_label,
			COUNT(DISTINCT eae.name) AS employee_count
		FROM `tabAllocation Rule Evaluation` are
		INNER JOIN `tabEmployee Allocation Evaluation` eae
			ON eae.name = are.parent
			AND eae.allocation_run = %s
		LEFT JOIN `tabAllocation Rule` ar ON ar.name = are.rule
		WHERE are.status = 'Failed'
		GROUP BY are.rule, ar.rule_name
		ORDER BY employee_count DESC, rule_label ASC
		""",
		allocation_run,
		as_dict=True,
	)
	if not rows:
		return _("No rule failures recorded.")

	lines = [
		_("{0} — {1} Employees").format(row.rule_label, int(row.employee_count))
		for row in rows
	]
	return "\n".join(lines)
