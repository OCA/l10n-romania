# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


def _l10n_ro_journal_domain(model):
    """Which journals a payment method may book into.

    Core offers a cash journal only while no payment method uses it yet, so
    every register ends up with a cash journal of its own. A Romanian shop
    running several registers in the same place keeps one *registru de casa*
    for that place: the cash of all of them is a single till, counted and
    reported together. Their payment methods therefore have to point at the
    same cash journal, so offer it whether or not another method already uses
    it.
    """
    core_domain = [
        "|",
        "&",
        ("type", "=", "cash"),
        ("pos_payment_method_ids", "=", False),
        ("type", "=", "bank"),
    ]
    if not model.env.company._check_is_l10n_ro_record():
        return core_domain
    return ["|", ("type", "=", "cash"), ("type", "=", "bank")]


class PosPaymentMethod(models.Model):
    _name = "pos.payment.method"
    _inherit = ["pos.payment.method", "l10n.ro.mixin"]

    journal_id = fields.Many2one(domain=_l10n_ro_journal_domain)
