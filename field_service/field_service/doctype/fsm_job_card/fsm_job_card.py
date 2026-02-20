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
def generate_and_email_pdf(job_card_name, recipient_email=None):
    job_card = frappe.get_doc("FSM Job Card", job_card_name)
    html = frappe.get_print("FSM Job Card", job_card_name, print_format="FSM Job Card Print")
    pdf = get_pdf(html)

    if not recipient_email and job_card.client:
        client = frappe.get_doc("Service Client", job_card.client)
        recipient_email = client.email

    if not recipient_email:
        frappe.throw("No recipient email found. Please provide an email address.")

    frappe.sendmail(
        recipients=[recipient_email],
        subject=f"Job Card {job_card.name} - Completed",
        message=f"""
            <p>Dear Sir/Madam,</p>
            <p>Please find attached the completed job card for Service Ticket {job_card.service_ticket}.</p>
            <ul>
                <li>Job Card No: {job_card.name}</li>
                <li>Date: {job_card.job_date}</li>
                <li>Technician: {job_card.technician}</li>
                <li>Client: {job_card.client}</li>
            </ul>
            <p>Thank you for your business.</p>
        """,
        attachments=[{'fname': f'{job_card.name}.pdf', 'fcontent': pdf}]
    )
    frappe.msgprint(f"Job Card PDF sent to {recipient_email}")
    return True
