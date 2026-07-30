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
		"rule_name": "Competency Match",
		"rule_code": "competency_match",
		"rule_category": "Eligibility",
		"priority": 4,
		"score": 0,
		"description": "Checks whether an employee possesses a Competency matching the required Designation and Skill combination.",
	},
	{
		"rule_name": "Prevent Duplicate Assignment",
		"rule_code": "duplicate_assignment",
		"rule_category": "Validation",
		"priority": 1,
		"score": 0,
		"description": "Prevent assigning the same employee twice for a date and shift.",
	},
	{
		"rule_name": "Prefer Certified Competency",
		"rule_code": "prefer_certified_competency",
		"rule_category": "Preference",
		"priority": 1,
		"score": 0,
		"description": "When multiple employees match the required competency, employees having Certified = Yes should be preferred.",
	},
]

REMOVED_ALLOCATION_RULE_CODES = (
	"competency_authorized",
	"designation_match",
	"skill_match",
	"prefer_primary_competency",
	"prefer_default_line",
)


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
