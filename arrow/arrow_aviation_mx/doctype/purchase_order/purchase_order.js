frappe.ui.form.on('Purchase Order', {
    refresh: function (frm) {
        // Set status indicator
        frm.page.set_indicator(frm.doc.status, get_status_color(frm.doc.status));

        // Show quotes warning
        update_quotes_warning(frm);

        // Add workflow buttons based on status
        add_workflow_buttons(frm);

        // Add PDF buttons
        if (!frm.is_new() && frm.doc.status !== 'New Order') {
            frm.add_custom_button(__('Generate PO PDF'), function () {
                generate_po_pdf(frm);
            }, __('Actions'));

            if (frm.doc.po_pdf) {
                frm.add_custom_button(__('Send PO to Supplier'), function () {
                    send_po_to_supplier(frm);
                }, __('Actions'));
            }
        }
    },

    validate: function (frm) {
        // Validate only one quote is selected
        let selected_count = 0;
        (frm.doc.quotes || []).forEach(q => {
            if (q.is_selected) selected_count++;
        });

        if (selected_count > 1) {
            frappe.throw(__('Only one quote can be selected'));
        }
    },

    status: function (frm) {
        frm.trigger('refresh');
    },

    approved_by_user: function (frm) {
        // When approver is set and status is New Order, suggest moving to Awaiting Approval
        if (frm.doc.approved_by_user && frm.doc.status === 'New Order') {
            frappe.confirm(
                'Move order to "Awaiting Approval" status?',
                function () {
                    frm.set_value('status', 'Awaiting Approval');
                }
            );
        }
    }
});

frappe.ui.form.on('Price Quote', {
    is_selected: function (frm, cdt, cdn) {
        // Ensure only one quote is selected
        let row = locals[cdt][cdn];
        if (row.is_selected) {
            frm.doc.quotes.forEach(q => {
                if (q.name !== cdn && q.is_selected) {
                    frappe.model.set_value(q.doctype, q.name, 'is_selected', 0);
                }
            });
        }
        frm.refresh_field('quotes');
    },

    supplier: function (frm, cdt, cdn) {
        // Check if supplier is approved
        let row = locals[cdt][cdn];
        if (row.supplier) {
            frappe.db.get_value('Supplier', row.supplier, 'is_approved', (r) => {
                if (r && !r.is_approved) {
                    frappe.show_alert({
                        message: __('Warning: This supplier is not approved'),
                        indicator: 'orange'
                    });
                }
            });
        }
    }
});

function get_status_color(status) {
    const colors = {
        'New Order': 'blue',
        'Awaiting Approval': 'orange',
        'Approved': 'green',
        'PO Issued': 'purple',
        'Awaiting Tracking': 'yellow',
        'In Transit': 'cyan',
        'Received': 'blue',
        'Awaiting Inspection': 'orange',
        'Awaiting Invoice': 'pink',
        'Completed': 'green',
        'Cancelled': 'red'
    };
    return colors[status] || 'gray';
}

function update_quotes_warning(frm) {
    let warning_html = '';
    let quotes_count = (frm.doc.quotes || []).length;

    if (quotes_count < 3 && quotes_count > 0) {
        warning_html = `<div class="alert alert-warning">
			<i class="fa fa-exclamation-triangle"></i> 
			Warning: Only ${quotes_count} quote(s). It's recommended to have at least 3 quotes.
		</div>`;
    } else if (quotes_count === 0 && !frm.is_new()) {
        warning_html = `<div class="alert alert-warning">
			<i class="fa fa-exclamation-triangle"></i> 
			No quotes added yet. Please add price quotes before proceeding.
		</div>`;
    }

    frm.get_field('quotes_warning_html').$wrapper.html(warning_html);
}

function add_workflow_buttons(frm) {
    if (frm.is_new()) return;

    switch (frm.doc.status) {
        case 'New Order':
            frm.add_custom_button(__('Submit for Approval'), function () {
                if (!frm.doc.approved_by_user) {
                    frappe.prompt({
                        label: 'Approver',
                        fieldname: 'approver',
                        fieldtype: 'Link',
                        options: 'User',
                        reqd: 1
                    }, (values) => {
                        frm.set_value('approved_by_user', values.approver);
                        frm.set_value('status', 'Awaiting Approval');
                        frm.save();
                    }, __('Select Approver'));
                } else {
                    frm.set_value('status', 'Awaiting Approval');
                    frm.save();
                }
            }, __('Workflow'));
            break;

        case 'Awaiting Approval':
            frm.add_custom_button(__('Approve Order'), function () {
                // Check if a quote is selected
                let has_selected = frm.doc.quotes.some(q => q.is_selected);
                if (!has_selected && frm.doc.quotes.length > 0) {
                    frappe.throw(__('Please select a quote before approving'));
                    return;
                }
                frm.set_value('status', 'Approved');
                frm.save().then(() => {
                    frappe.confirm(
                        'Generate PO PDF now?',
                        function () { generate_po_pdf(frm); }
                    );
                });
            }, __('Workflow'));

            frm.add_custom_button(__('Reject'), function () {
                frm.set_value('status', 'Cancelled');
                frm.save();
            }, __('Workflow'));
            break;

        case 'Approved':
            frm.add_custom_button(__('Issue PO'), function () {
                frm.set_value('status', 'PO Issued');
                frm.set_value('po_issue_date', frappe.datetime.get_today());
                frm.save();
            }, __('Workflow'));
            break;

        case 'PO Issued':
            frm.add_custom_button(__('Awaiting Tracking'), function () {
                frm.set_value('status', 'Awaiting Tracking');
                frm.save();
            }, __('Workflow'));
            break;

        case 'Awaiting Tracking':
            frm.add_custom_button(__('Mark In Transit'), function () {
                if (!frm.doc.tracking_number) {
                    frappe.prompt({
                        label: 'Tracking Number',
                        fieldname: 'tracking_number',
                        fieldtype: 'Data'
                    }, (values) => {
                        frm.set_value('tracking_number', values.tracking_number);
                        frm.set_value('status', 'In Transit');
                        frm.save();
                    }, __('Enter Tracking'));
                } else {
                    frm.set_value('status', 'In Transit');
                    frm.save();
                }
            }, __('Workflow'));
            break;

        case 'In Transit':
            frm.add_custom_button(__('Mark Received'), function () {
                frm.set_value('status', 'Received');
                frm.set_value('received_date', frappe.datetime.get_today());
                frm.save();
            }, __('Workflow'));
            break;

        case 'Received':
            frm.add_custom_button(__('Send to Inspection'), function () {
                if (!frm.doc.inspection_user) {
                    frappe.prompt({
                        label: 'Inspector',
                        fieldname: 'inspector',
                        fieldtype: 'Link',
                        options: 'User',
                        reqd: 1
                    }, (values) => {
                        frm.set_value('inspection_user', values.inspector);
                        frm.set_value('status', 'Awaiting Inspection');
                        frm.save();
                    }, __('Select Inspector'));
                } else {
                    frm.set_value('status', 'Awaiting Inspection');
                    frm.save();
                }
            }, __('Workflow'));
            break;

        case 'Awaiting Inspection':
            frm.add_custom_button(__('Pass Inspection'), function () {
                frm.set_value('inspection_passed', 1);
                frm.set_value('status', 'Awaiting Invoice');
                frm.save();
            }, __('Workflow'));

            frm.add_custom_button(__('Fail Inspection'), function () {
                frappe.prompt({
                    label: 'Inspection Notes',
                    fieldname: 'notes',
                    fieldtype: 'Text'
                }, (values) => {
                    frm.set_value('inspection_notes', values.notes);
                    frm.set_value('inspection_passed', 0);
                    frm.save();
                }, __('Enter Inspection Notes'));
            }, __('Workflow'));
            break;

        case 'Awaiting Invoice':
            frm.add_custom_button(__('Complete Order'), function () {
                if (!frm.doc.invoice_attachment) {
                    frappe.confirm(
                        'No invoice attached. Complete anyway?',
                        function () {
                            frm.set_value('status', 'Completed');
                            frm.save();
                        }
                    );
                } else {
                    frm.set_value('status', 'Completed');
                    frm.save();
                }
            }, __('Workflow'));
            break;
    }

    // Cancel button for most statuses
    if (!['Completed', 'Cancelled'].includes(frm.doc.status)) {
        frm.add_custom_button(__('Cancel Order'), function () {
            frappe.confirm(
                'Are you sure you want to cancel this order?',
                function () {
                    frm.set_value('status', 'Cancelled');
                    frm.save();
                }
            );
        }, __('Workflow'));
    }
}

function generate_po_pdf(frm) {
    frappe.call({
        method: 'arrow.arrow_aviation_mx.doctype.purchase_order.purchase_order.generate_po_pdf',
        args: { po_name: frm.doc.name },
        freeze: true,
        freeze_message: __('Generating PDF...'),
        callback: function (r) {
            if (r.message && r.message.success) {
                frappe.show_alert({
                    message: __('PO PDF generated successfully'),
                    indicator: 'green'
                });
                frm.reload_doc();
            } else {
                frappe.msgprint(r.message.message || 'Error generating PDF');
            }
        }
    });
}

function send_po_to_supplier(frm) {
    frappe.call({
        method: 'arrow.arrow_aviation_mx.doctype.purchase_order.purchase_order.send_po_to_supplier',
        args: { po_name: frm.doc.name },
        freeze: true,
        freeze_message: __('Sending email...'),
        callback: function (r) {
            if (r.message && r.message.success) {
                frappe.show_alert({
                    message: r.message.message,
                    indicator: 'green'
                });
            } else {
                frappe.msgprint(r.message.message || 'Error sending email');
            }
        }
    });
}
