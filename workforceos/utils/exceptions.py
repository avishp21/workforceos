"""Custom exceptions for WorkforceOS domain and service layers."""

from __future__ import annotations


class WorkforceOSException(Exception):
	"""Base exception for all WorkforceOS application errors."""

	def __init__(self, message: str, code: str | None = None) -> None:
		"""Initialize the exception.

		Args:
			message: Human-readable error description.
			code: Optional machine-readable error code.
		"""
		super().__init__(message)
		self.message = message
		self.code = code


class AttendanceIntegrationError(WorkforceOSException):
	"""Raised when attendance data cannot be retrieved or synchronized."""


class PlanningError(WorkforceOSException):
	"""Raised when daily planning cannot be created or updated."""


class AllocationError(WorkforceOSException):
	"""Raised when workforce allocation fails or produces invalid results."""


class AssignmentError(WorkforceOSException):
	"""Raised when employee-to-machine assignments cannot be applied."""


class RuleEngineError(WorkforceOSException):
	"""Raised when business rules cannot be evaluated or are misconfigured."""


class ScoringError(WorkforceOSException):
	"""Raised when candidate scoring or ranking fails."""


class ValidationError(WorkforceOSException):
	"""Raised when domain validation fails for plans, allocations, or overrides."""


class DisplayError(WorkforceOSException):
	"""Raised when display or dashboard data cannot be assembled."""
