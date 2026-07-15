"""Demo data API for WorkforceOS development."""

from __future__ import annotations

import frappe

from workforceos.workforce.setup.demo_data import (
	clear_demo_data,
	generate_demo_data,
	get_demo_entity_options,
)


@frappe.whitelist()
def options() -> dict:
	"""Return selectable demo entities for the Generate Demo Data page."""
	frappe.only_for("System Manager")
	return get_demo_entity_options()


@frappe.whitelist()
def generate(entities: str | list | None = None) -> dict:
	"""Generate WorkforceOS demo data for selected entities."""
	frappe.only_for("System Manager")
	return generate_demo_data(entities)


@frappe.whitelist()
def clear(entities: str | list | None = None) -> dict:
	"""Clear WorkforceOS demo data for selected entities."""
	frappe.only_for("System Manager")
	return clear_demo_data(entities)
