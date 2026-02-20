frappe.ui.form.on('Service Ticket', {
    refresh: function(frm) {
        if (!frm.is_new()) {
            if (!frm.doc.job_card) {
                frm.add_custom_button('Create FSM Job Card', function() {
                    frappe.call({
                        method: 'field_service.field_service.doctype.service_ticket.service_ticket.create_job_card',
                        args: { service_ticket: frm.doc.name },
                        callback: function(r) {
                            if (r.message) {
                                frm.reload_doc();
                                frappe.set_route('Form', 'FSM Job Card', r.message);
                            }
                        }
                    });
                }, 'Actions');
            } else {
                frm.add_custom_button('View FSM Job Card', function() {
                    frappe.set_route('Form', 'FSM Job Card', frm.doc.job_card);
                }, 'Actions');
            }
        }
    }
});
