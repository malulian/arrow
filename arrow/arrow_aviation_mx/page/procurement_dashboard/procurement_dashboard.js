frappe.pages['procurement_dashboard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Procurement Dashboard',
        single_column: true
    });

    // State
    let currentFilter = 'All';
    let currentAircraftFilter = 'All';
    let allOrders = [];

    // Main container
    $(wrapper).find('.layout-content').html(`
        <div class="procurement-dashboard" style="padding: 15px;">
            <!-- Stats bar -->
            <div class="stats-bar" style="display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap;">
                <div class="stat-card stat-new" data-status="New" style="flex: 1; min-width: 120px; padding: 12px; border-radius: 8px; background: #e3f2fd; border-left: 4px solid #2196f3; cursor: pointer;">
                    <div style="font-size: 24px; font-weight: bold; color: #1976d2;" id="stat-new">0</div>
                    <div style="font-size: 12px; color: #666;">🆕 New</div>
                </div>
                <div class="stat-card stat-ordered" data-status="Ordered" style="flex: 1; min-width: 120px; padding: 12px; border-radius: 8px; background: #f3e5f5; border-left: 4px solid #9c27b0; cursor: pointer;">
                    <div style="font-size: 24px; font-weight: bold; color: #7b1fa2;" id="stat-ordered">0</div>
                    <div style="font-size: 12px; color: #666;">📦 Ordered</div>
                </div>
                <div class="stat-card stat-received" data-status="Received" style="flex: 1; min-width: 120px; padding: 12px; border-radius: 8px; background: #e8f5e9; border-left: 4px solid #4caf50; cursor: pointer;">
                    <div style="font-size: 24px; font-weight: bold; color: #388e3c;" id="stat-received">0</div>
                    <div style="font-size: 12px; color: #666;">✅ Received</div>
                </div>
                <div class="stat-card stat-core" data-status="Core Returned" style="flex: 1; min-width: 120px; padding: 12px; border-radius: 8px; background: #f5f5f5; border-left: 4px solid #616161; cursor: pointer;">
                    <div style="font-size: 24px; font-weight: bold; color: #424242;" id="stat-core">0</div>
                    <div style="font-size: 12px; color: #666;">♻️ Core Returned</div>
                </div>
                <div class="stat-card stat-total" style="flex: 1; min-width: 120px; padding: 12px; border-radius: 8px; background: #fff3e0; border-left: 4px solid #ff9800; cursor: default;">
                    <div style="font-size: 24px; font-weight: bold; color: #e65100;" id="stat-total">0</div>
                    <div style="font-size: 12px; color: #666;">📊 Total</div>
                </div>
            </div>

            <!-- Filters + New button -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <div style="display: flex; gap: 10px; align-items: center;">
                    <select id="aircraft-filter" style="padding: 6px 12px; border-radius: 4px; border: 1px solid #ddd;">
                        <option value="All">All Aircraft</option>
                        <option value="4X-CNZ">4X-CNZ</option>
                        <option value="4X-CUT">4X-CUT</option>
                        <option value="4X-CZF">4X-CZF</option>
                        <option value="4X-CRZ">4X-CRZ</option>
                        <option value="4X-CUZ">4X-CUZ</option>
                        <option value="4X-CZH">4X-CZH</option>
                        <option value="N510SP">N510SP</option>
                        <option value="General">General</option>
                    </select>
                    <button class="btn btn-default btn-sm" id="refresh-btn">🔄 Refresh</button>
                </div>
                <button class="btn btn-primary" id="new-po-btn">+ New Order</button>
            </div>

            <!-- New Order Form (hidden by default) -->
            <div id="new-order-form" style="display: none; background: #f9f9f9; border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <h4 style="margin-top: 0;">New Purchase Order</h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 12px; margin-bottom: 12px;">
                    <div>
                        <label style="font-size: 12px; color: #666;">Part Number *</label>
                        <input type="text" id="new-part-number" class="form-control" placeholder="P/N" style="width: 100%;">
                    </div>
                    <div>
                        <label style="font-size: 12px; color: #666;">Part Name *</label>
                        <input type="text" id="new-item-name" class="form-control" placeholder="Item name" style="width: 100%;">
                    </div>
                    <div>
                        <label style="font-size: 12px; color: #666;">Quantity *</label>
                        <input type="number" id="new-quantity" class="form-control" value="1" min="1" style="width: 100%;">
                    </div>
                    <div>
                        <label style="font-size: 12px; color: #666;">Aircraft *</label>
                        <select id="new-aircraft" class="form-control" style="width: 100%;">
                            <option value="">Select...</option>
                            <option value="4X-CNZ">4X-CNZ</option>
                            <option value="4X-CUT">4X-CUT</option>
                            <option value="4X-CZF">4X-CZF</option>
                            <option value="4X-CRZ">4X-CRZ</option>
                            <option value="4X-CUZ">4X-CUZ</option>
                            <option value="4X-CZH">4X-CZH</option>
                            <option value="N510SP">N510SP</option>
                            <option value="General">General</option>
                        </select>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-bottom: 12px;">
                    <div>
                        <label style="font-size: 12px; color: #666;">Urgency</label>
                        <select id="new-urgency" class="form-control" style="width: 100%;">
                            <option value="Routine">Routine</option>
                            <option value="AOG">🚨 AOG</option>
                        </select>
                    </div>
                    <div>
                        <label style="font-size: 12px; color: #666;">Required By</label>
                        <input type="date" id="new-required-date" class="form-control" style="width: 100%;">
                    </div>
                    <div>
                        <label style="font-size: 12px; color: #666;">Supplier</label>
                        <input type="text" id="new-supplier" class="form-control" placeholder="Supplier (optional)" style="width: 100%;">
                    </div>
                </div>
                <div style="margin-bottom: 12px;">
                    <label style="font-size: 12px; color: #666;">Notes</label>
                    <textarea id="new-notes" class="form-control" rows="2" placeholder="Notes..." style="width: 100%;"></textarea>
                </div>
                <div style="display: flex; gap: 10px;">
                    <button class="btn btn-primary" id="submit-new-po">Create Order</button>
                    <button class="btn btn-default" id="cancel-new-po">Cancel</button>
                </div>
            </div>

            <!-- Orders table -->
            <div id="orders-table" style="overflow-x: auto;">
                <table class="table table-bordered" style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: #f5f5f5;">
                            <th style="padding: 8px; text-align: left;">PO #</th>
                            <th style="padding: 8px; text-align: left;">Status</th>
                            <th style="padding: 8px; text-align: left;">Part Number</th>
                            <th style="padding: 8px; text-align: left;">Item Name</th>
                            <th style="padding: 8px; text-align: center;">Qty</th>
                            <th style="padding: 8px; text-align: left;">Aircraft</th>
                            <th style="padding: 8px; text-align: left;">Urgency</th>
                            <th style="padding: 8px; text-align: left;">Supplier</th>
                            <th style="padding: 8px; text-align: left;">Created</th>
                            <th style="padding: 8px; text-align: center;">Actions</th>
                        </tr>
                    </thead>
                    <tbody id="orders-body">
                        <tr><td colspan="10" style="text-align: center; padding: 30px; color: #999;">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    `);

    // Status colors
    const statusColors = {
        'New': { bg: '#e3f2fd', text: '#1565c0', border: '#2196f3', emoji: '🆕' },
        'Ordered': { bg: '#f3e5f5', text: '#7b1fa2', border: '#9c27b0', emoji: '📦' },
        'Received': { bg: '#e8f5e9', text: '#2e7d32', border: '#4caf50', emoji: '✅' },
        'Core Returned': { bg: '#f5f5f5', text: '#424242', border: '#616161', emoji: '♻️' },
        'Cancelled': { bg: '#ffebee', text: '#c62828', border: '#f44336', emoji: '❌' }
    };

    // Load data
    function loadData() {
        $('#orders-body').html('<tr><td colspan="10" style="text-align: center; padding: 30px; color: #999;">Loading...</td></tr>');
        
        frappe.call({
            method: 'arrow.arrow_aviation_mx.doctype.purchase_order.purchase_order.get_procurement_dashboard_data',
            args: {
                status_filter: currentFilter,
                aircraft_filter: currentAircraftFilter
            },
            callback: function(r) {
                if (r.message) {
                    allOrders = r.message.orders;
                    updateStats(r.message.status_counts, r.message.total);
                    renderOrders(r.message.orders);
                }
            }
        });
    }

    function updateStats(counts, total) {
        $('#stat-new').text(counts['New'] || 0);
        $('#stat-ordered').text(counts['Ordered'] || 0);
        $('#stat-received').text(counts['Received'] || 0);
        $('#stat-core').text(counts['Core Returned'] || 0);
        $('#stat-total').text(total);
    }

    function renderOrders(orders) {
        if (!orders || orders.length === 0) {
            $('#orders-body').html('<tr><td colspan="10" style="text-align: center; padding: 30px; color: #999;">No orders found</td></tr>');
            return;
        }

        let html = '';
        orders.forEach(function(po) {
            let sc = statusColors[po.status] || { bg: '#fff', text: '#333', border: '#ddd', emoji: '📋' };
            let isAOG = po.urgency === 'AOG';
            let rowBg = isAOG ? '#fff3e0' : '';
            
            html += `<tr style="background: ${rowBg}; border-bottom: 1px solid #eee;">`;
            html += `<td style="padding: 8px;"><a href="/app/purchase-order/${po.name}" style="color: #1976d2; text-decoration: none;">${po.name}</a></td>`;
            html += `<td style="padding: 8px;"><span style="background: ${sc.bg}; color: ${sc.text}; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; border: 1px solid ${sc.border};">${sc.emoji} ${po.status}</span></td>`;
            html += `<td style="padding: 8px; font-family: monospace;">${po.part_number || '-'}</td>`;
            html += `<td style="padding: 8px;">${po.item_name || '-'}</td>`;
            html += `<td style="padding: 8px; text-align: center;">${po.quantity || 1}</td>`;
            html += `<td style="padding: 8px;">${po.aircraft || '-'}</td>`;
            html += `<td style="padding: 8px;">${isAOG ? '<span style="color: #d32f2f; font-weight: bold;">🚨 AOG</span>' : 'Routine'}</td>`;
            html += `<td style="padding: 8px;">${po.supplier_name || po.supplier || '-'}</td>`;
            html += `<td style="padding: 8px; font-size: 12px; color: #666;">${(po.creation || '').split(' ')[0]}</td>`;
            html += `<td style="padding: 8px; text-align: center; white-space: nowrap;">${getActionButtons(po)}</td>`;
            html += '</tr>';
        });
        $('#orders-body').html(html);
    }

    function getActionButtons(po) {
        let buttons = '';
        let status = po.status;

        if (status === 'New') {
            buttons += `<button class="btn btn-xs btn-primary" onclick="markOrdered('${po.name}')" style="margin: 2px;">📦 Order</button>`;
        }
        if (status === 'Ordered') {
            buttons += `<button class="btn btn-xs btn-success" onclick="markReceived('${po.name}')" style="margin: 2px;">✅ Received</button>`;
        }
        if (status === 'Received') {
            buttons += `<button class="btn btn-xs btn-default" onclick="markCoreReturned('${po.name}')" style="margin: 2px;">♻️ Core Return</button>`;
        }
        if (status !== 'Cancelled' && status !== 'Core Returned') {
            buttons += `<button class="btn btn-xs btn-default" onclick="cancelOrder('${po.name}')" style="margin: 2px; color: #d32f2f;">✖</button>`;
        }
        return buttons;
    }

    // Action functions (exposed globally)
    window.markOrdered = function(poName) {
        frappe.prompt(
            [
                {fieldname: 'supplier', fieldtype: 'Link', options: 'Supplier', label: 'Supplier (optional)', reqd: 0},
                {fieldname: 'notes', fieldtype: 'Text', label: 'Notes (optional)', reqd: 0}
            ],
            function(values) {
                frappe.call({
                    method: 'arrow.arrow_aviation_mx.doctype.purchase_order.purchase_order.mark_ordered',
                    args: {
                        po_name: poName,
                        supplier: values.supplier || undefined,
                        notes: values.notes || undefined
                    },
                    callback: function(r) {
                        if (r.message && r.message.success) {
                            frappe.show_alert({message: `PO ${poName} marked as Ordered`, indicator: 'green'});
                            loadData();
                        }
                    }
                });
            },
            'Mark as Ordered — ' + poName,
            'Confirm'
        );
    };

    window.markReceived = function(poName) {
        frappe.call({
            method: 'arrow.arrow_aviation_mx.doctype.purchase_order.purchase_order.mark_received',
            args: { po_name: poName },
            callback: function(r) {
                if (r.message && r.message.success) {
                    frappe.show_alert({message: `PO ${poName} marked as Received`, indicator: 'green'});
                    loadData();
                }
            }
        });
    };

    window.markCoreReturned = function(poName) {
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
                        po_name: poName,
                        core_return_supplier: values.core_return_supplier,
                        core_return_date: values.core_return_date,
                        core_return_notes: values.core_return_notes
                    },
                    callback: function(r) {
                        if (r.message && r.message.success) {
                            frappe.show_alert({message: `PO ${poName} — Core Returned`, indicator: 'green'});
                            loadData();
                        }
                    }
                });
            },
            'Core Return — ' + poName,
            'Confirm'
        );
    };

    window.cancelOrder = function(poName) {
        frappe.confirm(`Cancel PO ${poName}?`, function() {
            frappe.call({
                method: 'arrow.arrow_aviation_mx.doctype.purchase_order.purchase_order.cancel_order',
                args: { po_name: poName },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.show_alert({message: `PO ${poName} cancelled`, indicator: 'red'});
                        loadData();
                    }
                }
            });
        });
    };

    // Event handlers
    $('.stat-card[data-status]').click(function() {
        let status = $(this).data('status');
        if (currentFilter === status) {
            currentFilter = 'All';
        } else {
            currentFilter = status;
        }
        loadData();
    });

    $('#aircraft-filter').change(function() {
        currentAircraftFilter = $(this).val();
        loadData();
    });

    $('#refresh-btn').click(loadData);

    $('#new-po-btn').click(function() {
        $('#new-order-form').slideToggle();
    });

    $('#cancel-new-po').click(function() {
        $('#new-order-form').slideUp();
    });

    $('#submit-new-po').click(function() {
        let partNumber = $('#new-part-number').val().trim();
        let itemName = $('#new-item-name').val().trim();
        let quantity = $('#new-quantity').val();
        let aircraft = $('#new-aircraft').val();
        
        if (!partNumber || !itemName || !aircraft) {
            frappe.msgprint('Part Number, Item Name, and Aircraft are required');
            return;
        }

        // Create PO via standard insert
        frappe.call({
            method: 'frappe.client.insert',
            args: {
                doc: {
                    doctype: 'Purchase Order',
                    part_number: partNumber,
                    item_name: itemName,
                    quantity: quantity || 1,
                    aircraft: aircraft,
                    urgency: $('#new-urgency').val(),
                    required_date: $('#new-required-date').val() || undefined,
                    notes: $('#new-notes').val() || undefined
                }
            },
            callback: function(r) {
                if (r.message) {
                    frappe.show_alert({message: `PO ${r.message.name} created`, indicator: 'green'});
                    // Clear form
                    $('#new-part-number').val('');
                    $('#new-item-name').val('');
                    $('#new-quantity').val('1');
                    $('#new-aircraft').val('');
                    $('#new-notes').val('');
                    $('#new-required-date').val('');
                    $('#new-supplier').val('');
                    $('#new-order-form').slideUp();
                    loadData();
                }
            }
        });
    });

    // Initial load
    loadData();
    
    // Auto-refresh every 60 seconds
    setInterval(loadData, 60000);
};
