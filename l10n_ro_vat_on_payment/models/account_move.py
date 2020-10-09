# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange("partner_id", "company_id")
    def _onchange_partner_id(self):
        """Check if invoice is with VAT on Payment.
        Romanian law specify that the VAT on payment is applied only
        for internal invoices (National or not specified fiscal position)
        """
        result = super(AccountMove, self)._onchange_partner_id()
        fp_model = self.env["account.fiscal.position"]
        vatp = False
        ctx = dict(self._context)
        company = self.company_id
        partner = (
            self.env["res.partner"]._find_accounting_partner(self.partner_id)
            or self.partner_id
        )
        if self.invoice_date:
            ctx.update({"check_date": self.invoice_date})
        if "out" in self.move_type:
            vatp = company.partner_id.with_context(ctx)._check_vat_on_payment()
        else:
            if partner:
                vatp = partner.with_context(ctx)._check_vat_on_payment()
        if vatp:
            fptvainc = fp_model.search(
                [
                    ("name", "ilike", "Regim TVA la Incasare"),
                    ("company_id", "=", self.env.company.id),
                ],
                limit=1,
            )
            if fptvainc:
                self.fiscal_position_id = fptvainc
        return result
