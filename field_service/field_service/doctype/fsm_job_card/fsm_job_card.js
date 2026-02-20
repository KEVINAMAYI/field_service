frappe.ui.form.on('FSM Job Card', {
    refresh: function(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button('Send Job Card PDF', function() {
                frappe.prompt([
                    {
                        label: 'Recipient Email(s)',
                        fieldname: 'email',
                        fieldtype: 'Data',
                        options: 'Email',
                        description: 'Separate multiple emails with a comma. Leave blank to use client email.'
                    }
                ], function(values) {
                    frappe.call({
                        method: 'field_service.field_service.doctype.fsm_job_card.fsm_job_card.generate_and_email_pdf',
                        args: {
                            job_card_name: frm.doc.name,
                            recipient_emails: values.email || ''
                        },
                        callback: function(r) {
                            if (r.message) {
                                frappe.msgprint('PDF sent successfully');
                            }
                        }
                    });
                }, 'Send Job Card PDF', 'Send');
            });
        }
    },

    // Auto-populate subject from the linked Service Ticket
    service_ticket: function(frm) {
        if (frm.doc.service_ticket) {
            frappe.db.get_value('Service Ticket', frm.doc.service_ticket, 'subject', function(value) {
                if (value && value.subject) {
                    frm.set_value('subject', value.subject);
                }
            });
        }
    },

    qty_hrs: function(frm) { calculate_total(frm); },
    rate: function(frm) { calculate_total(frm); }
});

function calculate_total(frm) {
    if (frm.doc.qty_hrs && frm.doc.rate) {
        frm.set_value('total_in_kshs', frm.doc.qty_hrs * frm.doc.rate);
    }
}

frappe.ui.form.on('FSM Job Card Work Item', {
    qty: function(frm, cdt, cdn) { calculate_item_amount(frm, cdt, cdn); },
    rate: function(frm, cdt, cdn) { calculate_item_amount(frm, cdt, cdn); }
});

function calculate_item_amount(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.qty && row.rate) {
        frappe.model.set_value(cdt, cdn, 'amount', row.qty * row.rate);
    }
}