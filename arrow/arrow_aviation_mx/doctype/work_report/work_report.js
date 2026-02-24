frappe.ui.form.on('Work Report', {
    refresh: function (frm) {
        // Add Submit button for draft reports with parts
        if (frm.doc.docstatus === 0 && !frm.is_new() && frm.doc.parts_used && frm.doc.parts_used.length > 0) {
            frm.add_custom_button(__('Submit & Deduct from Inventory'), function () {
                frappe.confirm(
                    __('האם לשלוח את הדוח ולנכות את הפריטים מהמלאי?'),
                    function() {
                        frm.savesubmit();
                    }
                );
            }).addClass('btn-primary');
        }

        // Add PDF buttons
        if (!frm.is_new()) {
            frm.add_custom_button(__('Generate PDF'), function () {
                generate_pdf(frm);
            }, __('Actions'));

            frm.add_custom_button(__('Send Report by Email'), function () {
                send_by_email(frm);
            }, __('Actions'));
        }

        // Show parts used summary
        if (frm.doc.parts_used && frm.doc.parts_used.length > 0) {
            if (frm.doc.docstatus === 0) {
                frm.dashboard.add_comment(
                    `${frm.doc.parts_used.length} חלקים ינוכו מהמלאי כשתשלח את הדוח`,
                    'blue',
                    true
                );
            } else if (frm.doc.docstatus === 1) {
                frm.dashboard.add_comment(
                    `${frm.doc.parts_used.length} חלקים נוכו מהמלאי בהצלחה`,
                    'green',
                    true
                );
            }
        }
    },

    onload: function (frm) {
        // Auto-fill technician if new
        if (frm.is_new() && !frm.doc.technician) {
            frm.set_value('technician', frappe.session.user);
        }
    },

    before_save: function (frm) {
        // Check for duplicate parts if we have parts and haven't confirmed yet
        if (frm.doc.parts_used && frm.doc.parts_used.length > 0 && !frm.doc.duplicate_parts_confirmed) {
            // Return a promise to allow async check
            return new Promise((resolve, reject) => {
                frappe.call({
                    method: 'arrow.arrow_aviation_mx.doctype.work_report.work_report.check_duplicate_parts_api',
                    args: {
                        work_date: frm.doc.work_date,
                        aircraft: frm.doc.aircraft,
                        start_time: frm.doc.start_time,
                        end_time: frm.doc.end_time,
                        parts: frm.doc.parts_used,
                        current_name: frm.doc.name || null
                    },
                    async: false,
                    callback: function (r) {
                        if (r.message && r.message.has_duplicates) {
                            // Build warning message
                            let msg = '<b>⚠️ The following parts were already reported by another technician:</b><br><br>';
                            r.message.duplicates.forEach(dup => {
                                msg += `• Part <b>${dup.part}</b> - already in ${dup.other_report} by ${dup.other_technician}<br>`;
                            });
                            msg += '<br><b>Are you sure you actually used these parts?</b>';

                            frappe.confirm(
                                msg,
                                () => {
                                    // User confirmed - set flag and save again
                                    frm.set_value('duplicate_parts_confirmed', 1);
                                    frm.save();
                                },
                                () => {
                                    // User cancelled - reject save
                                    frappe.show_alert({
                                        message: __('Save cancelled. Remove duplicate parts or confirm usage.'),
                                        indicator: 'orange'
                                    });
                                }
                            );
                            reject();
                        } else {
                            resolve();
                        }
                    }
                });
            });
        }
    },

    start_time: function (frm) {
        calculate_total_hours(frm);
    },

    end_time: function (frm) {
        calculate_total_hours(frm);
    },

    gpu_usage: function (frm) {
        if (!frm.doc.gpu_usage) {
            frm.set_value('gpu_hours', 0);
        }
    }
});

frappe.ui.form.on('Work Report Part', {
    part: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.part) {
            // Fetch available quantity
            frappe.db.get_value('Inventory Item', row.part, ['quantity', 'item_name'], function (r) {
                if (r) {
                    frappe.model.set_value(cdt, cdn, 'available_quantity', r.quantity);

                    // Warn if low quantity
                    if (r.quantity < 1) {
                        frappe.show_alert({
                            message: __(`Warning: ${r.item_name} has low/no stock (${r.quantity})`),
                            indicator: 'orange'
                        });
                    }
                }
            });
        }
    },

    quantity_used: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.quantity_used > row.available_quantity) {
            frappe.show_alert({
                message: __('Quantity exceeds available stock!'),
                indicator: 'red'
            });
        }
    }
});

function calculate_total_hours(frm) {
    if (frm.doc.start_time && frm.doc.end_time) {
        // Parse times
        let start_parts = frm.doc.start_time.split(':');
        let end_parts = frm.doc.end_time.split(':');

        let start_minutes = parseInt(start_parts[0]) * 60 + parseInt(start_parts[1]);
        let end_minutes = parseInt(end_parts[0]) * 60 + parseInt(end_parts[1]);

        // Handle overnight work
        if (end_minutes < start_minutes) {
            end_minutes += 24 * 60;
        }

        let diff_minutes = end_minutes - start_minutes;
        let hours = Math.floor(diff_minutes / 60);
        let minutes = diff_minutes % 60;

        frm.set_value('total_hours', (diff_minutes / 60).toFixed(2));
        frm.set_value('total_hours_display', `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`);
    }
}

function generate_pdf(frm) {
    frappe.call({
        method: 'arrow.arrow_aviation_mx.doctype.work_report.work_report.generate_work_report_pdf',
        args: {
            report_name: frm.doc.name
        },
        freeze: true,
        freeze_message: __('Generating PDF...'),
        callback: function (r) {
            if (r.message && r.message.success) {
                window.open(r.message.file_url, '_blank');
                frappe.show_alert({
                    message: __('PDF generated successfully'),
                    indicator: 'green'
                });
            } else {
                frappe.msgprint(__('Failed to generate PDF'));
            }
        }
    });
}

function send_by_email(frm) {
    let d = new frappe.ui.Dialog({
        title: 'Send Report by Email',
        fields: [
            {
                label: 'Recipient Email',
                fieldname: 'email',
                fieldtype: 'Data',
                reqd: 1
            }
        ],
        primary_action_label: 'Send',
        primary_action(values) {
            frappe.call({
                method: 'arrow.arrow_aviation_mx.doctype.work_report.work_report.send_report_email',
                args: {
                    report_name: frm.doc.name,
                    recipient_email: values.email
                },
                freeze: true,
                freeze_message: __('Sending email...'),
                callback: function (r) {
                    if (r.message && r.message.success) {
                        frappe.show_alert({
                            message: __('Email sent successfully'),
                            indicator: 'green'
                        });
                        d.hide();
                    } else {
                        frappe.msgprint(r.message.message || __('Failed to send email'));
                    }
                }
            });
        }
    });
    d.show();
}
