# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr, get_time


class Shift(Document):
	"""Shift master for workforce scheduling."""

	def validate(self) -> None:
		"""Validate shift fields before save."""
		self.validate_shift_name()
		self.validate_shift_times()

	def validate_shift_name(self) -> None:
		"""Normalize shift name."""
		if self.shift_name:
			self.shift_name = cstr(self.shift_name).strip()

		if not self.shift_name:
			frappe.throw(_("Shift Name is required"))

	def validate_shift_times(self) -> None:
		"""Validate shift start and end times."""
		if not self.start_time or not self.end_time:
			frappe.throw(_("Start Time and End Time are required"))

		if get_time(self.start_time) == get_time(self.end_time):
			frappe.throw(_("Start Time and End Time cannot be the same"))
