# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime

ATTENDANCE_STATUSES = ("Present", "Absent", "Late", "Half Day")


class WorkforceAttendance(Document):
	"""Attendance record for workforce employees available for allocation."""

	def validate(self) -> None:
		"""Validate attendance fields before save."""
		self.normalize_shift_key()
		self.validate_shift_key()
		self.validate_duplicate_attendance()
		self.validate_status()
		self.validate_punch_times()
		self.validate_allocation()

	def normalize_shift_key(self) -> None:
		"""Keep the middleware pairing key trimmed and unchanged after insert."""
		if self.shift_key:
			self.shift_key = str(self.shift_key).strip()

	def validate_shift_key(self) -> None:
		"""Keep shift_key unique when middleware sends a pairing key."""
		if not self.shift_key:
			return

		if not self.is_new():
			previous = frappe.db.get_value("Workforce Attendance", self.name, "shift_key")
			if previous and previous != self.shift_key:
				frappe.throw(_("Shift Key cannot be changed"))

		if frappe.db.exists(
			"Workforce Attendance",
			{"shift_key": self.shift_key, "name": ["!=", self.name]},
		):
			frappe.throw(_("Shift Key {0} already exists").format(self.shift_key))

	def validate_duplicate_attendance(self) -> None:
		"""Prevent duplicate attendance for the same employee and date.

		Records paired by shift_key are allowed to span midnight, so they are
		not unique on calendar date.
		"""
		if self.shift_key or not (self.employee and self.attendance_date):
			return

		existing = frappe.get_all(
			"Workforce Attendance",
			filters={
				"employee": self.employee,
				"attendance_date": self.attendance_date,
				"name": ["!=", self.name],
			},
			fields=["name", "shift_key"],
			limit=20,
		)
		if any(not row.shift_key for row in existing):
			frappe.throw(
				_("Attendance already exists for Employee {0} on {1}").format(
					self.employee, self.attendance_date
				)
			)

	def validate_status(self) -> None:
		"""Ensure status is a supported value."""
		if self.status not in ATTENDANCE_STATUSES:
			frappe.throw(_("Status must be one of: {0}").format(", ".join(ATTENDANCE_STATUSES)))

	def validate_punch_times(self) -> None:
		"""Validate punch in and out times."""
		if self.in_time and self.out_time and get_datetime(self.in_time) > get_datetime(self.out_time):
			frappe.throw(_("In Time cannot be later than Out Time"))

	def validate_allocation(self) -> None:
		"""Validate allocation-related fields."""
		if self.is_allocated and not self.allocated_line:
			frappe.throw(_("Allocated Line is required when employee is marked as allocated"))

		if not self.is_allocated:
			self.allocated_line = None
