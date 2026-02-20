# Copyright (c) 2026, osher and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class TestAMPDocument(IntegrationTestCase):
	def setUp(self):
		self.amp_doc = frappe.get_doc(
			{
				"doctype": "AMP Document",
				"aircraft_type": "Hawker 800XP",
				"document_number": "AMP Hawker 800XP Test",
				"operator_name": "Arrow Aviation",
				"engine_type": "TFE 731-5BR-1H",
				"apu_type": "GTCP36-150W",
				"registrations": [
					{
						"registration": "4X-CUT",
						"serial_number": "258609",
						"active": 1,
					},
					{
						"registration": "4X-CUZ",
						"serial_number": "258345",
						"active": 1,
					},
				],
			}
		)

	def test_create_amp_document(self):
		self.amp_doc.insert()
		self.assertTrue(self.amp_doc.name)
		self.assertEqual(self.amp_doc.status, "Draft")
		self.amp_doc.delete()

	def test_duplicate_registration_validation(self):
		self.amp_doc.registrations.append(
			frappe._dict(
				{
					"registration": "4X-CUT",
					"serial_number": "999999",
					"active": 1,
				}
			)
		)
		self.assertRaises(frappe.exceptions.ValidationError, self.amp_doc.insert)

	def test_registration_list(self):
		self.amp_doc.insert()
		reg_list = self.amp_doc.get_registration_list()
		self.assertIn("4X-CUT", reg_list)
		self.assertIn("4X-CUZ", reg_list)
		self.amp_doc.delete()

	def test_auto_document_number(self):
		doc = frappe.get_doc(
			{
				"doctype": "AMP Document",
				"aircraft_type": "Test Type",
				"operator_name": "Test Operator",
				"registrations": [
					{
						"registration": "4X-TST",
						"serial_number": "000001",
						"active": 1,
					}
				],
			}
		)
		doc.insert()
		self.assertEqual(doc.document_number, "AMP Test Type")
		doc.delete()
