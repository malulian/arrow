# Copyright (c) 2026, osher and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, today, getdate
from frappe.core.doctype.communication.email import make


class PurchaseOrder(Document):
	def autoname(self):
		"""Generate PO number"""
		self.po_number = self.name
	
	def validate(self):
		"""Validate purchase order"""
		self.validate_quotes()
		self.check_supplier_approval()
		self.link_inventory_by_part_number()
		self.update_selected_quote_info()
	
	def validate_quotes(self):
		"""Warn if less than 3 quotes - only on first save or when quotes change"""
		if not self.quotes or len(self.quotes) >= 3:
			return
		
		# Only show warning on new document or when quotes table was modified
		if self.is_new() or self.has_value_changed('quotes'):
			frappe.msgprint(
				f"⚠️ Warning: Only {len(self.quotes)} quote(s) attached. It is recommended to have at least 3 quotes.",
				title="Quotes Warning",
				indicator="orange"
			)
	
	def check_supplier_approval(self):
		"""Warn if any supplier is not approved - only on first save or when quotes change"""
		if not self.quotes:
			return
		
		# Only check on new document or when quotes table was modified
		if not (self.is_new() or self.has_value_changed('quotes')):
			return
		
		unapproved = []
		for quote in self.quotes:
			if quote.supplier and not quote.is_approved_supplier:
				supplier_name = frappe.db.get_value('Supplier', quote.supplier, 'supplier_name')
				unapproved.append(supplier_name or quote.supplier)
		
		if unapproved:
			frappe.msgprint(
				f"⚠️ Warning: The following supplier(s) are not approved: {', '.join(unapproved)}",
				title="Unapproved Suppliers",
				indicator="orange"
			)
	
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
	
	def update_selected_quote_info(self):
		"""Update selected quote information"""
		if not self.quotes:
			return
		
		selected = None
		for idx, quote in enumerate(self.quotes):
			if quote.is_selected:
				selected = quote
				self.selected_quote_idx = idx + 1
				break
		
		if selected:
			self.selected_supplier_name = selected.supplier_name
			self.selected_quote_amount = selected.quote_amount
	
	def before_save(self):
		"""Actions before saving"""
		# Detect status changes and send notifications
		if self.has_value_changed('status'):
			self.handle_status_change()
	
	def handle_status_change(self):
		"""Handle status change actions"""
		if self.status == 'Awaiting Approval' and self.approved_by_user:
			self.send_approval_notification()
		
		elif self.status == 'Awaiting Inspection' and self.inspection_user:
			self.send_inspection_notification()
		
		elif self.status == 'Approved':
			self.approval_date = now_datetime()
	
	def send_approval_notification(self):
		"""Send email to approver when order awaits approval"""
		if not self.approved_by_user:
			return
		
		approver_email = frappe.db.get_value('User', self.approved_by_user, 'email')
		if not approver_email:
			return
		
		subject = f"Purchase Order {self.name} Awaiting Your Approval"
		message = f"""
		<h3>Purchase Order Awaiting Approval</h3>
		<p>A purchase order requires your approval:</p>
		<table border="1" cellpadding="5" style="border-collapse: collapse;">
			<tr><td><b>PO Number:</b></td><td>{self.name}</td></tr>
			<tr><td><b>Item:</b></td><td>{self.item_name}</td></tr>
			<tr><td><b>Part Number:</b></td><td>{self.part_number}</td></tr>
			<tr><td><b>Quantity:</b></td><td>{self.quantity}</td></tr>
			<tr><td><b>Created By:</b></td><td>{self.created_by_user}</td></tr>
		</table>
		<p><a href="{frappe.utils.get_url_to_form('Purchase Order', self.name)}">Click here to review</a></p>
		"""
		
		try:
			frappe.sendmail(
				recipients=[approver_email],
				subject=subject,
				message=message,
				reference_doctype='Purchase Order',
				reference_name=self.name
			)
			frappe.msgprint(f"📧 Approval notification sent to {approver_email}", alert=True)
		except Exception as e:
			frappe.log_error(f"Failed to send approval email: {str(e)}", "Purchase Order Email")
	
	def send_inspection_notification(self):
		"""Send email to inspector when item awaits inspection"""
		if not self.inspection_user:
			return
		
		inspector_email = frappe.db.get_value('User', self.inspection_user, 'email')
		if not inspector_email:
			return
		
		subject = f"Item Awaiting Inspection - PO {self.name}"
		message = f"""
		<h3>Item Awaiting Receiving Inspection</h3>
		<p>An item has been received and requires inspection:</p>
		<table border="1" cellpadding="5" style="border-collapse: collapse;">
			<tr><td><b>PO Number:</b></td><td>{self.name}</td></tr>
			<tr><td><b>Item:</b></td><td>{self.item_name}</td></tr>
			<tr><td><b>Part Number:</b></td><td>{self.part_number}</td></tr>
			<tr><td><b>Quantity:</b></td><td>{self.quantity}</td></tr>
			<tr><td><b>Received Date:</b></td><td>{self.received_date or 'N/A'}</td></tr>
		</table>
		<p><a href="{frappe.utils.get_url_to_form('Purchase Order', self.name)}">Click here to perform inspection</a></p>
		"""
		
		try:
			frappe.sendmail(
				recipients=[inspector_email],
				subject=subject,
				message=message,
				reference_doctype='Purchase Order',
				reference_name=self.name
			)
			frappe.msgprint(f"📧 Inspection notification sent to {inspector_email}", alert=True)
		except Exception as e:
			frappe.log_error(f"Failed to send inspection email: {str(e)}", "Purchase Order Email")
	
	def on_update(self):
		"""After save actions"""
		# Update inventory when completed
		if self.status == 'Completed' and self.linked_inventory_item:
			self.update_inventory_quantity()
	
	def update_inventory_quantity(self):
		"""Update inventory item quantity when PO is completed"""
		if not self.linked_inventory_item:
			return
		
		try:
			inv_item = frappe.get_doc('Inventory Item', self.linked_inventory_item)
			inv_item.quantity = (inv_item.quantity or 0) + self.quantity
			inv_item.last_received_date = self.received_date or today()
			inv_item.save(ignore_permissions=True)
			
			# Create inventory transaction
			frappe.get_doc({
				'doctype': 'Inventory Transaction',
				'inventory_item': self.linked_inventory_item,
				'transaction_type': 'Receive',
				'quantity': self.quantity,
				'reference_doctype': 'Purchase Order',
				'reference_name': self.name,
				'notes': f'Received from PO {self.name}'
			}).insert(ignore_permissions=True)
			
		except Exception as e:
			frappe.log_error(f"Failed to update inventory: {str(e)}", "Purchase Order Inventory")


@frappe.whitelist()
def generate_po_pdf(po_name):
	"""Generate PO PDF document"""
	po = frappe.get_doc('Purchase Order', po_name)
	
	# Get selected quote info
	selected_quote = None
	for quote in po.quotes:
		if quote.is_selected:
			selected_quote = quote
			break
	
	supplier_info = {}
	if selected_quote and selected_quote.supplier:
		supplier_info = frappe.db.get_value(
			'Supplier', 
			selected_quote.supplier,
			['supplier_name', 'address', 'phone', 'email', 'contact_person'],
			as_dict=True
		) or {}
	
	html = f"""
	<!DOCTYPE html>
	<html>
	<head>
		<style>
			body {{ font-family: Arial, sans-serif; margin: 40px; }}
			h1 {{ color: #333; border-bottom: 2px solid #333; padding-bottom: 10px; }}
			table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
			th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
			th {{ background-color: #f5f5f5; }}
			.header {{ display: flex; justify-content: space-between; }}
			.supplier-box {{ background: #f9f9f9; padding: 15px; margin: 20px 0; }}
		</style>
	</head>
	<body>
		<h1>PURCHASE ORDER</h1>
		<div class="header">
			<div><strong>PO Number:</strong> {po.name}</div>
			<div><strong>Date:</strong> {po.po_issue_date or today()}</div>
		</div>
		
		<div class="supplier-box">
			<h3>Supplier</h3>
			<p><strong>{supplier_info.get('supplier_name', 'N/A')}</strong></p>
			<p>{supplier_info.get('address', '')}</p>
			<p>Contact: {supplier_info.get('contact_person', '')} | Phone: {supplier_info.get('phone', '')} | Email: {supplier_info.get('email', '')}</p>
		</div>
		
		<table>
			<tr>
				<th>Item Description</th>
				<th>Part Number</th>
				<th>Quantity</th>
				<th>Unit Price</th>
				<th>Total</th>
			</tr>
			<tr>
				<td>{po.item_name}</td>
				<td>{po.part_number}</td>
				<td>{po.quantity}</td>
				<td>{selected_quote.quote_amount if selected_quote else 'N/A'} {selected_quote.currency if selected_quote else ''}</td>
				<td>{(selected_quote.quote_amount or 0) * po.quantity if selected_quote else 'N/A'}</td>
			</tr>
		</table>
		
		<p><strong>Aircraft:</strong> {po.aircraft or 'N/A'}</p>
		<p><strong>Notes:</strong> {po.notes or 'None'}</p>
		
		<hr>
		<p><strong>Created By:</strong> {po.created_by_user}</p>
		<p><strong>Approved By:</strong> {po.approved_by_user or 'Pending'}</p>
	</body>
	</html>
	"""
	
	# Generate PDF
	from frappe.utils.pdf import get_pdf
	pdf_content = get_pdf(html)
	
	# Save to files
	file_name = f"PO_{po.name}.pdf"
	file_doc = frappe.get_doc({
		'doctype': 'File',
		'file_name': file_name,
		'content': pdf_content,
		'attached_to_doctype': 'Purchase Order',
		'attached_to_name': po.name,
		'is_private': 0
	})
	file_doc.save(ignore_permissions=True)
	
	# Update PO with PDF link
	frappe.db.set_value('Purchase Order', po.name, 'po_pdf', file_doc.file_url)
	
	return {
		'success': True,
		'file_url': file_doc.file_url,
		'message': 'PO PDF generated successfully'
	}


@frappe.whitelist()
def send_po_to_supplier(po_name):
	"""Send PO PDF to supplier via email"""
	po = frappe.get_doc('Purchase Order', po_name)
	
	if not po.po_pdf:
		return {'success': False, 'message': 'Please generate PO PDF first'}
	
	# Get selected supplier email
	selected_quote = None
	for quote in po.quotes:
		if quote.is_selected:
			selected_quote = quote
			break
	
	if not selected_quote:
		return {'success': False, 'message': 'No quote selected'}
	
	supplier_email = frappe.db.get_value('Supplier', selected_quote.supplier, 'email')
	if not supplier_email:
		return {'success': False, 'message': 'Supplier has no email address'}
	
	subject = f"Purchase Order {po.name} - {po.item_name}"
	message = f"""
	<p>Dear Supplier,</p>
	<p>Please find attached our Purchase Order {po.name}.</p>
	<p><strong>Item:</strong> {po.item_name}<br>
	<strong>Part Number:</strong> {po.part_number}<br>
	<strong>Quantity:</strong> {po.quantity}</p>
	<p>Please confirm receipt and expected delivery date.</p>
	<p>Best regards</p>
	"""
	
	try:
		frappe.sendmail(
			recipients=[supplier_email],
			subject=subject,
			message=message,
			attachments=[{
				'fname': f"PO_{po.name}.pdf",
				'fcontent': frappe.get_doc('File', {'file_url': po.po_pdf}).get_content()
			}],
			reference_doctype='Purchase Order',
			reference_name=po.name
		)
		return {'success': True, 'message': f'PO sent to {supplier_email}'}
	except Exception as e:
		frappe.log_error(str(e), "Send PO Email")
		return {'success': False, 'message': str(e)}
