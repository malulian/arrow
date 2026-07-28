import frappe

def fix_all_perms():
    output = []
    
    for dt_name in ["Inventory Item", "Work Report Part", "Work Report"]:
        rows = frappe.db.sql(
            "SELECT role, permlevel FROM tabDocPerm WHERE parent = %s",
            (dt_name,), as_dict=True
        )
        output.append("=== {} ===".format(dt_name))
        
        if not any(r.role == "System Manager" and r.permlevel == 1 for r in rows):
            frappe.db.sql("""
                INSERT INTO tabDocPerm (name, creation, modified, modified_by, owner, docstatus, idx, parent, parentfield, parenttype, role, permlevel)
                VALUES (REPLACE(UUID(),'-',''), NOW(), NOW(), 'Administrator', 'Administrator', 0, 0, %s, 'permissions', 'DocType', 'System Manager', 1)
            """, (dt_name,))
            output.append("  + System Manager level 1 added")
        else:
            output.append("  System Manager level 1 already exists")
        
        if not any(r.role == "Price Manager" and r.permlevel == 0 for r in rows):
            frappe.db.sql("""
                INSERT INTO tabDocPerm (name, creation, modified, modified_by, owner, docstatus, idx, parent, parentfield, parenttype, role, permlevel)
                VALUES (REPLACE(UUID(),'-',''), NOW(), NOW(), 'Administrator', 'Administrator', 0, 0, %s, 'permissions', 'DocType', 'Price Manager', 0)
            """, (dt_name,))
            output.append("  + Price Manager level 0 added")
        else:
            output.append("  Price Manager level 0 already exists")
        
        if not any(r.role == "Price Manager" and r.permlevel == 1 for r in rows):
            frappe.db.sql("""
                INSERT INTO tabDocPerm (name, creation, modified, modified_by, owner, docstatus, idx, parent, parentfield, parenttype, role, permlevel)
                VALUES (REPLACE(UUID(),'-',''), NOW(), NOW(), 'Administrator', 'Administrator', 0, 0, %s, 'permissions', 'DocType', 'Price Manager', 1)
            """, (dt_name,))
            output.append("  + Price Manager level 1 added")
        else:
            output.append("  Price Manager level 1 already exists")
    
    frappe.db.commit()
    
    for user in ["osher@arrowaviation.biz", "lior@arrowaviation.biz"]:
        roles = frappe.db.sql("SELECT role FROM tabHasRole WHERE parent=%s", (user,), as_dict=True)
        output.append("\n{} roles: {}".format(user, [r.role for r in roles]))
    
    frappe.clear_cache()
    
    return "\n".join(output)
