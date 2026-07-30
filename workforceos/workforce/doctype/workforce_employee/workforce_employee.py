# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr

from workforceos.services.competency_service import CompetencyService

EMPLOYEE_STATUSES = ("Active", "Inactive")


class WorkforceEmployee(Document):
	"""Workforce employee master for allocation engine."""

	def validate(self) -> None:
		"""Validate employee fields before save."""
		self.validate_employee_id()
		self.validate_employee_name()
		self.validate_status()
		self.validate_competencies()
		self.sort_competencies()

	def validate_employee_id(self) -> None:
		"""Normalize employee ID and prevent duplicates."""
		if self.employee_id:
			self.employee_id = cstr(self.employee_id).strip().upper()

		if not self.employee_id:
			frappe.throw(_("Employee ID is required"))

		if frappe.db.exists(
			"Workforce Employee",
			{"employee_id": self.employee_id, "name": ["!=", self.name]},
		):
			frappe.throw(_("Employee ID {0} already exists").format(self.employee_id))

	def validate_employee_name(self) -> None:
		"""Ensure employee name is provided."""
		if self.employee_name:
			self.employee_name = cstr(self.employee_name).strip()

		if not self.employee_name:
			frappe.throw(_("Employee Name is required"))

	def validate_status(self) -> None:
		"""Ensure status is a supported value."""
		if self.status not in EMPLOYEE_STATUSES:
			frappe.throw(_("Status must be one of: {0}").format(", ".join(EMPLOYEE_STATUSES)))

	def validate_competencies(self) -> None:
		"""Ensure competency matrix integrity."""
		if not self.competencies:
			frappe.throw(_("At least one competency is required"))

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
