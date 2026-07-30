# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe

from workforceos.workforce.setup.default_allocation_rules import REMOVED_ALLOCATION_RULE_CODES


def execute() -> None:
	"""Remove legacy allocation rules that are no longer used by the engine."""
	if not frappe.db.exists("DocType", "Allocation Rule"):
		return

	for rule_code in REMOVED_ALLOCATION_RULE_CODES:
		rule_name = frappe.db.get_value("Allocation Rule", {"rule_code": rule_code})
		if not rule_name:
			continue

		frappe.db.sql(
			"""
			UPDATE `tabAllocation Decision Log`
			SET allocation_rule = NULL
			WHERE allocation_rule = %s
			""",
			rule_name,
		)

		frappe.delete_doc("Allocation Rule", rule_name, force=True, ignore_permissions=True)

	frappe.db.commit()
