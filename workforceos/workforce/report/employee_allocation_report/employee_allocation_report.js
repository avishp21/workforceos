frappe.query_reports["Employee Allocation Report"] = {
	filters: [
		{
			fieldname: "allocation_date",
			label: __("Allocation Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "shift",
			label: __("Shift"),
			fieldtype: "Link",
			options: "Shift",
		},
		{
			fieldname: "production_line",
			label: __("Production Line"),
			fieldtype: "Link",
			options: "Production Line",
		},
		{
			fieldname: "contractor",
			label: __("Contractor"),
			fieldtype: "Link",
			options: "Contractor",
		},
		{
			fieldname: "skill",
			label: __("Skill"),
			fieldtype: "Link",
			options: "Skill",
		},
		{
			fieldname: "designation",
			label: __("Designation"),
			fieldtype: "Link",
			options: "Workforce Designation",
		},
	],
};
