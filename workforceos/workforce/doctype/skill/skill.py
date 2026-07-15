# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr

SKILL_LEVELS = ("Unskilled", "Semi Skilled", "Skilled")


class Skill(Document):
	"""Skill master for workforce capability tracking."""

	def validate(self) -> None:
		"""Validate skill fields before save."""
		self.validate_skill_name()
		self.validate_skill_level()

	def validate_skill_name(self) -> None:
		"""Normalize skill name."""
		if self.skill_name:
			self.skill_name = cstr(self.skill_name).strip()

		if not self.skill_name:
			frappe.throw(_("Skill Name is required"))

	def validate_skill_level(self) -> None:
		"""Ensure skill level is a supported value."""
		if self.skill_level not in SKILL_LEVELS:
			frappe.throw(_("Skill Level must be one of: {0}").format(", ".join(SKILL_LEVELS)))
