"""Allocation Run operational API for WorkforceOS."""

from __future__ import annotations

import frappe

from workforceos.services.reallocation_service import ReallocationService


@frappe.whitelist()
def get_current_allocations(allocation_run: str) -> list[dict]:
	"""Return assignments for the Current Allocations view."""
	return ReallocationService().get_current_allocations(allocation_run)


@frappe.whitelist()
def get_workstations_for_line(allocation_run: str, production_line: str) -> list[dict]:
	"""Return workstation options for a production line (future Workstation module)."""
	return ReallocationService().get_workstations_for_line(allocation_run, production_line)


@frappe.whitelist()
def reallocate_employee(
	assignment_name: str,
	to_production_line: str,
	reason: str,
	comments: str | None = None,
	to_workstation: str | None = None,
) -> dict:
	"""Validate and apply a manual production-line reallocation."""
	return ReallocationService().reallocate(
		assignment_name=assignment_name,
		to_production_line=to_production_line,
		reason=reason,
		comments=comments,
		to_workstation=to_workstation,
	)
