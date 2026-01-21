# Copyright (c) 2026, osher and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, cstr


class InventoryDuplicatesCheck(Document):
	pass


@frappe.whitelist()
def run_duplicates_check():
	"""Run the duplicates check and return HTML results"""
	
	# Get all inventory items
	items = frappe.get_all(
		'Inventory Item',
		fields=['name', 'item_name', 'part_number', 'alternate_pn', 'quantity', 'location', 'status']
	)
	
	if not items:
		return {
			'html': '<div class="alert alert-warning">No inventory items found.</div>',
			'summary': {'total': 0, 'duplicates': 0, 'cross_matches': 0}
		}
	
	# Check duplicates by Part Number
	pn_map = {}
	for item in items:
		pn = cstr(item.part_number).strip().upper()
		if pn:
			if pn not in pn_map:
				pn_map[pn] = []
			pn_map[pn].append(item)
	
	# Find duplicates
	pn_duplicates = {pn: dup_items for pn, dup_items in pn_map.items() if len(dup_items) > 1}
	
	# Check for Alternate P/N matches
	all_pns = set(cstr(item.part_number).strip().upper() for item in items if item.part_number)
	
	cross_matches = []
	for item in items:
		alt_pn = cstr(item.alternate_pn).strip().upper()
		if alt_pn and alt_pn in all_pns:
			matching = [i for i in items if cstr(i.part_number).strip().upper() == alt_pn and i.name != item.name]
			if matching:
				cross_matches.append({
					'item': item,
					'matches': matching
				})
	
	# Build HTML
	html = f'''
	<div class="frappe-card p-3 mb-3">
		<h4>📊 Summary</h4>
		<div class="row">
			<div class="col-md-4">
				<div class="stat-label">Total Items</div>
				<div class="stat-value">{len(items)}</div>
			</div>
			<div class="col-md-4">
				<div class="stat-label">Duplicate P/N Groups</div>
				<div class="stat-value text-warning">{len(pn_duplicates)}</div>
			</div>
			<div class="col-md-4">
				<div class="stat-label">Alt P/N Matches</div>
				<div class="stat-value text-info">{len(cross_matches)}</div>
			</div>
		</div>
	</div>
	'''
	
	if pn_duplicates:
		html += '''
		<div class="frappe-card p-3 mb-3">
			<h4>⚠️ Duplicate Part Numbers</h4>
			<table class="table table-bordered">
				<thead><tr><th>Part Number</th><th>Duplicate Items</th></tr></thead>
				<tbody>
		'''
		for pn, dup_items in pn_duplicates.items():
			items_html = "<br>".join([
				f'<a href="/app/inventory-item/{i.name}">{i.item_name}</a> (Qty: {i.quantity}, Loc: {i.location or "N/A"})'
				for i in dup_items
			])
			html += f'<tr><td><b>{pn}</b></td><td>{items_html}</td></tr>'
		html += '</tbody></table></div>'
	else:
		html += '<div class="alert alert-success">✅ No duplicate Part Numbers found</div>'
	
	if cross_matches:
		html += '''
		<div class="frappe-card p-3 mb-3">
			<h4>🔄 Alternate P/N Matches</h4>
			<table class="table table-bordered">
				<thead><tr><th>Item</th><th>Alt P/N</th><th>Matches With</th></tr></thead>
				<tbody>
		'''
		for match in cross_matches:
			item = match['item']
			matches_html = "<br>".join([
				f'<a href="/app/inventory-item/{m.name}">{m.item_name}</a>'
				for m in match['matches']
			])
			html += f'''<tr>
				<td><a href="/app/inventory-item/{item.name}">{item.item_name}</a></td>
				<td>{item.alternate_pn}</td>
				<td>{matches_html}</td>
			</tr>'''
		html += '</tbody></table></div>'
	else:
		html += '<div class="alert alert-success">✅ No Alternate P/N cross-matches found</div>'
	
	# Update last run time
	frappe.db.set_single_value('Inventory Duplicates Check', 'last_run', now_datetime())
	
	return {
		'html': html,
		'summary': {
			'total': len(items),
			'duplicates': len(pn_duplicates),
			'cross_matches': len(cross_matches)
		}
	}
