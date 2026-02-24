// Add custom buttons to Work Report List
frappe.listview_settings['Work Report'] = {
	onload: function(listview) {
		// Button 1: Submit Draft Reports & Deduct Inventory
		listview.page.add_inner_button(__('Submit All Draft Reports'), function() {
			frappe.confirm(
				__('זה יבצע Submit לכל הדוחות ה-Draft שיש להם פריטים וינכה מהמלאי. להמשיך?'),
				function() {
					frappe.call({
						method: 'arrow.arrow_aviation_mx.doctype.work_report.work_report.fix_inventory_for_submitted_reports',
						args: {
							submit_drafts: true
						},
						freeze: true,
						freeze_message: __('מבצע Submit ומנכה מהמלאי...'),
						callback: function(r) {
							if (r.message && r.message.success) {
								let msg = `
									<div style="text-align: right; direction: rtl;">
										<h4>התהליך הושלם בהצלחה!</h4>
										<ul>
											<li><strong>דוחות שעברו Submit:</strong> ${r.message.reports_submitted}</li>
											<li><strong>דוחות שתוקנו:</strong> ${r.message.reports_fixed}</li>
											<li><strong>פריטים שנוכו מהמלאי:</strong> ${r.message.parts_deducted}</li>
											<li><strong>סה"כ דוחות שנבדקו:</strong> ${r.message.total_reports_checked}</li>
										</ul>
										${r.message.errors.length > 0 ? 
											'<p><strong>שגיאות:</strong></p><ul>' + 
											r.message.errors.map(e => '<li>' + e + '</li>').join('') + 
											'</ul>' : '<p style="color: green;">✓ לא היו שגיאות</p>'}
									</div>
								`;
								frappe.msgprint({
									title: __('הושלם בהצלחה'),
									indicator: 'green',
									message: msg
								});
								listview.refresh();
							} else {
								frappe.msgprint(__('Failed to process reports'));
							}
						}
					});
				}
			);
		}, __('Actions'));

		// Button 2: Fix inventory for already submitted reports
		listview.page.add_inner_button(__('Fix Inventory (Submitted Only)'), function() {
			frappe.confirm(
				__('זה יתקן ניכוי מלאי לדוחות שכבר עברו Submit. להמשיך?'),
				function() {
					frappe.call({
						method: 'arrow.arrow_aviation_mx.doctype.work_report.work_report.fix_inventory_for_submitted_reports',
						args: {
							submit_drafts: false
						},
						freeze: true,
						freeze_message: __('מתקן ניכוי מלאי...'),
						callback: function(r) {
							if (r.message && r.message.success) {
								let msg = `
									<div style="text-align: right; direction: rtl;">
										<h4>תיקון המלאי הושלם</h4>
										<ul>
											<li><strong>דוחות שתוקנו:</strong> ${r.message.reports_fixed}</li>
											<li><strong>פריטים שנוכו:</strong> ${r.message.parts_deducted}</li>
											<li><strong>סה"כ דוחות שנבדקו:</strong> ${r.message.total_reports_checked}</li>
										</ul>
										${r.message.errors.length > 0 ? 
											'<p><strong>שגיאות:</strong></p><ul>' + 
											r.message.errors.map(e => '<li>' + e + '</li>').join('') + 
											'</ul>' : '<p style="color: green;">✓ לא היו שגיאות</p>'}
									</div>
								`;
								frappe.msgprint({
									title: __('תיקון הושלם'),
									indicator: 'green',
									message: msg
								});
								listview.refresh();
							} else {
								frappe.msgprint(__('Failed to fix inventory'));
							}
						}
					});
				}
			);
		}, __('Actions'));
	}
};
