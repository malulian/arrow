# Copyright (c) 2026, osher and contributors
# Check for duplicate inventory items by Part Number
# Run with: bench --site [site-name] execute arrow.arrow_aviation_mx.scripts.check_duplicates.check_inventory_duplicates

import frappe
from frappe.utils import cstr


def check_inventory_duplicates():
	"""
	Check for duplicate parts in Inventory Item by Part Number and Alternate P/N
	"""
	print("\n" + "="*60)
	print("🔍 INVENTORY DUPLICATES CHECK")
	print("="*60 + "\n")
	
	# Get all inventory items
	items = frappe.get_all(
		'Inventory Item',
		fields=['name', 'item_name', 'part_number', 'alternate_pn', 'quantity', 'location', 'status']
	)
	
	if not items:
		print("❌ No inventory items found.")
		return
	
	print(f"📦 Total items in inventory: {len(items)}\n")
	
	# Check duplicates by Part Number
	pn_map = {}
	for item in items:
		pn = cstr(item.part_number).strip().upper()
		if pn:
			if pn not in pn_map:
				pn_map[pn] = []
			pn_map[pn].append(item)
	
	# Find duplicates
	pn_duplicates = {pn: items for pn, items in pn_map.items() if len(items) > 1}
	
	if pn_duplicates:
		print("⚠️  DUPLICATES FOUND BY PART NUMBER:")
		print("-"*60)
		for pn, dup_items in pn_duplicates.items():
			print(f"\n📌 Part Number: {pn}")
			for item in dup_items:
				print(f"   • {item.name}")
				print(f"     Name: {item.item_name}")
				print(f"     Qty: {item.quantity} | Location: {item.location or 'N/A'} | Status: {item.status}")
	else:
		print("✅ No duplicates found by Part Number")
	
	# Check for items where Alternate P/N matches another item's P/N
	print("\n" + "-"*60)
	print("🔄 CHECKING ALTERNATE P/N MATCHES...")
	print("-"*60)
	
	all_pns = set(cstr(item.part_number).strip().upper() for item in items if item.part_number)
	
	cross_matches = []
	for item in items:
		alt_pn = cstr(item.alternate_pn).strip().upper()
		if alt_pn and alt_pn in all_pns:
			# Find the matching item
			matching = [i for i in items if cstr(i.part_number).strip().upper() == alt_pn and i.name != item.name]
			if matching:
				cross_matches.append({
					'item': item,
					'matches': matching
				})
	
	if cross_matches:
		print("\n⚠️  ALTERNATE P/N MATCHES FOUND:")
		for match in cross_matches:
			item = match['item']
			print(f"\n📌 {item.name} (P/N: {item.part_number}, Alt: {item.alternate_pn})")
			print(f"   Matches with:")
			for m in match['matches']:
				print(f"   • {m.name} (P/N: {m.part_number})")
	else:
		print("✅ No Alternate P/N cross-matches found")
	
	# Summary
	print("\n" + "="*60)
	print("📊 SUMMARY")
	print("="*60)
	print(f"Total items scanned: {len(items)}")
	print(f"Duplicate P/N groups: {len(pn_duplicates)}")
	print(f"Alt P/N cross-matches: {len(cross_matches)}")
	
	if pn_duplicates or cross_matches:
		print("\n⚠️  ACTION REQUIRED: Review and merge duplicate items")
	else:
		print("\n✅ No issues found!")
	
	print("\n")
	
	return {
		'total_items': len(items),
		'pn_duplicates': pn_duplicates,
		'cross_matches': cross_matches
	}


def get_duplicate_report_html():
	"""Get HTML report of duplicates for display in Frappe"""
	result = check_inventory_duplicates()
	
	html = "<h3>Inventory Duplicates Report</h3>"
	
	if result['pn_duplicates']:
		html += "<h4>Duplicate Part Numbers</h4><ul>"
		for pn, items in result['pn_duplicates'].items():
			html += f"<li><b>{pn}</b>: "
			html += ", ".join([f"<a href='/app/inventory-item/{i.name}'>{i.item_name}</a>" for i in items])
			html += "</li>"
		html += "</ul>"
	else:
		html += "<p>✅ No duplicate Part Numbers found</p>"
	
	if result['cross_matches']:
		html += "<h4>Alternate P/N Matches</h4><ul>"
		for match in result['cross_matches']:
			html += f"<li>{match['item'].name} matches: "
			html += ", ".join([m.name for m in match['matches']])
			html += "</li>"
		html += "</ul>"
	else:
		html += "<p>✅ No Alternate P/N cross-matches</p>"
	
	return html


if __name__ == "__main__":
	check_inventory_duplicates()
