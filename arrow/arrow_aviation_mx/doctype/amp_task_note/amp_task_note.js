// Copyright (c) 2026, osher and contributors
// For license information, please see license.txt

frappe.ui.form.on("AMP Task Note", {
	refresh(frm) {
		// Status indicator
		if (frm.doc.status === "Active") {
			frm.dashboard.set_headline(
				'<span class="indicator-pill green"><span>Active</span></span>'
			);
		} else if (frm.doc.status === "Superseded") {
			frm.dashboard.set_headline(
				'<span class="indicator-pill orange"><span>Superseded</span></span>'
			);
		} else {
			frm.dashboard.set_headline(
				'<span class="indicator-pill red"><span>Removed</span></span>'
			);
		}
	},

	amp_document(frm) {
		// Filter chapters by selected AMP Document
		frm.set_query("chapter", function () {
			return {
				filters: {
					amp_document: frm.doc.amp_document,
				},
			};
		});
	},
});
