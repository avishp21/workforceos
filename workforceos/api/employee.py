# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _

from workforceos.services.competency_service import CompetencyService


@frappe.whitelist()
def get_employee(employee: str) -> dict:
	"""Return a Workforce Employee with competency matrix details."""
	if not employee:
		frappe.throw(_("Employee is required"))

	doc = frappe.get_doc("Workforce Employee", employee)
	return CompetencyService.build_employee_api_payload(doc)


@frappe.whitelist()
def get_employees(
	contractor: str | None = None,
	designation: str | None = None,
	skill: str | None = None,
	status: str | None = None,
) -> list[dict]:
	"""Return Workforce Employees filtered by competency-aware criteria."""
	filters: dict = {}
	if contractor:
		filters["contractor"] = contractor
	if status:
		filters["status"] = status

	names = frappe.get_all("Workforce Employee", filters=filters, pluck="name")
	if not names:
		return []

	competency_map = CompetencyService.load_competencies_for_employees(names)
	results: list[dict] = []

	for name in names:
		doc = frappe.get_doc("Workforce Employee", name)
		payload = CompetencyService.build_employee_api_payload(doc)
		competencies = competency_map.get(name, [])

		if designation and not any(row.get("designation") == designation for row in competencies):
			continue
		if skill and not any(row.get("skill") == skill for row in competencies):
			continue

		results.append(payload)

	return results
