# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe

from workforceos.workforce.setup.default_allocation_rules import DEFAULT_ALLOCATION_RULES


def execute() -> None:
	"""Ensure competency authorization rule exists for allocation."""
	if not frappe.db.exists("DocType", "Allocation Rule"):
		return

	rule = next(
		(item for item in DEFAULT_ALLOCATION_RULES if item["rule_code"] == "competency_authorized"),
		None,
	)
	if not rule:
		return

	if frappe.db.exists("Allocation Rule", {"rule_code": rule["rule_code"]}):
		return

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
