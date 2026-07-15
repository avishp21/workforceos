# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

import frappe

from workforceos.workforce.setup.default_allocation_rules import create_default_allocation_rules


def execute() -> None:
	"""Seed default allocation rules after model sync."""
	create_default_allocation_rules()
