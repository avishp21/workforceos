# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

from workforceos.workforce.setup.default_allocation_rules import create_default_allocation_rules


def after_install() -> None:
	"""Seed default allocation rules after app installation."""
	create_default_allocation_rules()
