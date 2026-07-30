# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe


def execute() -> None:
	"""Migrate legacy designation/skill pairs into the competency matrix."""
	employees = frappe.get_all(
		"Workforce Employee",
		fields=["name", "designation", "skill"],
	)

	for employee in employees:
		if frappe.db.exists(
			"Employee Competency",
			{"parent": employee.name, "parenttype": "Workforce Employee"},
		):
			continue

		if not employee.designation and not employee.skill:
			continue

		doc = frappe.get_doc("Workforce Employee", employee.name)
		doc.append(
			"competencies",
			{
				"designation": employee.designation,
				"skill": employee.skill,
				"priority": 1,
				"certified": 1,
			},
		)
		doc.save(ignore_permissions=True)

	frappe.db.commit()
