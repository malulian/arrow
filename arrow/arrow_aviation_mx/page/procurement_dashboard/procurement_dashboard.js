// Procurement Dashboard — direct DOM injection (no make_app_page needed)

(function() {
    var wrapper = document.getElementById('page-procurement_dashboard');
    if (!wrapper) {
        wrapper = document.querySelector('.page-content .layout-main-section') || document.querySelector('.layout-main-section');
    }
    if (!wrapper) return;

    // Make sure it's visible
    wrapper.style.display = 'block';

    // State
    var currentFilter = 'All';
    var currentAircraftFilter = 'All';

    // Status colors
    var statusColors = {
        'New': { bg: '#e3f2fd', text: '#1565c0', border: '#2196f3', emoji: '🆕' },
        'Ordered': { bg: '#f3e5f5', text: '#7b1fa2', border: '#9c27b0', emoji: '📦' },
        'Received': { bg: '#e8f5e9', text: '#2e7d32', border: '#4caf50', emoji: '✅' },
        'Core Returned': { bg: '#f5f5f5', text: '#424242', border: '#616161', emoji: '♻️' },
        'Cancelled': { bg: '#ffebee', text: '#c62828', border: '#f44336', emoji: '❌' }
    };

    // Build HTML
    wrapper.innerHTML = `
        <div class="procurement-dashboard" style="padding: 15px;">
            <div class="stats-bar" style="display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap;">
                <div class="stat-card" data-status="New" style="flex: 1; min-width: 120px; padding: 12px; border-radius: 8px; background: #e3f2fd; border-left: 4px solid #2196f3; cursor: pointer;">
                    <div style="font-size: 24px; font-weight: bold; color: #1976d2;" id="pd-stat-new">0</div>
                    <div style="font-size: 12px; color: #666;">🆕 New</div>
                </div>
                <div class="stat-card" data-status="Ordered" style="flex: 1; min-width: 120px; padding: 12px; border-radius: 8px; background: #f3e5f5; border-left: 4px solid #9c27b0; cursor: pointer;">
                    <div style="font-size: 24px; font-weight: bold; color: #7b1fa2;" id="pd-stat-ordered">0</div>
                    <div style="font-size: 12px; color: #666;">📦 Ordered</div>
                </div>
                <div class="stat-card" data-status="Received" style="flex: 1; min-width: 120px; padding: 12px; border-radius: 8px; background: #e8f5e9; border-left: 4px solid #4caf50; cursor: pointer;">
                    <div style="font-size: 24px; font-weight: bold; color: #388e3c;" id="pd-stat-received">0</div>
                    <div style="font-size: 12px; color: #666;">✅ Received</div>
                </div>
                <div class="stat-card" data-status="Core Returned" style="flex: 1; min-width: 120px; padding: 12px; border-radius: 8px; background: #f5f5f5; border-left: 4px solid #616161; cursor: pointer;">
                    <div style="font-size: 24px; font-weight: bold; color: #424242;" id="pd-stat-core">0</div>
                    <div style="font-size: 12px; color: #666;">♻️ Core Returned</div>
                </div>
                <div class="stat-card" style="flex: 1; min-width: 120px; padding: 12px; border-radius: 8px; background: #fff3e0; border-left: 4px solid #ff9800;">
                    <div style="font-size: 24px; font-weight: bold; color: #e65100;" id="pd-stat-total">0</div>
                    <div style="font-size: 12px; color: #666;">📊 Total</div>
                </div>
            </div>

            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <div style="display: flex; gap: 10px; align-items: center;">
                    <select id="pd-aircraft-filter" style="padding: 6px 12px; border-radius: 4px; border: 1px solid #ddd;">
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
                    <button class="btn btn-default btn-sm" id="pd-refresh">🔄 Refresh</button>
                </div>
                <button class="btn btn-primary" id="pd-new-po">+ New Order</button>
            </div>

            <div id="pd-new-form" style="display: none; background: #f9f9f9; border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <h4 style="margin-top: 0;">New Purchase Order</h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 12px; margin-bottom: 12px;">
                    <div><label style="font-size: 12px; color: #666;">Part Number *</label><input type="text" id="pd-new-pn" class="form-control" placeholder="P/N" style="width: 100%;"></div>
                    <div><label style="font-size: 12px; color: #666;">Part Name *</label><input type="text" id="pd-new-name" class="form-control" placeholder="Item name" style="width: 100%;"></div>
                    <div><label style="font-size: 12px; color: #666;">Quantity *</label><input type="number" id="pd-new-qty" class="form-control" value="1" min="1" style="width: 100%;"></div>
                    <div><label style="font-size: 12px; color: #666;">Aircraft *</label><select id="pd-new-ac" class="form-control" style="width: 100%;"><option value="">Select...</option><option value="4X-CNZ">4X-CNZ</option><option value="4X-CUT">4X-CUT</option><option value="4X-CZF">4X-CZF</option><option value="4X-CRZ">4X-CRZ</option><option value="4X-CUZ">4X-CUZ</option><option value="4X-CZH">4X-CZH</option><option value="N510SP">N510SP</option><option value="General">General</option></select></div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px;">
                    <div><label style="font-size: 12px; color: #666;">Urgency</label><select id="pd-new-urg" class="form-control" style="width: 100%;"><option value="Routine">Routine</option><option value="AOG">🚨 AOG</option></select></div>
                    <div><label style="font-size: 12px; color: #666;">Notes</label><input type="text" id="pd-new-notes" class="form-control" placeholder="Notes" style="width: 100%;"></div>
                </div>
                <div style="display: flex; gap: 10px;">
                    <button class="btn btn-primary" id="pd-submit-new">Create Order</button>
                    <button class="btn btn-default" id="pd-cancel-new">Cancel</button>
                </div>
            </div>

            <div id="pd-table-wrapper" style="overflow-x: auto;">
                <table class="table table-bordered" style="width: 100%; border-collapse: collapse;">
                    <thead><tr style="background: #f5f5f5;">
                        <th style="padding: 8px; text-align: left;">PO #</th>
                        <th style="padding: 8px; text-align: left;">Status</th>
                        <th style="padding: 8px; text-align: left;">Part Number</th>
                        <th style="padding: 8px; text-align: left;">Item Name</th>
                        <th style="padding: 8px; text-align: center;">Qty</th>
                        <th style="padding: 8px; text-align: left;">Aircraft</th>
                        <th style="padding: 8px; text-align: left;">Urgency</th>
                        <th style="padding: 8px; text-align: left;">Created</th>
                        <th style="padding: 8px; text-align: center;">Actions</th>
                    </tr></thead>
                    <tbody id="pd-tbody"><tr><td colspan="9" style="text-align: center; padding: 30px; color: #999;">Loading...</td></tr></tbody>
                </table>
            </div>
        </div>
    `;

    function loadData() {
        document.getElementById('pd-tbody').innerHTML = '<tr><td colspan="9" style="text-align: center; padding: 30px; color: #999;">Loading...</td></tr>';
        frappe.call({
            method: 'arrow.arrow_aviation_mx.doctype.purchase_order.purchase_order.get_procurement_dashboard_data',
            args: { status_filter: currentFilter, aircraft_filter: currentAircraftFilter },
            callback: function(r) {
                if (r.message) {
                    updateStats(r.message.status_counts, r.message.total);
                    renderOrders(r.message.orders);
                }
            }
        });
    }

    function updateStats(counts, total) {
        document.getElementById('pd-stat-new').textContent = counts['New'] || 0;
        document.getElementById('pd-stat-ordered').textContent = counts['Ordered'] || 0;
        document.getElementById('pd-stat-received').textContent = counts['Received'] || 0;
        document.getElementById('pd-stat-core').textContent = counts['Core Returned'] || 0;
        document.getElementById('pd-stat-total').textContent = total;
    }

    function getActionButtons(po) {
        var btns = '';
        if (po.status === 'New') btns += '<button class="btn btn-xs btn-primary" onclick="pdMarkOrdered(\\''+po.name+'\\')" style="margin:2px;">📦 Order</button>';
        if (po.status === 'Ordered') btns += '<button class="btn btn-xs btn-success" onclick="pdMarkReceived(\\''+po.name+'\\')" style="margin:2px;">✅ Received</button>';
        if (po.status === 'Received') btns += '<button class="btn btn-xs btn-default" onclick="pdMarkCore(\\''+po.name+'\\')" style="margin:2px;">♻️ Core</button>';
        if (po.status !== 'Cancelled' && po.status !== 'Core Returned') btns += '<button class="btn btn-xs btn-default" onclick="pdCancel(\\''+po.name+'\\')" style="margin:2px;color:#d32f2f;">✖</button>';
        return btns;
    }

    function renderOrders(orders) {
        if (!orders || orders.length === 0) {
            document.getElementById('pd-tbody').innerHTML = '<tr><td colspan="9" style="text-align: center; padding: 30px; color: #999;">No orders found</td></tr>';
            return;
        }
        var html = '';
        orders.forEach(function(po) {
            var sc = statusColors[po.status] || { bg: '#fff', text: '#333', border: '#ddd', emoji: '📋' };
            var isAOG = po.urgency === 'AOG';
            html += '<tr style="background:' + (isAOG ? '#fff3e0' : '') + ';border-bottom:1px solid #eee;">';
            html += '<td style="padding:8px;"><a href="/app/purchase-order/'+po.name+'" style="color:#1976d2;text-decoration:none;">'+po.name+'</a></td>';
            html += '<td style="padding:8px;"><span style="background:'+sc.bg+';color:'+sc.text+';padding:3px 10px;border-radius:12px;font-size:12px;font-weight:600;border:1px solid '+sc.border+';">'+sc.emoji+' '+po.status+'</span></td>';
            html += '<td style="padding:8px;font-family:monospace;">'+(po.part_number||'-')+'</td>';
            html += '<td style="padding:8px;">'+(po.item_name||'-')+'</td>';
            html += '<td style="padding:8px;text-align:center;">'+(po.quantity||1)+'</td>';
            html += '<td style="padding:8px;">'+(po.aircraft||'-')+'</td>';
            html += '<td style="padding:8px;">'+(isAOG?'<span style="color:#d32f2f;font-weight:bold;">🚨 AOG</span>':'Routine')+'</td>';
            html += '<td style="padding:8px;font-size:12px;color:#666;">'+(po.creation||'').split(' ')[0]+'</td>';
            html += '<td style="padding:8px;text-align:center;white-space:nowrap;">'+getActionButtons(po)+'</td>';
            html += '</tr>';
        });
        document.getElementById('pd-tbody').innerHTML = html;
    }

    // Global action functions
    window.pdMarkOrdered = function(name) {
        frappe.prompt([
            {fieldname: 'supplier', fieldtype: 'Link', options: 'Supplier', label: 'Supplier (optional)', reqd: 0},
            {fieldname: 'notes', fieldtype: 'Text', label: 'Notes', reqd: 0}
        ], function(values) {
            frappe.call({method: 'arrow.arrow_aviation_mx.doctype.purchase_order.purchase_order.mark_ordered',
                args: {po_name: name, supplier: values.supplier || undefined, notes: values.notes || undefined},
                callback: function(r) { if (r.message && r.message.success) { frappe.show_alert({message: name+' → Ordered', indicator: 'purple'}); loadData(); } }
            });
        }, 'Mark as Ordered — ' + name, 'Confirm');
    };

    window.pdMarkReceived = function(name) {
        frappe.confirm('Mark '+name+' as Received?', function() {
            frappe.call({method: 'arrow.arrow_aviation_mx.doctype.purchase_order.purchase_order.mark_received',
                args: {po_name: name},
                callback: function(r) { if (r.message && r.message.success) { frappe.show_alert({message: name+' → Received', indicator: 'green'}); loadData(); } }
            });
        });
    };

    window.pdMarkCore = function(name) {
        frappe.prompt([
            {fieldname: 'core_return_supplier', fieldtype: 'Link', options: 'Supplier', label: 'Returned to', reqd: 1},
            {fieldname: 'core_return_date', fieldtype: 'Date', label: 'Date', reqd: 1, default: frappe.datetime.get_today()},
            {fieldname: 'core_return_notes', fieldtype: 'Text', label: 'Notes', reqd: 0}
        ], function(values) {
            frappe.call({method: 'arrow.arrow_aviation_mx.doctype.purchase_order.purchase_order.mark_core_returned',
                args: {po_name: name, core_return_supplier: values.core_return_supplier, core_return_date: values.core_return_date, core_return_notes: values.core_return_notes},
                callback: function(r) { if (r.message && r.message.success) { frappe.show_alert({message: name+' → Core Returned', indicator: 'darkgrey'}); loadData(); } }
            });
        }, 'Core Return — ' + name, 'Confirm');
    };

    window.pdCancel = function(name) {
        frappe.confirm('Cancel '+name+'?', function() {
            frappe.call({method: 'arrow.arrow_aviation_mx.doctype.purchase_order.purchase_order.cancel_order',
                args: {po_name: name},
                callback: function(r) { if (r.message && r.message.success) { frappe.show_alert({message: name+' cancelled', indicator: 'red'}); loadData(); } }
            });
        });
    };

    // Event handlers
    wrapper.querySelectorAll('.stat-card[data-status]').forEach(function(card) {
        card.addEventListener('click', function() {
            var status = this.getAttribute('data-status');
            currentFilter = (currentFilter === status) ? 'All' : status;
            loadData();
        });
    });

    document.getElementById('pd-aircraft-filter').addEventListener('change', function() {
        currentAircraftFilter = this.value;
        loadData();
    });

    document.getElementById('pd-refresh').addEventListener('click', loadData);

    document.getElementById('pd-new-po').addEventListener('click', function() {
        var form = document.getElementById('pd-new-form');
        form.style.display = (form.style.display === 'none') ? 'block' : 'none';
    });

    document.getElementById('pd-cancel-new').addEventListener('click', function() {
        document.getElementById('pd-new-form').style.display = 'none';
    });

    document.getElementById('pd-submit-new').addEventListener('click', function() {
        var pn = document.getElementById('pd-new-pn').value.trim();
        var name = document.getElementById('pd-new-name').value.trim();
        var qty = document.getElementById('pd-new-qty').value;
        var ac = document.getElementById('pd-new-ac').value;
        if (!pn || !name || !ac) { frappe.msgprint('Part Number, Item Name, and Aircraft are required'); return; }
        frappe.call({
            method: 'frappe.client.insert',
            args: { doc: { doctype: 'Purchase Order', part_number: pn, item_name: name, quantity: qty || 1, aircraft: ac, urgency: document.getElementById('pd-new-urg').value, notes: document.getElementById('pd-new-notes').val() } },
            callback: function(r) {
                if (r.message) {
                    frappe.show_alert({message: 'PO '+r.message.name+' created', indicator: 'green'});
                    document.getElementById('pd-new-pn').value = '';
                    document.getElementById('pd-new-name').value = '';
                    document.getElementById('pd-new-qty').value = '1';
                    document.getElementById('pd-new-ac').value = '';
                    document.getElementById('pd-new-notes').value = '';
                    document.getElementById('pd-new-form').style.display = 'none';
                    loadData();
                }
            }
        });
    });

    // Initial load
    loadData();

    // Auto-refresh every 60 seconds
    setInterval(loadData, 60000);
})();

// Auto-trigger
if (typeof frappe !== 'undefined' && frappe.pages && frappe.pages['procurement_dashboard']) {
    // already executed above via IIFE
}
