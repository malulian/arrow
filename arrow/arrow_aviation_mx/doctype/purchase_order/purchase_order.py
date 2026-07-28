# Copyright (c) 2026, osher and contributors
# For license information, please see license.txt

import frappe
import json
import requests
from frappe.model.document import Document
from frappe.utils import now_datetime, today, getdate


class PurchaseOrder(Document):

	def autoname(self):
		"""Naming handled by Frappe expression (PO-YYYY-#####)"""
		self.po_number = self.name

	def validate(self):
		"""Validate purchase order"""
		self.set_requested_by()
		self.link_inventory_by_part_number()

	def set_requested_by(self):
		"""Auto-fill requested_by with the creator's full name if empty"""
		if not self.requested_by and self.owner:
			full_name = frappe.db.get_value('User', self.owner, 'full_name') or self.owner
			self.requested_by = full_name

	def link_inventory_by_part_number(self):
		"""Auto-link inventory item by part number"""
		if not self.linked_inventory_item and self.part_number:
			inventory_item = frappe.db.get_value(
				'Inventory Item',
				{'part_number': self.part_number},
				'name'
			)
			if inventory_item:
				self.linked_inventory_item = inventory_item

	def before_save(self):
		"""Actions before saving — fire notifications on status change"""
		if self.has_value_changed('status'):
			self.handle_status_change()

	def handle_status_change(self):
		"""Handle status change actions: email + WhatsApp"""
		old_status = self.get_doc_before_save().status if self.get_doc_before_save() else None

		# Send email notification
		self.send_status_email(old_status)

		# Send WhatsApp notification
		self.send_whatsapp_notification(old_status)

		# Handle received status
		if self.status == 'Received':
			self.received_date = self.received_date or today()
			self.handle_item_received()

		# Handle core returned
		if self.status == 'Core Returned':
			if not self.core_return_date:
				self.core_return_date = today()

	def send_status_email(self, old_status=None):
		"""Send email notification on status change"""
		recipients = self._get_notification_recipients()
		if not recipients:
			return

		status_emoji = {
			'New': '🆕',
			'Ordered': '📦',
			'Received': '✅',
			'Core Returned': '♻️',
			'Cancelled': '❌'
		}

		emoji = status_emoji.get(self.status, '📋')
		subject = f"{emoji} PO {self.name} — {self.status}"
		
		message = f"""
		<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
			<h2 style="color: #333; border-bottom: 2px solid #333; padding-bottom: 10px;">
				{emoji} Purchase Order {self.name} — {self.status}
			</h2>
			<table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
				<tr><td style="padding: 6px 0; font-weight: bold; width: 40%;">Item:</td><td>{self.item_name}</td></tr>
				<tr><td style="padding: 6px 0; font-weight: bold;">Part Number:</td><td>{self.part_number}</td></tr>
				<tr><td style="padding: 6px 0; font-weight: bold;">Quantity:</td><td>{self.quantity}</td></tr>
				<tr><td style="padding: 6px 0; font-weight: bold;">Aircraft:</td><td>{self.aircraft or 'N/A'}</td></tr>
				<tr><td style="padding: 6px 0; font-weight: bold;">Urgency:</td><td>{self.urgency or 'Routine'}</td></tr>
				<tr><td style="padding: 6px 0; font-weight: bold;">Supplier:</td><td>{self.supplier or 'N/A'}</td></tr>
				<tr><td style="padding: 6px 0; font-weight: bold;">Notes:</td><td>{self.notes or 'N/A'}</td></tr>
			</table>
			<p><a href="{frappe.utils.get_url_to_form('Purchase Order', self.name)}">View order in system</a></p>
		</div>
		"""

		try:
			frappe.sendmail(
				recipients=recipients,
				subject=subject,
				message=message,
				reference_doctype='Purchase Order',
				reference_name=self.name
			)
		except Exception as e:
			frappe.log_error(f"Failed to send PO status email: {str(e)}", "Purchase Order Email")

	def send_whatsapp_notification(self, old_status=None):
		"""Send WhatsApp notification via Hermes gateway webhook"""
		try:
			from arrow.arrow_aviation_mx.api.whatsapp import send_whatsapp_message
			send_whatsapp_message(self._build_whatsapp_message(old_status))
		except Exception as e:
			frappe.log_error(f"Failed to send WhatsApp: {str(e)}", "Purchase Order WhatsApp")

	def _build_whatsapp_message(self, old_status=None):
		"""Build WhatsApp message text"""
		status_emoji = {
			'New': '🆕',
			'Ordered': '📦',
			'Received': '✅',
			'Core Returned': '♻️',
			'Cancelled': '❌'
		}
		emoji = status_emoji.get(self.status, '📋')
		lines = [
			f"{emoji} *PO {self.name}* — {self.status}",
			f"",
			f"📋 *{self.item_name}*",
			f"P/N: {self.part_number}",
			f"Qty: {self.quantity}",
			f"✈️ {self.aircraft or 'N/A'}",
		]
		if self.urgency == 'AOG':
			lines.append(f"🚨 *AOG — Aircraft on Ground*")
		if self.supplier:
			supplier_name = frappe.db.get_value('Supplier', self.supplier, 'supplier_name') or self.supplier
			lines.append(f"🏭 {supplier_name}")
		if self.notes:
			notes_short = self.notes[:200] + ('...' if len(self.notes) > 200 else '')
			lines.append(f"📝 {notes_short}")
		if self.status == 'Core Returned' and self.core_return_supplier:
			supplier_name = frappe.db.get_value('Supplier', self.core_return_supplier, 'supplier_name') or self.core_return_supplier
			lines.append(f"♻️ Core returned to {supplier_name} on {self.core_return_date or today()}")
		return '\n'.join(lines)

	def _get_notification_recipients(self):
		"""Get email recipients — sends to Noa's email for WhatsApp relay"""
		return ['noa992250@gmail.com']

	def handle_item_received(self):
		"""When item is received — update inventory"""
		if not self.part_number:
			return

		inventory_item_name = frappe.db.get_value(
			'Inventory Item',
			{'part_number': self.part_number},
			'name'
		)

		if inventory_item_name:
			self.linked_inventory_item = inventory_item_name
		else:
			# Create new inventory item
			inv_doc = frappe.get_doc({
				'doctype': 'Inventory Item',
				'item_name': self.item_name,
				'part_number': self.part_number,
				'quantity': 0,
				'notes': f'Created from Purchase Order {self.name}'
			})
			inv_doc.insert(ignore_permissions=True)
			self.linked_inventory_item = inv_doc.name

	def on_update(self):
		"""After save — trigger auto-received check"""
		self._check_auto_received()

	def _check_auto_received(self):
		"""Check if linked inventory item has been restocked → auto-set Received"""
		if self.status != 'Ordered':
			return
		if not self.linked_inventory_item:
			return
		inv = frappe.db.get_value('Inventory Item', self.linked_inventory_item, 'quantity')
		if inv and inv > 0:
			# Inventory has stock → mark as received
			self.db_set('status', 'Received', notify=False)
			self.db_set('received_date', today(), notify=False)


@frappe.whitelist()
def mark_ordered(po_name, supplier=None, notes=None):
	"""Quick action: mark PO as Ordered"""
	po = frappe.get_doc('Purchase Order', po_name)
	if po.status != 'New':
		frappe.throw(f"Can only order from New status. Current: {po.status}")
	po.status = 'Ordered'
	if supplier:
		po.supplier = supplier
	if notes:
		po.notes = notes
	po.save(ignore_permissions=True)
	return {'success': True, 'status': po.status}


@frappe.whitelist()
def mark_received(po_name, received_date=None):
	"""Quick action: mark PO as Received"""
	po = frappe.get_doc('Purchase Order', po_name)
	if po.status not in ('Ordered', 'New'):
		frappe.throw(f"Can only receive from New/Ordered. Current: {po.status}")
	po.status = 'Received'
	po.received_date = received_date or today()
	po.save(ignore_permissions=True)
	return {'success': True, 'status': po.status}


@frappe.whitelist()
def mark_core_returned(po_name, core_return_supplier=None, core_return_date=None, core_return_notes=None):
	"""Quick action: mark PO as Core Returned"""
	po = frappe.get_doc('Purchase Order', po_name)
	if po.status not in ('Received', 'Ordered'):
		frappe.throw(f"Can only core-return from Received/Ordered. Current: {po.status}")
	po.status = 'Core Returned'
	po.core_return_supplier = core_return_supplier
	po.core_return_date = core_return_date or today()
	po.core_return_notes = core_return_notes
	po.save(ignore_permissions=True)
	return {'success': True, 'status': po.status}


@frappe.whitelist()
def cancel_order(po_name, reason=None):
	"""Quick action: cancel PO"""
	po = frappe.get_doc('Purchase Order', po_name)
	po.status = 'Cancelled'
	if reason:
		po.notes = (po.notes or '') + f"\n[Cancelled: {reason}]"
	po.save(ignore_permissions=True)
	return {'success': True, 'status': po.status}


@frappe.whitelist()
def get_procurement_dashboard_data(status_filter=None, aircraft_filter=None):
	"""Get all POs for the procurement dashboard"""
	filters = {}
	if status_filter and status_filter != 'All':
		filters['status'] = status_filter
	if aircraft_filter and aircraft_filter != 'All':
		filters['aircraft'] = aircraft_filter

	pos = frappe.get_all(
		'Purchase Order',
		filters=filters,
		fields=[
			'name', 'status', 'item_name', 'part_number', 'quantity',
						'aircraft', 'urgency', 'supplier', 'notes', 'requested_by',
			'creation_date', 'received_date', 'core_return_date',
			'core_return_supplier', 'linked_inventory_item', 'po_number',
			'creation', 'modified'
		],
		order_by='creation desc',
		limit=500
	)

	# Get supplier names
	supplier_names = {}
	for po in pos:
		if po.get('supplier'):
			if po['supplier'] not in supplier_names:
				supplier_names[po['supplier']] = frappe.db.get_value('Supplier', po['supplier'], 'supplier_name') or po['supplier']
		if po.get('core_return_supplier'):
			if po['core_return_supplier'] not in supplier_names:
				supplier_names[po['core_return_supplier']] = frappe.db.get_value('Supplier', po['core_return_supplier'], 'supplier_name') or po['core_return_supplier']

	# Enrich with supplier display names
	for po in pos:
		po['supplier_name'] = supplier_names.get(po.get('supplier'), '')
		po['core_return_supplier_name'] = supplier_names.get(po.get('core_return_supplier'), '')

	# Get counts by status
	status_counts = {}
	for po in pos:
		s = po.get('status', 'Unknown')
		status_counts[s] = status_counts.get(s, 0) + 1

	return {
		'orders': pos,
		'status_counts': status_counts,
		'total': len(pos)
	}


@frappe.whitelist()
def get_weekly_summary():
	"""Get weekly summary of POs for WhatsApp digest"""
	pos = frappe.get_all(
		'Purchase Order',
		filters={'status': ['in', ['New', 'Ordered']]},
		fields=['name', 'status', 'item_name', 'part_number', 'quantity', 'aircraft', 'urgency', 'supplier'],
		order_by='status, creation desc'
	)

	# Get supplier names
	for po in pos:
		if po.get('supplier'):
			po['supplier_name'] = frappe.db.get_value('Supplier', po['supplier'], 'supplier_name') or po['supplier']

	return pos
