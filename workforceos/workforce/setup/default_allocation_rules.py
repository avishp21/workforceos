# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

"""Default allocation rule seed data and helpers."""

from __future__ import annotations

import frappe

DEFAULT_ALLOCATION_RULES = [
	{
		"rule_name": "Employee Active",
		"rule_code": "employee_active",
		"rule_category": "Eligibility",
		"priority": 1,
		"score": 0,
		"description": "Employee must be active before allocation.",
	},
	{
		"rule_name": "Attendance Present",
		"rule_code": "attendance_present",
		"rule_category": "Eligibility",
		"priority": 2,
		"score": 0,
		"description": "Employee must be marked present for the shift.",
	},
	{
		"rule_name": "Shift Match",
		"rule_code": "shift_match",
		"rule_category": "Eligibility",
		"priority": 3,
		"score": 0,
		"description": "Employee attendance must match the planned shift.",
	},
	{
		"rule_name": "Designation Match",
		"rule_code": "designation_match",
		"rule_category": "Eligibility",
		"priority": 4,
		"score": 0,
		"description": "Employee designation must match the line requirement.",
	},
	{
		"rule_name": "Skill Match",
		"rule_code": "skill_match",
		"rule_category": "Eligibility",
		"priority": 5,
		"score": 0,
		"description": "Employee skill must match the line requirement.",
	},
	{
		"rule_name": "Prevent Duplicate Assignment",
		"rule_code": "duplicate_assignment",
		"rule_category": "Validation",
		"priority": 6,
		"score": 0,
		"description": "Prevent assigning the same employee twice for a date and shift.",
	},
	{
		"rule_name": "Prefer Default Line",
		"rule_code": "prefer_default_line",
		"rule_category": "Preference",
		"priority": 7,
		"score": 20,
		"description": "Prefer assigning employees to their default production line.",
	},
]


def create_default_allocation_rules() -> None:
	"""Insert default allocation rules if they do not already exist."""
	if not frappe.db.exists("DocType", "Allocation Rule"):
		return

	for rule in DEFAULT_ALLOCATION_RULES:
		if frappe.db.exists("Allocation Rule", {"rule_code": rule["rule_code"]}):
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
