// Purchase Order Form View — simplified, quick actions

frappe.ui.form.on('Purchase Order', {
    refresh: function (frm) {
        // Set status indicator
        const statusColors = {
            'New': 'blue',
            'Ordered': 'purple',
            'Received': 'green',
            'Core Returned': 'darkgrey',
            'Cancelled': 'red'
        };
        if (statusColors[frm.doc.status]) {
            frm.page.set_indicator(frm.doc.status, statusColors[frm.doc.status]);
        }

        // Add quick action buttons
        add_quick_actions(frm);
    },

    urgency: function(frm) {
        if (frm.doc.urgency === 'AOG') {
            frm.page.set_indicator('🚨 AOG', 'red');
        }
    },

    status: function (frm) {
        frm.trigger('refresh');
    },

    // Auto-set received_date when status changes to Received
    status: function(frm) {
        if (frm.doc.status === 'Received' && !frm.doc.received_date) {
            frm.set_value('received_date', frappe.datetime.get_today());
        }
        if (frm.doc.status === 'Core Returned' && !frm.doc.core_return_date) {
            frm.set_value('core_return_date', frappe.datetime.get_today());
        }
    }
});

function add_quick_actions(frm) {
    frm.page.clear_custom_buttons();

    if (frm.doc.__islocal) return;

    const status = frm.doc.status;

    if (status === 'New') {
        frm.add_custom_button(__('📦 Mark as Ordered'), function() {
            frappe.prompt(
                [
                    {fieldname: 'supplier', fieldtype: 'Link', options: 'Supplier', label: 'Supplier (optional)', reqd: 0},
                    {fieldname: 'notes', fieldtype: 'Text', label: 'Notes (optional)', reqd: 0}
                ],
                function(values) {
                    frappe.call({
                        method: 'arrow.arrow_aviation_mx.doctype.purchase_order.purchase_order.mark_ordered',
                        args: {
                            po_name: frm.doc.name,
                            supplier: values.supplier || undefined,
                            notes: values.notes || undefined
                        },
                        callback: function(r) {
                            if (r.message && r.message.success) frm.reload_doc();
                        }
                    });
                },
                'Mark as Ordered',
                'Confirm'
            );
        }).addClass('btn-primary');
    }

    if (status === 'Ordered') {
        frm.add_custom_button(__('✅ Mark as Received'), function() {
            frappe.call({
                method: 'arrow.arrow_aviation_mx.doctype.purchase_order.purchase_order.mark_received',
                args: { po_name: frm.doc.name },
                callback: function(r) {
                    if (r.message && r.message.success) frm.reload_doc();
                }
            });
        }).addClass('btn-success');
    }

    if (status === 'Received') {
        frm.add_custom_button(__('♻️ Core Return'), function() {
            frappe.prompt(
                [
                    {fieldname: 'core_return_supplier', fieldtype: 'Link', options: 'Supplier', label: 'Returned to Supplier', reqd: 1},
                    {fieldname: 'core_return_date', fieldtype: 'Date', label: 'Return Date', reqd: 1, default: frappe.datetime.get_today()},
                    {fieldname: 'core_return_notes', fieldtype: 'Text', label: 'Notes', reqd: 0}
                ],
                function(values) {
                    frappe.call({
                        method: 'arrow.arrow_aviation_mx.doctype.purchase_order.purchase_order.mark_core_returned',
                        args: {
                            po_name: frm.doc.name,
                            core_return_supplier: values.core_return_supplier,
                            core_return_date: values.core_return_date,
                            core_return_notes: values.core_return_notes
                        },
                        callback: function(r) {
                            if (r.message && r.message.success) frm.reload_doc();
                        }
                    });
                },
                'Core Return',
                'Confirm'
            );
        });
    }

    if (status !== 'Cancelled' && status !== 'Core Returned') {
        frm.add_custom_button(__('✖ Cancel'), function() {
            frappe.confirm('Cancel PO ' + frm.doc.name + '?', function() {
                frappe.call({
                    method: 'arrow.arrow_aviation_mx.doctype.purchase_order.purchase_order.cancel_order',
                    args: { po_name: frm.doc.name },
                    callback: function(r) {
                        if (r.message && r.message.success) frm.reload_doc();
                    }
                });
            });
        }).addClass('btn-danger');
    }
}
