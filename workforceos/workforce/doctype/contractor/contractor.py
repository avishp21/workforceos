# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr


class Contractor(Document):
	"""Contractor master for workforce allocation."""

	def validate(self) -> None:
		"""Validate contractor fields before save."""
		self.validate_contractor_code()

	def validate_contractor_code(self) -> None:
		"""Normalize and validate contractor code."""
		if self.contractor_code:
			self.contractor_code = cstr(self.contractor_code).strip().upper()

		if not self.contractor_code:
			frappe.throw(_("Contractor Code is required"))
