# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe


def execute() -> None:
	"""Enable the Prefer Certified Competency preference rule for MVP allocation."""
	if not frappe.db.exists("DocType", "Allocation Rule"):
		return

	rule_name = frappe.db.get_value("Allocation Rule", {"rule_code": "prefer_certified_competency"})
	if rule_name:
		frappe.db.set_value(
			"Allocation Rule",
			rule_name,
			{
				"is_enabled": 1,
				"score": 0,
				"rule_category": "Preference",
				"priority": 1,
				"description": "When multiple employees match the required competency, employees having Certified = Yes should be preferred.",
			},
		)
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Allocation Rule",
				"rule_name": "Prefer Certified Competency",
				"rule_code": "prefer_certified_competency",
				"rule_category": "Preference",
				"priority": 1,
				"is_enabled": 1,
				"score": 0,
				"description": "When multiple employees match the required competency, employees having Certified = Yes should be preferred.",
			}
		)
		doc.insert(ignore_permissions=True)

	frappe.db.commit()
