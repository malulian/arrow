# Copyright (c) 2026, osher and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, today


class InventoryItem(Document):
	def validate(self):
		"""Validate and update status"""
		self.update_status()
		self.calculate_total_cost()
	
	def calculate_total_cost(self):
		"""Calculate total cost = unit_price + shipping_cost safely"""
		unit_price = float(getattr(self, 'unit_price', 0) or 0)
		shipping_cost = float(getattr(self, 'shipping_cost', 0) or 0)
		self.total_cost = round(unit_price + shipping_cost, 2)
	
	def update_status(self):
		"""Update status based on quantity and expiry"""
		# Check expiry first
		if self.expiry_date and getdate(self.expiry_date) < getdate(today()):
			self.status = 'Expired'
			return
		
		# Check quantity
		if self.quantity <= 0:
			self.status = 'Out of Stock'
		elif self.minimum_quantity and self.quantity <= self.minimum_quantity:
			self.status = 'Low Stock'
		else:
			self.status = 'Active'
	
	def before_save(self):
		"""Check for low stock alert"""
		if self.has_value_changed('status') and self.status == 'Low Stock':
			frappe.msgprint(
				f"⚠️ Low stock alert: {self.item_name} ({self.part_number}) is at {self.quantity} {self.unit}",
				title="Low Stock",
				indicator="orange"
			)

	def on_update(self):
		"""After save — auto-update linked Purchase Orders to Received"""
		self._auto_receive_linked_pos()

	def _auto_receive_linked_pos(self):
		"""
		When inventory quantity increases (item received into stock),
		auto-update any linked Purchase Order from 'Ordered' to 'Received'.
		"""
		if not self.part_number:
			return

		# Only trigger if quantity changed (increased)
		if self.get_doc_before_save():
			old_qty = self.get_doc_before_save().quantity or 0
		else:
			old_qty = 0

		if (self.quantity or 0) <= old_qty:
			return  # Quantity didn't increase, skip

		# Find POs linked to this inventory item that are in 'Ordered' status
		linked_pos = frappe.get_all(
			'Purchase Order',
			filters={
				'status': 'Ordered',
				'linked_inventory_item': self.name
			},
			fields=['name']
		)

		# Also find by part_number if no linked_inventory_item
		if not linked_pos:
			linked_pos = frappe.get_all(
				'Purchase Order',
				filters={
					'status': 'Ordered',
					'part_number': self.part_number
				},
				fields=['name']
			)

		for po_data in linked_pos:
			# If an active Purchase Order Receiving record exists for this PO,
			# the receiving workflow is authoritative — do NOT auto-close.
			active_receiving = frappe.db.get_value(
				'Purchase Order Receiving',
				{'purchase_order': po_data['name'], 'status': ['!=', 'Received']},
				'name'
			)
			if active_receiving:
				continue
			try:
				po = frappe.get_doc('Purchase Order', po_data['name'])
				po.db_set('status', 'Received', notify=False)
				po.db_set('received_date', today(), notify=False)
				po.db_set('linked_inventory_item', self.name, notify=False)
				
				# Send WhatsApp + email notification
				po.send_status_email('Ordered')
				po.send_whatsapp_notification('Ordered')
			except Exception as e:
				frappe.log_error(
					f"Failed to auto-receive PO {po_data['name']}: {str(e)}",
					"Auto-Receive PO"
				)


@frappe.whitelist()
def receive_item(item_name, quantity, notes=None, reference_doctype=None, reference_name=None):
	"""Receive items into inventory"""
	item = frappe.get_doc('Inventory Item', item_name)
	item.quantity = (item.quantity or 0) + float(quantity)
	item.last_received_date = today()
	item.save(ignore_permissions=True)
	
	# Create transaction record
	frappe.get_doc({
		'doctype': 'Inventory Transaction',
		'inventory_item': item_name,
		'transaction_type': 'Receive',
		'quantity': float(quantity),
		'reference_doctype': reference_doctype,
		'reference_name': reference_name,
		'notes': notes
	}).insert(ignore_permissions=True)
	
	return {'success': True, 'new_quantity': item.quantity}


@frappe.whitelist()
def withdraw_item(item_name, quantity, notes=None, reference_doctype=None, reference_name=None):
	"""Withdraw items from inventory"""
	item = frappe.get_doc('Inventory Item', item_name)
	
	qty = float(quantity)
	if item.quantity < qty:
		return {
			'success': False, 
			'message': f'Insufficient quantity. Available: {item.quantity}'
		}
	
	item.quantity = item.quantity - qty
	item.last_withdrawal_date = today()
	item.save(ignore_permissions=True)
	
	# Create transaction record
	frappe.get_doc({
		'doctype': 'Inventory Transaction',
		'inventory_item': item_name,
		'transaction_type': 'Withdraw',
		'quantity': qty,
		'reference_doctype': reference_doctype,
		'reference_name': reference_name,
		'notes': notes
	}).insert(ignore_permissions=True)
	
	return {'success': True, 'new_quantity': item.quantity}


@frappe.whitelist()
def adjust_quantity(item_name, new_quantity, notes=None):
	"""Adjust inventory quantity (for corrections)"""
	item = frappe.get_doc('Inventory Item', item_name)
	old_quantity = item.quantity
	item.quantity = float(new_quantity)
	item.save(ignore_permissions=True)
	
	# Create adjustment transaction
	adjustment = float(new_quantity) - old_quantity
	frappe.get_doc({
		'doctype': 'Inventory Transaction',
		'inventory_item': item_name,
		'transaction_type': 'Adjustment',
		'quantity': adjustment,
		'notes': f"Adjusted from {old_quantity} to {new_quantity}. {notes or ''}"
	}).insert(ignore_permissions=True)
	
	return {'success': True, 'new_quantity': item.quantity}


@frappe.whitelist()
def get_available_quantity(item_name):
	"""Get current available quantity for an item"""
	return frappe.db.get_value('Inventory Item', item_name, 'quantity') or 0
