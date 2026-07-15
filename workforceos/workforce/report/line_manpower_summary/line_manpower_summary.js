frappe.query_reports["Line Manpower Summary"] = {
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
	],
};
