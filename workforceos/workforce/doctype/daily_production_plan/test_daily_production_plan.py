# Copyright (c) 2026, WorkforceOS and contributors

import frappe
from frappe.tests.utils import FrappeTestCase

from workforceos.services.daily_production_plan_service import DailyProductionPlanService


class TestDailyProductionPlan(FrappeTestCase):
	def setUp(self):
		self.line_a = "TEST-LINE-A"
		self.line_b = "TEST-LINE-B"
		self.line_c = "TEST-LINE-C"
		self.shift = "TEST-SHIFT-1"
		self._ensure_master_data()

	def _ensure_master_data(self):
		if not frappe.db.exists("Shift", self.shift):
			frappe.get_doc(
				{
					"doctype": "Shift",
					"shift_name": self.shift,
					"start_time": "06:00:00",
					"end_time": "14:00:00",
				}
			).insert(ignore_permissions=True)

		for code, line_name in (
			(self.line_a, "Test Line A"),
			(self.line_b, "Test Line B"),
			(self.line_c, "Test Line C"),
		):
			if not frappe.db.exists("Production Line", code):
				frappe.get_doc(
					{
						"doctype": "Production Line",
						"line_code": code,
						"line_name": line_name,
						"is_active": 1,
					}
				).insert(ignore_permissions=True)

		for skill_name in ("TEST-Semi-Skilled", "TEST-Skilled"):
			if not frappe.db.exists("Skill", skill_name):
				frappe.get_doc(
					{
						"doctype": "Skill",
						"skill_name": skill_name,
						"skill_level": "Semi Skilled"
						if "Semi" in skill_name
						else "Skilled",
					}
				).insert(ignore_permissions=True)

		for designation_name in ("TEST-Helper", "TEST-Welder"):
			if not frappe.db.exists("Workforce Designation", designation_name):
				frappe.get_doc(
					{
						"doctype": "Workforce Designation",
						"designation_name": designation_name,
					}
				).insert(ignore_permissions=True)

	def _make_production_plan(self):
		plan = frappe.get_doc(
			{
				"doctype": "Daily Production Plan",
				"production_date": "2026-07-30",
				"shift": self.shift,
				"status": "Draft",
				"production_requirements": [
					{
						"production_line": self.line_a,
						"designation": "TEST-Helper",
						"skill": "TEST-Semi-Skilled",
						"required_manpower": 2,
					},
					{
						"production_line": self.line_a,
						"designation": "TEST-Welder",
						"skill": "TEST-Skilled",
						"required_manpower": 3,
					},
					{
						"production_line": self.line_b,
						"designation": "TEST-Helper",
						"skill": "TEST-Semi-Skilled",
						"required_manpower": 4,
					},
				],
			}
		)
		plan.insert(ignore_permissions=True)
		return plan

	def test_generate_creates_line_plans_per_production_line(self):
		plan = self._make_production_plan()
		service = DailyProductionPlanService()

		result = service.generate_daily_line_plans(plan.name)
		self.assertEqual(result["status"], "success")
		self.assertEqual(len(result["created"]), 2)

		line_plans = frappe.get_all(
			"Daily Line Plan",
			filters={"daily_production_plan": plan.name},
			fields=["name", "line"],
		)
		self.assertEqual(len(line_plans), 2)
		self.assertEqual({row.line for row in line_plans}, {self.line_a, self.line_b})

		line_a_plan = frappe.db.get_value(
			"Daily Line Plan",
			{"daily_production_plan": plan.name, "line": self.line_a},
			"name",
		)
		line_a_doc = frappe.get_doc("Daily Line Plan", line_a_plan)
		self.assertEqual(len(line_a_doc.requirements), 2)

		plan.reload()
		self.assertEqual(plan.status, "Generated")

	def test_generate_prompts_on_existing_line_plan(self):
		plan = self._make_production_plan()
		service = DailyProductionPlanService()

		first = service.generate_daily_line_plans(plan.name)
		self.assertEqual(first["status"], "success")

		plan.reload()
		plan.append(
			"production_requirements",
			{
				"production_line": self.line_c,
				"designation": "TEST-Helper",
				"skill": "TEST-Semi-Skilled",
				"required_manpower": 1,
			},
		)
		plan.save(ignore_permissions=True)

		conflict = service.generate_daily_line_plans(plan.name)
		self.assertEqual(conflict["status"], "needs_confirmation")
		self.assertEqual(len(conflict["conflicts"]), 2)

		overwrite_lines = [row["production_line"] for row in conflict["conflicts"]]
		second = service.generate_daily_line_plans(plan.name, overwrite_lines)
		self.assertEqual(second["status"], "success")
		self.assertEqual(len(second["updated"]), 2)
		self.assertEqual(len(second["created"]), 1)
