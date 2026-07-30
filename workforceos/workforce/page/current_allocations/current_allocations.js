frappe.provide("workforceos");

/** Enable when the Workstation module is available (future release). */
workforceos.WORKSTATION_REALLOCATION_ENABLED = false;

frappe.pages["current-allocations"].on_page_load = function (wrapper) {
	frappe.breadcrumbs.add({
		module: "Workforce",
		workspace: "WorkforceOS",
	});

	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Current Allocations"),
		single_column: true,
	});

	new workforceos.CurrentAllocationsPage(page);
};

workforceos.CurrentAllocationsPage = class CurrentAllocationsPage {
	constructor(page) {
		this.page = page;
		this.allocation_run =
			(frappe.route_options && frappe.route_options.allocation_run) || null;
		this.make_layout();
		if (this.allocation_run) {
			this.refresh();
		} else {
			this.show_missing_run_message();
		}
	}

	make_layout() {
		this.page.main.html(`
			<div class="current-allocations-meta" data-field="meta"></div>
			<div class="current-allocations-toolbar">
				<button class="btn btn-default btn-sm btn-suggest-reallocation" disabled title="${__(
					"Coming soon"
				)}">
					${__("Suggest Reallocation")}
				</button>
			</div>
			<div class="current-allocations-table" data-field="table"></div>
		`);
		this.$meta = this.page.main.find('[data-field="meta"]');
		this.$table = this.page.main.find('[data-field="table"]');
	}

	show_missing_run_message() {
		this.$meta.text(__("Open this page from an Allocation Run using Current Allocations."));
		this.$table.empty();
	}

	refresh() {
		frappe.call({
			method: "workforceos.api.allocation_run.get_current_allocations",
			args: { allocation_run: this.allocation_run },
			callback: (response) => {
				this.render_table(response.message || []);
			},
		});
	}

	render_table(rows) {
		this.$meta.html(
			`<strong>${__("Allocation Run")}:</strong> ${frappe.utils.escape_html(
				this.allocation_run
			)} &nbsp;|&nbsp; ${rows.length} ${__("assignments")}`
		);

		if (!rows.length) {
			this.$table.html(`<p class="text-muted">${__("No active assignments for this run.")}</p>`);
			return;
		}

		const table = $(`
			<table class="table table-bordered table-hover">
				<thead>
					<tr>
						<th>${__("Employee")}</th>
						<th>${__("Employee Name")}</th>
						<th>${__("Production Line")}</th>
						<th>${__("Matched Competency")}</th>
						<th>${__("Certified")}</th>
						<th>${__("Assignment Status")}</th>
						<th>${__("Actions")}</th>
					</tr>
				</thead>
				<tbody></tbody>
			</table>
		`);

		const tbody = table.find("tbody");
		rows.forEach((row) => {
			const certified = row.matched_certified ? __("Yes") : __("No");
			tbody.append(`
				<tr data-assignment="${frappe.utils.escape_html(row.name)}">
					<td>${frappe.utils.escape_html(row.employee)}</td>
					<td>${frappe.utils.escape_html(row.employee_name || "")}</td>
					<td>${frappe.utils.escape_html(row.production_line || "")}</td>
					<td>${frappe.utils.escape_html(row.matched_competency || "")}</td>
					<td>${certified}</td>
					<td>${frappe.utils.escape_html(row.assignment_status || "")}</td>
					<td>
						<button class="btn btn-primary btn-xs btn-reallocate">${__("Reallocate")}</button>
					</td>
				</tr>
			`);
		});

		this.$table.empty().append(table);
		this.$table.find(".btn-reallocate").on("click", (event) => {
			const assignment = $(event.currentTarget).closest("tr").attr("data-assignment");
			const row = rows.find((item) => item.name === assignment);
			if (row) {
				this.open_reallocate_dialog(row);
			}
		});
	}

	get_reallocate_dialog_fields(assignment_row) {
		const fields = [
			{
				fieldtype: "Section Break",
				fieldname: "current_section",
				label: __("Current Assignment"),
			},
			{
				fieldtype: "Data",
				fieldname: "employee",
				label: __("Employee"),
				read_only: 1,
				default: assignment_row.employee_name || assignment_row.employee,
			},
			{
				fieldtype: "Data",
				fieldname: "current_production_line",
				label: __("Current Production Line"),
				read_only: 1,
				default: assignment_row.production_line,
			},
			{
				fieldtype: "Data",
				fieldname: "matched_competency",
				label: __("Matched Competency"),
				read_only: 1,
				default: assignment_row.matched_competency,
			},
			{
				fieldtype: "Section Break",
				fieldname: "target_section",
				label: __("New Assignment"),
			},
			{
				fieldtype: "Link",
				fieldname: "new_production_line",
				label: __("New Production Line"),
				options: "Production Line",
				reqd: 1,
				default: assignment_row.production_line,
			},
		];

		if (workforceos.WORKSTATION_REALLOCATION_ENABLED) {
			fields.push(
				{
					fieldtype: "Data",
					fieldname: "current_workstation",
					label: __("Current Workstation"),
					read_only: 1,
				},
				{
					fieldtype: "Select",
					fieldname: "new_workstation",
					label: __("New Workstation"),
					options: [],
					reqd: 1,
				}
			);
		}

		fields.push(
			{
				fieldtype: "Section Break",
				fieldname: "reason_section",
				label: __("Reason"),
			},
			{
				fieldtype: "Select",
				fieldname: "reason",
				label: __("Reason"),
				options: [
					"Supervisor Request",
					"Production Change",
					"Competency Fit",
					"Absence Cover",
					"Other",
				],
				reqd: 1,
			},
			{
				fieldtype: "Small Text",
				fieldname: "comments",
				label: __("Comments"),
			}
		);

		return fields;
	}

	open_reallocate_dialog(assignment_row) {
		const dialog = new frappe.ui.Dialog({
			title: __("Reallocate Employee"),
			fields: this.get_reallocate_dialog_fields(assignment_row),
			primary_action_label: __("Confirm Reallocation"),
			primary_action: () => this.submit_reallocation(dialog, assignment_row.name),
		});

		dialog.show();

		if (workforceos.WORKSTATION_REALLOCATION_ENABLED) {
			this.load_workstation_options(dialog, assignment_row);
		}
	}

	load_workstation_options(dialog, assignment_row) {
		const production_line =
			dialog.get_value("new_production_line") || assignment_row.production_line;
		if (!production_line) {
			return;
		}

		frappe.call({
			method: "workforceos.api.allocation_run.get_workstations_for_line",
			args: {
				allocation_run: this.allocation_run,
				production_line,
			},
			callback: (response) => {
				const options = (response.message || []).map((item) => item.value);
				const field = dialog.fields_dict.new_workstation;
				if (!field) {
					return;
				}
				field.df.options = options;
				field.refresh();
			},
		});
	}

	submit_reallocation(dialog, assignment_name) {
		const values = dialog.get_values();
		if (!values) {
			return;
		}

		const args = {
			assignment_name,
			to_production_line: values.new_production_line,
			reason: values.reason,
			comments: values.comments,
		};

		if (workforceos.WORKSTATION_REALLOCATION_ENABLED && values.new_workstation) {
			args.to_workstation = values.new_workstation;
		}

		frappe.call({
			method: "workforceos.api.allocation_run.reallocate_employee",
			args,
			freeze: true,
			freeze_message: __("Validating and applying reallocation..."),
			callback: (response) => {
				const result = response.message || {};
				if (!result.success) {
					frappe.msgprint({
						title: __("Reallocation Blocked"),
						indicator: "red",
						message: result.message || __("Validation failed"),
					});
					return;
				}
				frappe.show_alert({
					message: result.message || __("Employee reallocated"),
					indicator: "green",
				});
				dialog.hide();
				this.refresh();
			},
		});
	}
};
