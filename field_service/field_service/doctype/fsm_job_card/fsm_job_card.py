import frappe
from frappe.model.document import Document
from frappe.utils.pdf import get_pdf


class FSMJobCard(Document):
    def validate(self):
        # Always sync technician from the linked Service Ticket — single source of truth
        if self.service_ticket:
            self.technician = frappe.db.get_value("Service Ticket", self.service_ticket, "assigned_to")

        if self.qty_hrs and self.rate:
            self.total_in_kshs = self.qty_hrs * self.rate

        for item in self.work_items:
            if item.qty and item.rate:
                item.amount = item.qty * item.rate

    def on_submit(self):
        if self.service_ticket:
            ticket = frappe.get_doc("Service Ticket", self.service_ticket)
            ticket.status = "Completed"
            ticket.actual_completion = frappe.utils.today()
            ticket.save(ignore_permissions=True)

    def on_cancel(self):
        if self.service_ticket:
            ticket = frappe.get_doc("Service Ticket", self.service_ticket)
            ticket.status = "In Progress"
            ticket.save(ignore_permissions=True)


# --- Module-level permission functions (NOT inside the class) ---

def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user
    if "FSM Manager" in frappe.get_roles(user) or "System Manager" in frappe.get_roles(user):
        return ""
    return f'`tabFSM Job Card`.`technician` = "{user}"'


def has_permission(doc, ptype="read", user=None):
    if not user:
        user = frappe.session.user
    if "FSM Manager" in frappe.get_roles(user) or "System Manager" in frappe.get_roles(user):
        return True
    return doc.technician == user


@frappe.whitelist()
def generate_and_email_pdf(job_card_name, recipient_emails=None):
    job_card = frappe.get_doc("FSM Job Card", job_card_name)

    # Subject — from Service Ticket
    job_subject = frappe.db.get_value("Service Ticket", job_card.service_ticket, "subject") or "Completed"

    # Technician — resolve to full name
    tech_name = (
        frappe.db.get_value("User", job_card.technician, "full_name")
        or job_card.technician
        or "N/A"
    )

    html = frappe.get_print(
        "FSM Job Card",
        job_card_name,
        print_format="FSM Job Card Print",
        no_letterhead=False,
    )

    options = {
        "disable-javascript": "",
        "no-images": "",
        "disable-external-links": "",
        "encoding": "UTF-8",
        "page-size": "A4",
        "margin-right": "15mm",
        "margin-left": "15mm",
        "margin-top": "15mm",
        "margin-bottom": "15mm",
    }

    pdf = get_pdf(html, options=options)

    recipients = []
    if recipient_emails:
        recipients = [e.strip() for e in recipient_emails.split(",") if e.strip()]

    if not recipients and job_card.client:
        client = frappe.get_doc("Service Client", job_card.client)
        client_email = getattr(client, "email", None) or getattr(client, "email_id", None)
        if client_email:
            recipients.append(client_email)

    if not recipients:
        frappe.throw("No recipient email found. Please provide at least one email address.")

    frappe.sendmail(
        recipients=recipients,
        subject=f"Job Card {job_card.name} - {job_subject}",
        message=f"""
            <p>Dear Sir/Madam,</p>
            <p>Please find attached the completed job card for Service Ticket <strong>{job_card.service_ticket}</strong>.</p>
            <ul>
                <li><strong>Job Card No:</strong> {job_card.name}</li>
                <li><strong>Subject:</strong> {job_subject}</li>
                <li><strong>Date:</strong> {job_card.job_date}</li>
                <li><strong>Technician:</strong> {tech_name}</li>
                <li><strong>Client:</strong> {job_card.client}</li>
            </ul>
            <p>Thank you for your business.</p>
        """,
        attachments=[{"fname": f"{job_card.name}.pdf", "fcontent": pdf}],
        now=True,
    )

    frappe.msgprint(f"Job Card PDF sent to: {', '.join(recipients)}")
    return True