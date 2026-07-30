# Copyright (c) 2026, WorkforceOS and contributors
# For license information, please see license.txt

"""Development-only demo data generator for WorkforceOS."""

from __future__ import annotations

import json
import random
from typing import Any

import frappe
from frappe import _
from frappe.utils import add_days, get_datetime, today

DEMO_PREFIX = "DEMO"
DEMO_RULE_PREFIX = "demo_"

GENERATABLE_ENTITIES = [
	"contractors",
	"designations",
	"skills",
	"production_lines",
	"shifts",
	"employees",
	"attendance",
	"daily_line_plans",
	"allocation_rules",
]

CLEARABLE_ENTITIES = [
	"employee_assignments",
	"allocation_decision_logs",
	"allocation_runs",
	"attendance",
	"daily_line_plans",
	"employees",
	"allocation_rules",
	"skills",
	"designations",
	"shifts",
	"production_lines",
	"contractors",
]

ENTITY_LABELS = {
	"contractors": "Contractors",
	"designations": "Workforce Designations",
	"skills": "Skills",
	"production_lines": "Production Lines",
	"shifts": "Shifts",
	"employees": "Workforce Employees",
	"attendance": "Workforce Attendance",
	"daily_line_plans": "Daily Line Plans",
	"allocation_rules": "Allocation Rules",
	"employee_assignments": "Employee Assignments",
	"allocation_decision_logs": "Allocation Decision Logs",
	"allocation_runs": "Allocation Runs",
}

CONTRACTOR_NAMES = [
	"Apex Workforce Services",
	"BlueStar Manpower",
	"Core Industrial Staffing",
	"Delta Contract Labour",
	"Evergreen Workforce",
	"Frontier Staffing Solutions",
	"Global Talent Partners",
	"Harbor Manpower Agency",
	"Ironclad Workforce",
	"Jupiter Staffing Co.",
]

LINE_DEFINITIONS = [
	("Assembly Line A", "DEMO-LINE-A"),
	("Assembly Line B", "DEMO-LINE-B"),
	("Packaging Line", "DEMO-LINE-PKG"),
	("Quality Inspection Line", "DEMO-LINE-QA"),
	("Dispatch Line", "DEMO-LINE-DSP"),
]

SHIFT_DEFINITIONS = [
	("Morning Shift", "06:00:00", "14:00:00"),
	("Afternoon Shift", "14:00:00", "22:00:00"),
	("Night Shift", "22:00:00", "06:00:00"),
]

SKILL_DEFINITIONS = [
	("Welding", "Skilled"),
	("Assembly", "Semi Skilled"),
	("Machine Operation", "Skilled"),
	("Quality Inspection", "Skilled"),
	("Packaging", "Unskilled"),
]

DESIGNATION_NAMES = [
	"Production Operator",
	"Assembly Technician",
	"Quality Inspector",
	"Line Helper",
	"Shift Supervisor",
]

FIRST_NAMES = [
	"Aarav", "Vivaan", "Aditya", "Arjun", "Rohan", "Kabir", "Ishaan", "Manish", "Nitin", "Suresh",
	"Priya", "Ananya", "Kavya", "Neha", "Pooja", "Ritu", "Sneha", "Divya", "Lakshmi", "Meera",
	"Rahul", "Amit", "Vikram", "Sanjay", "Deepak", "Harish", "Gopal", "Rajesh", "Kiran", "Anil",
]

LAST_NAMES = [
	"Sharma", "Patel", "Singh", "Kumar", "Reddy", "Nair", "Iyer", "Gupta", "Das", "Mehta",
	"Joshi", "Chopra", "Malhotra", "Bose", "Verma", "Agarwal", "Pillai", "Rao", "Kulkarni", "Desai",
]

DEMO_ALLOCATION_RULES = [
	{
		"rule_name": "Demo Prefer Experienced Skill",
		"rule_code": "demo_prefer_experienced_skill",
		"rule_category": "Preference",
		"priority": 20,
		"score": 15,
		"description": "Demo preference rule for skilled employees.",
	},
	{
		"rule_name": "Demo Prefer Same Contractor",
		"rule_code": "demo_prefer_same_contractor",
		"rule_category": "Preference",
		"priority": 21,
		"score": 10,
		"description": "Demo preference rule for contractor continuity.",
	},
	{
		"rule_name": "Demo Prefer Default Shift",
		"rule_code": "demo_prefer_default_shift",
		"rule_category": "Preference",
		"priority": 22,
		"score": 8,
		"description": "Demo preference rule for employees on their default shift.",
	},
	{
		"rule_name": "Demo Block Inactive Employees",
		"rule_code": "demo_block_inactive",
		"rule_category": "Eligibility",
		"priority": 0,
		"score": 0,
		"description": "Demo eligibility rule placeholder for inactive employees.",
	},
	{
		"rule_name": "Demo Validate Single Assignment",
		"rule_code": "demo_validate_single_assignment",
		"rule_category": "Validation",
		"priority": 30,
		"score": 0,
		"description": "Demo validation rule ensuring one assignment per employee per run.",
	},
]


def ensure_developer_mode() -> None:
	"""Restrict demo utilities to developer mode."""
	if not frappe.conf.developer_mode:
		frappe.throw(_("Generate Demo Data is only available in developer mode."))


def get_demo_entity_options() -> dict[str, list[dict[str, str]]]:
	"""Return checkbox options for generate and clear actions."""
	return {
		"generate": [{"key": key, "label": ENTITY_LABELS[key]} for key in GENERATABLE_ENTITIES],
		"clear": [{"key": key, "label": ENTITY_LABELS[key]} for key in CLEARABLE_ENTITIES],
	}


def generate_demo_data(entities: list[str] | str | None = None) -> dict[str, Any]:
	"""Generate realistic WorkforceOS demo data for selected entities."""
	ensure_developer_mode()
	selected = _normalize_entities(entities, GENERATABLE_ENTITIES)

	summary = {key: 0 for key in selected}
	created: dict[str, list[str]] = {}

	if "contractors" in selected:
		created["contractors"] = _create_contractors()
		summary["contractors"] = len(created["contractors"])

	if "designations" in selected:
		created["designations"] = _create_designations()
		summary["designations"] = len(created["designations"])

	if "skills" in selected:
		created["skills"] = _create_skills()
		summary["skills"] = len(created["skills"])

	if "production_lines" in selected:
		created["production_lines"] = _create_production_lines()
		summary["production_lines"] = len(created["production_lines"])

	if "shifts" in selected:
		created["shifts"] = _create_shifts()
		summary["shifts"] = len(created["shifts"])

	if "employees" in selected:
		contractors = created.get("contractors") or _get_existing_demo_contractors()
		designations = created.get("designations") or _get_existing_designations()
		skills = created.get("skills") or _get_existing_skills()
		lines = created.get("production_lines") or _get_existing_demo_lines()
		shifts = created.get("shifts") or _get_existing_shifts()
		_ensure_dependencies(
			{
				"Contractors": contractors,
				"Workforce Designations": designations,
				"Skills": skills,
				"Production Lines": lines,
				"Shifts": shifts,
			},
			target=_("Workforce Employees"),
		)
		created["employees"] = _create_employees(contractors, designations, skills, lines, shifts)
		summary["employees"] = len(created["employees"])

	if "attendance" in selected:
		employees = created.get("employees") or _get_existing_demo_employees()
		shifts = created.get("shifts") or _get_existing_shifts()
		_ensure_dependencies(
			{"Workforce Employees": employees, "Shifts": shifts},
			target=_("Workforce Attendance"),
		)
		summary["attendance"] = _create_attendance(employees, shifts)

	if "daily_line_plans" in selected:
		lines = created.get("production_lines") or _get_existing_demo_lines()
		shifts = created.get("shifts") or _get_existing_shifts()
		designations = created.get("designations") or _get_existing_designations()
		skills = created.get("skills") or _get_existing_skills()
		_ensure_dependencies(
			{
				"Production Lines": lines,
				"Shifts": shifts,
				"Workforce Designations": designations,
				"Skills": skills,
			},
			target=_("Daily Line Plans"),
		)
		summary["daily_line_plans"] = _create_daily_line_plans(lines, shifts, designations, skills)

	if "allocation_rules" in selected:
		summary["allocation_rules"] = _create_demo_allocation_rules()

	frappe.db.commit()
	return summary


def clear_demo_data(entities: list[str] | str | None = None) -> dict[str, int]:
	"""Remove WorkforceOS demo data for selected entities."""
	ensure_developer_mode()
	selected = _normalize_entities(entities, CLEARABLE_ENTITIES)

	deleted: dict[str, int] = {}
	clear_handlers = {
		"employee_assignments": _delete_demo_assignments,
		"allocation_decision_logs": _delete_demo_decision_logs,
		"allocation_runs": _delete_demo_allocation_runs,
		"attendance": _delete_demo_attendance,
		"daily_line_plans": _delete_demo_daily_line_plans,
		"employees": _delete_demo_employees,
		"allocation_rules": _delete_demo_allocation_rules,
		"skills": _delete_demo_skills,
		"designations": _delete_demo_designations,
		"shifts": _delete_demo_shifts,
		"production_lines": _delete_demo_production_lines,
		"contractors": _delete_demo_contractors,
	}

	for key in CLEARABLE_ENTITIES:
		if key in selected:
			deleted[key] = clear_handlers[key]()

	frappe.db.commit()
	return deleted


def _normalize_entities(entities: list[str] | str | None, allowed: list[str]) -> set[str]:
	if entities is None or entities == "":
		return set(allowed)

	if isinstance(entities, str):
		entities = json.loads(entities) if entities.strip().startswith("[") else [entities]

	if not isinstance(entities, (list, tuple, set)):
		frappe.throw(_("Entities must be a list of keys."))

	selected = {str(item).strip() for item in entities if str(item).strip()}
	invalid = selected - set(allowed)
	if invalid:
		frappe.throw(_("Invalid entities: {0}").format(", ".join(sorted(invalid))))
	if not selected:
		frappe.throw(_("Select at least one entity."))
	return selected


def _ensure_dependencies(dependencies: dict[str, list[str]], target: str) -> None:
	missing = [label for label, values in dependencies.items() if not values]
	if missing:
		frappe.throw(
			_("Cannot generate {0}. Missing required data: {1}. Generate those first or select them too.").format(
				target, ", ".join(missing)
			)
		)


def _get_existing_demo_contractors() -> list[str]:
	return frappe.get_all(
		"Contractor",
		filters={"contractor_code": ["like", f"{DEMO_PREFIX}-CON-%"]},
		pluck="name",
	)


def _get_existing_designations() -> list[str]:
	return frappe.get_all("Workforce Designation", pluck="name")


def _get_existing_skills() -> list[str]:
	return frappe.get_all("Skill", pluck="name")


def _get_existing_demo_lines() -> list[str]:
	return frappe.get_all(
		"Production Line",
		filters={"line_code": ["like", f"{DEMO_PREFIX}-LINE-%"]},
		pluck="name",
	)


def _get_existing_shifts() -> list[str]:
	return frappe.get_all("Shift", pluck="name")


def _get_existing_demo_employees() -> list[str]:
	return frappe.get_all(
		"Workforce Employee",
		filters={"employee_id": ["like", f"{DEMO_PREFIX}-EMP-%"]},
		pluck="name",
	)


def _insert_if_missing(doctype: str, unique_filters: dict[str, Any], data: dict[str, Any]) -> str | None:
	"""Insert a document when it does not already exist."""
	if frappe.db.exists(doctype, unique_filters):
		return frappe.db.get_value(doctype, unique_filters, "name")

	doc = frappe.get_doc({"doctype": doctype, **data})
	doc.insert(ignore_permissions=True)
	return doc.name


def _create_contractors() -> list[str]:
	names = []
	for index, contractor_name in enumerate(CONTRACTOR_NAMES, start=1):
		contractor_code = f"{DEMO_PREFIX}-CON-{index:02d}"
		name = _insert_if_missing(
			"Contractor",
			{"contractor_code": contractor_code},
			{
				"contractor_name": contractor_name,
				"contractor_code": contractor_code,
				"is_active": 1,
			},
		)
		if name:
			names.append(name)
	return names


def _create_designations() -> list[str]:
	names = []
	for designation_name in DESIGNATION_NAMES:
		name = _insert_if_missing(
			"Workforce Designation",
			{"designation_name": designation_name},
			{"designation_name": designation_name},
		)
		if name:
			names.append(name)
	return names


def _create_skills() -> list[str]:
	names = []
	for skill_name, skill_level in SKILL_DEFINITIONS:
		name = _insert_if_missing(
			"Skill",
			{"skill_name": skill_name},
			{"skill_name": skill_name, "skill_level": skill_level},
		)
		if name:
			names.append(name)
	return names


def _create_production_lines() -> list[str]:
	names = []
	for line_name, line_code in LINE_DEFINITIONS:
		name = _insert_if_missing(
			"Production Line",
			{"line_code": line_code},
			{
				"line_name": line_name,
				"line_code": line_code,
				"is_active": 1,
			},
		)
		if name:
			names.append(name)
	return names


def _create_shifts() -> list[str]:
	names = []
	for shift_name, start_time, end_time in SHIFT_DEFINITIONS:
		name = _insert_if_missing(
			"Shift",
			{"shift_name": shift_name},
			{
				"shift_name": shift_name,
				"start_time": start_time,
				"end_time": end_time,
			},
		)
		if name:
			names.append(name)
	return names


def _create_employees(
	contractors: list[str],
	designations: list[str],
	skills: list[str],
	lines: list[str],
	shifts: list[str],
) -> list[str]:
	names = []
	used_full_names: set[str] = set()

	for index in range(1, 101):
		employee_id = f"{DEMO_PREFIX}-EMP-{index:03d}"
		if frappe.db.exists("Workforce Employee", {"employee_id": employee_id}):
			names.append(employee_id)
			continue

		while True:
			employee_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
			if employee_name not in used_full_names:
				used_full_names.add(employee_name)
				break

		designation = random.choice(designations)
		skill = random.choice(skills)
		competencies = [
			{
				"designation": designation,
				"skill": skill,
				"priority": 1,
				"certified": 1,
			}
		]

		if random.random() < 0.35 and len(designations) > 1:
			secondary_designation = random.choice([item for item in designations if item != designation])
			competencies.append(
				{
					"designation": secondary_designation,
					"skill": random.choice(skills),
					"priority": 2,
					"certified": random.randint(0, 1),
				}
			)

		doc = frappe.get_doc(
			{
				"doctype": "Workforce Employee",
				"employee_id": employee_id,
				"employee_name": employee_name,
				"contractor": random.choice(contractors),
				"designation": designation,
				"skill": skill,
				"competencies": competencies,
				"default_line": random.choice(lines),
				"default_shift": random.choice(shifts),
				"status": "Active" if random.random() > 0.08 else "Inactive",
				"joining_date": add_days(today(), -random.randint(30, 1500)),
				"remarks": f"{DEMO_PREFIX} demo employee",
			}
		)
		doc.insert(ignore_permissions=True)
		names.append(doc.name)

	return names


def _create_attendance(employees: list[str], shifts: list[str]) -> int:
	created = 0
	active_employees = [
		employee
		for employee in employees
		if frappe.db.get_value("Workforce Employee", employee, "status") == "Active"
	]

	for day_offset in range(0, 3):
		attendance_date = add_days(today(), -day_offset)
		for employee in active_employees:
			default_shift = frappe.db.get_value("Workforce Employee", employee, "default_shift")
			shift = default_shift if default_shift and random.random() < 0.8 else random.choice(shifts)
			if frappe.db.exists(
				"Workforce Attendance",
				{
					"employee": employee,
					"attendance_date": attendance_date,
					"shift": shift,
				},
			):
				continue

			status = random.choices(
				["Present", "Present", "Present", "Late", "Absent", "Half Day"],
				weights=[55, 20, 10, 8, 5, 2],
				k=1,
			)[0]

			attendance_data = {
				"doctype": "Workforce Attendance",
				"employee": employee,
				"attendance_date": attendance_date,
				"shift": shift,
				"status": status,
				"remarks": f"{DEMO_PREFIX} demo attendance",
			}
			if status in ("Present", "Late", "Half Day"):
				shift_start = frappe.db.get_value("Shift", shift, "start_time")
				if shift_start:
					in_time = get_datetime(f"{attendance_date} {shift_start}")
					attendance_data["in_time"] = in_time

			doc = frappe.get_doc(attendance_data)
			doc.insert(ignore_permissions=True)
			created += 1

	return created


def _create_daily_line_plans(
	lines: list[str],
	shifts: list[str],
	designations: list[str],
	skills: list[str],
) -> int:
	created = 0
	statuses = ["Draft", "Planned", "Planned", "Completed"]

	for day_offset in range(0, 3):
		plan_date = add_days(today(), day_offset)
		for line in lines:
			for shift in shifts:
				if frappe.db.exists(
					"Daily Line Plan",
					{"date": plan_date, "shift": shift, "line": line},
				):
					continue

				requirements = []
				pair_count = random.randint(2, min(4, len(designations)))
				selected_designations = random.sample(designations, k=pair_count)
				selected_pairs = [
					(designation, random.choice(skills)) for designation in selected_designations
				]
				for designation, skill in selected_pairs:
					requirements.append(
						{
							"designation": designation,
							"skill": skill,
							"required_manpower": random.randint(2, 8),
						}
					)

				doc = frappe.get_doc(
					{
						"doctype": "Daily Line Plan",
						"date": plan_date,
						"shift": shift,
						"line": line,
						"status": random.choice(statuses),
						"requirements": requirements,
						"remarks": f"{DEMO_PREFIX} demo daily line plan",
					}
				)
				doc.insert(ignore_permissions=True)
				created += 1

	return created


def _create_demo_allocation_rules() -> int:
	created = 0
	for rule in DEMO_ALLOCATION_RULES:
		if frappe.db.exists("Allocation Rule", {"rule_code": rule["rule_code"]}):
			continue

		doc = frappe.get_doc(
			{
				"doctype": "Allocation Rule",
				"rule_name": rule["rule_name"],
				"rule_code": rule["rule_code"],
				"rule_category": rule["rule_category"],
				"priority": rule["priority"],
				"is_enabled": 1,
				"score": rule["score"],
				"description": rule["description"],
			}
		)
		doc.insert(ignore_permissions=True)
		created += 1

	return created


def _delete_demo_assignments() -> int:
	names = frappe.get_all(
		"Employee Assignment",
		filters={"employee": ["like", f"{DEMO_PREFIX}-EMP-%"]},
		pluck="name",
	)
	return _delete_docs("Employee Assignment", names)


def _delete_demo_decision_logs() -> int:
	deleted = 0
	names = frappe.get_all(
		"Employee Allocation Evaluation",
		filters={"employee": ["like", f"{DEMO_PREFIX}-EMP-%"]},
		pluck="name",
	)
	deleted += _delete_docs("Employee Allocation Evaluation", names)
	names = frappe.get_all(
		"Allocation Decision Log",
		filters={"employee": ["like", f"{DEMO_PREFIX}-EMP-%"]},
		pluck="name",
	)
	deleted += _delete_docs("Allocation Decision Log", names)
	return deleted


def _delete_demo_allocation_runs() -> int:
	names = frappe.get_all(
		"Employee Assignment",
		filters={"employee": ["like", f"{DEMO_PREFIX}-EMP-%"]},
		pluck="allocation_run",
		distinct=True,
	)
	# Also pick runs that may already have lost assignments
	run_names = [name for name in names if name]
	demo_runs = frappe.get_all(
		"Allocation Run",
		filters={"remarks": ["like", f"%{DEMO_PREFIX}%"]},
		pluck="name",
	)
	return _delete_docs("Allocation Run", list(set(run_names + demo_runs)))


def _delete_demo_attendance() -> int:
	names = frappe.get_all(
		"Workforce Attendance",
		filters={"remarks": ["like", f"%{DEMO_PREFIX}%"]},
		pluck="name",
	)
	return _delete_docs("Workforce Attendance", names)


def _delete_demo_daily_line_plans() -> int:
	names = frappe.get_all(
		"Daily Line Plan",
		filters={"remarks": ["like", f"%{DEMO_PREFIX}%"]},
		pluck="name",
	)
	return _delete_docs("Daily Line Plan", names)


def _delete_demo_employees() -> int:
	names = frappe.get_all(
		"Workforce Employee",
		filters={"employee_id": ["like", f"{DEMO_PREFIX}-EMP-%"]},
		pluck="name",
	)
	return _delete_docs("Workforce Employee", names)


def _delete_demo_allocation_rules() -> int:
	names = frappe.get_all(
		"Allocation Rule",
		filters={"rule_code": ["like", f"{DEMO_RULE_PREFIX}%"]},
		pluck="name",
	)
	return _delete_docs("Allocation Rule", names)


def _delete_demo_skills() -> int:
	names = []
	for skill, _ in SKILL_DEFINITIONS:
		if not frappe.db.exists("Skill", skill):
			continue
		if _is_demo_only_master_reference("Workforce Employee", "skill", skill):
			names.append(skill)
	return _delete_docs("Skill", names)


def _delete_demo_designations() -> int:
	names = []
	for designation in DESIGNATION_NAMES:
		if not frappe.db.exists("Workforce Designation", designation):
			continue
		if _is_demo_only_master_reference("Workforce Employee", "designation", designation):
			names.append(designation)
	return _delete_docs("Workforce Designation", names)


def _delete_demo_shifts() -> int:
	names = []
	for shift, _, _ in SHIFT_DEFINITIONS:
		if not frappe.db.exists("Shift", shift):
			continue
		if _is_demo_only_master_reference("Workforce Employee", "default_shift", shift):
			names.append(shift)
	return _delete_docs("Shift", names)


def _delete_demo_production_lines() -> int:
	names = frappe.get_all(
		"Production Line",
		filters={"line_code": ["like", f"{DEMO_PREFIX}-LINE-%"]},
		pluck="name",
	)
	return _delete_docs("Production Line", names)


def _delete_demo_contractors() -> int:
	names = frappe.get_all(
		"Contractor",
		filters={"contractor_code": ["like", f"{DEMO_PREFIX}-CON-%"]},
		pluck="name",
	)
	return _delete_docs("Contractor", names)


def _is_demo_only_master_reference(doctype: str, fieldname: str, value: str) -> bool:
	non_demo_reference = frappe.db.exists(
		doctype,
		{
			fieldname: value,
			"employee_id": ["not like", f"{DEMO_PREFIX}-EMP-%"],
		},
	)
	return not non_demo_reference


def _delete_docs(doctype: str, names: list[str]) -> int:
	deleted = 0
	for name in names:
		if name and frappe.db.exists(doctype, name):
			frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)
			deleted += 1
	return deleted
