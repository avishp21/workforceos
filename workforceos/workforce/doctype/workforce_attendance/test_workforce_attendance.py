# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from workforceos.services.attendance_service import AttendanceService


class TestWorkforceAttendance(FrappeTestCase):
	def setUp(self):
		self.department = self._ensure("Workforce Department", "department_name", "Test Department")
		self.designation = self._ensure("Workforce Designation", "designation_name", "Test Operator")
		self.employee = self._insert_employee("ATT-1001")
		self.service = AttendanceService()

	def test_middleware_punch_creates_and_updates_same_row(self):
		created = self.service.upsert_punch(
			{
				"employee_id": "att-1001",
				"attendance_date": today(),
				"in_time": f"{today()} 08:05:00",
			}
		)
		self.assertEqual(created["action"], "created")

		doc = frappe.get_doc("Workforce Attendance", created["name"])
		doc.is_allocated = 1
		doc.allocated_line = None
		doc.remarks = "Allocated locally"
		doc.save()

		updated = self.service.upsert_punch(
			{
				"employee_id": "ATT-1001",
				"attendance_date": today(),
				"shift": "Ignored Shift",
				"out_time": f"{today()} 16:30:00",
				"status": "Late",
			}
		)
		self.assertEqual(updated["action"], "updated")
		self.assertEqual(updated["name"], created["name"])

		doc.reload()
		self.assertTrue(doc.in_time)
		self.assertTrue(doc.out_time)
		self.assertEqual(doc.status, "Late")
		self.assertFalse(doc.shift)
		self.assertEqual(doc.is_allocated, 1)
		self.assertEqual(doc.remarks, "Allocated locally")
		self.assertEqual(frappe.db.count("Workforce Attendance", {"employee": self.employee}), 1)

	def test_overnight_checkout_updates_open_check_in(self):
		created = self.service.upsert_punch(
			{
				"employee_id": "ATT-1001",
				"attendance_date": "2026-11-14",
				"in_time": "2026-11-14 22:00:00",
				"status": "Late",
			}
		)
		updated = self.service.upsert_punch(
			{
				"employee_id": "ATT-1001",
				"attendance_date": "2026-11-15",
				"out_time": "2026-11-15 03:00:00",
			}
		)
		self.assertEqual(updated["name"], created["name"])
		self.assertEqual(updated["action"], "updated")
		self.assertEqual(
			frappe.db.count("Workforce Attendance", {"employee": self.employee}),
			1,
		)

		doc = frappe.get_doc("Workforce Attendance", created["name"])
		self.assertEqual(str(doc.attendance_date), "2026-11-14")
		self.assertEqual(str(doc.in_time), "2026-11-14 22:00:00")
		self.assertEqual(str(doc.out_time), "2026-11-15 03:00:00")
		self.assertEqual(doc.status, "Late")

	def test_overnight_out_does_not_attach_to_later_same_day_in(self):
		previous = self.service.upsert_punch(
			{
				"employee_id": "ATT-1001",
				"attendance_date": "2026-11-13",
				"in_time": "2026-11-13 17:33:04",
			}
		)
		self.service.upsert_punch(
			{
				"employee_id": "ATT-1001",
				"attendance_date": "2026-11-14",
				"in_time": "2026-11-14 17:29:06",
			}
		)
		updated = self.service.upsert_punch(
			{
				"employee_id": "ATT-1001",
				"attendance_date": "2026-11-14",
				"out_time": "2026-11-14 03:30:55",
			}
		)
		self.assertEqual(updated["name"], previous["name"])
		doc = frappe.get_doc("Workforce Attendance", previous["name"])
		self.assertEqual(str(doc.out_time), "2026-11-14 03:30:55")
		self.assertEqual(
			frappe.db.count("Workforce Attendance", {"employee": self.employee}),
			2,
		)

	def test_shift_key_pairs_overnight_in_and_out(self):
		created = self.service.upsert_punch(
			{
				"employee_id": "ATT-1001",
				"attendance_date": "2026-11-13",
				"in_time": "2026-11-13 17:33:04",
				"status": "Present",
				"shift_key": "ATT-1001-1410000",
			}
		)
		self.service.upsert_punch(
			{
				"employee_id": "ATT-1001",
				"attendance_date": "2026-11-14",
				"in_time": "2026-11-14 17:29:06",
				"shift_key": "ATT-1001-1410001",
			}
		)
		updated = self.service.upsert_punch(
			{
				"employee_id": "ATT-1001",
				"attendance_date": "2026-11-14",
				"out_time": "2026-11-14 03:30:55",
				"shift_key": "ATT-1001-1410000",
			}
		)
		self.assertEqual(updated["name"], created["name"])
		self.assertEqual(updated["shift_key"], "ATT-1001-1410000")
		doc = frappe.get_doc("Workforce Attendance", created["name"])
		self.assertEqual(str(doc.attendance_date), "2026-11-13")
		self.assertEqual(str(doc.out_time), "2026-11-14 03:30:55")

		with self.assertRaises(frappe.ValidationError):
			self.service.upsert_punch(
				{
					"employee_id": "ATT-1001",
					"attendance_date": "2026-11-15",
					"out_time": "2026-11-15 03:00:00",
					"shift_key": "ATT-1001-missing",
				}
			)

	def _insert_employee(self, employee_id: str) -> str:
		doc = frappe.get_doc(
			{
				"doctype": "Workforce Employee",
				"employee_id": employee_id,
				"first_name": "Test",
				"last_name": "Punch",
				"department": self.department,
				"designation": self.designation,
				"status": "Active",
			}
		)
		doc.insert()
		return doc.name

	def _ensure(self, doctype: str, fieldname: str, value: str) -> str:
		if not frappe.db.exists(doctype, value):
			frappe.get_doc({"doctype": doctype, fieldname: value}).insert()
		return value

