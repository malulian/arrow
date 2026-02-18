// Copyright (c) 2026, osher and contributors
// For license information, please see license.txt

frappe.ui.form.on("AMP Chapter", {
	refresh(frm) {
		// Show chapter info
		if (frm.doc.revision) {
			frm.dashboard.set_headline(
				`<span class="indicator-pill blue">
					<span>Revision ${frm.doc.revision}</span>
				</span>`
			);
		}

		if (!frm.is_new()) {
			// Preview chapter button
			frm.add_custom_button(__("Preview Chapter"), function () {
				frappe.call({
					method: "arrow.amp.amp_pdf_generator.preview_chapter",
					args: { chapter_name: frm.doc.name },
					freeze: true,
					freeze_message: __("Generating preview..."),
					callback: function (r) {
						if (r.message) {
							let w = window.open();
							w.document.write(r.message);
							w.document.close();
						}
					},
				});
			}, __("Actions"));

			// Add task note
			frm.add_custom_button(__("Add Task Note"), function () {
				frappe.new_doc("AMP Task Note", {
					amp_document: frm.doc.amp_document,
					chapter: frm.doc.name,
				});
			}, __("Actions"));

			// Show task count for table-type chapters
			let task_types = ["Task Table", "Component Table", "Checklist"];
			if (task_types.includes(frm.doc.content_type)) {
				let count = (frm.doc.chapter_tasks || []).length;
				frm.dashboard.add_indicator(
					__("Tasks: {0}", [count]),
					"blue"
				);
			}
		}
	},

	content_type(frm) {
		// Set header style based on section type
		if (frm.doc.section_type === "Report") {
			frm.set_value("header_style", "Report");
		} else {
			frm.set_value("header_style", "Preface");
		}
	},

	section_type(frm) {
		if (frm.doc.section_type === "Report") {
			frm.set_value("header_style", "Report");
		} else {
			frm.set_value("header_style", "Preface");
		}
	},
});
