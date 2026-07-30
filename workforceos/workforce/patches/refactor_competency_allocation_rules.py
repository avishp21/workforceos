# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe

from workforceos.workforce.setup.default_allocation_rules import DEFAULT_ALLOCATION_RULES

_LEGACY_RULE_CODES = ("designation_match", "skill_match")


def execute() -> None:
	"""Migrate allocation rules to the competency-based rule engine."""
	if not frappe.db.exists("DocType", "Allocation Rule"):
		return

	for legacy_code in _LEGACY_RULE_CODES:
		legacy_name = frappe.db.get_value("Allocation Rule", {"rule_code": legacy_code})
		if not legacy_name:
			continue
		frappe.db.set_value("Allocation Rule", legacy_name, {"is_enabled": 0})

	for rule in DEFAULT_ALLOCATION_RULES:
		existing_name = frappe.db.get_value("Allocation Rule", {"rule_code": rule["rule_code"]})
		if existing_name:
			frappe.db.set_value(
				"Allocation Rule",
				existing_name,
				{
					"rule_name": rule["rule_name"],
					"rule_category": rule["rule_category"],
					"priority": rule["priority"],
					"score": rule["score"],
					"description": rule.get("description"),
					"is_enabled": 1,
				},
			)
			continue

		doc = frappe.get_doc(
			{
				"doctype": "Allocation Rule",
				"rule_name": rule["rule_name"],
				"rule_code": rule["rule_code"],
				"rule_category": rule["rule_category"],
				"priority": rule["priority"],
				"is_enabled": 1,
				"score": rule["score"],
				"description": rule.get("description"),
			}
		)
		doc.insert(ignore_permissions=True)

	frappe.db.commit()
