# Copyright (C) 2020 OdooERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    # store partner data in case of some future partner modification
    # for reports to have the values form invoice time
    invoice_partner_display_vat = fields.Char(
        "VAT Number", compute="_compute_vat_store", store=True
    )

    @api.depends("partner_id")
    def _compute_vat_store(self):
        for record in self:
            record.invoice_partner_display_vat = record.partner_id.vat or ""
