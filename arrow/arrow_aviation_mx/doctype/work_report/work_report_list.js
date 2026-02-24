// Add a custom button to Work Report List to fix inventory deduction
frappe.listview_settings['Work Report'] = {
	onload: function(listview) {
		// Add a custom button to fix inventory for all submitted reports
		listview.page.add_inner_button(__('Fix Inventory for Submitted Reports'), function() {
			frappe.confirm(
				__('This will check all submitted Work Reports and deduct parts from inventory if not already done. Continue?'),
				function() {
					// Yes - run the fix
					frappe.call({
						method: 'arrow.arrow_aviation_mx.doctype.work_report.work_report.fix_inventory_for_submitted_reports',
						freeze: true,
						freeze_message: __('Fixing inventory deductions...'),
						callback: function(r) {
							if (r.message && r.message.success) {
								let msg = `
									<div>
										<h4>תיקון המלאי הושלם בהצלחה</h4>
										<ul>
											<li><strong>דוחות שתוקנו:</strong> ${r.message.reports_fixed}</li>
											<li><strong>פריטים שנוכו:</strong> ${r.message.parts_deducted}</li>
											<li><strong>סה"כ דוחות שנבדקו:</strong> ${r.message.total_reports_checked}</li>
										</ul>
										${r.message.errors.length > 0 ? 
											'<p><strong>שגיאות:</strong></p><ul>' + 
											r.message.errors.map(e => '<li>' + e + '</li>').join('') + 
											'</ul>' : ''}
									</div>
								`;
								frappe.msgprint({
									title: __('תיקון המלאי הושלם'),
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
		});
	}
};
