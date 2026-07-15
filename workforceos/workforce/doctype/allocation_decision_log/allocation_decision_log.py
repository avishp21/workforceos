# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class AllocationDecisionLog(Document):
	"""Audit log for allocation rule evaluations and decisions."""
