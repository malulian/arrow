frappe.ui.form.on('Inventory Item', {
    part_number: function(frm) {
        if (frm.doc.part_number && frm.doc.part_number.trim() !== "") {
            let filters = { part_number: frm.doc.part_number.trim() };
            if (!frm.is_new()) {
                filters.name = ['!=', frm.doc.name];
            }
            frappe.db.get_list('Inventory Item', {
                filters: filters,
                fields: ['name'],
                limit: 1
            }).then(res => {
                if (res && res.length > 0) {
                    frappe.msgprint({
                        title: __('Duplicate Part Number'),
                        indicator: 'orange',
                        message: __(`A record with this Part Number already exists (e.g., <b>${res[0].name}</b>). Multiple records with the same Part Number are allowed, but please verify this is intentional.`)
                    });
                }
            }).catch(err => {
                console.error("Error checking part number:", err);
            });
        }
    },

    refresh: function (frm) {

        // Set status indicator
        set_status_indicator(frm);

        // Add action buttons
        if (!frm.is_new()) {
            frm.add_custom_button(__('Receive Items'), function () {
                receive_items_dialog(frm);
            }, __('Actions'));

            frm.add_custom_button(__('Withdraw Items'), function () {
                withdraw_items_dialog(frm);
            }, __('Actions'));

            frm.add_custom_button(__('Adjust Quantity'), function () {
                adjust_quantity_dialog(frm);
            }, __('Actions'));

            frm.add_custom_button(__('View Transactions'), function () {
                frappe.set_route('List', 'Inventory Transaction', {
                    inventory_item: frm.doc.name
                });
            }, __('Actions'));
        }

        // Show pending receiving inspection warning
        if (frm.doc.pending_receiving_inspection) {
            let inspection_msg = 'Pending Receiving Inspection';
            if (frm.doc.quantity > 0) {
                inspection_msg += ' (IN STOCK)';
            }
            frm.dashboard.add_comment(inspection_msg, 'orange', true);

            frm.add_custom_button(__('Complete Inspection'), function () {
                frm.set_value('pending_receiving_inspection', 0);
                frm.save();
                frappe.show_alert({
                    message: __('Receiving inspection completed'),
                    indicator: 'green'
                });
            }, __('Actions'));
        }

        // Show expiry warning
        if (frm.doc.expiry_date) {
            let expiry = frappe.datetime.str_to_obj(frm.doc.expiry_date);
            let today = frappe.datetime.str_to_obj(frappe.datetime.get_today());
            let days_until = frappe.datetime.get_diff(expiry, today);

            if (days_until < 0) {
                frm.dashboard.add_comment('This item has EXPIRED!', 'red', true);
            } else if (days_until <= 30) {
                frm.dashboard.add_comment(`Expires in ${days_until} days`, 'orange', true);
            }
        }
    },

    quantity: function (frm) {
        update_status_preview(frm);
    },

    expiry_date: function (frm) {
        update_status_preview(frm);
    }
});

function set_status_indicator(frm) {
    const colors = {
        'Active': 'green',
        'Low Stock': 'orange',
        'Out of Stock': 'red',
        'Expired': 'gray'
    };
    frm.page.set_indicator(frm.doc.status, colors[frm.doc.status] || 'blue');
}

function update_status_preview(frm) {
    let status = 'Active';

    if (frm.doc.expiry_date) {
        let expiry = frappe.datetime.str_to_obj(frm.doc.expiry_date);
        let today = frappe.datetime.str_to_obj(frappe.datetime.get_today());
        if (expiry < today) {
            status = 'Expired';
        }
    }

    if (status !== 'Expired') {
        if (frm.doc.quantity <= 0) {
            status = 'Out of Stock';
        } else if (frm.doc.minimum_quantity && frm.doc.quantity <= frm.doc.minimum_quantity) {
            status = 'Low Stock';
        }
    }

    frm.set_value('status', status);
}

function receive_items_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: 'Receive Items',
        fields: [
            {
                label: 'Quantity to Receive',
                fieldname: 'quantity',
                fieldtype: 'Float',
                reqd: 1
            },
            {
                label: 'Notes',
                fieldname: 'notes',
                fieldtype: 'Small Text'
            }
        ],
        primary_action_label: 'Receive',
        primary_action: function (values) {
            frappe.call({
                method: 'arrow.arrow_aviation_mx.doctype.inventory_item.inventory_item.receive_item',
                args: {
                    item_name: frm.doc.name,
                    quantity: values.quantity,
                    notes: values.notes
                },
                callback: function (r) {
                    if (r.message && r.message.success) {
                        frappe.show_alert({
                            message: `Received ${values.quantity} items. New quantity: ${r.message.new_quantity}`,
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    }
                }
            });
            d.hide();
        }
    });
    d.show();
}

function withdraw_items_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: 'Withdraw Items',
        fields: [
            {
                label: 'Available Quantity',
                fieldname: 'available',
                fieldtype: 'Float',
                default: frm.doc.quantity,
                read_only: 1
            },
            {
                label: 'Quantity to Withdraw',
                fieldname: 'quantity',
                fieldtype: 'Float',
                reqd: 1
            },
            {
                label: 'Notes',
                fieldname: 'notes',
                fieldtype: 'Small Text'
            }
        ],
        primary_action_label: 'Withdraw',
        primary_action: function (values) {
            if (values.quantity > frm.doc.quantity) {
                frappe.msgprint('Cannot withdraw more than available quantity');
                return;
            }
            frappe.call({
                method: 'arrow.arrow_aviation_mx.doctype.inventory_item.inventory_item.withdraw_item',
                args: {
                    item_name: frm.doc.name,
                    quantity: values.quantity,
                    notes: values.notes
                },
                callback: function (r) {
                    if (r.message && r.message.success) {
                        frappe.show_alert({
                            message: `Withdrawn ${values.quantity} items. Remaining: ${r.message.new_quantity}`,
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    } else if (r.message) {
                        frappe.msgprint(r.message.message);
                    }
                }
            });
            d.hide();
        }
    });
    d.show();
}

function adjust_quantity_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: 'Adjust Quantity',
        fields: [
            {
                label: 'Current Quantity',
                fieldname: 'current',
                fieldtype: 'Float',
                default: frm.doc.quantity,
                read_only: 1
            },
            {
                label: 'New Quantity',
                fieldname: 'new_quantity',
                fieldtype: 'Float',
                reqd: 1
            },
            {
                label: 'Reason for Adjustment',
                fieldname: 'notes',
                fieldtype: 'Small Text',
                reqd: 1
            }
        ],
        primary_action_label: 'Adjust',
        primary_action: function (values) {
            frappe.call({
                method: 'arrow.arrow_aviation_mx.doctype.inventory_item.inventory_item.adjust_quantity',
                args: {
                    item_name: frm.doc.name,
                    new_quantity: values.new_quantity,
                    notes: values.notes
                },
                callback: function (r) {
                    if (r.message && r.message.success) {
                        frappe.show_alert({
                            message: `Quantity adjusted to ${r.message.new_quantity}`,
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    }
                }
            });
            d.hide();
        }
    });
    d.show();
}
