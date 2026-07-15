# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr


class WorkforceDesignation(Document):
	"""Designation master for workforce employee role classification."""

	def validate(self) -> None:
		"""Validate designation fields before save."""
		if self.designation_name:
			self.designation_name = cstr(self.designation_name).strip()

		if not self.designation_name:
			frappe.throw(_("Designation Name is required"))
