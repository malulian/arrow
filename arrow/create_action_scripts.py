import frappe

def create_action_buttons():
    DOC_TYPES = [
        "Work Report",
        "Inventory Item",
        "Inventory Transaction",
        "Purchase Order",
        "Supplier",
        "AMP Chapter",
        "AMP Document",
        "AMP Revision",
        "AMP Task Note",
    ]

    STANDARD_SCRIPT = """
frappe.ui.form.on('{doctype}', {{
    refresh: function(frm) {{
        frm.page.hide_actions_menu();

        frm.add_custom_button(__('Print'), function() {{
            frm.print_doc();
        }});

        frm.add_custom_button(__('Email'), function() {{
            frm.email_doc();
        }});

        if (!frm.is_new()) {{
            frm.add_custom_button(__('Duplicate'), function() {{
                var newdoc = frappe.model.copy_doc(frm.doc);
                frappe.set_route('Form', frm.doc.doctype, newdoc.name);
            }});
        }}

        if (!frm.is_new()) {{
            frm.add_custom_button(__('Delete'), function() {{
                frappe.confirm(__('Are you sure?'), function() {{
                    frm.delete_doc();
                }});
            }}, __('Actions'));
        }}
    }}
}});
"""

    SUBMITTABLE_SCRIPT = """
frappe.ui.form.on('{doctype}', {{
    refresh: function(frm) {{
        frm.page.hide_actions_menu();

        frm.add_custom_button(__('Print'), function() {{
            frm.print_doc();
        }});

        frm.add_custom_button(__('Email'), function() {{
            frm.email_doc();
        }});

        if (frm.doc.docstatus === 0 && !frm.is_new()) {{
            frm.add_custom_button(__('Submit'), function() {{
                frm.savesubmit();
            }});
        }}

        if (frm.doc.docstatus === 1) {{
            frm.add_custom_button(__('Cancel'), function() {{
                frappe.confirm(__('Are you sure you want to cancel?'), function() {{
                    frm.savecancel();
                }});
            }});
        }}

        if (!frm.is_new()) {{
            frm.add_custom_button(__('Duplicate'), function() {{
                var newdoc = frappe.model.copy_doc(frm.doc);
                frappe.set_route('Form', frm.doc.doctype, newdoc.name);
            }});
        }}

        if (!frm.is_new() && frm.doc.docstatus !== 1) {{
            frm.add_custom_button(__('Delete'), function() {{
                frappe.confirm(__('Are you sure?'), function() {{
                    frm.delete_doc();
                }});
            }}, __('Actions'));
        }}
    }}
}});
"""

    results = []

    for dt in DOC_TYPES:
        is_submit = frappe.db.get_value("DocType", dt, "is_submittable")
        script_content = SUBMITTABLE_SCRIPT.format(doctype=dt) if is_submit else STANDARD_SCRIPT.format(doctype=dt)
        cs_name = "Action Buttons - " + dt

        # Delete existing if any
        if frappe.db.exists("Client Script", cs_name):
            frappe.delete_doc("Client Script", cs_name, ignore_permissions=True, force=True)
            results.append("Deleted old: " + cs_name)

        try:
            doc = frappe.new_doc("Client Script")
            doc.name = cs_name
            doc.dt = dt
            doc.view = "Form"
            doc.script = script_content.strip()
            doc.enabled = 1
            doc.insert(ignore_permissions=True)
            results.append("Created: " + cs_name)
        except Exception as e:
            results.append("Error " + cs_name + ": " + str(e))

    frappe.db.commit()
    frappe.clear_cache()

    return "\n".join(results)
