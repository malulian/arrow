# Copyright (c) 2026, osher and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_months, getdate, today


class Supplier(Document):
	def autoname(self):
		"""Generate supplier code"""
		# Get next number in sequence
		count = frappe.db.count('Supplier') + 1
		self.supplier_code = f"SUP-{count:04d}"
	
	def validate(self):
		"""Validate and calculate survey dates"""
		self.update_survey_info()
		self.calculate_next_survey_date()
	
	def update_survey_info(self):
		"""Update survey info from the surveys table"""
		if self.surveys:
			# Get the latest survey
			latest_survey = max(self.surveys, key=lambda s: getdate(s.survey_date) if s.survey_date else getdate('1900-01-01'))
			
			if latest_survey.survey_date:
				self.is_surveyed = 1
				self.last_survey_date = latest_survey.survey_date
				
				# Update attachment if exists
				if latest_survey.attachment:
					self.last_survey_attachment = latest_survey.attachment
	
	def calculate_next_survey_date(self):
		"""Calculate next survey date based on last survey + interval"""
		if self.last_survey_date and self.survey_interval_months:
			self.next_survey_date = add_months(
				getdate(self.last_survey_date), 
				self.survey_interval_months
			)
		else:
			self.next_survey_date = None
	
	def before_save(self):
		"""Actions before saving"""
		# Check for overdue findings in surveys
		self.check_overdue_findings()
	
	def check_overdue_findings(self):
		"""Check if there are any overdue unresolved findings"""
		if not self.surveys:
			return
		
		today_date = getdate(today())
		overdue_findings = []
		
		for survey in self.surveys:
			if (survey.has_findings and 
				not survey.findings_resolved and 
				survey.findings_due_date and 
				getdate(survey.findings_due_date) < today_date):
				overdue_findings.append(survey.survey_date)
		
		if overdue_findings:
			frappe.msgprint(
				f"⚠️ This supplier has overdue unresolved findings from survey(s): {', '.join(str(d) for d in overdue_findings)}",
				title="Overdue Findings",
				indicator="orange"
			)


@frappe.whitelist()
def get_approved_suppliers():
	"""Get list of approved suppliers for use in other doctypes"""
	return frappe.get_all(
		'Supplier',
		filters={'is_approved': 1},
		fields=['name', 'supplier_name', 'email', 'phone']
	)
