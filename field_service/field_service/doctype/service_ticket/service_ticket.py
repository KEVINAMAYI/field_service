import frappe
from frappe.model.document import Document


class ServiceTicket(Document):
    def validate(self):
        if not self.assigned_to:
            frappe.throw("Please assign the Service Ticket to a technician before saving.")

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
                event="service_ticket_assigned",
                message={
                    "ticket": self.name,
                    "subject": self.subject,
                    "priority": self.priority,
                },
                user=self.assigned_to,
            )
        except Exception as e:
            frappe.log_error(f"Failed to notify technician: {str(e)}")


# --- Module-level permission functions (NOT inside the class) ---

def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user
    if "FSM Manager" in frappe.get_roles(user) or "System Manager" in frappe.get_roles(user):
        return ""
    return f'`tabService Ticket`.`assigned_to` = "{user}"'


def has_permission(doc, ptype="read", user=None):
    if not user:
        user = frappe.session.user
    if "FSM Manager" in frappe.get_roles(user) or "System Manager" in frappe.get_roles(user):
        return True
    return doc.assigned_to == user


@frappe.whitelist()
def create_job_card(service_ticket):
    ticket = frappe.get_doc("Service Ticket", service_ticket)

    if not ticket.assigned_to:
        frappe.throw("Cannot create a Job Card — Service Ticket has no assigned technician.")

    if ticket.job_card:
        frappe.throw(f"FSM Job Card {ticket.job_card} already exists for this ticket.")

    job_card = frappe.new_doc("FSM Job Card")
    job_card.service_ticket = ticket.name
    job_card.client         = ticket.client
    job_card.technician     = ticket.assigned_to
    job_card.job_date       = frappe.utils.today()
    job_card.insert(ignore_permissions=True)

    ticket.job_card = job_card.name
    ticket.status   = "In Progress"
    ticket.save(ignore_permissions=True)

    frappe.msgprint(f"FSM Job Card {job_card.name} created successfully")
    return job_card.name