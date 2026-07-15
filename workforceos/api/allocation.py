"""Allocation API for WorkforceOS."""

from __future__ import annotations

import frappe

from workforceos.services.allocation_engine import AllocationEngine


@frappe.whitelist()
def allocate(date: str, shift: str) -> dict:
	"""Run workforce allocation for a date and shift.

	Args:
		date: Allocation date.
		shift: Shift name.

	Returns:
		The Allocation Run document as a dictionary.
	"""
	frappe.has_permission("Allocation Run", throw=True)
	frappe.has_permission("Employee Assignment", "create", throw=True)

	run = AllocationEngine.allocate(date, shift)
	response = run.as_dict()
	response["summary"] = getattr(run, "_allocation_summary", None)
	return response
