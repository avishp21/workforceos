# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr

RULE_CATEGORIES = ("Eligibility", "Preference", "Validation")


class AllocationRule(Document):
	"""Business rule configuration for the workforce allocation engine."""

	def validate(self) -> None:
		"""Validate allocation rule fields before save."""
		self.validate_rule_name()
		self.validate_rule_code()
		self.validate_rule_category()
		self.validate_priority()

	def validate_rule_name(self) -> None:
		"""Ensure rule name is provided."""
		if self.rule_name:
			self.rule_name = cstr(self.rule_name).strip()

		if not self.rule_name:
			frappe.throw(_("Rule Name is required"))

	def validate_rule_code(self) -> None:
		"""Normalize rule code and prevent duplicates."""
		if self.rule_code:
			self.rule_code = cstr(self.rule_code).strip().lower()

		if not self.rule_code:
			frappe.throw(_("Rule Code is required"))

		if frappe.db.exists(
			"Allocation Rule",
			{"rule_code": self.rule_code, "name": ["!=", self.name]},
		):
			frappe.throw(_("Rule Code {0} already exists").format(self.rule_code))

	def validate_rule_category(self) -> None:
		"""Ensure rule category is a supported value."""
		if self.rule_category not in RULE_CATEGORIES:
			frappe.throw(_("Rule Category must be one of: {0}").format(", ".join(RULE_CATEGORIES)))

	def validate_priority(self) -> None:
		"""Ensure priority is a valid execution order value."""
		if self.priority is None:
			frappe.throw(_("Priority is required"))

		if self.priority < 0:
			frappe.throw(_("Priority must be zero or greater"))
