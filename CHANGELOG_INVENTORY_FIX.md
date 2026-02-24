# CHANGELOG - Work Report Inventory Fix

## [2026-02-24] - Fix for Missing Inventory Deductions

### Problem
Work Reports that were submitted in the system did not properly deduct parts from inventory because they lacked proper submit status handling.

### Changes Made

#### 1. Core Logic Fix
**File:** `arrow/arrow_aviation_mx/doctype/work_report/work_report.py`

- **Updated `deduct_parts_from_inventory()` method:**
  - Added check to prevent duplicate deductions
  - Verifies if an Inventory Transaction already exists before deducting
  - Skips parts that have already been deducted
  
- **Added new function `fix_inventory_for_submitted_reports()`:**
  - Scans all submitted Work Reports
  - Identifies reports with missing inventory deductions
  - Safely deducts parts and creates missing Inventory Transactions
  - Returns detailed results including errors

#### 2. UI Enhancement
**File:** `arrow/arrow_aviation_mx/doctype/work_report/work_report_list.js` (NEW)

- Added "Fix Inventory for Submitted Reports" button to Work Report list view
- Provides user-friendly interface to run the fix
- Shows confirmation dialog before execution
- Displays results summary with counts and errors

#### 3. Standalone Scripts
**Files Created:**
- `fix_inventory_deduction.py` - Standalone script for direct execution
- `check_inventory_issues.py` - SQL queries to identify problematic reports

#### 4. Documentation
**Files Created:**
- `INVENTORY_FIX_README.md` - Detailed technical documentation
- `הוראות_תיקון_מלאי.md` - Quick start guide in Hebrew

### Technical Details

#### Safety Features
1. **Idempotent Operations:** The fix can be run multiple times safely
2. **Transaction Checks:** Always checks for existing transactions before deducting
3. **Error Handling:** Errors are logged and don't stop the entire process
4. **Audit Trail:** All deductions create Inventory Transactions for tracking

#### Code Flow
```
on_submit()
  └─> deduct_parts_from_inventory()
       ├─> Check if transaction exists
       ├─> If exists: Skip (already deducted)
       └─> If not exists:
            ├─> Deduct from Inventory Item
            └─> Create Inventory Transaction
```

### API Endpoints

#### New Whitelisted Function
```python
@frappe.whitelist()
def fix_inventory_for_submitted_reports()
```

**Returns:**
```python
{
    'success': True,
    'reports_fixed': int,        # Number of reports fixed
    'parts_deducted': int,        # Number of parts deducted
    'total_reports_checked': int, # Total submitted reports
    'errors': list               # List of error messages
}
```

### How to Use

#### Option 1: Via UI
1. Navigate to Work Report list
2. Click "Fix Inventory for Submitted Reports"
3. Confirm the action
4. Review results

#### Option 2: Via Console
```bash
bench --site [site-name] execute arrow.arrow_aviation_mx.doctype.work_report.work_report.fix_inventory_for_submitted_reports
```

#### Option 3: Via Script
```bash
bench --site [site-name] execute fix_inventory_deduction.fix_inventory_for_submitted_reports
```

### Verification Queries

#### Check for reports without transactions:
```sql
SELECT wr.name, wr.work_date, wr.aircraft, COUNT(wrp.name) as parts_count
FROM `tabWork Report` wr
LEFT JOIN `tabWork Report Part` wrp ON wrp.parent = wr.name
LEFT JOIN `tabInventory Transaction` it 
    ON it.reference_doctype = 'Work Report' 
    AND it.reference_name = wr.name
WHERE wr.docstatus = 1
  AND wrp.quantity_used > 0
  AND it.name IS NULL
GROUP BY wr.name
```

### Impact

#### Before Fix:
- Submitted Work Reports didn't deduct inventory
- No Inventory Transactions were created
- Inventory counts were incorrect

#### After Fix:
- All submitted reports properly deduct inventory
- Inventory Transactions are created for audit
- Duplicate deductions are prevented
- Legacy reports can be fixed with one click

### Testing Recommendations

1. **Test on staging first**
2. **Backup database before running fix**
3. **Verify inventory counts after fix**
4. **Check Inventory Transaction list**
5. **Review error logs if any failures occur**

### Rollback Plan

If needed to rollback:
1. Delete Inventory Transactions created by the fix:
   ```sql
   DELETE FROM `tabInventory Transaction`
   WHERE notes LIKE '%Fixed by script%'
   ```
2. Restore Inventory Item quantities from backup
3. Revert code changes in work_report.py

### Future Enhancements

- [ ] Add scheduled job to check for orphaned reports
- [ ] Create dashboard widget showing inventory status
- [ ] Add email notifications for admin when fix is run
- [ ] Implement dry-run mode to preview changes

### Related Issues

- Missing inventory deductions on submitted Work Reports
- Inconsistent inventory counts
- Lack of audit trail for part usage

### Contributors

- Osher (2026-02-24)
