# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr


class Customer(Document):
	"""Customer master that can be mapped to one or more production lines."""

	def validate(self) -> None:
		"""Normalize customer identity before save."""
		if self.customer_name:
			self.customer_name = cstr(self.customer_name).strip()

		if not self.customer_name:
			frappe.throw(_("Customer Name is required"))
