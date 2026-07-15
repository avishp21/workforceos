# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

PLAN_STATUSES = ("Draft", "Planned", "Completed")


class DailyLinePlan(Document):
	"""Daily production line plan with manpower requirements."""

	def validate(self) -> None:
		"""Validate plan fields before save."""
		self.validate_duplicate_plan()
		self.validate_status()
		self.validate_requirements()

	def validate_duplicate_plan(self) -> None:
		"""Prevent duplicate plans for the same date, shift, and line."""
		if not (self.date and self.shift and self.line):
			return

		if frappe.db.exists(
			"Daily Line Plan",
			{
				"date": self.date,
				"shift": self.shift,
				"line": self.line,
				"name": ["!=", self.name],
			},
		):
			frappe.throw(
				_("A Daily Line Plan already exists for Date {0}, Shift {1}, and Line {2}").format(
					self.date, self.shift, self.line
				)
			)

	def validate_status(self) -> None:
		"""Ensure status is a supported value."""
		if self.status not in PLAN_STATUSES:
			frappe.throw(_("Status must be one of: {0}").format(", ".join(PLAN_STATUSES)))

	def validate_requirements(self) -> None:
		"""Validate child table requirement rows."""
		if not self.requirements:
			frappe.throw(_("At least one manpower requirement is required"))

		for row in self.requirements:
			if not row.required_manpower or row.required_manpower <= 0:
				frappe.throw(_("Required Manpower must be greater than zero for all requirement rows"))
