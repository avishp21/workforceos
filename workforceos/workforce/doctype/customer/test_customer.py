# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestCustomer(FrappeTestCase):
	def test_line_can_map_multiple_customers_and_customer_can_map_multiple_lines(self):
		renault = self._ensure_customer("Renault ETB")
		bajaj = self._ensure_customer("Bajaj ETB")
		mahindra = self._ensure_customer("Mahindra")
		line_seven = self._ensure_line("Line 7 ETB", "LINE-7")
		line_eight = self._ensure_line("Line 8 ETB", "LINE-8")

		seven = frappe.get_doc("Production Line", line_seven)
		seven.append("customers", {"customer": renault})
		seven.save()

		eight = frappe.get_doc("Production Line", line_eight)
		eight.append("customers", {"customer": bajaj})
		eight.append("customers", {"customer": mahindra})
		eight.save()

		self.assertEqual([row.customer for row in seven.customers], [renault])
		self.assertEqual([row.customer for row in eight.customers], [bajaj, mahindra])

	def _ensure_customer(self, customer_name: str) -> str:
		if not frappe.db.exists("Customer", customer_name):
			frappe.get_doc({"doctype": "Customer", "customer_name": customer_name, "is_active": 1}).insert()
		return customer_name

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
