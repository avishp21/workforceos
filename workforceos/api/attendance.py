# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _

from workforceos.services.attendance_service import AttendanceService


PUNCH_KEYS = (
	"employee_id",
	"employee",
	"employee_code",
	"attendance_date",
	"in_time",
	"out_time",
	"status",
	"remarks",
	"shift_key",
)


@frappe.whitelist()
def sync_attendance(data: str | dict | None = None, records: str | list | None = None) -> dict:
	"""Create or update Workforce Attendance from middleware punch data.

	POST /api/method/workforceos.api.attendance.sync_attendance

	Send one punch as ``data`` (or as top-level fields) or many punches as
	``records``. Identify the 	employee with Matrix HR ``employee_id``. When ``shift_key`` is sent, IN and
	OUT are paired by that key. Otherwise matching falls back to the open
	check-in. ``in_time`` and ``out_time`` are both accepted.
	"""
	frappe.has_permission("Workforce Attendance", "write", throw=True)

	if records is None and data is None:
		data = {
			key: frappe.form_dict.get(key)
			for key in PUNCH_KEYS
			if frappe.form_dict.get(key) not in (None, "")
		}

	if records is None and not data:
		frappe.throw(_("Attendance payload is required"))

	service = AttendanceService()
	if records is not None:
		return service.upsert_punches(records)
	return service.upsert_punch(data)
