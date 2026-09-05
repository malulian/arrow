# Copyright (c) 2026, osher and contributors
# For license information, please see license.txt

"""End-to-end tests for the Purchase Order Receiving workflow.

Covers: auto-creation on PO -> Ordered, full receipt (stock + transaction +
PO closure), multi-delivery partial receipt (delta application), idempotent
re-save, P/N mismatch rejection, and double-confirm protection.

All test data uses part numbers prefixed RCVTEST and is cleaned up before and
after every test, so the suite is safe to run against the live dev site.
"""

import frappe
import unittest

from frappe.exceptions import ValidationError

from arrow.arrow_aviation_mx.doctype.purchase_order_receiving.purchase_order_receiving import (
	confirm_receipt,
)


class TestPurchaseOrderReceiving(unittest.TestCase):
	PREFIX = 'RCVTEST'

	def setUp(self):
		frappe.set_user('Administrator')
		self._cleanup()

	def tearDown(self):
		self._cleanup()

	def _cleanup(self):
		pn_like = f'%{self.PREFIX}%'
		for dt, field in (
			('Purchase Order Receiving', 'part_number'),
			('Purchase Order', 'part_number'),
			('Inventory Transaction', 'inventory_item'),
			('Inventory Item', 'part_number'),
		):
			for name in frappe.get_all(dt, filters={field: ['like', pn_like]}, pluck='name'):
				frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
		frappe.db.commit()

	def _make(self, suffix, qty=2, po_qty=50):
		"""Create an Inventory Item + an Ordered Purchase Order for it."""
		pn = f'{self.PREFIX}-{suffix}'
		inv = frappe.get_doc({
			'doctype': 'Inventory Item',
			'item_name': f'Receiving test item {suffix}',
			'part_number': pn,
			'quantity': qty,
			'location': 'A1',
		}).insert(ignore_permissions=True)

		po = frappe.get_doc({
			'doctype': 'Purchase Order',
			'status': 'Ordered',
			'item_name': f'Receiving test item {suffix}',
			'part_number': pn,
			'quantity': po_qty,
			'aircraft': 'General',
			'linked_inventory_item': inv.name,
		}).insert(ignore_permissions=True)

		rcv_name = frappe.db.get_value(
			'Purchase Order Receiving', {'purchase_order': po.name}, 'name'
		)
		return inv, po, frappe.get_doc('Purchase Order Receiving', rcv_name)

	def _transactions(self, inv_name):
		return frappe.get_all(
			'Inventory Transaction',
			filters={
				'inventory_item': inv_name,
				'transaction_type': 'Receive',
				'reference_doctype': 'Purchase Order Receiving',
			},
			pluck='quantity',
			order_by='creation asc',
		)

	def test_01_auto_created_on_ordered(self):
		inv, po, rcv = self._make('auto')
		self.assertTrue(rcv.name)
		self.assertEqual(rcv.status, 'Awaiting Receipt')
		self.assertEqual(rcv.part_number, po.part_number)
		self.assertEqual(float(rcv.ordered_quantity), float(po.quantity))
		self.assertEqual(rcv.linked_inventory_item, inv.name)

	def test_02_full_receipt_updates_stock_and_closes(self):
		inv, po, rcv = self._make('full', qty=2, po_qty=50)
		result = confirm_receipt(rcv.name, received_quantity=50,
		                         received_location='B2',
		                         received_part_number=po.part_number)
		self.assertTrue(result['success'])
		self.assertEqual(result['status'], 'Received')
		self.assertEqual(result['po_status'], 'Received')
		self.assertFalse(result['deviation'])
		# Stock: 2 on-hand + 50 received
		self.assertEqual(float(frappe.db.get_value('Inventory Item', inv.name, 'quantity')), 52.0)
		self.assertEqual(frappe.db.get_value('Inventory Item', inv.name, 'location'), 'B2')
		# Exactly one Receive transaction referencing the receiving doc
		self.assertEqual(self._transactions(inv.name), [50.0])
		self.assertEqual(frappe.db.get_value('Purchase Order Receiving', rcv.name, 'status'), 'Received')

	def test_03_partial_then_remainder(self):
		inv, po, rcv = self._make('partial', qty=0, po_qty=50)

		# First delivery: only 30 of 50 arrive
		r1 = confirm_receipt(rcv.name, received_quantity=30,
		                     received_location='C3',
		                     received_part_number=po.part_number)
		self.assertEqual(r1['status'], 'Partially Received')
		self.assertEqual(r1['po_status'], 'Partially Received')
		self.assertTrue(r1['deviation'])
		self.assertEqual(float(frappe.db.get_value('Inventory Item', inv.name, 'quantity')), 30.0)

		# Second delivery: the remaining 20 (cumulative total 50)
		r2 = confirm_receipt(rcv.name, received_quantity=50,
		                     received_location='C3',
		                     received_part_number=po.part_number)
		self.assertEqual(r2['status'], 'Received')
		self.assertEqual(r2['po_status'], 'Received')
		self.assertFalse(r2['deviation'])
		# Stock got the delta (20), not the full 50 again
		self.assertEqual(float(frappe.db.get_value('Inventory Item', inv.name, 'quantity')), 50.0)
		# Two Receive transactions: 30 then 20
		self.assertEqual(self._transactions(inv.name), [30.0, 20.0])

	def test_04_resave_does_not_double_apply(self):
		inv, po, rcv = self._make('resave', qty=2, po_qty=10)
		confirm_receipt(rcv.name, received_quantity=10,
		                received_part_number=po.part_number)
		# Plain re-save (user hits Save again / reload + save)
		rcv = frappe.get_doc('Purchase Order Receiving', rcv.name)
		rcv.save(ignore_permissions=True)
		frappe.db.commit()
		self.assertEqual(float(frappe.db.get_value('Inventory Item', inv.name, 'quantity')), 12.0)
		self.assertEqual(len(self._transactions(inv.name)), 1)

	def test_05_part_number_mismatch_rejected(self):
		inv, po, rcv = self._make('pncheck', qty=0, po_qty=5)
		with self.assertRaises(ValidationError):
			confirm_receipt(rcv.name, received_quantity=5,
			                received_part_number='WRONG-PN-999')
		# Nothing was applied
		self.assertEqual(float(frappe.db.get_value('Inventory Item', inv.name, 'quantity')), 0.0)
		self.assertEqual(self._transactions(inv.name), [])

	def test_06_confirm_on_closed_record_rejected(self):
		inv, po, rcv = self._make('closed', qty=0, po_qty=5)
		confirm_receipt(rcv.name, received_quantity=5,
		                received_part_number=po.part_number)
		with self.assertRaises(ValidationError):
			confirm_receipt(rcv.name, received_quantity=5,
			                received_part_number=po.part_number)
		self.assertEqual(len(self._transactions(inv.name)), 1)

	def test_07_plain_save_applies_receiving(self):
		inv, po, rcv = self._make('plain', qty=1, po_qty=7)
		# User fills received_quantity in the form and clicks Save (no button)
		rcv.received_quantity = 7
		rcv.received_location = 'D4'
		rcv.received_part_number = po.part_number
		rcv.save(ignore_permissions=True)
		frappe.db.commit()
		self.assertEqual(frappe.db.get_value('Purchase Order Receiving', rcv.name, 'status'), 'Received')
		self.assertEqual(frappe.db.get_value('Purchase Order', po.name, 'status'), 'Received')
		self.assertEqual(float(frappe.db.get_value('Inventory Item', inv.name, 'quantity')), 8.0)
		self.assertEqual(self._transactions(inv.name), [7.0])
