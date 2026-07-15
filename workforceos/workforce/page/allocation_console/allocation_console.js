frappe.provide("workforceos");

frappe.pages["allocation-console"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Allocation Console"),
		single_column: true,
	});

	new workforceos.AllocationConsole(page);
};

workforceos.AllocationConsole = class AllocationConsole {
	constructor(page) {
		this.page = page;
		this.make_form();
	}

	make_form() {
		this.form = new frappe.ui.FieldGroup({
			fields: [
				{
					label: __("Allocation Date"),
					fieldname: "allocation_date",
					fieldtype: "Date",
					reqd: 1,
					default: frappe.datetime.get_today(),
				},
				{
					fieldtype: "Column Break",
				},
				{
					label: __("Shift"),
					fieldname: "shift",
					fieldtype: "Link",
					options: "Shift",
					reqd: 1,
				},
				{
					fieldtype: "Section Break",
				},
				{
					fieldtype: "HTML",
					fieldname: "results",
				},
			],
			body: this.page.body,
		});

		this.form.make();
		this.page.set_primary_action(__("Generate Allocation"), () => this.generate_allocation());
		this.clear_results();
	}

	generate_allocation() {
		const values = this.form.get_values();
		if (!values) {
			return;
		}

		this.page.set_primary_action(__("Generating..."), () => {});
		this.show_loading();

		frappe.call({
			method: "workforceos.api.allocation.allocate",
			args: {
				date: values.allocation_date,
				shift: values.shift,
			},
			freeze: true,
			freeze_message: __("Running allocation..."),
			callback: (response) => {
				this.page.set_primary_action(__("Generate Allocation"), () => this.generate_allocation());
				this.render_results(response.message);
			},
			error: (error) => {
				this.page.set_primary_action(__("Generate Allocation"), () => this.generate_allocation());
				this.render_error(error);
			},
		});
	}

	show_loading() {
		this.form.get_field("results").$wrapper.html(`
			<div class="text-muted margin-top">
				${__("Running allocation. Please wait...")}
			</div>
		`);
	}

	clear_results() {
		this.form.get_field("results").$wrapper.html(`
			<div class="text-muted margin-top">
				${__("Select a date and shift, then click Generate Allocation.")}
			</div>
		`);
	}

	render_results(run) {
		if (!run) {
			this.render_error({ message: __("No allocation result was returned.") });
			return;
		}

		if (run.status === "Failed") {
			this.render_failed_run(run);
			return;
		}

		const summary = run.summary || {};
		const formatted_date = summary.date
			? frappe.datetime.str_to_user(summary.date)
			: frappe.datetime.str_to_user(run.allocation_date);

		let html = `
			<div class="allocation-summary margin-top">
				<h5>${__("Allocation Summary")}</h5>
				<div class="allocation-summary-meta">
					<div><span class="text-muted">${__("Run")}</span><strong>${frappe.utils.escape_html(summary.run || run.run_name || run.name || "")}</strong></div>
					<div><span class="text-muted">${__("Date")}</span><strong>${frappe.utils.escape_html(formatted_date)}</strong></div>
					<div><span class="text-muted">${__("Shift")}</span><strong>${frappe.utils.escape_html(summary.shift || run.shift || "")}</strong></div>
				</div>
				<hr class="allocation-summary-divider">
				<div class="allocation-summary-totals">
					<div><span class="text-muted">${__("Required")}</span><strong>${summary.required ?? run.total_required ?? 0}</strong></div>
					<div><span class="text-muted">${__("Allocated")}</span><strong>${summary.allocated ?? run.total_allocated ?? 0}</strong></div>
					<div><span class="text-muted">${__("Shortage")}</span><strong>${summary.shortage ?? run.total_shortage ?? 0}</strong></div>
				</div>
				<hr class="allocation-summary-divider">
				<div class="allocation-summary-lines">
					${this.render_line_summaries(summary.lines || [])}
				</div>
		`;

		const unallocated = summary.unallocated_employees || [];
		if (unallocated.length) {
			html += `
				<hr class="allocation-summary-divider">
				<div class="allocation-summary-unallocated">
					<h6>${__("Unallocated Employees")}</h6>
					${this.render_unallocated_employees(unallocated)}
				</div>
			`;
		}

		html += `
				<div class="text-muted allocation-summary-footer margin-top">
					${__("Execution Time")}: ${run.execution_time_seconds || 0}s
				</div>
			</div>
		`;

		this.form.get_field("results").$wrapper.html(html);
	}

	render_line_summaries(lines) {
		if (!lines.length) {
			return `<div class="text-muted">${__("No line breakdown available.")}</div>`;
		}

		return lines
			.map((line) => {
				const label = frappe.utils.escape_html(line.line_label || line.line || "");
				const allocated = line.allocated || 0;
				const required = line.required || 0;
				return `<div class="allocation-summary-line"><strong>${label}</strong><span>${allocated} / ${required}</span></div>`;
			})
			.join("");
	}

	render_unallocated_employees(employees) {
		return employees
			.map((employee) => {
				const name = frappe.utils.escape_html(employee.employee || "");
				const reason = frappe.utils.escape_html(employee.reason || "");
				return `
					<div class="allocation-summary-employee">
						<div class="allocation-summary-employee-name">${name}</div>
						<div class="allocation-summary-employee-reason">
							<span class="text-muted">${__("Reason")}:</span> ${reason}
						</div>
					</div>
				`;
			})
			.join("");
	}

	render_failed_run(run) {
		let html = `
			<div class="margin-top">
				<div class="indicator red">${__("Failed")}</div>
				<div class="allocation-console-results margin-top">
					<p><strong>${__("Run Number")}:</strong> ${frappe.utils.escape_html(run.run_name || run.name || "")}</p>
					<p><strong>${__("Execution Time")}:</strong> ${run.execution_time_seconds || 0}s</p>
				</div>
		`;

		if (run.error_log) {
			html += `
				<div class="alert alert-danger margin-top">
					<strong>${__("Error")}</strong>
					<pre class="allocation-console-error">${frappe.utils.escape_html(run.error_log)}</pre>
				</div>
			`;
		}

		html += `</div>`;
		this.form.get_field("results").$wrapper.html(html);
	}

	render_error(error) {
		const message =
			(error && error.message) ||
			(error && error._server_messages && JSON.parse(error._server_messages)[0]) ||
			__("Allocation failed.");

		this.form.get_field("results").$wrapper.html(`
			<div class="alert alert-danger margin-top">
				<strong>${__("Error")}</strong>
				<pre class="allocation-console-error">${frappe.utils.escape_html(message)}</pre>
			</div>
		`);
	}
};
