import frappe
from frappe.model.document import Document
from frappe.utils.pdf import get_pdf

class FSMJobCard(Document):
    def validate(self):
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
            ticket.save()

    def on_cancel(self):
        if self.service_ticket:
            ticket = frappe.get_doc("Service Ticket", self.service_ticket)
            ticket.status = "In Progress"
            ticket.save()


@frappe.whitelist()
def generate_and_email_pdf(job_card_name, recipient_emails=None):
    job_card = frappe.get_doc("FSM Job Card", job_card_name)

    # Fetch subject directly from the linked Service Ticket — no field needed on Job Card
    job_subject = None
    if job_card.service_ticket:
        job_subject = frappe.db.get_value("Service Ticket", job_card.service_ticket, "subject")
    job_subject = job_subject or "Completed"

    # Resolve technician display name — same logic as the print format
    tech_name = (
        frappe.db.get_value("User", job_card.technician, "full_name")
        or frappe.db.get_value("Employee", {"user_id": job_card.technician}, "employee_name")
        or job_card.technician
        or "N/A"
    )

    html = frappe.get_print(
        "FSM Job Card",
        job_card_name,
        print_format="FSM Job Card Print",
        no_letterhead=False
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

    # Build recipient list — support comma-separated emails from the prompt
    recipients = []

    if recipient_emails:
        # Split on commas, strip whitespace, drop empty strings
        recipients = [e.strip() for e in recipient_emails.split(",") if e.strip()]

    # Fall back to client email if nothing was provided
    if not recipients and job_card.client:
        client = frappe.get_doc("Service Client", job_card.client)
        if client.email:
            recipients.append(client.email)

    if not recipients:
        frappe.throw("No recipient email found. Please provide at least one email address.")

    frappe.sendmail(
        recipients=recipients,          # list → Frappe handles multiple addresses natively
        subject=f"Job Card {job_card.name} - {job_subject}",
        message=f"""
            <p>Dear Sir/Madam,</p>
            <p>Please find attached the completed job card for Service Ticket {job_card.service_ticket}.</p>
            <ul>
                <li>Job Card No: {job_card.name}</li>
                <li>Subject: {job_subject}</li>
                <li>Date: {job_card.job_date}</li>
                <li>Technician: {tech_name}</li>
                <li>Client: {job_card.client}</li>
            </ul>
            <p>Thank you for your business.</p>
        """,
        attachments=[{'fname': f'{job_card.name}.pdf', 'fcontent': pdf}],
        now=True
    )

    # Friendly confirmation listing all addresses
    sent_to = ", ".join(recipients)
    frappe.msgprint(f"Job Card PDF sent to: {sent_to}")
    return True