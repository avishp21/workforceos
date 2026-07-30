// Copyright (c) 2026, WorkforceOS and contributors

frappe.ui.form.on("Daily Production Plan", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		frm.add_custom_button(__("Generate Daily Line Plans"), () => {
			generate_daily_line_plans(frm);
		}).addClass("btn-primary");

		render_generated_line_plans(frm);
	},
});

function generate_daily_line_plans(frm) {
	if (!frm.doc.production_requirements?.length) {
		frappe.msgprint(__("Add at least one production requirement before generating."));
		return;
	}

	const run_generation = (overwrite_production_lines) => {
		frappe.call({
			method: "workforceos.api.daily_production_plan.generate_daily_line_plans",
			args: {
				daily_production_plan: frm.doc.name,
				overwrite_production_lines: overwrite_production_lines || [],
			},
			freeze: true,
			freeze_message: __("Generating Daily Line Plans..."),
			callback: (response) => {
				const result = response.message;
				if (!result) {
					return;
				}

				if (result.status === "needs_confirmation") {
					const lines = (result.conflicts || [])
						.map((row) => row.production_line)
						.join(", ");
					frappe.confirm(
						__(
							"Daily Line Plans already exist for: {0}. Overwrite existing line plans?",
							[lines]
						),
						() => {
							const overwrite = (result.conflicts || []).map(
								(row) => row.production_line
							);
							run_generation(overwrite);
						}
					);
					return;
				}

				frappe.show_alert({
					message: result.message || __("Daily Line Plans generated."),
					indicator: "green",
				});
				frm.reload_doc();
			},
		});
	};

	run_generation([]);
}

function render_generated_line_plans(frm) {
	frappe.call({
		method: "workforceos.api.daily_production_plan.get_generated_line_plans",
		args: { daily_production_plan: frm.doc.name },
		callback: (response) => {
			const $wrapper = frm.fields_dict.generated_plans_html?.$wrapper;
			if (!$wrapper) {
				return;
			}

			const rows = response.message || [];
			if (!rows.length) {
				$wrapper.html(
					`<p class="text-muted">${__("No Daily Line Plans generated yet.")}</p>`
				);
				return;
			}

			const table_rows = rows
				.map(
					(row) => `
				<tr>
					<td><a href="/app/daily-line-plan/${encodeURIComponent(row.name)}">${frappe.utils.escape_html(
						row.name
					)}</a></td>
					<td>${frappe.utils.escape_html(row.line || "")}</td>
					<td>${frappe.utils.escape_html(row.status || "")}</td>
				</tr>`
				)
				.join("");

			$wrapper.html(`
				<table class="table table-bordered table-sm">
					<thead>
						<tr>
							<th>${__("Daily Line Plan")}</th>
							<th>${__("Production Line")}</th>
							<th>${__("Status")}</th>
						</tr>
					</thead>
					<tbody>${table_rows}</tbody>
				</table>`);
		},
	});
}
