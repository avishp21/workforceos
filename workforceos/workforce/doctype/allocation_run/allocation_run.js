// Copyright (c) 2026, WorkforceOS and contributors

frappe.ui.form.on("Allocation Run", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		frm.add_custom_button(__("Current Allocations"), () => {
			frappe.route_options = { allocation_run: frm.doc.name };
			frappe.set_route("current-allocations");
		}).addClass("btn-primary");

		frm.add_custom_button(__("Employee Evaluations"), () => {
			frappe.set_route("List", "Employee Allocation Evaluation", {
				allocation_run: frm.doc.name,
			});
		});

		if (frm.doc.status !== "Completed") {
			return;
		}

		frm.dashboard.reset();
		const success = flt(frm.doc.allocation_success_percent);
		const shortage = cint(frm.doc.total_shortage);
		const allocated = cint(frm.doc.total_allocated);
		const required = cint(frm.doc.total_required);
		const employees_allocated = cint(frm.doc.employees_allocated);
		const employees_rejected = cint(frm.doc.employees_rejected);

		const alert_class = shortage > 0 ? "orange" : "green";
		const message =
			shortage > 0
				? __("Allocation completed with {0} open positions ({1}% success).", [
						shortage,
						success,
				  ])
				: __("Allocation completed successfully ({0}% of required positions filled).", [
						success,
				  ]);
		frm.dashboard.set_headline_alert(message, alert_class);

		frm.dashboard.add_indicator(
			__("Success: {0}%", [success]),
			shortage > 0 ? "orange" : "green"
		);
		frm.dashboard.add_indicator(
			__("Assigned / Required: {0} / {1}", [allocated, required]),
			"blue"
		);
		frm.dashboard.add_indicator(
			__("Shortage: {0}", [shortage]),
			shortage > 0 ? "red" : "green"
		);
		frm.dashboard.add_indicator(
			__("Employees Allocated: {0}", [employees_allocated]),
			"green"
		);
		frm.dashboard.add_indicator(
			__("Employees Rejected: {0}", [employees_rejected]),
			"red"
		);
	},
});
