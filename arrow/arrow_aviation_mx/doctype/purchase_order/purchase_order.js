frappe.ui.form.on('Purchase Order', {
    refresh: function (frm) {
        // Set status indicator
        frm.page.set_indicator(frm.doc.status, get_status_color(frm.doc.status));

        // Show quotes warning (inline, no popups)
        update_quotes_warning(frm);

        // Add workflow buttons based on status
        add_workflow_buttons(frm);

        // Add action buttons (PDF, RFQ)
        add_action_buttons(frm);
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
        let row = locals[cdt][cdn];
        if (row.supplier) {
            frappe.db.get_value('Supplier', row.supplier, 'is_approved', r => {
                if (r && !r.is_approved) {
                    frappe.show_alert({
                        message: __('Note: This supplier is not approved'),
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
        'Ordered': 'purple',
        'Sent': 'cyan',
        'Received': 'blue',
        'Pending Inspection': 'yellow',
        'Completed': 'green',
        'Cancelled': 'red'
    };
    return colors[status] || 'gray';
}

function update_quotes_warning(frm) {
    let warning_html = '';
    let quotes_count = (frm.doc.quotes || []).length;

    if (quotes_count > 0 && quotes_count < 3) {
        warning_html = `<div class="text-muted" style="padding: 8px 0; font-size: 12px;">
            <i class="fa fa-info-circle"></i>
            ${quotes_count} quote(s) entered. It is recommended to have at least 3 quotes.
        </div>`;
    } else if (quotes_count === 0 && !frm.is_new()) {
        warning_html = `<div class="text-muted" style="padding: 8px 0; font-size: 12px;">
            <i class="fa fa-info-circle"></i>
            No quotes added yet. Add at least one price quote before submitting for approval.
        </div>`;
    }

    if (frm.get_field('quotes_warning_html')) {
        frm.get_field('quotes_warning_html').$wrapper.html(warning_html);
    }
}

function add_workflow_buttons(frm) {
    if (frm.is_new()) return;

    switch (frm.doc.status) {
        case 'New Order':
            // Step 2: Submit for Approval (requires at least 1 quote)
            frm.add_custom_button(__('Submit for Approval'), function () {
                let quotes_count = (frm.doc.quotes || []).length;
                if (quotes_count === 0) {
                    frappe.msgprint(__('Please add at least one price quote before submitting for approval.'));
                    return;
                }
                frm.set_value('status', 'Awaiting Approval');
                frm.save();
            }, __('Workflow'));
            break;

        case 'Awaiting Approval':
            // Step 3: Approve (select a quote first)
            frm.add_custom_button(__('Approve Order'), function () {
                let has_selected = (frm.doc.quotes || []).some(q => q.is_selected);
                if (!has_selected && (frm.doc.quotes || []).length > 0) {
                    frappe.msgprint(__('Please select a quote before approving.'));
                    return;
                }
                frm.set_value('status', 'Approved');
                frm.save();
            }, __('Workflow'));

            frm.add_custom_button(__('Reject'), function () {
                frappe.confirm(
                    __('Are you sure you want to reject this order?'),
                    function () {
                        frm.set_value('status', 'Cancelled');
                        frm.save();
                    }
                );
            }, __('Workflow'));
            break;

        case 'Approved':
            // Step 4: Mark as Ordered
            frm.add_custom_button(__('Mark as Ordered'), function () {
                frm.set_value('status', 'Ordered');
                if (!frm.doc.po_issue_date) {
                    frm.set_value('po_issue_date', frappe.datetime.get_today());
                }
                frm.save();
            }, __('Workflow'));
            break;

        case 'Ordered':
            // Step 4: Mark as Sent (manual)
            frm.add_custom_button(__('Mark as Sent'), function () {
                frm.set_value('status', 'Sent');
                frm.save();
            }, __('Workflow'));
            break;

        case 'Sent':
            // Step 5: Mark as Received
            frm.add_custom_button(__('Mark as Received'), function () {
                if (!frm.doc.received_date) {
                    frm.set_value('received_date', frappe.datetime.get_today());
                }
                frm.set_value('status', 'Received');
                frm.save();
            }, __('Workflow'));
            break;

        case 'Received':
            // Step 5: Send to Inspection
            frm.add_custom_button(__('Send to Inspection'), function () {
                if (!frm.doc.inspection_user) {
                    frappe.prompt(
                        {
                            label: 'Inspector',
                            fieldname: 'inspector',
                            fieldtype: 'Link',
                            options: 'User',
                            reqd: 1
                        },
                        values => {
                            frm.set_value('inspection_user', values.inspector);
                            frm.set_value('status', 'Pending Inspection');
                            frm.save();
                        },
                        __('Select Inspector')
                    );
                } else {
                    frm.set_value('status', 'Pending Inspection');
                    frm.save();
                }
            }, __('Workflow'));
            break;

        case 'Pending Inspection':
            // Step 5-6: Pass or Fail Inspection
            frm.add_custom_button(__('Pass Inspection'), function () {
                frm.set_value('inspection_passed', 1);
                frm.set_value('status', 'Completed');
                frm.save();
            }, __('Workflow'));

            frm.add_custom_button(__('Fail Inspection'), function () {
                frappe.prompt(
                    {
                        label: 'Inspection Notes',
                        fieldname: 'notes',
                        fieldtype: 'Text'
                    },
                    values => {
                        frm.set_value('inspection_notes', values.notes);
                        frm.set_value('inspection_passed', 0);
                        frm.save();
                    },
                    __('Enter Inspection Notes')
                );
            }, __('Workflow'));
            break;
    }

    // Cancel button for active statuses
    if (!['Completed', 'Cancelled'].includes(frm.doc.status)) {
        frm.add_custom_button(__('Cancel Order'), function () {
            frappe.confirm(__('Are you sure you want to cancel this order?'), function () {
                frm.set_value('status', 'Cancelled');
                frm.save();
            });
        }, __('Workflow'));
    }
}

function add_action_buttons(frm) {
    if (frm.is_new()) return;

    // RFQ PDF generation - available from New Order onwards
    if (['New Order', 'Awaiting Approval'].includes(frm.doc.status)) {
        frm.add_custom_button(__('Generate RFQ PDF'), function () {
            frappe.call({
                method: 'arrow.arrow_aviation_mx.doctype.purchase_order.purchase_order.generate_rfq_pdf',
                args: { po_name: frm.doc.name },
                freeze: true,
                freeze_message: __('Generating RFQ PDF...'),
                callback: function (r) {
                    if (r.message && r.message.success) {
                        frappe.show_alert({
                            message: __('RFQ PDF generated'),
                            indicator: 'green'
                        });
                        window.open(r.message.file_url, '_blank');
                    }
                }
            });
        }, __('Actions'));

        // Send RFQ to suppliers
        frm.add_custom_button(__('Send RFQ to Suppliers'), function () {
            send_rfq_dialog(frm);
        }, __('Actions'));
    }

    // PO PDF - available after approval
    if (
        !['New Order', 'Awaiting Approval', 'Cancelled'].includes(frm.doc.status)
    ) {
        frm.add_custom_button(__('Generate PO PDF'), function () {
            frappe.call({
                method: 'arrow.arrow_aviation_mx.doctype.purchase_order.purchase_order.generate_po_pdf',
                args: { po_name: frm.doc.name },
                freeze: true,
                freeze_message: __('Generating PDF...'),
                callback: function (r) {
                    if (r.message && r.message.success) {
                        frappe.show_alert({
                            message: __('PO PDF generated'),
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    }
                }
            });
        }, __('Actions'));

        if (frm.doc.po_pdf) {
            frm.add_custom_button(__('Send PO to Supplier'), function () {
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
                            frappe.msgprint(
                                r.message.message || 'Error sending email'
                            );
                        }
                    }
                });
            }, __('Actions'));
        }
    }
}

function send_rfq_dialog(frm) {
    // Fetch suppliers list
    frappe.call({
        method: 'arrow.arrow_aviation_mx.doctype.purchase_order.purchase_order.get_approved_suppliers_list',
        callback: function (r) {
            if (!r.message || r.message.length === 0) {
                frappe.msgprint(__('No suppliers found. Please add suppliers first.'));
                return;
            }

            let suppliers = r.message;
            let fields = [
                {
                    label: 'Select Suppliers to send RFQ',
                    fieldname: 'info',
                    fieldtype: 'HTML',
                    options:
                        '<p class="text-muted">Select the suppliers you want to send the RFQ to.</p>'
                }
            ];

            suppliers.forEach((sup, idx) => {
                let approved_text = sup.is_approved ? ' [Approved]' : '';
                let email_text = sup.email ? ` (${sup.email})` : ' (no email)';
                fields.push({
                    label: `${sup.supplier_name}${approved_text}${email_text}`,
                    fieldname: `supplier_${idx}`,
                    fieldtype: 'Check',
                    default: sup.is_approved && sup.email ? 1 : 0
                });
            });

            let d = new frappe.ui.Dialog({
                title: 'Send RFQ to Suppliers',
                fields: fields,
                size: 'large',
                primary_action_label: 'Send RFQ',
                primary_action: function (values) {
                    let selected = [];
                    suppliers.forEach((sup, idx) => {
                        if (values[`supplier_${idx}`]) {
                            selected.push(sup.name);
                        }
                    });

                    if (selected.length === 0) {
                        frappe.msgprint(
                            __('Please select at least one supplier.')
                        );
                        return;
                    }

                    d.hide();
                    frappe.call({
                        method: 'arrow.arrow_aviation_mx.doctype.purchase_order.purchase_order.send_rfq_to_suppliers',
                        args: {
                            po_name: frm.doc.name,
                            supplier_names: selected
                        },
                        freeze: true,
                        freeze_message: __('Sending RFQ emails...'),
                        callback: function (r) {
                            if (r.message) {
                                frappe.show_alert({
                                    message: r.message.message,
                                    indicator: r.message.success
                                        ? 'green'
                                        : 'orange'
                                });
                            }
                        }
                    });
                }
            });
            d.show();
        }
    });
}
