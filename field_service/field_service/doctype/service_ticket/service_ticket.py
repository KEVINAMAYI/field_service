import frappe
from frappe.model.document import Document

class ServiceTicket(Document):
    def validate(self):
        if self.assigned_to and self.status == "Open":
            self.status = "Assigned"
        if self.status in ["Completed", "Closed"] and not self.actual_completion:
            self.actual_completion = frappe.utils.today()

    def on_update(self):
        if self.has_value_changed("assigned_to") and self.assigned_to:
            self.notify_technician()

    def notify_technician(self):
        try:
            frappe.publish_realtime(
                event='service_ticket_assigned',
                message={'ticket': self.name, 'subject': self.subject, 'priority': self.priority},
                user=self.assigned_to
            )
        except Exception as e:
            frappe.log_error(f"Failed to notify technician: {str(e)}")

@frappe.whitelist()
def create_job_card(service_ticket):
    ticket = frappe.get_doc("Service Ticket", service_ticket)
    if ticket.job_card:
        frappe.throw(f"FSM Job Card {ticket.job_card} already exists for this ticket")

    job_card = frappe.new_doc("FSM Job Card")
    job_card.service_ticket = ticket.name
    job_card.client = ticket.client
    job_card.technician = ticket.assigned_to
    job_card.job_date = frappe.utils.today()
    job_card.insert()

    ticket.job_card = job_card.name
    ticket.status = "In Progress"
    ticket.save()

    frappe.msgprint(f"FSM Job Card {job_card.name} created successfully")
    return job_card.name
