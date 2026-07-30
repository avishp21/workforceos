# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now


class EmployeeAllocationEvaluation(Document):
	"""Audit record for a single employee evaluation during an allocation run."""

	def before_insert(self) -> None:
		if not self.created_on:
			self.created_on = now()
