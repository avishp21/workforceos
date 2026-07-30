"""Daily Production Plan API for WorkforceOS."""

from __future__ import annotations

import frappe

from workforceos.services.daily_production_plan_service import DailyProductionPlanService


@frappe.whitelist()
def generate_daily_line_plans(
	daily_production_plan: str,
	overwrite_production_lines: str | list | None = None,
) -> dict:
	"""Generate Daily Line Plans grouped by production line."""
	if isinstance(overwrite_production_lines, str):
		overwrite_production_lines = frappe.parse_json(overwrite_production_lines)

	return DailyProductionPlanService().generate_daily_line_plans(
		daily_production_plan=daily_production_plan,
		overwrite_production_lines=overwrite_production_lines,
	)


@frappe.whitelist()
def get_generated_line_plans(daily_production_plan: str) -> list[dict]:
	"""List Daily Line Plans created from a Daily Production Plan."""
	frappe.has_permission("Daily Production Plan", "read", throw=True)
	return DailyProductionPlanService().get_generated_line_plans(daily_production_plan)
