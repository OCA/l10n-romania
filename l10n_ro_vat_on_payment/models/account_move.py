# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import date

from odoo import api, models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n.ro.mixin"]

    @api.onchange("partner_id", "company_id")
    def _onchange_partner_id(self):
        """Check if invoice is with VAT on Payment.
        Romanian law specify that the VAT on payment is applied only
        for internal invoices (National or not specified fiscal position)
        """
        result = super()._onchange_partner_id()
        if self.is_l10n_ro_record:
            ctx = dict(self.env.context)
            company = self.company_id
            partner = (
                self.env["res.partner"]._find_accounting_partner(self.partner_id)
                or self.partner_id
            )
            if self.invoice_date:
                ctx.update({"check_date": self.invoice_date})
            else:
                ctx.update({"check_date": date.today()})
            vatp = company.partner_id.with_context(**ctx)._check_vat_on_payment()
            if not vatp and self.is_purchase_document() and partner:
                vatp = partner.with_context(**ctx)._check_vat_on_payment()
            if vatp and self.move_type != "entry":
                fptvainc = company.l10n_ro_property_vat_on_payment_position_id
                if fptvainc:
                    self.fiscal_position_id = fptvainc
        return result

    @api.depends("line_ids.account_id.account_type")
    def _compute_always_tax_exigible(self):
        self_ro = self.filtered(lambda line: line.is_l10n_ro_record)
        self_no_ro = self - self_ro
        for record in self_ro:
            record.always_tax_exigible = (
                record.is_invoice(True) and record._collect_tax_cash_basis_values()
            )
        return super(AccountMove, self_no_ro)._compute_always_tax_exigible()
