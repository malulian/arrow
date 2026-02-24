"""
SQL queries to check Work Report inventory status
"""

# Query 1: Find submitted Work Reports without inventory transactions
submitted_reports_without_transactions = """
SELECT 
    wr.name,
    wr.work_date,
    wr.aircraft,
    wr.technician,
    COUNT(wrp.name) as parts_count
FROM `tabWork Report` wr
LEFT JOIN `tabWork Report Part` wrp ON wrp.parent = wr.name
LEFT JOIN `tabInventory Transaction` it 
    ON it.reference_doctype = 'Work Report' 
    AND it.reference_name = wr.name
    AND it.transaction_type = 'Withdraw'
WHERE 
    wr.docstatus = 1
    AND wrp.name IS NOT NULL
    AND wrp.quantity_used > 0
    AND it.name IS NULL
GROUP BY wr.name
ORDER BY wr.work_date DESC
"""

# Query 2: Check total counts
summary_query = """
SELECT 
    'Total Submitted Reports' as metric,
    COUNT(*) as count
FROM `tabWork Report`
WHERE docstatus = 1

UNION ALL

SELECT 
    'Reports with Parts' as metric,
    COUNT(DISTINCT wr.name) as count
FROM `tabWork Report` wr
INNER JOIN `tabWork Report Part` wrp ON wrp.parent = wr.name
WHERE wr.docstatus = 1 AND wrp.quantity_used > 0

UNION ALL

SELECT 
    'Reports with Inventory Transactions' as metric,
    COUNT(DISTINCT it.reference_name) as count
FROM `tabInventory Transaction` it
WHERE 
    it.reference_doctype = 'Work Report'
    AND it.transaction_type = 'Withdraw'

UNION ALL

SELECT 
    'Reports MISSING Transactions' as metric,
    COUNT(DISTINCT wr.name) as count
FROM `tabWork Report` wr
INNER JOIN `tabWork Report Part` wrp ON wrp.parent = wr.name
LEFT JOIN `tabInventory Transaction` it 
    ON it.reference_doctype = 'Work Report' 
    AND it.reference_name = wr.name
    AND it.transaction_type = 'Withdraw'
WHERE 
    wr.docstatus = 1
    AND wrp.quantity_used > 0
    AND it.name IS NULL
"""

# Query 3: Detailed view of parts without transactions
detailed_parts_query = """
SELECT 
    wr.name as work_report,
    wr.work_date,
    wr.aircraft,
    wrp.part,
    wrp.part_number,
    wrp.quantity_used,
    ii.quantity as current_inventory_quantity,
    ii.item_name
FROM `tabWork Report` wr
INNER JOIN `tabWork Report Part` wrp ON wrp.parent = wr.name
LEFT JOIN `tabInventory Transaction` it 
    ON it.reference_doctype = 'Work Report' 
    AND it.reference_name = wr.name
    AND it.inventory_item = wrp.part
    AND it.transaction_type = 'Withdraw'
LEFT JOIN `tabInventory Item` ii ON ii.name = wrp.part
WHERE 
    wr.docstatus = 1
    AND wrp.quantity_used > 0
    AND it.name IS NULL
ORDER BY wr.work_date DESC, wr.name
"""

print("Query 1: Submitted Work Reports without transactions")
print("=" * 80)
print(submitted_reports_without_transactions)
print("\n\n")

print("Query 2: Summary")
print("=" * 80)
print(summary_query)
print("\n\n")

print("Query 3: Detailed parts view")
print("=" * 80)
print(detailed_parts_query)
