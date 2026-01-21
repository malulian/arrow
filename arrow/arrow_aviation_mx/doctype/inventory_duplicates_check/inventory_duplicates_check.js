frappe.ui.form.on('Inventory Duplicates Check', {
    refresh: function (frm) {
        frm.disable_save();

        // Style improvements
        frm.get_field('results_html').$wrapper.css('min-height', '200px');
    },

    run_check_button: function (frm) {
        frappe.call({
            method: 'arrow.arrow_aviation_mx.doctype.inventory_duplicates_check.inventory_duplicates_check.run_duplicates_check',
            freeze: true,
            freeze_message: __('Checking for duplicates...'),
            callback: function (r) {
                if (r.message) {
                    frm.get_field('results_html').$wrapper.html(r.message.html);
                    frm.refresh_field('last_run');

                    // Show summary
                    let summary = r.message.summary;
                    if (summary.duplicates > 0 || summary.cross_matches > 0) {
                        frappe.show_alert({
                            message: __(`Found ${summary.duplicates} duplicate groups and ${summary.cross_matches} cross-matches`),
                            indicator: 'orange'
                        });
                    } else {
                        frappe.show_alert({
                            message: __('No duplicates found!'),
                            indicator: 'green'
                        });
                    }
                }
            }
        });
    }
});
