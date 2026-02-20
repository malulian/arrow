# Copyright (c) 2026, osher and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AMPTaskNote(Document):
	def validate(self):
		self.validate_effective_dates()

	def validate_effective_dates(self):
		if self.effective_until == "Specific Date" and not self.effective_until_date:
			frappe.throw("Please specify the effective until date")
		if (
			self.effective_until == "Specific Date"
			and self.effective_until_date
			and self.effective_from
			and self.effective_until_date < self.effective_from
		):
			frappe.throw("Effective Until Date cannot be before Effective From date")
