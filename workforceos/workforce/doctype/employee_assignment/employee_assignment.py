# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now

ASSIGNMENT_STATUSES = ("Assigned", "Reassigned", "Released", "Cancelled")
ASSIGNMENT_TYPES = ("Auto", "Manual")


class EmployeeAssignment(Document):
	"""Final workforce allocation of an employee to a production line."""

	def before_insert(self) -> None:
		"""Set default assignment metadata on create."""
		self.set_assignment_defaults()

	def validate(self) -> None:
		"""Validate assignment fields before save."""
		self.set_assignment_defaults()
		self.validate_duplicate_assignment()
		self.validate_assignment_status()
		self.validate_assignment_type()

	def set_assignment_defaults(self) -> None:
		"""Apply default values for assignment metadata."""
		if not self.assignment_status:
			self.assignment_status = "Assigned"

		if not self.assignment_type:
			self.assignment_type = "Auto"

		if not self.assigned_by:
			self.assigned_by = frappe.session.user

		if not self.assigned_on:
			self.assigned_on = now()

	def validate_duplicate_assignment(self) -> None:
		"""Prevent duplicate assignments for the same date, shift, and employee."""
		if not (self.assignment_date and self.shift and self.employee):
			return

		if frappe.db.exists(
			"Employee Assignment",
			{
				"assignment_date": self.assignment_date,
				"shift": self.shift,
				"employee": self.employee,
				"name": ["!=", self.name],
			},
		):
			frappe.throw(
				_(
					"An assignment already exists for Employee {0} on {1} for Shift {2}"
				).format(self.employee, self.assignment_date, self.shift)
			)

	def validate_assignment_status(self) -> None:
		"""Ensure assignment status is a supported value."""
		if self.assignment_status not in ASSIGNMENT_STATUSES:
			frappe.throw(
				_("Assignment Status must be one of: {0}").format(", ".join(ASSIGNMENT_STATUSES))
			)

	def validate_assignment_type(self) -> None:
		"""Ensure assignment type is a supported value."""
		if self.assignment_type not in ASSIGNMENT_TYPES:
			frappe.throw(
				_("Assignment Type must be one of: {0}").format(", ".join(ASSIGNMENT_TYPES))
			)
