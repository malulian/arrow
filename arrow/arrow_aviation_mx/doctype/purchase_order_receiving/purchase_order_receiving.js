// Copyright (c) 2026, osher and contributors
// For license information, please see license.txt

frappe.ui.form.on('Purchase Order Receiving', {
	refresh(frm) {
		// Auto-copy the expected P/N as a convenience for verification
		if (!frm.doc.received_part_number && frm.doc.part_number) {
			frm.set_value('received_part_number', frm.doc.part_number);
		}

		// Disable confirm when already received
		const closed = frm.doc.status === 'Received';

		// NOTE: frm.add_custom_action() does not exist on Form in Frappe v16
		// (it is a Dialog API) — it silently threw and the button never showed.
		// The correct Form API is add_custom_button(). Set it as the page's
		// primary action so it renders prominently.
		frm.add_custom_button(__('Confirm Receipt'), () => confirm_receipt(frm), __('Actions'));
		if (!closed) {
			frm.page.set_primary_action(__('Confirm Receipt'), () => confirm_receipt(frm));
		} else {
			frm.page.set_primary_action(__('Received'), () => frappe.msgprint(__('This receiving record is already closed.')));
		}
	},
});

async function confirm_receipt(frm) {
	if (frm.doc.status === 'Received') {
		frappe.msgprint(__('This receiving record is already closed.'));
		return;
	}
	if (!frm.doc.purchase_order) {
		frappe.msgprint(__('No linked Purchase Order.'));
		return;
	}
	const qty = frm.doc.received_quantity;
	if (!qty || qty <= 0) {
		frappe.msgprint(__('Enter the actual quantity received (greater than zero).'));
		return;
	}

	frappe.confirm(
		__('Confirm receiving {0} units of {1} ({2}) into inventory?', [qty, frm.doc.item_name, frm.doc.part_number]),
		() => {
			frappe.call({
				method: 'arrow.arrow_aviation_mx.doctype.purchase_order_receiving.purchase_order_receiving.confirm_receipt',
				args: {
					rcv_name: frm.doc.name,
					received_quantity: frm.doc.received_quantity,
					received_location: frm.doc.received_location,
					received_part_number: frm.doc.received_part_number,
					received_by: frm.doc.received_by,
					notes: frm.doc.notes,
				},
				callback(r) {
					if (r.message && r.message.success) {
						const m = r.message;
						let msg = `✅ Received ${m.received} units. New on-hand: ${m.new_quantity}.`;
						if (m.deviation) {
							msg += `\n⚠️ Deviation from order (ordered ${m.ordered}). PO kept open, alert sent.`;
						}
						frappe.show_alert(msg, m.deviation ? 'warning' : 'success');
						frm.reload_doc();
					} else if (r.exc) {
						frappe.msgprint(r.exc);
					}
				},
			});
		}
	);
}
