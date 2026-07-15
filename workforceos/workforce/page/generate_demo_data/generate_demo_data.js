frappe.provide("workforceos");

frappe.pages["generate-demo-data"].on_page_load = function (wrapper) {
	if (!frappe.boot.developer_mode) {
		frappe.msgprint({
			title: __("Developer Mode Required"),
			message: __("Generate Demo Data is only available in developer mode."),
			indicator: "red",
		});
		return;
	}

	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Generate Demo Data"),
		single_column: true,
	});

	new workforceos.GenerateDemoData(page);
};

workforceos.GenerateDemoData = class GenerateDemoData {
	constructor(page) {
		this.page = page;
		this.generate_options = [];
		this.clear_options = [];
		this.make_layout();
		this.load_options();
	}

	make_layout() {
		this.page.main.html(`
			<div class="demo-data-page margin-top">
				<p class="text-muted">
					${__(
						"Select the doctypes to create or clear. Only demo WorkforceOS records are affected."
					)}
				</p>

				<div class="demo-data-section margin-top">
					<div class="demo-data-section-header">
						<h5>${__("Generate")}</h5>
						<div class="demo-data-select-actions">
							<button type="button" class="btn btn-xs btn-default btn-select-all-generate">
								${__("Select All")}
							</button>
							<button type="button" class="btn btn-xs btn-default btn-clear-all-generate">
								${__("Clear All")}
							</button>
						</div>
					</div>
					<div class="demo-data-checkboxes demo-generate-checkboxes"></div>
					<button class="btn btn-primary btn-generate-demo margin-top">
						${__("Generate")}
					</button>
				</div>

				<div class="demo-data-section margin-top">
					<div class="demo-data-section-header">
						<h5>${__("Clear Demo Data")}</h5>
						<div class="demo-data-select-actions">
							<button type="button" class="btn btn-xs btn-default btn-select-all-clear">
								${__("Select All")}
							</button>
							<button type="button" class="btn btn-xs btn-default btn-clear-all-clear">
								${__("Clear All")}
							</button>
						</div>
					</div>
					<div class="demo-data-checkboxes demo-clear-checkboxes"></div>
					<button class="btn btn-danger btn-clear-demo margin-top">
						${__("Clear Selected")}
					</button>
				</div>

				<div class="demo-data-results margin-top"></div>
			</div>
		`);

		this.$results = this.page.main.find(".demo-data-results");
		this.$generate_boxes = this.page.main.find(".demo-generate-checkboxes");
		this.$clear_boxes = this.page.main.find(".demo-clear-checkboxes");

		this.page.main.find(".btn-generate-demo").on("click", () => this.generate_demo_data());
		this.page.main.find(".btn-clear-demo").on("click", () => this.clear_demo_data());
		this.page.main
			.find(".btn-select-all-generate")
			.on("click", () => this.set_all_checked(this.$generate_boxes, true));
		this.page.main
			.find(".btn-clear-all-generate")
			.on("click", () => this.set_all_checked(this.$generate_boxes, false));
		this.page.main
			.find(".btn-select-all-clear")
			.on("click", () => this.set_all_checked(this.$clear_boxes, true));
		this.page.main
			.find(".btn-clear-all-clear")
			.on("click", () => this.set_all_checked(this.$clear_boxes, false));

		this.show_message(__("Loading options..."));
	}

	load_options() {
		frappe.call({
			method: "workforceos.api.demo_data.options",
			callback: (response) => {
				const data = response.message || {};
				this.generate_options = data.generate || [];
				this.clear_options = data.clear || [];
				this.render_checkboxes(this.$generate_boxes, this.generate_options, "generate");
				this.render_checkboxes(this.$clear_boxes, this.clear_options, "clear");
				this.show_message(__("Select entities, then generate or clear demo data."));
			},
			error: (error) => {
				this.render_error(error);
			},
		});
	}

	render_checkboxes($container, options, group) {
		const html = (options || [])
			.map((option) => {
				const key = frappe.utils.escape_html(option.key);
				const label = frappe.utils.escape_html(option.label);
				return `
					<label class="demo-data-checkbox">
						<input type="checkbox" data-group="${group}" value="${key}" checked>
						<span>${label}</span>
					</label>
				`;
			})
			.join("");

		$container.html(html || `<div class="text-muted">${__("No options available.")}</div>`);
	}

	set_all_checked($container, checked) {
		$container.find('input[type="checkbox"]').prop("checked", checked);
	}

	get_selected($container) {
		return $container
			.find('input[type="checkbox"]:checked')
			.map((_, el) => el.value)
			.get();
	}

	generate_demo_data() {
		const entities = this.get_selected(this.$generate_boxes);
		if (!entities.length) {
			frappe.msgprint(__("Select at least one doctype to generate."));
			return;
		}

		frappe.call({
			method: "workforceos.api.demo_data.generate",
			args: { entities },
			freeze: true,
			freeze_message: __("Generating demo data..."),
			callback: (response) => {
				this.render_summary(__("Demo data generated successfully."), response.message, "green");
			},
			error: (error) => {
				this.render_error(error);
			},
		});
	}

	clear_demo_data() {
		const entities = this.get_selected(this.$clear_boxes);
		if (!entities.length) {
			frappe.msgprint(__("Select at least one doctype to clear."));
			return;
		}

		frappe.confirm(
			__("This will delete selected demo WorkforceOS records. Continue?"),
			() => {
				frappe.call({
					method: "workforceos.api.demo_data.clear",
					args: { entities },
					freeze: true,
					freeze_message: __("Clearing demo data..."),
					callback: (response) => {
						this.render_summary(
							__("Demo data cleared successfully."),
							response.message,
							"orange"
						);
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
				const label = key.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
				return `<tr><td>${frappe.utils.escape_html(label)}</td><td>${value}</td></tr>`;
			})
			.join("");

		this.$results.html(`
			<div class="indicator ${indicator}">${frappe.utils.escape_html(title)}</div>
			<table class="table table-bordered margin-top">
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
				<pre class="demo-data-error">${frappe.utils.escape_html(message)}</pre>
			</div>
		`);
	}
};
