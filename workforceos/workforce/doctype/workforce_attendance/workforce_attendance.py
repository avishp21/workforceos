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
		self.validate_duplicate_attendance()
		self.validate_status()
		self.validate_punch_times()
		self.validate_allocation()

	def validate_duplicate_attendance(self) -> None:
		"""Prevent duplicate attendance for the same employee, date, and shift."""
		if not (self.employee and self.attendance_date and self.shift):
			return

		if frappe.db.exists(
			"Workforce Attendance",
			{
				"employee": self.employee,
				"attendance_date": self.attendance_date,
				"shift": self.shift,
				"name": ["!=", self.name],
			},
		):
			frappe.throw(
				_("Attendance already exists for Employee {0} on {1} for Shift {2}").format(
					self.employee, self.attendance_date, self.shift
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
