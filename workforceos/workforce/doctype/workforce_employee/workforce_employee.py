# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import cstr, validate_email_address

from workforceos.services.competency_service import CompetencyService

EMPLOYEE_STATUSES = ("Active", "Inactive", "Suspended")
ALLOCATION_BLOCKED_STATUSES = ("Inactive", "Suspended")

# Fields owned by Matrix HR. Synchronization may create or update these.
MATRIX_HR_FIELDS = (
	"salutation",
	"first_name",
	"last_name",
	"gender",
	"status",
	"department",
	"designation",
	"joining_date",
	"mobile_no",
	"email",
)

# Fields owned by WorkforceOS. Matrix HR synchronization must not change them.
WORKFORCEOS_MANAGED_FIELDS = (
	"employee_code",
	"competencies",
	"default_line",
	"default_shift",
	"contractor",
	"remarks",
	"skill",
)


class WorkforceEmployee(Document):
	"""Workforce employee master for allocation engine."""

	def before_insert(self) -> None:
		"""Assign a WorkforceOS employee code before the document is named."""
		self.ensure_employee_code()

	def before_validate(self) -> None:
		"""Normalize identity fields before mandatory checks."""
		self.ensure_employee_code()
		self.apply_name_parts()

	def validate(self) -> None:
		"""Validate employee fields before save."""
		self.validate_employee_code()
		self.validate_employee_id()
		self.validate_name_parts()
		self.validate_status()
		self.validate_contact()
		self.validate_competencies()
		self.sort_competencies()

	def ensure_employee_code(self) -> None:
		"""Generate a unique WorkforceOS employee code when one is not set."""
		if self.employee_code:
			self.employee_code = cstr(self.employee_code).strip().upper()
			return

		if not self.is_new() and self.name:
			existing_code = frappe.db.get_value("Workforce Employee", self.name, "employee_code")
			if existing_code:
				self.employee_code = existing_code
				return

		self.employee_code = make_autoname("EMP-.#####")

	def validate_employee_code(self) -> None:
		"""Keep the generated employee code unique and unchanged."""
		if not self.employee_code:
			frappe.throw(_("Employee Code is required"))

		if not self.is_new():
			previous_code = frappe.db.get_value("Workforce Employee", self.name, "employee_code")
			if previous_code and previous_code != self.employee_code:
				frappe.throw(_("Employee Code cannot be changed"))

		if frappe.db.exists(
			"Workforce Employee",
			{"employee_code": self.employee_code, "name": ["!=", self.name]},
		):
			frappe.throw(_("Employee Code {0} already exists").format(self.employee_code))

	def validate_employee_id(self) -> None:
		"""Normalize the Matrix HR employee ID and prevent duplicates."""
		if self.employee_id:
			self.employee_id = cstr(self.employee_id).strip().upper()

		if not self.employee_id:
			frappe.throw(_("Employee ID is required"))

		if frappe.db.exists(
			"Workforce Employee",
			{"employee_id": self.employee_id, "name": ["!=", self.name]},
		):
			frappe.throw(_("Employee ID {0} already exists").format(self.employee_id))

	def apply_name_parts(self) -> None:
		"""Build the display name, or split a legacy full name into parts."""
		if self.first_name:
			self.first_name = cstr(self.first_name).strip()
		if self.last_name:
			self.last_name = cstr(self.last_name).strip()

		if not self.first_name and self.employee_name:
			pieces = cstr(self.employee_name).strip().split(None, 1)
			self.first_name = pieces[0]
			if len(pieces) > 1 and not self.last_name:
				self.last_name = pieces[1]

		full_name = " ".join(part for part in (self.first_name, self.last_name) if part)
		if full_name:
			self.employee_name = full_name

	def validate_name_parts(self) -> None:
		"""Require a first name and a derived employee name."""
		if not self.first_name:
			frappe.throw(_("First Name is required"))
		if not self.employee_name:
			frappe.throw(_("Employee Name is required"))

	def validate_status(self) -> None:
		"""Ensure employment status is a supported value."""
		if self.status not in EMPLOYEE_STATUSES:
			frappe.throw(_("Employment Status must be one of: {0}").format(", ".join(EMPLOYEE_STATUSES)))

	def validate_contact(self) -> None:
		"""Normalize contact fields."""
		if self.mobile_no:
			self.mobile_no = cstr(self.mobile_no).strip()

		if self.email:
			self.email = cstr(self.email).strip()
			validate_email_address(self.email, throw=True)

	def validate_competencies(self) -> None:
		"""Ensure competency matrix integrity when competencies are present."""
		if not self.competencies:
			return

		seen_pairs: set[tuple[str, str]] = set()
		seen_priorities: set[int] = set()

		for row in self.competencies:
			if not row.designation or not row.skill:
				frappe.throw(_("Each competency must have a Designation and Skill"))

			pair = (row.designation, row.skill)
			if pair in seen_pairs:
				frappe.throw(
					_("Duplicate competency found for Designation {0} and Skill {1}").format(
						row.designation,
						row.skill,
					)
				)
			seen_pairs.add(pair)

			priority = row.priority or 1
			if priority in seen_priorities:
				frappe.throw(_("Duplicate competency priority {0} is not allowed").format(priority))
			seen_priorities.add(priority)

	def sort_competencies(self) -> None:
		"""Sort competency rows by ascending priority."""
		self.competencies.sort(key=lambda row: (row.priority or 9999, row.designation or "", row.skill or ""))

	def is_allocation_eligible(self) -> bool:
		"""Return whether this employee can be considered for future allocation."""
		return self.status == "Active"

	def get_competencies(self) -> list[dict]:
		"""Return all competencies ordered by priority."""
		return [
			CompetencyService.serialize_competency(row)
			for row in sorted(
				self.competencies,
				key=lambda row: (row.priority or 9999, row.designation or "", row.skill or ""),
			)
		]

	def get_primary_competency(self) -> dict | None:
		"""Return the primary (lowest priority number) competency."""
		return CompetencyService.get_primary_competency(self.get_competencies())

	def has_competency(self, designation: str, skill: str) -> bool:
		"""Return whether the employee has the given competency pair."""
		return CompetencyService.employee_has_competency(self.get_competencies(), designation, skill)

	def find_competency(self, designation: str, skill: str) -> dict | None:
		"""Return the matching competency row for designation + skill."""
		for row in self.get_competencies():
			if row.get("designation") == designation and row.get("skill") == skill:
				return row
		return None

	@classmethod
	def sync_from_matrix_hr(cls, data: dict | str) -> str:
		"""Create or update an employee from Matrix HR without touching WorkforceOS data.

		Matching uses Employee ID. A repeated sync updates the existing record.
		"""
		if isinstance(data, str):
			data = frappe.parse_json(data)
		if not isinstance(data, dict):
			frappe.throw(_("Matrix HR employee payload must be an object"))

		employee_id = cstr(data.get("employee_id")).strip().upper()
		if not employee_id:
			frappe.throw(_("Employee ID is required"))

		existing_name = frappe.db.get_value("Workforce Employee", {"employee_id": employee_id}, "name")
		if existing_name:
			doc = frappe.get_doc("Workforce Employee", existing_name)
			for fieldname in MATRIX_HR_FIELDS:
				if fieldname in data and data.get(fieldname) is not None:
					doc.set(fieldname, data.get(fieldname))
			doc.save(ignore_permissions=True)
			return doc.name

		payload = {
			"doctype": "Workforce Employee",
			"employee_id": employee_id,
		}
		for fieldname in MATRIX_HR_FIELDS:
			if fieldname in data and data.get(fieldname) is not None:
				payload[fieldname] = data.get(fieldname)

		doc = frappe.get_doc(payload)
		doc.insert(ignore_permissions=True)
		return doc.name
