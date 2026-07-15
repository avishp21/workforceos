frappe.query_reports["Allocation Run Summary"] = {
	filters: [
		{
			fieldname: "date",
			label: __("Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "shift",
			label: __("Shift"),
			fieldtype: "Link",
			options: "Shift",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "Draft\nRunning\nCompleted\nFailed",
		},
	],
};
