// Copyright (c) 2026, osher and contributors
// For license information, please see license.txt

frappe.ui.form.on("AMP Document", {
	refresh(frm) {
		// Status indicator
		if (frm.doc.status === "Approved") {
			frm.dashboard.set_headline(
				`<span class="indicator-pill green">
					<span>Approved — Revision ${frm.doc.current_revision || "0"}</span>
				</span>`
			);
		} else if (frm.doc.status === "Under Review") {
			frm.dashboard.set_headline(
				'<span class="indicator-pill orange"><span>Under Review</span></span>'
			);
		}

		if (!frm.is_new()) {
			// Export PDF button
			frm.add_custom_button(__("Export PDF"), function () {
				frappe.call({
					method: "generate_pdf",
					doc: frm.doc,
					freeze: true,
					freeze_message: __("Generating AMP PDF..."),
					callback: function (r) {
						if (r.message) {
							window.open(r.message);
						}
					},
				});
			}, __("Actions"));

			// Create New Revision button
			frm.add_custom_button(__("Create New Revision"), function () {
				create_revision_dialog(frm);
			}, __("Actions"));

			// Add Task Note button
			frm.add_custom_button(__("Add Task Note"), function () {
				frappe.new_doc("AMP Task Note", {
					amp_document: frm.doc.name,
				});
			}, __("Actions"));

			// Update Revision Info button
			frm.add_custom_button(__("Update Revision Info"), function () {
				frappe.call({
					method: "update_revision_info",
					doc: frm.doc,
					callback: function () {
						frm.reload_doc();
						frappe.show_alert({
							message: __("Revision info updated"),
							indicator: "green",
						});
					},
				});
			}, __("Actions"));

			// Show linked records in dashboard
			frm.dashboard.add_indicator(
				__("Chapters: {0}", [frm.doc.__onload?.chapter_count || "..."]),
				"blue"
			);
		}
	},

	aircraft_type(frm) {
		if (frm.doc.aircraft_type && !frm.doc.document_number) {
			frm.set_value("document_number", "AMP " + frm.doc.aircraft_type);
		}
	},
});


function create_revision_dialog(frm) {
	let d = new frappe.ui.Dialog({
		title: __("Create New Revision"),
		fields: [
			{
				fieldname: "revision_type",
				fieldtype: "Select",
				label: "Revision Type",
				options: "Regular\nTemporary",
				default: "Regular",
				reqd: 1,
			},
			{
				fieldname: "revision_number",
				fieldtype: "Data",
				label: "Revision Number",
				description: "Auto-suggested. Override if needed.",
				reqd: 1,
			},
			{
				fieldname: "author",
				fieldtype: "Data",
				label: "Author",
				default: frappe.session.user_fullname,
				reqd: 1,
			},
			{
				fieldname: "revision_date",
				fieldtype: "Date",
				label: "Revision Date",
				default: frappe.datetime.nowdate(),
				reqd: 1,
			},
			{
				fieldname: "highlights",
				fieldtype: "Long Text",
				label: "Revision Highlights",
				description: "Describe what changed in this revision",
			},
		],
		primary_action_label: __("Create"),
		primary_action(values) {
			frappe.call({
				method: "frappe.client.insert",
				args: {
					doc: {
						doctype: "AMP Revision",
						amp_document: frm.doc.name,
						revision_type: values.revision_type,
						revision_number: values.revision_number,
						author: values.author,
						revision_date: values.revision_date,
						highlights: values.highlights,
						status: "Draft",
					},
				},
				callback: function (r) {
					if (r.message) {
						d.hide();
						frappe.set_route("Form", "AMP Revision", r.message.name);
						frappe.show_alert({
							message: __("Revision {0} created", [values.revision_number]),
							indicator: "green",
						});
					}
				},
			});
		},
	});

	// Auto-suggest next revision number
	let current = parseInt(frm.doc.current_revision) || 0;
	d.set_value("revision_number", String(current + 1));

	d.fields_dict.revision_type.$input.on("change", function () {
		let type = d.get_value("revision_type");
		if (type === "Temporary") {
			d.set_value("revision_number", "TR " + String(current + 1));
		} else {
			d.set_value("revision_number", String(current + 1));
		}
	});

	d.show();
}
