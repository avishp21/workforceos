frappe.ui.form.on("Production Line", {
	refresh(frm) {
		frm.set_query("customer", "customers", () => ({
			filters: { is_active: 1 },
		}));

		if (frm.is_new()) {
			return;
		}

		frm.add_custom_button(__("Add Workstation"), () => {
			frappe.new_doc("Workstation", {
				production_line: frm.doc.name,
			});
		});

		frm.add_custom_button(__("Generate Workstations"), () => {
			frappe.prompt(
				[
					{
						fieldname: "from_number",
						fieldtype: "Int",
						label: __("Starting Workstation"),
						reqd: 1,
						default: 1,
					},
					{
						fieldname: "to_number",
						fieldtype: "Int",
						label: __("Ending Workstation"),
						reqd: 1,
					},
				],
				(values) => generate_workstations_for_line(frm, values),
				__("Generate Workstations"),
				__("Generate")
			);
		});
	},
});

function generate_workstations_for_line(frm, values) {
	frappe.call({
		method: "workforceos.workforce.doctype.production_line.production_line.generate_workstations",
		args: {
			production_line: frm.doc.name,
			from_number: values.from_number,
			to_number: values.to_number,
		},
		freeze: true,
		freeze_message: __("Generating workstations"),
		callback(r) {
			if (!r.message) {
				return;
			}
			frappe.show_alert({ message: r.message.message, indicator: "green" });
			frm.reload_doc();
		},
	});
}
