"""
Script to fix inventory deduction for submitted Work Reports that were created
before the deduction logic was implemented or were submitted without proper inventory update.

This script:
1. Finds all submitted Work Reports
2. Checks if their parts were already deducted from inventory
3. Deducts parts that weren't deducted yet
"""

import frappe
from frappe.utils import today

def fix_inventory_for_submitted_reports():
	"""Fix inventory deduction for all submitted work reports"""
	
	# Get all submitted work reports
	submitted_reports = frappe.get_all(
		'Work Report',
		filters={'docstatus': 1},  # 1 = Submitted
		fields=['name', 'aircraft', 'work_date']
	)
	
	print(f"\nFound {len(submitted_reports)} submitted work reports")
	
	reports_fixed = 0
	parts_deducted = 0
	errors = []
	
	for report_data in submitted_reports:
		try:
			report = frappe.get_doc('Work Report', report_data.name)
			
			if not report.parts_used:
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
				item_name = inv_item.item_name
				
				print(f"\n  Deducting {part.quantity_used} x {item_name} from report {report.name}")
				
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
			print(f"\n  ERROR: {error_msg}")
			errors.append(error_msg)
	
	# Commit changes
	frappe.db.commit()
	
	print(f"\n{'='*60}")
	print(f"SUMMARY:")
	print(f"  Reports fixed: {reports_fixed}")
	print(f"  Parts deducted: {parts_deducted}")
	print(f"  Errors: {len(errors)}")
	print(f"{'='*60}\n")
	
	if errors:
		print("ERRORS:")
		for error in errors:
			print(f"  - {error}")
	
	return {
		'reports_fixed': reports_fixed,
		'parts_deducted': parts_deducted,
		'errors': errors
	}


if __name__ == '__main__':
	# Run the fix
	result = fix_inventory_for_submitted_reports()
	print("\nDone!")
