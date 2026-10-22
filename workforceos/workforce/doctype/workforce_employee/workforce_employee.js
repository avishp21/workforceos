frappe.ui.form.on("Workforce Employee", {
	refresh(frm) {
		// Frappe hides the autoname field after the document is saved.
		// Employee Code must stay visible because it is the WorkforceOS identifier.
		frm.toggle_display("employee_code", true);
		const field = frm.get_field("employee_code");
		if (field && field.$input) {
			field.$input.prop("disabled", true);
		}
	},
	first_name(frm) {
		set_employee_name(frm);
	},
	last_name(frm) {
		set_employee_name(frm);
	},
});

function set_employee_name(frm) {
	const employee_name = [frm.doc.first_name, frm.doc.last_name].filter(Boolean).join(" ").trim();
	frm.set_value("employee_name", employee_name);
}
