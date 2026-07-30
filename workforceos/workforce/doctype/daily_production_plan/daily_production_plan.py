# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

PLAN_STATUSES = ("Draft", "Planned", "Generated", "Completed")


class DailyProductionPlan(Document):
	"""Plant-level daily production plan that generates Daily Line Plans."""

	def validate(self) -> None:
		self.validate_status()
		self.validate_production_requirements()

	def validate_status(self) -> None:
		if self.status not in PLAN_STATUSES:
			frappe.throw(_("Status must be one of: {0}").format(", ".join(PLAN_STATUSES)))

	def validate_production_requirements(self) -> None:
		if not self.production_requirements:
			frappe.throw(_("At least one production requirement is required"))

		for row in self.production_requirements:
			if not row.production_line:
				frappe.throw(_("Production Line is required on all requirement rows"))
			if not row.required_manpower or row.required_manpower <= 0:
				frappe.throw(
					_("Required Manpower must be greater than zero for all requirement rows")
				)
