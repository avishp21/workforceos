# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, cstr

MAX_GENERATED_WORKSTATIONS = 50


class ProductionLine(Document):
	"""Production line master for workforce allocation."""

	def validate(self) -> None:
		"""Validate production line fields before save."""
		self.validate_line_code()
		self.validate_customers()

	def validate_line_code(self) -> None:
		"""Normalize and validate line code."""
		if self.line_code:
			self.line_code = cstr(self.line_code).strip().upper()

		if not self.line_code:
			frappe.throw(_("Line Code is required"))

		if not self.line_name:
			frappe.throw(_("Line Name is required"))

	def validate_customers(self) -> None:
		"""Keep mapped customers unique on this line."""
		seen: set[str] = set()
		for row in self.get("customers") or []:
			customer = cstr(row.customer).strip()
			if not customer:
				frappe.throw(_("Customer is required on each customer row"))
			if customer in seen:
				frappe.throw(_("Customer {0} is mapped more than once on this line").format(customer))
			seen.add(customer)


@frappe.whitelist()
def generate_workstations(production_line: str, from_number: int | str, to_number: int | str) -> dict:
	"""Create a numbered range of workstations for one production line.

	Workstation codes follow WS1, WS2, WS7. Document names use the line code,
	for example LINE-8-WS1.
	"""
	frappe.has_permission("Production Line", "write", throw=True)
	frappe.has_permission("Workstation", "create", throw=True)

	if not production_line or not frappe.db.exists("Production Line", production_line):
		frappe.throw(_("Production Line {0} was not found").format(production_line))

	start = cint(from_number)
	end = cint(to_number)
	if start < 1 or end < 1:
		frappe.throw(_("Workstation numbers must be 1 or greater"))
	if start > end:
		frappe.throw(_("Starting workstation cannot be greater than ending workstation"))
	if end - start + 1 > MAX_GENERATED_WORKSTATIONS:
		frappe.throw(
			_("Cannot generate more than {0} workstations at once").format(MAX_GENERATED_WORKSTATIONS)
		)

	created: list[str] = []
	skipped: list[str] = []

	for number in range(start, end + 1):
		workstation_code = f"WS{number}"
		existing = frappe.db.exists(
			"Workstation",
			{"production_line": production_line, "workstation_code": workstation_code},
		)
		if existing:
			skipped.append(cstr(existing))
			continue

		doc = frappe.get_doc(
			{
				"doctype": "Workstation",
				"production_line": production_line,
				"workstation_code": workstation_code,
				"workstation_name": _("Workstation {0}").format(number),
				"sequence": number,
				"is_active": 1,
			}
		)
		doc.insert(ignore_permissions=True)
		created.append(doc.name)

	return {
		"created": created,
		"skipped": skipped,
		"message": _("Created {0} workstation(s), skipped {1} existing").format(
			len(created), len(skipped)
		),
	}
