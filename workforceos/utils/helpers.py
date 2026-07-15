"""Shared helper utilities for WorkforceOS."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


def parse_date(value: str | date | datetime | None) -> date | None:
	"""Parse a value into a date object.

	Args:
		value: A date string, date, datetime, or None.

	Returns:
		A date instance, or None if the input is None.
	"""
	pass


def ensure_dict(value: Any) -> dict[str, Any]:
	"""Ensure a value is returned as a dictionary.

	Args:
		value: Any input value expected to represent a mapping.

	Returns:
		A dictionary representation of the input.
	"""
	pass


def merge_context(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
	"""Merge override values into a base context dictionary.

	Args:
		base: The base context dictionary.
		overrides: Values to merge on top of the base context.

	Returns:
		A new dictionary containing merged context values.
	"""
	pass


def get_service_logger(name: str) -> Any:
	"""Return a logger instance for a service module.

	Args:
		name: The logger name, typically the service module path.

	Returns:
		A configured logger instance.
	"""
	pass
