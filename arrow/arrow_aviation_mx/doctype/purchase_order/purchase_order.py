# Copyright (c) 2026, osher and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, today, getdate, random_string


class PurchaseOrder(Document):
	def autoname(self):
		"""Generate PO number"""
		self.po_number = self.name

	def validate(self):
		"""Validate purchase order"""
		self.link_inventory_by_part_number()
		self.update_selected_quote_info()

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
		if self.has_value_changed('status'):
			self.handle_status_change()

	def handle_status_change(self):
		"""Handle status change actions"""
		if self.status == 'Awaiting Approval':
			self.generate_approval_token()
			self.send_approval_notification()

		elif self.status == 'Approved':
			self.approval_date = now_datetime()

		elif self.status == 'Received':
			self.handle_item_received()

		elif self.status == 'Pending Inspection':
			if self.inspection_user:
				self.send_inspection_notification()

		elif self.status == 'Completed':
			self.handle_order_completed()

	def generate_approval_token(self):
		"""Generate a unique token for email-based approval"""
		self.approval_token = random_string(32)

	def send_approval_notification(self):
		"""Send detailed email to approver with approve/reject options"""
		if not self.approved_by_user:
			return

		approver_email = frappe.db.get_value('User', self.approved_by_user, 'email')
		if not approver_email:
			return

		# Build quotes table HTML
		quotes_html = ""
		if self.quotes:
			quotes_html = """
			<table border="1" cellpadding="8" style="border-collapse: collapse; width: 100%; margin: 15px 0;">
				<tr style="background: #f5f5f5;">
					<th style="text-align: left;">#</th>
					<th style="text-align: left;">Supplier</th>
					<th style="text-align: left;">Amount</th>
					<th style="text-align: left;">Currency</th>
					<th style="text-align: left;">Delivery Time</th>
					<th style="text-align: left;">Approved Supplier</th>
					<th style="text-align: center;">Action</th>
				</tr>
			"""
			base_url = frappe.utils.get_url()
			for idx, quote in enumerate(self.quotes):
				approved_badge = '<span style="color: green;">Yes</span>' if quote.is_approved_supplier else '<span style="color: orange;">No</span>'
				approve_url = f"{base_url}/api/method/arrow.arrow_aviation_mx.doctype.purchase_order.purchase_order.approve_order_via_email?token={self.approval_token}&action=approve&quote_idx={idx + 1}"
				quotes_html += f"""
				<tr>
					<td>{idx + 1}</td>
					<td>{quote.supplier_name or quote.supplier}</td>
					<td>{quote.quote_amount}</td>
					<td>{quote.currency or 'USD'}</td>
					<td>{quote.estimated_delivery_time or 'N/A'}</td>
					<td>{approved_badge}</td>
					<td style="text-align: center;">
						<a href="{approve_url}" style="display: inline-block; padding: 6px 16px; background: #28a745; color: white; text-decoration: none; border-radius: 4px; font-size: 13px;">Approve</a>
					</td>
				</tr>
				"""
			quotes_html += "</table>"

		# Build reject URL
		base_url = frappe.utils.get_url()
		reject_url = f"{base_url}/api/method/arrow.arrow_aviation_mx.doctype.purchase_order.purchase_order.approve_order_via_email?token={self.approval_token}&action=reject"
		order_url = frappe.utils.get_url_to_form('Purchase Order', self.name)

		# Get creator full name
		creator_name = frappe.db.get_value('User', self.created_by_user, 'full_name') or self.created_by_user

		subject = f"Purchase Order {self.name} - Approval Required"
		message = f"""
		<div style="font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto;">
			<h2 style="color: #333; border-bottom: 2px solid #333; padding-bottom: 10px;">Purchase Order - Approval Required</h2>

			<table style="width: 100%; margin: 15px 0; border-collapse: collapse;">
				<tr><td style="padding: 6px 0; font-weight: bold; width: 40%;">PO Number:</td><td>{self.name}</td></tr>
				<tr><td style="padding: 6px 0; font-weight: bold;">Item:</td><td>{self.item_name}</td></tr>
				<tr><td style="padding: 6px 0; font-weight: bold;">Part Number:</td><td>{self.part_number}</td></tr>
				<tr><td style="padding: 6px 0; font-weight: bold;">Quantity:</td><td>{self.quantity}</td></tr>
				<tr><td style="padding: 6px 0; font-weight: bold;">Aircraft:</td><td>{self.aircraft}</td></tr>
				<tr><td style="padding: 6px 0; font-weight: bold;">Market Price:</td><td>{self.market_price or 'N/A'}</td></tr>
				<tr><td style="padding: 6px 0; font-weight: bold;">Created By:</td><td>{creator_name}</td></tr>
				<tr><td style="padding: 6px 0; font-weight: bold;">Date:</td><td>{self.creation_date}</td></tr>
			</table>

			<h3 style="color: #333; margin-top: 20px;">Price Quotes</h3>
			{quotes_html if quotes_html else '<p style="color: #999;">No quotes attached yet.</p>'}

			<p style="margin-top: 10px; color: #666; font-size: 13px;">Click "Approve" next to the quote you want to proceed with.</p>

			<div style="margin: 25px 0; text-align: center;">
				<a href="{reject_url}" style="display: inline-block; padding: 10px 30px; background: #dc3545; color: white; text-decoration: none; border-radius: 4px; font-size: 14px;">Reject Order</a>
			</div>

			<hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
			<p style="color: #666; font-size: 12px;">
				Need more details? <a href="{order_url}">View full order on the system</a>
			</p>
		</div>
		"""

		try:
			frappe.sendmail(
				recipients=[approver_email],
				subject=subject,
				message=message,
				reference_doctype='Purchase Order',
				reference_name=self.name
			)
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
		<div style="font-family: Arial, sans-serif; max-width: 600px;">
			<h3>Item Awaiting Receiving Inspection</h3>
			<table style="width: 100%; border-collapse: collapse;">
				<tr><td style="padding: 6px 0; font-weight: bold; width: 40%;">PO Number:</td><td>{self.name}</td></tr>
				<tr><td style="padding: 6px 0; font-weight: bold;">Item:</td><td>{self.item_name}</td></tr>
				<tr><td style="padding: 6px 0; font-weight: bold;">Part Number:</td><td>{self.part_number}</td></tr>
				<tr><td style="padding: 6px 0; font-weight: bold;">Quantity:</td><td>{self.quantity}</td></tr>
				<tr><td style="padding: 6px 0; font-weight: bold;">Received Date:</td><td>{self.received_date or 'N/A'}</td></tr>
			</table>
			<p><a href="{frappe.utils.get_url_to_form('Purchase Order', self.name)}">Click here to perform inspection</a></p>
		</div>
		"""

		try:
			frappe.sendmail(
				recipients=[inspector_email],
				subject=subject,
				message=message,
				reference_doctype='Purchase Order',
				reference_name=self.name
			)
		except Exception as e:
			frappe.log_error(f"Failed to send inspection email: {str(e)}", "Purchase Order Email")

	def handle_item_received(self):
		"""Handle when item is physically received - create/update inventory item"""
		if not self.part_number:
			return

		# Check if inventory item exists
		inventory_item = frappe.db.get_value(
			'Inventory Item',
			{'part_number': self.part_number},
			'name'
		)

		if inventory_item:
			# Item exists - set pending receiving inspection flag
			inv_doc = frappe.get_doc('Inventory Item', inventory_item)
			inv_doc.pending_receiving_inspection = 1
			inv_doc.save(ignore_permissions=True)
			self.linked_inventory_item = inventory_item
		else:
			# Create new inventory item with pending inspection
			inv_doc = frappe.get_doc({
				'doctype': 'Inventory Item',
				'item_name': self.item_name,
				'part_number': self.part_number,
				'quantity': 0,
				'pending_receiving_inspection': 1,
				'notes': f'Created from Purchase Order {self.name}'
			})
			inv_doc.insert(ignore_permissions=True)
			self.linked_inventory_item = inv_doc.name

	def handle_order_completed(self):
		"""Handle order completion - update inventory quantity and clear inspection flag"""
		if not self.linked_inventory_item:
			return

		try:
			inv_item = frappe.get_doc('Inventory Item', self.linked_inventory_item)
			inv_item.quantity = (inv_item.quantity or 0) + self.quantity
			inv_item.last_received_date = self.received_date or today()
			inv_item.pending_receiving_inspection = 0
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

	def on_update(self):
		"""After save actions - kept for backward compatibility"""
		pass


@frappe.whitelist(allow_guest=True)
def approve_order_via_email(token, action, quote_idx=None):
	"""Handle approval/rejection via email link"""
	if not token:
		frappe.respond_as_web_page(
			"Error",
			"Invalid request - missing token.",
			indicator_color="red"
		)
		return

	# Find the PO with this token
	po_name = frappe.db.get_value('Purchase Order', {'approval_token': token}, 'name')
	if not po_name:
		frappe.respond_as_web_page(
			"Error",
			"Invalid or expired approval link.",
			indicator_color="red"
		)
		return

	po = frappe.get_doc('Purchase Order', po_name)

	if po.status != 'Awaiting Approval':
		status_msg = "approved" if po.status in ('Approved', 'Ordered', 'Sent', 'Received', 'Pending Inspection', 'Completed') else po.status.lower()
		frappe.respond_as_web_page(
			"Already Processed",
			f"This order has already been {status_msg}.",
			indicator_color="blue"
		)
		return

	if action == 'approve':
		# Select the quote
		if quote_idx and po.quotes:
			idx = int(quote_idx) - 1
			if 0 <= idx < len(po.quotes):
				# Deselect all quotes first
				for q in po.quotes:
					q.is_selected = 0
				# Select the chosen quote
				po.quotes[idx].is_selected = 1

		po.status = 'Approved'
		po.approval_date = now_datetime()
		po.update_selected_quote_info()
		# Invalidate token after use
		po.approval_token = random_string(32)
		po.save(ignore_permissions=True)
		frappe.db.commit()

		frappe.respond_as_web_page(
			"Order Approved",
			f"""<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; text-align: center;">
				<h2 style="color: #28a745;">Order Approved Successfully</h2>
				<p>Purchase Order <b>{po.name}</b> has been approved.</p>
				<p><b>Item:</b> {po.item_name}</p>
				<p><b>Selected Supplier:</b> {po.selected_supplier_name or 'N/A'}</p>
				<p><b>Amount:</b> {po.selected_quote_amount or 'N/A'}</p>
				<br>
				<a href="{frappe.utils.get_url_to_form('Purchase Order', po.name)}" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px;">View Order</a>
			</div>""",
			indicator_color="green"
		)

	elif action == 'reject':
		po.status = 'Cancelled'
		# Invalidate token
		po.approval_token = random_string(32)
		po.save(ignore_permissions=True)
		frappe.db.commit()

		frappe.respond_as_web_page(
			"Order Rejected",
			f"""<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; text-align: center;">
				<h2 style="color: #dc3545;">Order Rejected</h2>
				<p>Purchase Order <b>{po.name}</b> has been rejected.</p>
				<br>
				<a href="{frappe.utils.get_url_to_form('Purchase Order', po.name)}" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px;">View Order</a>
			</div>""",
			indicator_color="red"
		)
	else:
		frappe.respond_as_web_page(
			"Error",
			"Invalid action.",
			indicator_color="red"
		)


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
			.supplier-box {{ background: #f9f9f9; padding: 15px; margin: 20px 0; }}
		</style>
	</head>
	<body>
		<h1>PURCHASE ORDER</h1>
		<div>
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

	from frappe.utils.pdf import get_pdf
	pdf_content = get_pdf(html)

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

	frappe.db.set_value('Purchase Order', po.name, 'po_pdf', file_doc.file_url)

	return {
		'success': True,
		'file_url': file_doc.file_url,
		'message': 'PO PDF generated successfully'
	}


@frappe.whitelist()
def generate_rfq_pdf(po_name):
	"""Generate RFQ (Request for Quotation) PDF document"""
	po = frappe.get_doc('Purchase Order', po_name)

	html = f"""
	<!DOCTYPE html>
	<html>
	<head>
		<style>
			body {{ font-family: Arial, sans-serif; margin: 40px; }}
			h1 {{ color: #333; border-bottom: 2px solid #333; padding-bottom: 10px; text-align: center; }}
			h2 {{ color: #555; font-size: 16px; }}
			table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
			th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
			th {{ background-color: #f5f5f5; }}
			.info-box {{ background: #f9f9f9; padding: 15px; margin: 20px 0; }}
			.response-section {{ margin-top: 30px; }}
			.response-section td {{ height: 40px; }}
		</style>
	</head>
	<body>
		<h1>REQUEST FOR QUOTATION</h1>
		<p style="text-align: center; color: #666;">RFQ Reference: {po.name}</p>
		<p style="text-align: center; color: #666;">Date: {today()}</p>

		<div class="info-box">
			<h2>Item Details</h2>
			<table>
				<tr><td style="font-weight: bold; width: 30%;">Item Name</td><td>{po.item_name}</td></tr>
				<tr><td style="font-weight: bold;">Part Number</td><td>{po.part_number}</td></tr>
				<tr><td style="font-weight: bold;">Quantity Required</td><td>{po.quantity}</td></tr>
				<tr><td style="font-weight: bold;">Aircraft</td><td>{po.aircraft or 'N/A'}</td></tr>
			</table>
		</div>

		<div class="response-section">
			<h2>Supplier Response (please fill in)</h2>
			<table>
				<tr>
					<th>Field</th>
					<th>Details</th>
				</tr>
				<tr>
					<td style="font-weight: bold;">Company Name</td>
					<td></td>
				</tr>
				<tr>
					<td style="font-weight: bold;">Contact Person</td>
					<td></td>
				</tr>
				<tr>
					<td style="font-weight: bold;">Unit Price</td>
					<td></td>
				</tr>
				<tr>
					<td style="font-weight: bold;">Currency</td>
					<td></td>
				</tr>
				<tr>
					<td style="font-weight: bold;">Total Price</td>
					<td></td>
				</tr>
				<tr>
					<td style="font-weight: bold;">Estimated Delivery Time</td>
					<td></td>
				</tr>
				<tr>
					<td style="font-weight: bold;">Quote Valid Until</td>
					<td></td>
				</tr>
				<tr>
					<td style="font-weight: bold;">Notes / Conditions</td>
					<td></td>
				</tr>
			</table>
		</div>

		<div style="margin-top: 30px;">
			<p><strong>Signature:</strong> _________________________</p>
			<p><strong>Date:</strong> _________________________</p>
		</div>

		<hr style="margin-top: 40px;">
		<p style="color: #999; font-size: 11px;">
			Please return this form with your quotation. Reference: {po.name}
		</p>
	</body>
	</html>
	"""

	from frappe.utils.pdf import get_pdf
	pdf_content = get_pdf(html)

	file_name = f"RFQ_{po.name}.pdf"
	file_doc = frappe.get_doc({
		'doctype': 'File',
		'file_name': file_name,
		'content': pdf_content,
		'attached_to_doctype': 'Purchase Order',
		'attached_to_name': po.name,
		'is_private': 0
	})
	file_doc.save(ignore_permissions=True)

	return {
		'success': True,
		'file_url': file_doc.file_url,
		'message': 'RFQ PDF generated successfully'
	}


@frappe.whitelist()
def send_rfq_to_suppliers(po_name, supplier_names):
	"""Send RFQ PDF to selected suppliers via email"""
	import json

	po = frappe.get_doc('Purchase Order', po_name)

	if isinstance(supplier_names, str):
		supplier_names = json.loads(supplier_names)

	# Generate RFQ PDF
	rfq_result = generate_rfq_pdf(po_name)
	if not rfq_result.get('success'):
		return {'success': False, 'message': 'Failed to generate RFQ PDF'}

	file_doc = frappe.get_doc('File', {'file_url': rfq_result['file_url']})
	pdf_content = file_doc.get_content()

	sent_to = []
	errors = []

	for supplier_name in supplier_names:
		supplier_email = frappe.db.get_value('Supplier', supplier_name, 'email')
		supplier_display = frappe.db.get_value('Supplier', supplier_name, 'supplier_name')

		if not supplier_email:
			errors.append(f"{supplier_display}: no email address")
			continue

		subject = f"Request for Quotation - {po.item_name} (Ref: {po.name})"
		message = f"""
		<div style="font-family: Arial, sans-serif;">
			<p>Dear Supplier,</p>
			<p>Please find attached our Request for Quotation for the following item:</p>
			<table style="border-collapse: collapse; margin: 15px 0;">
				<tr><td style="padding: 5px 15px 5px 0; font-weight: bold;">Item:</td><td>{po.item_name}</td></tr>
				<tr><td style="padding: 5px 15px 5px 0; font-weight: bold;">Part Number:</td><td>{po.part_number}</td></tr>
				<tr><td style="padding: 5px 15px 5px 0; font-weight: bold;">Quantity:</td><td>{po.quantity}</td></tr>
			</table>
			<p>Please fill in the attached RFQ form and return it to us at your earliest convenience.</p>
			<p>We kindly request that you include the estimated delivery time and quote validity in your response.</p>
			<p>Best regards</p>
		</div>
		"""

		try:
			frappe.sendmail(
				recipients=[supplier_email],
				subject=subject,
				message=message,
				attachments=[{
					'fname': f"RFQ_{po.name}.pdf",
					'fcontent': pdf_content
				}],
				reference_doctype='Purchase Order',
				reference_name=po.name
			)
			sent_to.append(supplier_display)
		except Exception as e:
			errors.append(f"{supplier_display}: {str(e)}")
			frappe.log_error(str(e), "Send RFQ Email")

	result_msg = ""
	if sent_to:
		result_msg += f"RFQ sent to: {', '.join(sent_to)}. "
	if errors:
		result_msg += f"Errors: {'; '.join(errors)}"

	return {
		'success': len(sent_to) > 0,
		'message': result_msg,
		'sent_count': len(sent_to),
		'error_count': len(errors)
	}


@frappe.whitelist()
def send_po_to_supplier(po_name):
	"""Send PO PDF to supplier via email"""
	po = frappe.get_doc('Purchase Order', po_name)

	if not po.po_pdf:
		# Auto-generate if not exists
		result = generate_po_pdf(po_name)
		if not result.get('success'):
			return {'success': False, 'message': 'Failed to generate PO PDF'}
		po.reload()

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
	<div style="font-family: Arial, sans-serif;">
		<p>Dear Supplier,</p>
		<p>Please find attached our Purchase Order {po.name}.</p>
		<table style="border-collapse: collapse; margin: 15px 0;">
			<tr><td style="padding: 5px 15px 5px 0; font-weight: bold;">Item:</td><td>{po.item_name}</td></tr>
			<tr><td style="padding: 5px 15px 5px 0; font-weight: bold;">Part Number:</td><td>{po.part_number}</td></tr>
			<tr><td style="padding: 5px 15px 5px 0; font-weight: bold;">Quantity:</td><td>{po.quantity}</td></tr>
		</table>
		<p>Please confirm receipt and expected delivery date.</p>
		<p>Best regards</p>
	</div>
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


@frappe.whitelist()
def get_approved_suppliers_list():
	"""Get list of all suppliers for RFQ sending"""
	suppliers = frappe.get_all(
		'Supplier',
		fields=['name', 'supplier_name', 'email', 'is_approved'],
		order_by='supplier_name asc'
	)
	return suppliers
