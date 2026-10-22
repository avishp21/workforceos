# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.naming import make_autoname
from frappe.utils import cstr


def execute() -> None:
	"""Fill generated employee codes and split legacy employee names."""
	if not frappe.db.exists("DocType", "Workforce Employee"):
		return
	if not frappe.db.has_column("Workforce Employee", "employee_code"):
		return

	employees = frappe.get_all(
		"Workforce Employee",
		fields=["name", "employee_code", "employee_name", "first_name", "last_name"],
	)
	for employee in employees:
		updates = {}
		if not employee.employee_code:
			updates["employee_code"] = make_autoname("EMP-.#####")

		if not employee.first_name and employee.employee_name:
			pieces = cstr(employee.employee_name).strip().split(None, 1)
			updates["first_name"] = pieces[0]
			if len(pieces) > 1 and not employee.last_name:
				updates["last_name"] = pieces[1]

		if updates:
			frappe.db.set_value("Workforce Employee", employee.name, updates, update_modified=False)

	frappe.db.commit()
