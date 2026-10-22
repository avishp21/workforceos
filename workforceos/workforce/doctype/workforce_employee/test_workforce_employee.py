# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from workforceos.services.rule_engine import _employee_active
from workforceos.workforce.doctype.workforce_employee.workforce_employee import WorkforceEmployee


class TestWorkforceEmployee(FrappeTestCase):
	def setUp(self):
		self.department = self._ensure_department("Test Department")
		self.designation = self._ensure_designation("Test Operator")

	def test_employee_code_is_generated_and_employee_id_is_unique(self):
		first = self._insert_employee("MX-1001", "Asha", "Rao")
		self.assertTrue(first.employee_code.startswith("EMP-"))
		self.assertEqual(first.name, first.employee_code)
		self.assertEqual(first.employee_name, "Asha Rao")

		with self.assertRaises(frappe.ValidationError):
			self._insert_employee("MX-1001", "Other", "Person")

	def test_matrix_sync_updates_existing_employee_and_preserves_workforceos_fields(self):
		created_name = WorkforceEmployee.sync_from_matrix_hr(
			{
				"employee_id": "MX-2002",
				"first_name": "Ravi",
				"last_name": "Iyer",
				"department": self.department,
				"designation": self.designation,
				"status": "Active",
				"email": "ravi@example.com",
				"default_line": "Should Not Stick",
				"employee_code": "HR-CODE",
			}
		)
		doc = frappe.get_doc("Workforce Employee", created_name)
		doc.default_line = None
		doc.remarks = "Allocated locally"
		doc.save()
		original_code = doc.employee_code

		updated_name = WorkforceEmployee.sync_from_matrix_hr(
			{
				"employee_id": "mx-2002",
				"first_name": "Ravi",
				"last_name": "Menon",
				"status": "Suspended",
				"department": self.department,
				"designation": self.designation,
				"default_line": "Line From HR",
				"remarks": "Overwrite me",
				"employee_code": "DIFFERENT",
			}
		)

		self.assertEqual(updated_name, created_name)
		updated = frappe.get_doc("Workforce Employee", updated_name)
		self.assertEqual(updated.employee_code, original_code)
		self.assertEqual(updated.last_name, "Menon")
		self.assertEqual(updated.status, "Suspended")
		self.assertEqual(updated.remarks, "Allocated locally")
		self.assertFalse(updated.default_line)
		self.assertEqual(frappe.db.count("Workforce Employee", {"employee_id": "MX-2002"}), 1)

	def test_inactive_and_suspended_employees_are_not_allocation_eligible(self):
		inactive = self._insert_employee("MX-3003", "Neha", "Das", status="Inactive")
		suspended = self._insert_employee("MX-3004", "Amit", "Shah", status="Suspended")
		self.assertFalse(inactive.is_allocation_eligible())
		self.assertFalse(suspended.is_allocation_eligible())

		inactive_passed, _, inactive_message = _employee_active({"employee": {"status": "Inactive"}}, {})
		suspended_passed, _, suspended_message = _employee_active({"employee": {"status": "Suspended"}}, {})
		self.assertFalse(inactive_passed)
		self.assertFalse(suspended_passed)
		self.assertIn("Inactive", inactive_message)
		self.assertIn("Suspended", suspended_message)

	def _insert_employee(self, employee_id: str, first_name: str, last_name: str, status: str = "Active"):
		doc = frappe.get_doc(
			{
				"doctype": "Workforce Employee",
				"employee_id": employee_id,
				"first_name": first_name,
				"last_name": last_name,
				"department": self.department,
				"designation": self.designation,
				"status": status,
			}
		)
		doc.insert()
		return doc

	def _ensure_department(self, department_name: str) -> str:
		if not frappe.db.exists("Workforce Department", department_name):
			frappe.get_doc(
				{"doctype": "Workforce Department", "department_name": department_name}
			).insert()
		return department_name

	def _ensure_designation(self, designation_name: str) -> str:
		if not frappe.db.exists("Workforce Designation", designation_name):
			frappe.get_doc(
				{"doctype": "Workforce Designation", "designation_name": designation_name}
			).insert()
		return designation_name
