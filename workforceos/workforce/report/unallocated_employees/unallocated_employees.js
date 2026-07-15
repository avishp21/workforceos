frappe.query_reports["Unallocated Employees"] = {
	filters: [
		{
			fieldname: "date",
			label: __("Date"),
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
