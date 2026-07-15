"""Public allocation engine entry point for WorkforceOS."""

from __future__ import annotations

from datetime import date

import frappe
from frappe.model.document import Document
from frappe.utils import getdate

from workforceos.services.allocation_service import AllocationService


class AllocationEngine:
	"""Facade for the workforce allocation engine."""

	@staticmethod
	def allocate(allocation_date: str | date, shift: str) -> Document:
		"""Run workforce allocation for a date and shift.

		Args:
			allocation_date: Business date for allocation.
			shift: Shift identifier.

		Returns:
			The Allocation Run document.
		"""
		return AllocationService().allocate(getdate(allocation_date), shift)
