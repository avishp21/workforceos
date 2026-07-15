# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

RUN_STATUSES = ("Draft", "Running", "Completed", "Failed")


class AllocationRun(Document):
	"""Represents a single execution of the workforce allocation engine."""

	def before_insert(self) -> None:
		"""Set default run metadata on create."""
		if not self.status:
			self.status = "Draft"

	def after_insert(self) -> None:
		"""Sync run name after the naming series is applied."""
		if self.name and self.run_name != self.name:
			self.db_set("run_name", self.name, update_modified=False)
			self.run_name = self.name

	def validate(self) -> None:
		"""Validate allocation run fields before save."""
		self.set_run_name()
		self.validate_status()
		self.validate_summary_fields()

	def set_run_name(self) -> None:
		"""Sync run name with the generated document name."""
		if self.name and not self.name.startswith("New "):
			self.run_name = self.name

	def validate_status(self) -> None:
		"""Ensure status is a supported value."""
		if not self.status:
			self.status = "Draft"

		if self.status not in RUN_STATUSES:
			frappe.throw(_("Status must be one of: {0}").format(", ".join(RUN_STATUSES)))

	def validate_summary_fields(self) -> None:
		"""Ensure summary counters remain non-negative."""
		for fieldname in (
			"total_required",
			"total_allocated",
			"total_shortage",
			"lines_processed",
			"assignments_created",
		):
			value = getattr(self, fieldname, None)
			if value is not None and value < 0:
				frappe.throw(_("{0} cannot be negative").format(self.meta.get_label(fieldname)))
