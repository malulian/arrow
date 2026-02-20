# Copyright (c) 2026, osher and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AMPRevision(Document):
	def validate(self):
		self.validate_revision_number()

	def validate_revision_number(self):
		if not self.revision_number:
			frappe.throw("Revision Number is required")

	@frappe.whitelist()
	def approve_revision(self):
		"""Approve this revision and update all affected chapters."""
		self.status = "Approved"
		self.approval_date = frappe.utils.today()
		self.approved_by = frappe.session.user

		# Update affected chapters
		for row in self.affected_chapters:
			chapter = frappe.get_doc("AMP Chapter", row.chapter)
			chapter.revision = row.new_revision
			chapter.revision_date = self.revision_date
			chapter.effective_date = self.revision_date
			chapter.save()

		self.save()

		# Update parent AMP Document
		amp_doc = frappe.get_doc("AMP Document", self.amp_document)
		amp_doc.current_revision = self.revision_number
		amp_doc.current_revision_date = self.revision_date
		amp_doc.save()

		frappe.msgprint(
			f"Revision {self.revision_number} approved. {len(self.affected_chapters)} chapters updated.",
			title="Revision Approved",
			indicator="green",
		)
