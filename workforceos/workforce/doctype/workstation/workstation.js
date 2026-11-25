frappe.ui.form.on("Workstation", {
	refresh(frm) {
		set_name_preview(frm);
	},
	production_line(frm) {
		set_name_preview(frm);
	},
	workstation_code(frm) {
		set_name_preview(frm);
	},
});

function set_name_preview(frm) {
	if (!frm.is_new() || !frm.doc.production_line || !frm.doc.workstation_code) {
		return;
	}

	frappe.db.get_value("Production Line", frm.doc.production_line, "line_code", (r) => {
		if (!r || !r.line_code) {
			return;
		}
		const workstation_id = `${String(r.line_code).toUpperCase()}-${String(
			frm.doc.workstation_code
		)
			.trim()
			.toUpperCase()}`;
		frm.set_df_property(
			"workstation_code",
			"description",
			__("This workstation will be saved as {0}", [workstation_id])
		);
	});
}
