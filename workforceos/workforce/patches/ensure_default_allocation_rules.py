# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

from workforceos.workforce.setup.default_allocation_rules import create_default_allocation_rules


def execute() -> None:
	"""Ensure default allocation rules exist after setup fix."""
	create_default_allocation_rules()
