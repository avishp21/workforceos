# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr, cint


class Workstation(Document):
	"""Workstation master belonging to a single production line."""

	def autoname(self) -> None:
		"""Name the workstation {line_code}-{workstation_code}."""
		self.name = self.build_workstation_name()

	def validate(self) -> None:
		"""Validate workstation identity before save."""
		self.normalize_fields()
		self.validate_production_line()
		self.validate_unique_code_on_line()

	def normalize_fields(self) -> None:
		"""Normalize code and name."""
		if self.workstation_code:
			self.workstation_code = cstr(self.workstation_code).strip().upper()
		if self.workstation_name:
			self.workstation_name = cstr(self.workstation_name).strip()
		self.sequence = cint(self.sequence) or 1

	def validate_production_line(self) -> None:
		"""Require an existing production line."""
		if not self.production_line:
			frappe.throw(_("Production Line is required"))
		if not frappe.db.exists("Production Line", self.production_line):
			frappe.throw(_("Production Line {0} was not found").format(self.production_line))

	def validate_unique_code_on_line(self) -> None:
		"""Keep workstation code unique within the same production line."""
		if not (self.production_line and self.workstation_code):
			frappe.throw(_("Workstation Code is required"))

		if not self.workstation_name:
			frappe.throw(_("Workstation Name is required"))

		filters = {
			"production_line": self.production_line,
			"workstation_code": self.workstation_code,
		}
		if not self.is_new():
			filters["name"] = ["!=", self.name]

		if frappe.db.exists("Workstation", filters):
			frappe.throw(
				_("Workstation Code {0} already exists on Production Line {1}").format(
					self.workstation_code, self.production_line
				)
			)

	def build_workstation_name(self) -> str:
		"""Return the line-scoped document name."""
		self.normalize_fields()
		line_code = frappe.db.get_value("Production Line", self.production_line, "line_code")
		if not line_code:
			frappe.throw(_("Production Line {0} has no Line Code").format(self.production_line))
		return f"{cstr(line_code).strip().upper()}-{self.workstation_code}"
