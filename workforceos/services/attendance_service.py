"""Attendance integration service for WorkforceOS."""

from __future__ import annotations

from datetime import date
from typing import Any

import frappe
from frappe import _
from frappe.utils import add_to_date, cstr, get_datetime, getdate

from workforceos.workforce.doctype.workforce_attendance.workforce_attendance import (
	ATTENDANCE_STATUSES,
	WorkforceAttendance,
)


class AttendanceService:
	"""Handles attendance data ingestion and availability queries.

	Responsibility:
		Integrate with external or internal attendance sources, normalize
		presence data, and expose employee availability for planning and
		allocation workflows.
	"""

	def upsert_punch(self, data: dict | str) -> dict[str, Any]:
		"""Create or update one daily attendance record from middleware.

		Matching prefers middleware ``shift_key`` so IN and OUT stay one
		session across midnight. Without a shift_key, an overnight checkout is
		attached to the open check-in. Allocation fields are never overwritten.
		"""
		payload = self._parse_payload(data)
		employee = self._resolve_employee(payload)
		in_time = self._parse_datetime(payload.get("in_time")) if "in_time" in payload else None
		out_time = self._parse_datetime(payload.get("out_time")) if "out_time" in payload else None
		shift_key = self._normalize_shift_key(payload.get("shift_key"))
		attendance_date = self._resolve_attendance_date(payload, in_time, out_time)

		existing_name = self._find_existing_attendance(
			employee=employee,
			attendance_date=attendance_date,
			in_time=in_time,
			out_time=out_time,
			shift_key=shift_key,
		)

		if existing_name:
			doc = frappe.get_doc("Workforce Attendance", existing_name)
			self._apply_punch_fields(doc, payload, overwrite_empty=False)
			doc.save(ignore_permissions=True)
			self._discard_split_checkout_row(employee, attendance_date, doc.name)
			return self._punch_result(doc, employee, "updated")

		if out_time and not in_time and shift_key:
			frappe.throw(_("No open IN found for Shift Key {0}").format(shift_key))

		doc = frappe.get_doc(
			{
				"doctype": "Workforce Attendance",
				"employee": employee,
				"attendance_date": attendance_date,
				"shift_key": shift_key,
				"status": self._resolve_status(payload, existing_in_time=None),
			}
		)
		self._apply_punch_fields(doc, payload, overwrite_empty=True)
		if not doc.status:
			doc.status = "Present" if doc.in_time else "Absent"
		doc.insert(ignore_permissions=True)
		return self._punch_result(doc, employee, "created")

	def upsert_punches(self, records: list | str) -> dict[str, Any]:
		"""Upsert many attendance punches and return per-row results."""
		if isinstance(records, str):
			records = frappe.parse_json(records)
		if not isinstance(records, list):
			frappe.throw(_("Attendance records must be a list"))

		results: list[dict[str, Any]] = []
		created = 0
		updated = 0
		failed = 0

		for index, row in enumerate(records):
			try:
				result = self.upsert_punch(row)
				if result["action"] == "created":
					created += 1
				else:
					updated += 1
				results.append({"index": index, "ok": True, **result})
				frappe.db.commit()
			except Exception as exc:
				frappe.db.rollback()
				failed += 1
				results.append({"index": index, "ok": False, "error": self._error_message(exc)})
				frappe.clear_messages()

		return {
			"created": created,
			"updated": updated,
			"failed": failed,
			"results": results,
		}

	def sync_attendance(self, target_date: date, source: str | None = None) -> dict[str, Any]:
		"""Synchronize attendance records for a given date.

		Args:
			target_date: The business date for which attendance should be synced.
			source: Optional attendance source identifier.

		Returns:
			A summary of the synchronization result.
		"""
		return {"date": str(target_date), "source": source, "synced": 0}

	def get_present_employees(
		self,
		target_date: date,
		shift: str | None = None,
		production_line: str | None = None,
	) -> list[dict[str, Any]]:
		"""Return employees marked present for the given context."""
		filters: dict[str, Any] = {
			"attendance_date": target_date,
			"status": ["in", ["Present", "Late", "Half Day"]],
		}
		if shift:
			filters["shift"] = shift
		if production_line:
			filters["allocated_line"] = production_line

		return frappe.get_all(
			"Workforce Attendance",
			filters=filters,
			fields=["name", "employee", "shift", "status", "in_time", "out_time", "allocated_line"],
		)

	def get_attendance_summary(self, target_date: date) -> dict[str, Any]:
		"""Build an attendance summary for planning and dashboards."""
		rows = frappe.get_all(
			"Workforce Attendance",
			filters={"attendance_date": target_date},
			fields=["status"],
		)
		counts: dict[str, int] = {status: 0 for status in ATTENDANCE_STATUSES}
		for row in rows:
			counts[row.status] = counts.get(row.status, 0) + 1
		return {"date": str(target_date), "total": len(rows), **counts}

	def get_employee_attendance_status(self, employee: str, target_date: date) -> dict[str, Any]:
		"""Return attendance status for a single employee."""
		rows = frappe.get_all(
			"Workforce Attendance",
			filters={"employee": employee, "attendance_date": target_date},
			fields=["name", "shift", "status", "in_time", "out_time"],
		)
		return {"employee": employee, "date": str(target_date), "records": rows}

	def validate_attendance_readiness(self, target_date: date) -> bool:
		"""Check whether attendance data is ready for downstream workflows."""
		return bool(
			frappe.db.exists("Workforce Attendance", {"attendance_date": target_date})
		)

	def _punch_result(self, doc: WorkforceAttendance, employee: str, action: str) -> dict[str, Any]:
		return {
			"name": doc.name,
			"employee": employee,
			"action": action,
			"attendance_date": str(doc.attendance_date) if doc.attendance_date else None,
			"in_time": str(doc.in_time) if doc.in_time else None,
			"out_time": str(doc.out_time) if doc.out_time else None,
			"status": doc.status,
			"shift_key": doc.shift_key,
		}

	def _parse_payload(self, data: dict | str) -> dict[str, Any]:
		if isinstance(data, str):
			data = frappe.parse_json(data)
		if not isinstance(data, dict):
			frappe.throw(_("Attendance payload must be an object"))
		return data

	def _resolve_employee(self, payload: dict[str, Any]) -> str:
		employee_id = cstr(payload.get("employee_id")).strip().upper()
		employee_code = cstr(payload.get("employee") or payload.get("employee_code")).strip().upper()

		if employee_id:
			employee = frappe.db.get_value("Workforce Employee", {"employee_id": employee_id}, "name")
			if not employee:
				frappe.throw(_("Employee ID {0} was not found in WorkforceOS").format(employee_id))
			return employee

		if employee_code:
			if not frappe.db.exists("Workforce Employee", employee_code):
				frappe.throw(_("Employee {0} was not found in WorkforceOS").format(employee_code))
			return employee_code

		frappe.throw(_("Employee ID is required"))

	def _require_date(self, value: Any):
		if not value:
			frappe.throw(_("Attendance Date is required"))
		return getdate(value)

	def _resolve_attendance_date(self, payload: dict[str, Any], in_time, out_time):
		if payload.get("attendance_date"):
			return getdate(payload.get("attendance_date"))
		if in_time:
			return getdate(in_time)
		if out_time:
			return getdate(out_time)
		frappe.throw(_("Attendance Date is required"))

	def _normalize_shift_key(self, value: Any) -> str | None:
		shift_key = cstr(value).strip()
		return shift_key or None

	def _find_existing_attendance(
		self, employee: str, attendance_date, in_time, out_time, shift_key: str | None = None
	) -> str | None:
		if shift_key:
			return frappe.db.get_value("Workforce Attendance", {"shift_key": shift_key}, "name")

		if out_time and not in_time:
			overnight_name = self._find_overnight_check_in(employee, out_time)
			if overnight_name:
				return overnight_name

			same_day = frappe.db.get_value(
				"Workforce Attendance",
				{"employee": employee, "attendance_date": attendance_date},
				["name", "in_time"],
				as_dict=True,
			)
			if same_day and self._out_belongs_to_record(same_day.in_time, out_time):
				return same_day.name
			return None

		return frappe.db.get_value(
			"Workforce Attendance",
			{"employee": employee, "attendance_date": attendance_date},
			"name",
		)

	def _find_overnight_check_in(self, employee: str, out_time) -> str | None:
		out_time = get_datetime(out_time)
		earliest = add_to_date(out_time, hours=-36)
		rows = frappe.get_all(
			"Workforce Attendance",
			filters={"employee": employee},
			fields=["name", "in_time", "out_time"],
			order_by="in_time desc",
			limit=20,
		)
		open_match = None
		closed_match = None
		for row in rows:
			if not row.in_time:
				continue
			punch_in = get_datetime(row.in_time)
			if punch_in < earliest or punch_in > out_time:
				continue
			if not row.out_time:
				open_match = row.name
				break
			if not closed_match:
				closed_match = row.name
		return open_match or closed_match

	def _out_belongs_to_record(self, in_time, out_time) -> bool:
		if not in_time:
			return True
		return get_datetime(in_time) <= get_datetime(out_time)

	def _discard_split_checkout_row(self, employee: str, attendance_date, keep_name: str) -> None:
		rows = frappe.get_all(
			"Workforce Attendance",
			filters={
				"employee": employee,
				"attendance_date": attendance_date,
				"name": ["!=", keep_name],
			},
			fields=["name", "in_time"],
		)
		for row in rows:
			if row.in_time:
				continue
			frappe.delete_doc("Workforce Attendance", row.name, force=1, ignore_permissions=True)

	def _apply_punch_fields(self, doc: WorkforceAttendance, payload: dict[str, Any], overwrite_empty: bool) -> None:
		if "in_time" in payload:
			in_time = self._parse_datetime(payload.get("in_time"))
			if in_time or overwrite_empty:
				doc.in_time = in_time
		if "out_time" in payload:
			out_time = self._parse_datetime(payload.get("out_time"))
			if out_time or overwrite_empty:
				doc.out_time = out_time
		if "remarks" in payload and payload.get("remarks") is not None:
			doc.remarks = payload.get("remarks")
		if not doc.shift_key:
			shift_key = self._normalize_shift_key(payload.get("shift_key"))
			if shift_key:
				doc.shift_key = shift_key

		if "status" in payload and payload.get("status"):
			status = self._normalize_status(payload.get("status"))
			if not (status == "Absent" and doc.in_time):
				doc.status = status
		elif overwrite_empty or not doc.status:
			doc.status = "Present" if doc.in_time else "Absent"

	def _resolve_status(self, payload: dict[str, Any], existing_in_time: Any) -> str:
		if payload.get("status"):
			return self._normalize_status(payload.get("status"))
		in_time = payload.get("in_time") or existing_in_time
		return "Present" if in_time else "Absent"

	def _normalize_status(self, value: Any) -> str:
		status = cstr(value).strip()
		lookup = {item.lower(): item for item in ATTENDANCE_STATUSES}
		normalized = lookup.get(status.lower())
		if not normalized:
			frappe.throw(_("Status must be one of: {0}").format(", ".join(ATTENDANCE_STATUSES)))
		return normalized

	def _parse_datetime(self, value: Any):
		if value in (None, ""):
			return None
		return get_datetime(value)

	def _error_message(self, exc: Exception) -> str:
		if getattr(exc, "args", None) and exc.args:
			message = exc.args[0]
			if isinstance(message, str) and message:
				return message
		return str(exc)
