"""Application-wide constants for WorkforceOS."""

from __future__ import annotations

APP_NAME = "workforceos"

# Allocation lifecycle states
ALLOCATION_STATUS_DRAFT = "Draft"
ALLOCATION_STATUS_IN_PROGRESS = "In Progress"
ALLOCATION_STATUS_COMPLETED = "Completed"
ALLOCATION_STATUS_FAILED = "Failed"

# Assignment types
ASSIGNMENT_TYPE_AUTO = "Auto"
ASSIGNMENT_TYPE_MANUAL = "Manual"
ASSIGNMENT_TYPE_OVERRIDE = "Override"

# Display modes
DISPLAY_MODE_TV = "TV"
DISPLAY_MODE_SUPERVISOR = "Supervisor"
DISPLAY_MODE_ANALYTICS = "Analytics"

# Rule engine scopes
RULE_SCOPE_ALLOCATION = "Allocation"
RULE_SCOPE_ASSIGNMENT = "Assignment"
RULE_SCOPE_PLANNING = "Planning"
RULE_SCOPE_VALIDATION = "Validation"

# Scoring dimensions
SCORING_DIMENSION_SKILL = "skill"
SCORING_DIMENSION_AVAILABILITY = "availability"
SCORING_DIMENSION_PREFERENCE = "preference"
SCORING_DIMENSION_PROXIMITY = "proximity"

# Scheduler job types
JOB_SYNC_ATTENDANCE = "sync_attendance"
JOB_DAILY_PLANNING = "daily_planning"
JOB_RUN_ALLOCATION = "run_allocation"
JOB_REFRESH_DISPLAYS = "refresh_displays"
