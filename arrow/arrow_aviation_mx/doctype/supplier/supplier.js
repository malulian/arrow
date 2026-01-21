frappe.ui.form.on('Supplier', {
    refresh: function (frm) {
        // Add indicator for approval status
        if (frm.doc.is_approved) {
            frm.page.set_indicator('Approved', 'green');
        } else {
            frm.page.set_indicator('Not Approved', 'orange');
        }

        // Add indicator for survey status
        if (frm.doc.next_survey_date) {
            let next_survey = frappe.datetime.str_to_obj(frm.doc.next_survey_date);
            let today = frappe.datetime.str_to_obj(frappe.datetime.get_today());

            if (next_survey < today) {
                frm.dashboard.add_comment('Survey is overdue!', 'red', true);
            } else {
                let days_until = frappe.datetime.get_diff(next_survey, today);
                if (days_until <= 30) {
                    frm.dashboard.add_comment(`Survey due in ${days_until} days`, 'orange', true);
                }
            }
        }

        // Add button to add a new survey
        if (!frm.is_new()) {
            frm.add_custom_button(__('Add Survey'), function () {
                let d = new frappe.ui.Dialog({
                    title: 'Add Survey',
                    fields: [
                        {
                            label: 'Survey Date',
                            fieldname: 'survey_date',
                            fieldtype: 'Date',
                            default: frappe.datetime.get_today(),
                            reqd: 1
                        },
                        {
                            label: 'Surveyed By',
                            fieldname: 'surveyed_by',
                            fieldtype: 'Link',
                            options: 'User',
                            default: frappe.session.user
                        },
                        {
                            label: 'Result',
                            fieldname: 'survey_result',
                            fieldtype: 'Select',
                            options: 'Pass\nFail\nConditional',
                            default: 'Pass',
                            reqd: 1
                        },
                        {
                            label: 'Has Findings',
                            fieldname: 'has_findings',
                            fieldtype: 'Check'
                        },
                        {
                            label: 'Findings',
                            fieldname: 'findings',
                            fieldtype: 'Text',
                            depends_on: 'eval:doc.has_findings'
                        },
                        {
                            label: 'Findings Due Date',
                            fieldname: 'findings_due_date',
                            fieldtype: 'Date',
                            depends_on: 'eval:doc.has_findings'
                        },
                        {
                            label: 'Survey Document',
                            fieldname: 'attachment',
                            fieldtype: 'Attach'
                        }
                    ],
                    primary_action_label: 'Add',
                    primary_action: function (values) {
                        let row = frm.add_child('surveys', values);
                        frm.refresh_field('surveys');
                        frm.save();
                        d.hide();
                    }
                });
                d.show();
            }, __('Actions'));
        }
    },

    surveys_add: function (frm) {
        // Trigger recalculation when survey is added
        frm.trigger('calculate_next_survey');
    },

    surveys_remove: function (frm) {
        // Trigger recalculation when survey is removed
        frm.trigger('calculate_next_survey');
    }
});
