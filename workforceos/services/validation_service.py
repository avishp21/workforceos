"""Domain validation service for WorkforceOS."""

from __future__ import annotations

from typing import Any


class ValidationService:
	"""Validates plans, allocations, assignments, and overrides.

	Responsibility:
		Enforce structural and business constraints before and after core
		workforce workflows execute, ensuring data integrity across the
		application.
	"""

	def validate_plan(self, plan: dict[str, Any]) -> dict[str, Any]:
		"""Validate a daily plan payload.

		Args:
			plan: Daily plan data to validate.

		Returns:
			Validation result with errors and warnings.
		"""
		pass

	def validate_allocation(self, allocation: dict[str, Any]) -> dict[str, Any]:
		"""Validate an allocation result.

		Args:
			allocation: Allocation payload to validate.

		Returns:
			Validation result with errors and warnings.
		"""
		pass

	def validate_assignment(self, assignment: dict[str, Any]) -> dict[str, Any]:
		"""Validate a single assignment record.

		Args:
			assignment: Assignment data to validate.

		Returns:
			Validation result with errors and warnings.
		"""
		pass

	def validate_override(self, override: dict[str, Any]) -> dict[str, Any]:
		"""Validate a manual override request.

		Args:
			override: Override instructions to validate.

		Returns:
			Validation result with errors and warnings.
		"""
		pass

	def validate_attendance_context(self, context: dict[str, Any]) -> dict[str, Any]:
		"""Validate attendance-related input context.

		Args:
			context: Attendance context to validate.

		Returns:
			Validation result with errors and warnings.
		"""
		pass

	def is_valid(self, validation_result: dict[str, Any]) -> bool:
		"""Determine whether a validation result represents a passing state.

		Args:
			validation_result: Result returned by a validation method.

		Returns:
			True if no blocking validation errors exist.
		"""
		pass
