# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr


class WorkforceDepartment(Document):
	"""Department master for workforce employee assignment."""

	def validate(self) -> None:
		"""Validate department fields before save."""
		if self.department_name:
			self.department_name = cstr(self.department_name).strip()

		if not self.department_name:
			frappe.throw(_("Department Name is required"))
