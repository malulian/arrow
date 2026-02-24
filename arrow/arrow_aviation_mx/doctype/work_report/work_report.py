# Copyright (c) 2026, osher and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today, now_datetime, time_diff_in_hours, get_time


class WorkReport(Document):
	def autoname(self):
		"""Set report number"""
		self.report_number = self.name
	
	def validate(self):
		"""Validate work report"""
		self.calculate_total_hours()
		self.validate_parts_availability()
		self.check_duplicate_parts()
	
	def calculate_total_hours(self):
		"""Calculate total hours from start and end time"""
		if self.start_time and self.end_time:
			start = get_time(self.start_time)
			end = get_time(self.end_time)
			
			# Calculate difference in minutes
			start_minutes = start.hour * 60 + start.minute
			end_minutes = end.hour * 60 + end.minute
			
			# Handle overnight work
			if end_minutes < start_minutes:
				end_minutes += 24 * 60
			
			diff_minutes = end_minutes - start_minutes
			self.total_hours = round(diff_minutes / 60, 2)
			
			# Set HH:MM display format
			hours = diff_minutes // 60
			minutes = diff_minutes % 60
			self.total_hours_display = f"{hours:02d}:{minutes:02d}"
	
	def check_duplicate_parts(self):
		"""Check if parts were already reported by another technician for same aircraft/time"""
		if not self.parts_used:
			return
		
		# Skip if user already confirmed
		if self.duplicate_parts_confirmed:
			return
		
		# Find overlapping work reports for same aircraft on same date
		overlapping_reports = frappe.get_all(
			'Work Report',
			filters={
				'work_date': self.work_date,
				'aircraft': self.aircraft,
				'name': ['!=', self.name or ''],
				'docstatus': ['<', 2]  # Not cancelled
			},
			fields=['name', 'technician', 'start_time', 'end_time']
		)
		
		if not overlapping_reports:
			return
		
		# Check if times overlap
		my_start = get_time(self.start_time)
		my_end = get_time(self.end_time)
		my_start_mins = my_start.hour * 60 + my_start.minute
		my_end_mins = my_end.hour * 60 + my_end.minute
		if my_end_mins < my_start_mins:
			my_end_mins += 24 * 60
		
		duplicate_parts = []
		
		for report in overlapping_reports:
			# Check time overlap
			other_start = get_time(report.start_time)
			other_end = get_time(report.end_time)
			other_start_mins = other_start.hour * 60 + other_start.minute
			other_end_mins = other_end.hour * 60 + other_end.minute
			if other_end_mins < other_start_mins:
				other_end_mins += 24 * 60
			
			# Check if times overlap
			if not (my_end_mins <= other_start_mins or my_start_mins >= other_end_mins):
				# Times overlap - check for duplicate parts
				other_parts = frappe.get_all(
					'Work Report Part',
					filters={'parent': report.name},
					fields=['part', 'part_number', 'quantity_used']
				)
				
				for my_part in self.parts_used:
					for other_part in other_parts:
						if my_part.part == other_part.part:
							technician_name = frappe.db.get_value('User', report.technician, 'full_name') or report.technician
							duplicate_parts.append({
								'part': my_part.part_number or my_part.part,
								'other_report': report.name,
								'other_technician': technician_name
							})
		
		if duplicate_parts:
			# Store duplicate info for client-side confirmation
			self._duplicate_parts_warning = duplicate_parts
	
	def validate_parts_availability(self):
		"""Check if requested parts are available in inventory"""
		if not self.parts_used:
			return
		
		insufficient = []
		for part in self.parts_used:
			if part.part:
				available = frappe.db.get_value('Inventory Item', part.part, 'quantity') or 0
				if part.quantity_used > available:
					item_name = frappe.db.get_value('Inventory Item', part.part, 'item_name')
					insufficient.append(f"{item_name}: requested {part.quantity_used}, available {available}")
		
		if insufficient:
			frappe.throw(
				f"Insufficient inventory for the following parts:\n" + "\n".join(insufficient),
				title="Insufficient Inventory"
			)
	
	def on_submit(self):
		"""Actions on submit"""
		self.deduct_parts_from_inventory()
		self.send_parts_notification()
	
	def deduct_parts_from_inventory(self):
		"""Deduct used parts from inventory"""
		if not self.parts_used:
			return
		
		for part in self.parts_used:
			if part.part and part.quantity_used > 0:
				# Check if already deducted (prevent duplicate deduction)
				existing_transaction = frappe.db.exists(
					'Inventory Transaction',
					{
						'reference_doctype': 'Work Report',
						'reference_name': self.name,
						'inventory_item': part.part,
						'transaction_type': 'Withdraw'
					}
				)
				
				if existing_transaction:
					# Already deducted, skip
					continue
				
				# Deduct from Inventory Item
				inv_item = frappe.get_doc('Inventory Item', part.part)
				inv_item.quantity = (inv_item.quantity or 0) - part.quantity_used
				inv_item.last_withdrawal_date = today()
				inv_item.save(ignore_permissions=True)
				
				# Create transaction record
				frappe.get_doc({
					'doctype': 'Inventory Transaction',
					'inventory_item': part.part,
					'transaction_type': 'Withdraw',
					'quantity': part.quantity_used,
					'reference_doctype': 'Work Report',
					'reference_name': self.name,
					'notes': f'Used in Work Report {self.name} on aircraft {self.aircraft}'
				}).insert(ignore_permissions=True)
	
	def send_parts_notification(self):
		"""Send email notification when parts are used"""
		if not self.parts_used or len(self.parts_used) == 0:
			return
		
		# Get notification recipient (could be from settings)
		recipient = frappe.db.get_single_value('System Settings', 'admin_email') or 'admin@example.com'
		
		# Build parts table
		parts_html = ""
		for part in self.parts_used:
			parts_html += f"""
			<tr>
				<td>{part.part_number or 'N/A'}</td>
				<td>{part.quantity_used}</td>
			</tr>
			"""
		
		subject = f"Work Report {self.name} - Parts Used on {self.aircraft}"
		message = f"""
		<h3>Work Report with Parts Used</h3>
		<p>A work report has been submitted with parts usage:</p>
		<table border="1" cellpadding="5" style="border-collapse: collapse;">
			<tr><td><b>Report Number:</b></td><td>{self.name}</td></tr>
			<tr><td><b>Aircraft:</b></td><td>{self.aircraft}</td></tr>
			<tr><td><b>Technician:</b></td><td>{self.technician}</td></tr>
			<tr><td><b>Work Date:</b></td><td>{self.work_date}</td></tr>
			<tr><td><b>Total Hours:</b></td><td>{self.total_hours}</td></tr>
		</table>
		
		<h4>Parts Used:</h4>
		<table border="1" cellpadding="5" style="border-collapse: collapse;">
			<tr><th>Part Number</th><th>Quantity</th></tr>
			{parts_html}
		</table>
		
		<p>Please update part prices for accounting.</p>
		<p><a href="{frappe.utils.get_url_to_form('Work Report', self.name)}">Click here to view report</a></p>
		"""
		
		try:
			frappe.sendmail(
				recipients=[recipient],
				subject=subject,
				message=message,
				reference_doctype='Work Report',
				reference_name=self.name
			)
		except Exception as e:
			frappe.log_error(f"Failed to send parts notification: {str(e)}", "Work Report Email")


@frappe.whitelist()
def check_duplicate_parts_api(work_date, aircraft, start_time, end_time, parts, current_name=None):
	"""Check for duplicate parts before saving - returns warning if found"""
	import json
	
	if isinstance(parts, str):
		parts = json.loads(parts)
	
	if not parts:
		return {'has_duplicates': False}
	
	# Find overlapping work reports for same aircraft on same date
	filters = {
		'work_date': work_date,
		'aircraft': aircraft,
		'docstatus': ['<', 2]
	}
	if current_name:
		filters['name'] = ['!=', current_name]
	
	overlapping_reports = frappe.get_all(
		'Work Report',
		filters=filters,
		fields=['name', 'technician', 'start_time', 'end_time']
	)
	
	if not overlapping_reports:
		return {'has_duplicates': False}
	
	# Parse times
	my_start = get_time(start_time)
	my_end = get_time(end_time)
	my_start_mins = my_start.hour * 60 + my_start.minute
	my_end_mins = my_end.hour * 60 + my_end.minute
	if my_end_mins < my_start_mins:
		my_end_mins += 24 * 60
	
	duplicate_parts = []
	
	for report in overlapping_reports:
		other_start = get_time(report.start_time)
		other_end = get_time(report.end_time)
		other_start_mins = other_start.hour * 60 + other_start.minute
		other_end_mins = other_end.hour * 60 + other_end.minute
		if other_end_mins < other_start_mins:
			other_end_mins += 24 * 60
		
		# Check if times overlap
		if not (my_end_mins <= other_start_mins or my_start_mins >= other_end_mins):
			other_parts = frappe.get_all(
				'Work Report Part',
				filters={'parent': report.name},
				fields=['part', 'part_number']
			)
			
			for my_part in parts:
				part_name = my_part.get('part')
				if part_name:
					for other_part in other_parts:
						if part_name == other_part.part:
							technician_name = frappe.db.get_value('User', report.technician, 'full_name') or report.technician
							duplicate_parts.append({
								'part': other_part.part_number or part_name,
								'other_report': report.name,
								'other_technician': technician_name
							})
	
	if duplicate_parts:
		return {
			'has_duplicates': True,
			'duplicates': duplicate_parts
		}
	
	return {'has_duplicates': False}


@frappe.whitelist()
def generate_work_report_pdf(report_name):
	"""Generate PDF for work report"""
	report = frappe.get_doc('Work Report', report_name)
	
	# Build work types HTML
	work_types = []
	if report.oxygen_fill:
		work_types.append("מילוי חמצן (Oxygen Fill)")
	if report.nitrogen_fill:
		work_types.append("מילוי חנקן (Nitrogen Fill)")
	if report.tks_fill:
		work_types.append("מילוי TKS")
	if report.hydraulic_oil_fill:
		work_types.append("מילוי שמן הידראולי (Hydraulic Oil)")
	if report.gpu_usage:
		work_types.append(f"GPU ({report.gpu_hours or 0} hours)")
	if report.wi_di:
		work_types.append("WI/DI")
	
	work_types_html = "<br>".join(work_types) if work_types else "None specified"
	
	# Build parts table
	parts_html = ""
	if report.parts_used:
		parts_html = """
		<table border="1" cellpadding="5" style="border-collapse: collapse; width: 100%;">
			<tr style="background: #f5f5f5;"><th>Part Number</th><th>Quantity</th></tr>
		"""
		for part in report.parts_used:
			parts_html += f"<tr><td>{part.part_number or 'N/A'}</td><td>{part.quantity_used}</td></tr>"
		parts_html += "</table>"
	else:
		parts_html = "<p>No parts used</p>"
	
	# Get technician full name
	technician_name = frappe.db.get_value('User', report.technician, 'full_name') or report.technician
	
	html = f"""
	<!DOCTYPE html>
	<html>
	<head>
		<style>
			body {{ font-family: Arial, sans-serif; margin: 40px; }}
			h1 {{ color: #333; border-bottom: 2px solid #333; padding-bottom: 10px; text-align: center; }}
			.info-table {{ width: 100%; margin: 20px 0; }}
			.info-table td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
			.label {{ font-weight: bold; width: 30%; }}
			.section {{ margin: 20px 0; }}
			.section-title {{ font-weight: bold; font-size: 14px; margin-bottom: 10px; border-bottom: 1px solid #333; }}
			.signature-box {{ border: 1px solid #333; padding: 10px; min-height: 80px; margin-top: 10px; }}
		</style>
	</head>
	<body>
		<h1>WORK REPORT</h1>
		
		<table class="info-table">
			<tr><td class="label">Report Number:</td><td>{report.name}</td></tr>
			<tr><td class="label">Work Date:</td><td>{report.work_date}</td></tr>
			<tr><td class="label">Aircraft:</td><td>{report.aircraft}</td></tr>
			<tr><td class="label">Technician:</td><td>{technician_name}</td></tr>
			<tr><td class="label">Start Time:</td><td>{report.start_time}</td></tr>
			<tr><td class="label">End Time:</td><td>{report.end_time}</td></tr>
			<tr><td class="label">Total Hours:</td><td>{report.total_hours}</td></tr>
		</table>
		
		<div class="section">
			<div class="section-title">Work Performed</div>
			{work_types_html}
		</div>
		
		<div class="section">
			<div class="section-title">Parts Used</div>
			{parts_html}
		</div>
		
		<div class="section">
			<div class="section-title">Notes</div>
			{report.notes or 'None'}
		</div>
		
		<div class="section">
			<div class="section-title">Technician Signature</div>
			<div class="signature-box">
				{f'<img src="{report.signature}" style="max-height: 60px;">' if report.signature else 'Not signed'}
			</div>
		</div>
	</body>
	</html>
	"""
	
	# Generate PDF
	from frappe.utils.pdf import get_pdf
	pdf_content = get_pdf(html)
	
	# Save to files
	file_name = f"Work_Report_{report.name}.pdf"
	file_doc = frappe.get_doc({
		'doctype': 'File',
		'file_name': file_name,
		'content': pdf_content,
		'attached_to_doctype': 'Work Report',
		'attached_to_name': report.name,
		'is_private': 0
	})
	file_doc.save(ignore_permissions=True)
	
	return {
		'success': True,
		'file_url': file_doc.file_url,
		'message': 'Work Report PDF generated successfully'
	}


@frappe.whitelist()
def send_report_email(report_name, recipient_email):
	"""Send work report PDF to specified email"""
	result = generate_work_report_pdf(report_name)
	
	if not result.get('success'):
		return {'success': False, 'message': 'Failed to generate PDF'}
	
	report = frappe.get_doc('Work Report', report_name)
	
	subject = f"Work Report {report_name} - {report.aircraft} - {report.work_date}"
	message = f"""
	<p>Please find attached the work report for:</p>
	<ul>
		<li><strong>Aircraft:</strong> {report.aircraft}</li>
		<li><strong>Date:</strong> {report.work_date}</li>
		<li><strong>Technician:</strong> {report.technician}</li>
		<li><strong>Total Hours:</strong> {report.total_hours}</li>
	</ul>
	"""
	
	try:
		file_doc = frappe.get_doc('File', {'file_url': result['file_url']})
		frappe.sendmail(
			recipients=[recipient_email],
			subject=subject,
			message=message,
			attachments=[{
				'fname': f"Work_Report_{report_name}.pdf",
				'fcontent': file_doc.get_content()
			}],
			reference_doctype='Work Report',
			reference_name=report_name
		)
		return {'success': True, 'message': f'Report sent to {recipient_email}'}
	except Exception as e:
		frappe.log_error(str(e), "Send Work Report Email")
		return {'success': False, 'message': str(e)}


@frappe.whitelist()
def fix_inventory_for_submitted_reports(submit_drafts=False):
	"""Fix inventory deduction for all submitted work reports that are missing inventory transactions
	
	Args:
		submit_drafts: If True, will also submit draft reports with parts and deduct inventory
	"""
	
	# Get reports based on parameter
	if submit_drafts:
		# Get all draft reports (0) and submitted reports (1)
		all_reports = frappe.get_all(
			'Work Report',
			filters={'docstatus': ['in', [0, 1]]},
			fields=['name', 'aircraft', 'work_date', 'docstatus']
		)
	else:
		# Get only submitted work reports
		all_reports = frappe.get_all(
			'Work Report',
			filters={'docstatus': 1},  # 1 = Submitted
			fields=['name', 'aircraft', 'work_date', 'docstatus']
		)
	
	reports_fixed = 0
	reports_submitted = 0
	parts_deducted = 0
	errors = []
	
	for report_data in all_reports:
		try:
			report = frappe.get_doc('Work Report', report_data.name)
			
			if not report.parts_used:
				continue
			
			# If report is draft and submit_drafts is True, submit it first
			if report.docstatus == 0 and submit_drafts:
				try:
					report.submit()
					reports_submitted += 1
					# The on_submit hook will handle inventory deduction
					# Skip to next report since deduction is done
					reports_fixed += 1
					continue
				except Exception as e:
					error_msg = f"Error submitting draft report {report.name}: {str(e)}"
					errors.append(error_msg)
					frappe.log_error(error_msg, "Submit Draft Report")
					continue
			
			# Only process submitted reports for fixing inventory
			if report.docstatus != 1:
				continue
			
			report_has_missing_deductions = False
			
			for part in report.parts_used:
				if not part.part or part.quantity_used <= 0:
					continue
				
				# Check if this part was already deducted
				existing_transaction = frappe.db.exists(
					'Inventory Transaction',
					{
						'reference_doctype': 'Work Report',
						'reference_name': report.name,
						'inventory_item': part.part,
						'transaction_type': 'Withdraw'
					}
				)
				
				if existing_transaction:
					# Already deducted
					continue
				
				# This part needs to be deducted
				report_has_missing_deductions = True
				
				# Get inventory item
				inv_item = frappe.get_doc('Inventory Item', part.part)
				
				# Deduct from inventory
				inv_item.quantity = (inv_item.quantity or 0) - part.quantity_used
				inv_item.last_withdrawal_date = today()
				inv_item.save(ignore_permissions=True)
				
				# Create transaction record
				frappe.get_doc({
					'doctype': 'Inventory Transaction',
					'inventory_item': part.part,
					'transaction_type': 'Withdraw',
					'quantity': part.quantity_used,
					'reference_doctype': 'Work Report',
				'reference_name': report.name,
				'notes': f'Used in Work Report {report.name} on aircraft {report.aircraft} (Fixed by script)'
			}).insert(ignore_permissions=True)
			
			parts_deducted += 1
		
			if report_has_missing_deductions:
				reports_fixed += 1
				
		except Exception as e:
			error_msg = f"Error processing report {report_data.name}: {str(e)}"
			errors.append(error_msg)
			frappe.log_error(error_msg, "Fix Inventory Deduction")
	
	# Commit changes
	frappe.db.commit()
	
	return {
		'success': True,
		'reports_fixed': reports_fixed,
		'reports_submitted': reports_submitted,
		'parts_deducted': parts_deducted,
		'total_reports_checked': len(all_reports),
		'errors': errors
	}
