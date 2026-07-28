// Purchase Order List View — procurement dashboard replacement
// Color-coded rows by status, quick action buttons, inline filtering

frappe.listview_settings['Purchase Order'] = {
    onload: function(listview) {
        // Add quick filter buttons
        listview.page.add_menu_item(__('🆕 New Order'), function() {
            quick_new_order();
        });

        // Add custom filter for urgency
        listview.page.add_menu_item(__('🚨 AOG Only'), function() {
            listview.filter_area.clear();
            listview.filter_area.add_filter('Purchase Order', 'urgency', '=', 'AOG');
            listview.refresh();
        });

        // Weekly summary button
        listview.page.add_menu_item(__('📋 Weekly Summary'), function() {
            frappe.call({
                method: 'arrow.arrow_aviation_mx.api.whatsapp.send_weekly_digest',
                callback: function(r) {
                    if (r.message && r.message.message) {
                        frappe.msgprint({
                            title: 'Weekly Summary',
                            message: '<pre>' + r.message.message + '</pre>',
                            indicator: 'blue'
                        });
                    }
                }
            });
        });
    },

    // Color the rows by status
    get_indicator: function(doc) {
        const colors = {
            'New': 'blue',
            'Ordered': 'purple',
            'Received': 'green',
            'Core Returned': 'darkgrey',
            'Cancelled': 'red'
        };
        return [__(doc.status), colors[doc.status] || 'grey', 'status,=,' + doc.status];
    },

    // Custom formatters for list view columns
    formatters: {
        urgency: function(value, row) {
            if (value === 'AOG') {
                return '<span style="color: #d32f2f; font-weight: bold;">🚨 AOG</span>';
            }
            return value || 'Routine';
        }
    },

    // Right-click / row click actions
    right_column: function(doc) {
        // This adds action buttons to each row
        let html = '<div class="list-row-actions" style="display: flex; gap: 4px;">';

        if (doc.status === 'New') {
            html += '<button class="btn btn-xs btn-primary po-quick-order" data-name="' + doc.name + '" style="margin: 2px;">📦 Order</button>';
        }
        if (doc.status === 'Ordered') {
            html += '<button class="btn btn-xs btn-success po-quick-receive" data-name="' + doc.name + '" style="margin: 2px;">✅ Received</button>';
        }
        if (doc.status === 'Received') {
            html += '<button class="btn btn-xs btn-default po-quick-core" data-name="' + doc.name + '" style="margin: 2px;">♻️ Core</button>';
        }

        html += '</div>';
        return html;
    },

    // Called after list is refreshed
    refresh: function(listview) {
        // Bind click handlers for quick action buttons
        $('.po-quick-order').off('click').on('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            let name = $(this).data('name');
            frappe.prompt(
                [
                    {fieldname: 'supplier', fieldtype: 'Link', options: 'Supplier', label: 'Supplier (optional)', reqd: 0},
                    {fieldname: 'notes', fieldtype: 'Text', label: 'Notes (optional)', reqd: 0}
                ],
                function(values) {
                    frappe.call({
                        method: 'arrow.arrow_aviation_mx.doctype.purchase_order.purchase_order.mark_ordered',
                        args: {po_name: name, supplier: values.supplier || undefined, notes: values.notes || undefined},
                        callback: function(r) {
                            if (r.message && r.message.success) {
                                frappe.show_alert({message: name + ' → Ordered', indicator: 'purple'});
                                listview.refresh();
                            }
                        }
                    });
                },
                'Mark as Ordered — ' + name,
                'Confirm'
            );
        });

        $('.po-quick-receive').off('click').on('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            let name = $(this).data('name');
            frappe.confirm('Mark ' + name + ' as Received?', function() {
                frappe.call({
                    method: 'arrow.arrow_aviation_mx.doctype.purchase_order.purchase_order.mark_received',
                    args: {po_name: name},
                    callback: function(r) {
                        if (r.message && r.message.success) {
                            frappe.show_alert({message: name + ' → Received', indicator: 'green'});
                            listview.refresh();
                        }
                    }
                });
            });
        });

        $('.po-quick-core').off('click').on('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            let name = $(this).data('name');
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
                            po_name: name,
                            core_return_supplier: values.core_return_supplier,
                            core_return_date: values.core_return_date,
                            core_return_notes: values.core_return_notes
                        },
                        callback: function(r) {
                            if (r.message && r.message.success) {
                                frappe.show_alert({message: name + ' → Core Returned', indicator: 'darkgrey'});
                                listview.refresh();
                            }
                        }
                    });
                },
                'Core Return — ' + name,
                'Confirm'
            );
        });
    }
};

// Quick new order dialog
function quick_new_order() {
    let d = new frappe.ui.Dialog({
        title: 'New Purchase Order',
        fields: [
            {fieldname: 'part_number', fieldtype: 'Data', label: 'Part Number *', reqd: 1},
            {fieldname: 'item_name', fieldtype: 'Data', label: 'Part Name *', reqd: 1},
            {fieldname: 'quantity', fieldtype: 'Int', label: 'Quantity *', reqd: 1, default: 1},
            {fieldname: 'aircraft', fieldtype: 'Select', label: 'Aircraft *', reqd: 1,
             options: '\n4X-CNZ\n4X-CUT\n4X-CZF\n4X-CRZ\n4X-CUZ\n4X-CZH\nN510SP\nGeneral'},
            {fieldname: 'urgency', fieldtype: 'Select', label: 'Urgency', default: 'Routine',
             options: 'Routine\nAOG'},
            {fieldname: 'required_date', fieldtype: 'Date', label: 'Required By'},
            {fieldname: 'supplier', fieldtype: 'Link', options: 'Supplier', label: 'Supplier'},
            {fieldname: 'notes', fieldtype: 'Text', label: 'Notes'}
        ],
        primary_action_label: 'Create Order',
        primary_action: function(values) {
            frappe.call({
                method: 'frappe.client.insert',
                args: {
                    doc: Object.assign({doctype: 'Purchase Order'}, values)
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.show_alert({
                            message: 'PO ' + r.message.name + ' created',
                            indicator: 'green'
                        });
                        d.hide();
                        // Refresh the list
                        cur_list && cur_list.refresh();
                    }
                }
            });
        }
    });
    d.show();
}
