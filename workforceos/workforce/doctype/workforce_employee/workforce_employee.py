# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr

EMPLOYEE_STATUSES = ("Active", "Inactive")


class WorkforceEmployee(Document):
	"""Workforce employee master for allocation engine."""

	def validate(self) -> None:
		"""Validate employee fields before save."""
		self.validate_employee_id()
		self.validate_employee_name()
		self.validate_status()

	def validate_employee_id(self) -> None:
		"""Normalize employee ID and prevent duplicates."""
		if self.employee_id:
			self.employee_id = cstr(self.employee_id).strip().upper()

		if not self.employee_id:
			frappe.throw(_("Employee ID is required"))

		if frappe.db.exists(
			"Workforce Employee",
			{"employee_id": self.employee_id, "name": ["!=", self.name]},
		):
			frappe.throw(_("Employee ID {0} already exists").format(self.employee_id))

	def validate_employee_name(self) -> None:
		"""Ensure employee name is provided."""
		if self.employee_name:
			self.employee_name = cstr(self.employee_name).strip()

		if not self.employee_name:
			frappe.throw(_("Employee Name is required"))

	def validate_status(self) -> None:
		"""Ensure status is a supported value."""
		if self.status not in EMPLOYEE_STATUSES:
			frappe.throw(_("Status must be one of: {0}").format(", ".join(EMPLOYEE_STATUSES)))
