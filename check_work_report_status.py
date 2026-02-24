"""
Script to check Work Report status and help debug why submission isn't working
"""

import frappe

def check_work_reports_status():
	"""Check the status of all Work Reports"""
	
	print("\n" + "="*80)
	print("WORK REPORT STATUS CHECK")
	print("="*80)
	
	# Get all work reports
	all_reports = frappe.get_all(
		'Work Report',
		fields=['name', 'docstatus', 'aircraft', 'work_date', 'technician'],
		order_by='creation desc',
		limit=20
	)
	
	print(f"\nTotal Work Reports (last 20): {len(all_reports)}")
	
	draft_count = 0
	submitted_count = 0
	cancelled_count = 0
	
	for report in all_reports:
		status_map = {0: 'Draft', 1: 'Submitted', 2: 'Cancelled'}
		status = status_map.get(report.docstatus, 'Unknown')
		
		if report.docstatus == 0:
			draft_count += 1
		elif report.docstatus == 1:
			submitted_count += 1
		elif report.docstatus == 2:
			cancelled_count += 1
		
		print(f"  {report.name} - {status} - {report.aircraft} - {report.work_date}")
	
	print(f"\nSummary:")
	print(f"  Draft: {draft_count}")
	print(f"  Submitted: {submitted_count}")
	print(f"  Cancelled: {cancelled_count}")
	
	# Check if DocType is submittable
	doctype_meta = frappe.get_meta('Work Report')
	print(f"\nDocType Settings:")
	print(f"  Is Submittable: {doctype_meta.is_submittable}")
	print(f"  Track Changes: {doctype_meta.track_changes}")
	
	# Check permissions
	print(f"\nPermissions:")
	current_user = frappe.session.user
	print(f"  Current User: {current_user}")
	
	roles = frappe.get_roles(current_user)
	print(f"  Roles: {', '.join(roles)}")
	
	# Check if user can submit
	can_submit = frappe.has_permission('Work Report', 'submit', user=current_user)
	can_create = frappe.has_permission('Work Report', 'create', user=current_user)
	can_write = frappe.has_permission('Work Report', 'write', user=current_user)
	
	print(f"  Can Create: {can_create}")
	print(f"  Can Write: {can_write}")
	print(f"  Can Submit: {can_submit}")
	
	# Check for reports with parts
	print(f"\nReports with Parts:")
	reports_with_parts = frappe.db.sql("""
		SELECT 
			wr.name,
			wr.docstatus,
			COUNT(wrp.name) as parts_count,
			SUM(wrp.quantity_used) as total_quantity
		FROM `tabWork Report` wr
		INNER JOIN `tabWork Report Part` wrp ON wrp.parent = wr.name
		WHERE wrp.quantity_used > 0
		GROUP BY wr.name
		ORDER BY wr.creation DESC
		LIMIT 10
	""", as_dict=True)
	
	for rep in reports_with_parts:
		status_map = {0: 'Draft', 1: 'Submitted', 2: 'Cancelled'}
		status = status_map.get(rep.docstatus, 'Unknown')
		print(f"  {rep.name} - {status} - {rep.parts_count} parts ({rep.total_quantity} total qty)")
	
	# Check for inventory transactions
	print(f"\nInventory Transactions from Work Reports:")
	transactions = frappe.db.sql("""
		SELECT 
			reference_name,
			COUNT(*) as transaction_count,
			SUM(quantity) as total_deducted
		FROM `tabInventory Transaction`
		WHERE reference_doctype = 'Work Report'
		GROUP BY reference_name
		ORDER BY creation DESC
		LIMIT 10
	""", as_dict=True)
	
	print(f"  Total Work Reports with transactions: {len(transactions)}")
	for trans in transactions:
		print(f"    {trans.reference_name} - {trans.transaction_count} transactions, {trans.total_deducted} qty deducted")
	
	print("\n" + "="*80)
	
	return {
		'total': len(all_reports),
		'draft': draft_count,
		'submitted': submitted_count,
		'cancelled': cancelled_count,
		'is_submittable': doctype_meta.is_submittable,
		'can_submit': can_submit
	}


if __name__ == '__main__':
	result = check_work_reports_status()
	print(f"\nResult: {result}")
