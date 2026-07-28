// Copyright (c) 2026, osher and contributors
// For license information, please see license.txt

frappe.ui.form.on("AMP Revision", {
	refresh(frm) {
		// Status indicator
		if (frm.doc.status === "Approved") {
			frm.dashboard.set_headline(
				'<span class="indicator-pill green"><span>Approved</span></span>'
			);
		} else if (frm.doc.status === "Under Review") {
			frm.dashboard.set_headline(
				'<span class="indicator-pill orange"><span>Under Review</span></span>'
			);
		} else {
			frm.dashboard.set_headline(
				'<span class="indicator-pill red"><span>Draft</span></span>'
			);
		}

		if (!frm.is_new() && frm.doc.status !== "Approved") {
			// Approve Revision button
			frm.add_custom_button(__("Approve Revision"), function () {
				frappe.confirm(
					__("Are you sure you want to approve Revision {0}? This will update all affected chapters.", [frm.doc.revision_number]),
					function () {
						frappe.call({
							method: "approve_revision",
							doc: frm.doc,
							freeze: true,
							freeze_message: __("Approving revision..."),
							callback: function () {
								frm.reload_doc();
							},
						});
					}
				);
			});

			// Submit for Review button
			if (frm.doc.status === "Draft") {
				frm.add_custom_button(__("Submit for Review"), function () {
					frm.set_value("status", "Under Review");
					frm.save();
				});
			}
		}
	},
});