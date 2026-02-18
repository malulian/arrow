# Copyright (c) 2026, osher and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AMPDocument(Document):
	def validate(self):
		self.update_document_number()
		self.validate_registrations()

	def update_document_number(self):
		if not self.document_number and self.aircraft_type:
			self.document_number = f"AMP {self.aircraft_type}"

	def validate_registrations(self):
		seen = set()
		for reg in self.registrations:
			if reg.registration in seen:
				frappe.throw(f"Duplicate registration: {reg.registration}")
			seen.add(reg.registration)

	def get_active_registrations(self):
		return [r for r in self.registrations if r.active]

	def get_registration_list(self):
		return ", ".join(r.registration for r in self.get_active_registrations())

	def get_serial_number_list(self):
		return ", ".join(r.serial_number for r in self.get_active_registrations())

	def get_chapters(self, section_type=None):
		filters = {"amp_document": self.name}
		if section_type:
			filters["section_type"] = section_type
		return frappe.get_all(
			"AMP Chapter",
			filters=filters,
			fields=["*"],
			order_by="sort_order asc",
		)

	def get_revisions(self):
		return frappe.get_all(
			"AMP Revision",
			filters={"amp_document": self.name},
			fields=["*"],
			order_by="revision_date desc",
		)

	def get_active_task_notes(self):
		return frappe.get_all(
			"AMP Task Note",
			filters={"amp_document": self.name, "status": "Active"},
			fields=["*"],
			order_by="chapter asc, task_number asc",
		)

	@frappe.whitelist()
	def update_revision_info(self):
		"""Update current revision info from the latest approved revision."""
		latest = frappe.get_all(
			"AMP Revision",
			filters={"amp_document": self.name, "status": "Approved"},
			fields=["revision_number", "revision_date"],
			order_by="revision_date desc",
			limit=1,
		)
		if latest:
			self.current_revision = latest[0].revision_number
			self.current_revision_date = latest[0].revision_date
			self.save()

	@frappe.whitelist()
	def generate_pdf(self):
		"""Generate the complete AMP PDF document."""
		from arrow.amp.amp_pdf_generator import generate_amp_pdf
		return generate_amp_pdf(self.name)
