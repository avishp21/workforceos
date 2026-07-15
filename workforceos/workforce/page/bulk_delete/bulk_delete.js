frappe.provide("workforceos");

frappe.pages["bulk-delete"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Bulk Delete"),
		single_column: true,
	});

	new workforceos.BulkDelete(page);
};

workforceos.BulkDelete = class BulkDelete {
	constructor(page) {
		this.page = page;
		this.options = [];
		this.make_layout();
		this.load_options();
	}

	make_layout() {
		this.page.main.html(`
			<div class="bulk-delete-page margin-top">
				<div class="alert alert-warning">
					${__(
						"This permanently deletes ALL records for the selected WorkforceOS DocTypes. This cannot be undone."
					)}
				</div>

				<div class="bulk-delete-section-header">
					<h5>${__("Select DocTypes")}</h5>
					<div class="bulk-delete-select-actions">
						<button type="button" class="btn btn-xs btn-default btn-select-all">
							${__("Select All")}
						</button>
						<button type="button" class="btn btn-xs btn-default btn-clear-all">
							${__("Clear All")}
						</button>
						<button type="button" class="btn btn-xs btn-default btn-refresh-counts">
							${__("Refresh Counts")}
						</button>
					</div>
				</div>

				<div class="bulk-delete-checkboxes"></div>

				<button class="btn btn-danger btn-bulk-delete margin-top">
					${__("Delete Selected")}
				</button>

				<div class="bulk-delete-results margin-top"></div>
			</div>
		`);

		this.$boxes = this.page.main.find(".bulk-delete-checkboxes");
		this.$results = this.page.main.find(".bulk-delete-results");

		this.page.main.find(".btn-bulk-delete").on("click", () => this.delete_selected());
		this.page.main.find(".btn-select-all").on("click", () => this.set_all_checked(true));
		this.page.main.find(".btn-clear-all").on("click", () => this.set_all_checked(false));
		this.page.main.find(".btn-refresh-counts").on("click", () => this.load_options());

		this.show_message(__("Loading DocTypes..."));
	}

	load_options() {
		frappe.call({
			method: "workforceos.api.bulk_delete.options",
			callback: (response) => {
				this.options = response.message || [];
				this.render_checkboxes();
				this.show_message(__("Select DocTypes, then delete."));
			},
			error: (error) => {
				this.render_error(error);
			},
		});
	}

	render_checkboxes() {
		const previously_checked = new Set(this.get_selected());

		const html = (this.options || [])
			.map((option) => {
				const doctype = frappe.utils.escape_html(option.doctype);
				const count = option.count || 0;
				const checked = previously_checked.has(option.doctype) ? "checked" : "";
				return `
					<label class="bulk-delete-checkbox">
						<input type="checkbox" value="${doctype}" ${checked}>
						<span class="bulk-delete-label">
							<span>${doctype}</span>
							<span class="text-muted">(${count})</span>
						</span>
					</label>
				`;
			})
			.join("");

		this.$boxes.html(html || `<div class="text-muted">${__("No DocTypes available.")}</div>`);
	}

	set_all_checked(checked) {
		this.$boxes.find('input[type="checkbox"]').prop("checked", checked);
	}

	get_selected() {
		return this.$boxes
			.find('input[type="checkbox"]:checked')
			.map((_, el) => el.value)
			.get();
	}

	delete_selected() {
		const doctypes = this.get_selected();
		if (!doctypes.length) {
			frappe.msgprint(__("Select at least one DocType to delete."));
			return;
		}

		const list = doctypes.map((name) => frappe.utils.escape_html(name)).join(", ");
		frappe.confirm(
			__("Permanently delete ALL records for: {0}?", [list]),
			() => {
				frappe.call({
					method: "workforceos.api.bulk_delete.delete",
					args: { doctypes },
					freeze: true,
					freeze_message: __("Deleting records..."),
					callback: (response) => {
						this.render_summary(
							__("Bulk delete completed."),
							response.message,
							"red"
						);
						this.load_options();
					},
					error: (error) => {
						this.render_error(error);
					},
				});
			}
		);
	}

	show_message(message) {
		this.$results.html(`<div class="text-muted">${message}</div>`);
	}

	render_summary(title, data, indicator) {
		const rows = Object.entries(data || {})
			.map(([key, value]) => {
				return `<tr><td>${frappe.utils.escape_html(key)}</td><td>${value}</td></tr>`;
			})
			.join("");

		this.$results.html(`
			<div class="indicator ${indicator}">${frappe.utils.escape_html(title)}</div>
			<table class="table table-bordered margin-top">
				<thead>
					<tr><th>${__("DocType")}</th><th>${__("Deleted")}</th></tr>
				</thead>
				<tbody>${rows}</tbody>
			</table>
		`);
	}

	render_error(error) {
		const message =
			(error && error.message) ||
			(error && error._server_messages && JSON.parse(error._server_messages)[0]) ||
			__("Operation failed.");

		this.$results.html(`
			<div class="alert alert-danger margin-top">
				<strong>${__("Error")}</strong>
				<pre class="bulk-delete-error">${frappe.utils.escape_html(message)}</pre>
			</div>
		`);
	}
};
