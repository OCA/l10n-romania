from . import models
from odoo import api, SUPERUSER_ID


def give_initial_sequence_to_payments(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Cache_journals = env["account.journal"].search([("type", "=", "cash")])
    Payment = env["account.payment"]
    for journal in Cache_journals:
        payments = Payment.search(
            [
                ("state", "=", "posted"),
                ("is_internal_transfer", "!=", True),
                ("journal_id", "=", journal.id),
                ("partner_type", "=", "customer"),
                ("payment_out_number", "=", ""),
            ],
            order="date asc, id asc",
        )
        prefix = "C"
        index = 1
        for payment in payments:
            payment.payment_out_number = prefix + f"{index:04}"
            index += 1
