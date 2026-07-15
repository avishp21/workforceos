# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr


class ProductionLine(Document):
	"""Production line master for workforce allocation."""

	def validate(self) -> None:
		"""Validate production line fields before save."""
		self.validate_line_code()

	def validate_line_code(self) -> None:
		"""Normalize and validate line code."""
		if self.line_code:
			self.line_code = cstr(self.line_code).strip().upper()

		if not self.line_code:
			frappe.throw(_("Line Code is required"))

		if not self.line_name:
			frappe.throw(_("Line Name is required"))
