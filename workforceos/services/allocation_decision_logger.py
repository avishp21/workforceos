"""Deprecated allocation decision logging.

New allocation runs persist audits via Employee Allocation Evaluation.
"""

from __future__ import annotations

from workforceos.services.employee_allocation_evaluation_service import (
	EmployeeAllocationEvaluationService,
)
from workforceos.services.rule_engine import RuleEngine


class AllocationDecisionLogger(EmployeeAllocationEvaluationService):
	"""Backward-compatible alias for legacy imports."""

	def __init__(self, rule_engine: RuleEngine | None = None) -> None:
		super().__init__(rule_engine=rule_engine)
