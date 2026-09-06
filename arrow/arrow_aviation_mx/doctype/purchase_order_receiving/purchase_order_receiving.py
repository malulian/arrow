# Copyright (c) 2026, osher and contributors
# For license information, please see license.txt

"""
Purchase Order Receiving — the intermediate "awaiting warehouse receipt" stage
for Purchase Orders that moved to status = Ordered.

For each Ordered PO a receiving record is auto-created. It shows:
  - the order details (item, P/N, ordered qty, supplier, aircraft)
  - the CURRENT stock on hand and its location (read-only, pulled live from the
    linked Inventory Item)
The receiving agent confirms the ACTUAL quantity that arrived (correct P/N +
quantity). On confirm (via the Confirm Receipt button, or simply by saving the
form with a received_quantity):
  - inventory quantity is increased by the received amount
  - placement location is updated
  - an Inventory Transaction (Receive) is recorded
  - if the received qty matches the order -> PO -> Received, receiving closed
  - if there's a deviation (short/over) -> stock updates with what actually
    arrived, PO is NOT closed, and an email is sent to Osher that the order
    was not completed fully.

The receiving is idempotent: a received record is locked (status != Awaiting
Receipt) so saving it again won't re-apply stock.
"""

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import today, now_datetime


class PurchaseOrderReceiving(Document):
	def validate(self):
		self._validate_part_number()
		self._refresh_current_stock()
		# Auto-apply the receiving if a real (cumulative) quantity was entered by
		# the user and it differs from what was already applied to stock.
		# This makes the flow work both from the "Confirm Receipt" button and
		# from plain form saves, AND supports multi-delivery partial receipts:
		# a second confirm with a larger cumulative total applies only the delta.
		qty = _as_float(self.get("received_quantity"))
		applied = _as_float(self.get("applied_quantity"))
		if (qty and qty > 0 and qty != applied
			and self.status in ("Awaiting Receipt", "Partially Received", "Discrepancy")):
			self._apply_receiving(qty, applied)

	def _validate_part_number(self):
		"""Verify the received P/N against the ordered P/N on every save path."""
		incoming_pn = (self.get("received_part_number") or '').strip().lower()
		expected_pn = (self.part_number or '').strip().lower()
		if (expected_pn and incoming_pn and self.status != 'Received'
				and incoming_pn != expected_pn):
			frappe.throw(
				_('Received P/N "{0}" does not match the ordered P/N "{1}". '
				  'Verify the part before confirming.').format(
					self.received_part_number, self.part_number
				)
			)

	def _refresh_current_stock(self):
		"""Pull current on-hand qty + location from the linked inventory item."""
		if not self.linked_inventory_item:
			return
		inv = frappe.db.get_value(
			'Inventory Item',
			self.linked_inventory_item,
			['quantity', 'location', 'status'],
			as_dict=True,
		)
		if inv:
			self.current_quantity = inv.quantity or 0
			self.current_location = inv.location or ''
			self.inventory_item_status = inv.status or ''

	def _apply_receiving(self, qty, already_applied=0.0):
		"""Apply actual receipt: update stock, record transaction, reconcile PO.

		`qty` is the CUMULATIVE total received so far; `already_applied` is what
		was previously applied to stock. Only the delta hits inventory, so a
		partial receipt followed by the remainder produces two Inventory
		Transactions and the correct total on-hand quantity.
		"""
		if not self.purchase_order:
			return
		delta = qty - (already_applied or 0.0)
		if delta <= 0:
			return

		# ---- Load / create the inventory item ----
		inv_name = self.linked_inventory_item
		if not inv_name and self.part_number:
			inv_name = frappe.db.get_value('Inventory Item', {'part_number': self.part_number}, 'name')
		if not inv_name:
			inv = frappe.get_doc({
				'doctype': 'Inventory Item',
				'item_name': self.item_name,
				'part_number': self.part_number,
				'quantity': 0,
				'notes': f'Created from receiving {self.name}',
			}).insert(ignore_permissions=True)
			inv_name = inv.name
			self.linked_inventory_item = inv_name

		inv = frappe.get_doc('Inventory Item', inv_name)
		old_qty = inv.quantity or 0
		# Update via db_set to avoid re-entering InventoryItem.on_update
		# (its legacy auto-receive would otherwise loop back into this flow).
		frappe.db.set_value('Inventory Item', inv_name, {
			'quantity': old_qty + delta,
			'location': self.received_location or inv.location or '',
			'last_received_date': today(),
		})
		inv.reload()
		# db_set bypasses InventoryItem.validate() -> update_status(), so the stored
		# status stays stale: a new item is inserted at qty 0 ('Out of Stock') and
		# the receipt that follows never refreshes it. Recompute + persist explicitly.
		inv.update_status()
		frappe.db.set_value('Inventory Item', inv_name, 'status', inv.status)

		# ---- Record inventory transaction (only the newly arrived delta) ----
		frappe.get_doc({
			'doctype': 'Inventory Transaction',
			'inventory_item': inv_name,
			'transaction_type': 'Receive',
			'quantity': delta,
			'date': now_datetime(),
			'performed_by': self.received_by or frappe.session.user,
			'reference_doctype': 'Purchase Order Receiving',
			'reference_name': self.name,
			'notes': (self.notes or f'Received via {self.name}'),
		}).insert(ignore_permissions=True)

		# ---- Update this record's snapshot (do not re-trigger apply) ----
		self.current_quantity = inv.quantity
		self.current_location = inv.location or self.current_location or ''

		# ---- Reconcile with the original order ----
		ordered_qty = _as_float(self.get('ordered_quantity'))
		deviation = qty != ordered_qty
		partial = qty < ordered_qty
		self.applied_quantity = qty
		self.receiving_applied = 1

		if deviation:
			self.status = 'Partially Received' if partial else 'Discrepancy'
			_disable_auto_receive_for(self.purchase_order)
			po = frappe.get_doc('Purchase Order', self.purchase_order)
			po.db_set('status', 'Partially Received', notify=False)
			if not po.db_get('received_date'):
				po.db_set('received_date', today(), notify=False)
			_send_completion_alert(self, po, qty, ordered_qty, partial)
		else:
			self.status = 'Received'
			_disable_auto_receive_for(self.purchase_order)
			po = frappe.get_doc('Purchase Order', self.purchase_order)
			po.db_set('status', 'Received', notify=False)
			if not po.db_get('received_date'):
				po.db_set('received_date', today(), notify=False)


@frappe.whitelist()
def confirm_receipt(
	rcv_name,
	received_quantity=None,
	received_location=None,
	received_part_number=None,
	received_by=None,
	notes=None,
):
	"""Entry point for the 'Confirm Receipt' button — sets the entered fields and
	saves, which flows through validate() -> _apply_receiving()."""
	rcv = frappe.get_doc('Purchase Order Receiving', rcv_name)

	if rcv.status == 'Received':
		frappe.throw(_('This receiving record is already closed (Received).'))

	qty = _as_float(received_quantity)
	if qty <= 0:
		frappe.throw(_('Quantity received must be greater than zero.'))

	# ---- P/N verification happens in validate() (shared with plain saves) ----

	rcv.received_quantity = qty
	if received_location:
		rcv.received_location = received_location
	if received_part_number:
		rcv.received_part_number = received_part_number
	if received_by:
		rcv.received_by = received_by
	if notes:
		rcv.notes = (rcv.notes or '') + f'\n[{now_datetime().strftime("%Y-%m-%d %H:%M")}] {notes}'
	rcv.save(ignore_permissions=True)

	rcv.reload()
	inv_qty = frappe.db.get_value('Inventory Item', rcv.linked_inventory_item, 'quantity') or 0
	return {
		'success': True,
		'new_quantity': inv_qty,
		'status': rcv.status,
		'po_status': frappe.db.get_value('Purchase Order', rcv.purchase_order, 'status'),
		'deviation': rcv.status != 'Received',
		'received': qty,
		'ordered': rcv.ordered_quantity,
	}


def _disable_auto_receive_for(po_name):
	"""Prevent the legacy auto-receive on PO save from re-opening this flow."""
	# The InventoryItem.on_update auto-receive already skips POs that have an
	# active receiving record; this is a safety no-op marker kept for clarity.
	pass


def _send_completion_alert(rcv, po, qty, ordered_qty, partial):
	"""Email Osher that the order was NOT completed fully."""
	recipients = ['oshermalul@gmail.com']
	subject = (
		f'⚠️ PO {po.name} — received {qty}/{ordered_qty} '
		f'({("less than ordered" if partial else "more than ordered")})'
	)
	message = f"""
	<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
		<h2 style="color: #b00020;">⚠️ Order not completed fully</h2>
		<p>A received quantity does <b>not</b> match the original order.</p>
		<table style="width:100%; border-collapse:collapse; margin:12px 0;">
			<tr><td style="padding:6px 0;font-weight:bold;width:40%;">PO:</td><td>{po.name}</td></tr>
			<tr><td style="padding:6px 0;font-weight:bold;">Item:</td><td>{rcv.item_name}</td></tr>
			<tr><td style="padding:6px 0;font-weight:bold;">P/N:</td><td>{rcv.part_number}</td></tr>
			<tr><td style="padding:6px 0;font-weight:bold;">Ordered:</td><td>{ordered_qty}</td></tr>
			<tr><td style="padding:6px 0;font-weight:bold;color:#b00020;">Actually received:</td><td>{qty} ({'shortage' if partial else 'over-delivery'})</td></tr>
			<tr><td style="padding:6px 0;font-weight:bold;">On-hand after:</td><td>{rcv.current_quantity}</td></tr>
			<tr><td style="padding:6px 0;font-weight:bold;">Location:</td><td>{rcv.current_location or '—'}</td></tr>
		</table>
		<p>Inventory was updated with the actual received quantity. The PO remains open
		for follow-up — review and resolve the discrepancy.</p>
		<p><a href="{frappe.utils.get_url_to_form('Purchase Order', po.name)}">Open the order</a></p>
	</div>
	"""
	try:
		frappe.sendmail(
			recipients=recipients,
			subject=subject,
			message=message,
			reference_doctype='Purchase Order Receiving',
			reference_name=rcv.name,
		)
	except Exception as e:
		frappe.log_error(f"Failed to send PO completion alert: {str(e)}", "Receiving Alert")


@frappe.whitelist()
def create_receiving_for_po(po_name):
	"""Auto-create a receiving record for an Ordered PO (idempotent)."""
	po = frappe.get_doc('Purchase Order', po_name)
	existing = frappe.db.get_value(
		'Purchase Order Receiving', {'purchase_order': po_name}, 'name'
	)
	if existing:
		return {'success': True, 'name': existing, 'created': False}

	receiving = frappe.get_doc({
		'doctype': 'Purchase Order Receiving',
		'purchase_order': po_name,
		'status': 'Awaiting Receipt',
		'item_name': po.item_name,
		'part_number': po.part_number,
		'ordered_quantity': po.quantity,
		'supplier': po.supplier,
		'aircraft': po.aircraft,
		'expected_arrival': po.expected_arrival,
		'linked_inventory_item': po.linked_inventory_item,
	}).insert(ignore_permissions=True)
	return {'success': True, 'name': receiving.name, 'created': True}


def _as_float(v):
	try:
		f = float(v or 0)
		return f if f > 0 else 0.0
	except (TypeError, ValueError):
		return 0.0
