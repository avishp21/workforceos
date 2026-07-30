"""Generate Daily Line Plans from Daily Production Plans."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from frappe import _


class DailyProductionPlanService:
	"""Groups production requirements by line and upserts Daily Line Plans."""

	def generate_daily_line_plans(
		self,
		daily_production_plan: str,
		overwrite_production_lines: list[str] | None = None,
	) -> dict[str, Any]:
		"""Create or update Daily Line Plans from a Daily Production Plan.

		When existing line plans conflict and their production line is not in
		``overwrite_production_lines``, returns ``needs_confirmation`` without
		writing any documents.
		"""
		frappe.has_permission("Daily Production Plan", "write", throw=True)
		frappe.has_permission("Daily Line Plan", "create", throw=True)

		plan = frappe.get_doc("Daily Production Plan", daily_production_plan)
		grouped = self._group_requirements(plan)
		overwrite = set(overwrite_production_lines or [])

		conflicts = self._find_conflicts(plan, grouped, overwrite)
		if conflicts:
			return {
				"status": "needs_confirmation",
				"conflicts": conflicts,
				"message": _("Daily Line Plans already exist for some production lines."),
			}

		created: list[str] = []
		updated: list[str] = []
		skipped: list[str] = []

		for production_line, rows in grouped.items():
			existing_name = self._find_existing_line_plan(plan, production_line)
			if existing_name and production_line not in overwrite:
				skipped.append(production_line)
				continue

			line_plan_name = self._upsert_line_plan(
				plan=plan,
				production_line=production_line,
				requirement_rows=rows,
				existing_name=existing_name,
			)
			if existing_name:
				updated.append(line_plan_name)
			else:
				created.append(line_plan_name)

		if created or updated:
			plan.reload()
			if plan.status in ("Draft", "Planned"):
				plan.status = "Generated"
				plan.save(ignore_permissions=True)

		return {
			"status": "success",
			"created": created,
			"updated": updated,
			"skipped": skipped,
			"message": self._success_message(created, updated, skipped),
		}

	def get_generated_line_plans(self, daily_production_plan: str) -> list[dict[str, Any]]:
		"""Return Daily Line Plans linked to this production plan."""
		return frappe.get_all(
			"Daily Line Plan",
			filters={"daily_production_plan": daily_production_plan},
			fields=["name", "line", "date", "shift", "status"],
			order_by="line asc",
		)

	def _group_requirements(self, plan) -> dict[str, list]:
		grouped: dict[str, list] = defaultdict(list)
		for row in plan.production_requirements:
			grouped[row.production_line].append(row)
		return dict(grouped)

	def _find_conflicts(
		self, plan, grouped: dict[str, list], overwrite: set[str]
	) -> list[dict[str, str]]:
		conflicts: list[dict[str, str]] = []
		for production_line in grouped:
			if production_line in overwrite:
				continue
			existing_name = self._find_existing_line_plan(plan, production_line)
			if existing_name:
				conflicts.append(
					{
						"production_line": production_line,
						"daily_line_plan": existing_name,
					}
				)
		return conflicts

	def _find_existing_line_plan(self, plan, production_line: str) -> str | None:
		return frappe.db.get_value(
			"Daily Line Plan",
			{
				"date": plan.production_date,
				"shift": plan.shift,
				"line": production_line,
			},
			"name",
		)

	def _upsert_line_plan(
		self,
		plan,
		production_line: str,
		requirement_rows: list,
		existing_name: str | None,
	) -> str:
		requirements = [
			{
				"designation": row.designation,
				"skill": row.skill,
				"required_manpower": row.required_manpower,
			}
			for row in requirement_rows
		]

		if existing_name:
			line_plan = frappe.get_doc("Daily Line Plan", existing_name)
			line_plan.requirements = []
			for req in requirements:
				line_plan.append("requirements", req)
			line_plan.daily_production_plan = plan.name
			if line_plan.status == "Draft":
				line_plan.status = "Planned"
			line_plan.save(ignore_permissions=True)
			return line_plan.name

		line_plan = frappe.get_doc(
			{
				"doctype": "Daily Line Plan",
				"date": plan.production_date,
				"shift": plan.shift,
				"line": production_line,
				"status": "Planned",
				"daily_production_plan": plan.name,
				"requirements": requirements,
			}
		)
		line_plan.insert(ignore_permissions=True)
		return line_plan.name

	def _success_message(self, created: list[str], updated: list[str], skipped: list[str]) -> str:
		parts: list[str] = []
		if created:
			parts.append(_("Created {0} Daily Line Plan(s)").format(len(created)))
		if updated:
			parts.append(_("Updated {0} Daily Line Plan(s)").format(len(updated)))
		if skipped:
			parts.append(_("Skipped {0} production line(s)").format(len(skipped)))
		return ". ".join(parts) if parts else _("No Daily Line Plans were generated.")
