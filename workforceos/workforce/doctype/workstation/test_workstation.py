# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestWorkstation(FrappeTestCase):
	def setUp(self):
		self.line_one = self._ensure_line("Assembly Line 1", "LINE-1")
		self.line_two = self._ensure_line("Assembly Line 2", "LINE-2")

	def test_same_workstation_name_is_unique_per_line(self):
		first = self._insert_workstation(self.line_one, "WS-1", "Workstation 1")
		second = self._insert_workstation(self.line_two, "WS-1", "Workstation 1")

		self.assertEqual(first.name, "LINE-1-WS-1")
		self.assertEqual(second.name, "LINE-2-WS-1")
		self.assertEqual(first.workstation_name, second.workstation_name)

		with self.assertRaises(frappe.ValidationError):
			self._insert_workstation(self.line_one, "WS-1", "Workstation 1 Duplicate")

	def _ensure_line(self, line_name: str, line_code: str) -> str:
		if not frappe.db.exists("Production Line", line_code):
			frappe.get_doc(
				{
					"doctype": "Production Line",
					"line_name": line_name,
					"line_code": line_code,
					"is_active": 1,
				}
			).insert()
		return line_code

	def _insert_workstation(self, production_line: str, workstation_code: str, workstation_name: str):
		doc = frappe.get_doc(
			{
				"doctype": "Workstation",
				"production_line": production_line,
				"workstation_code": workstation_code,
				"workstation_name": workstation_name,
			}
		)
		doc.insert()
		return doc
