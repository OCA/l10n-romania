# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import date

from odoo import models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n.ro.mixin"]

    def get_l10n_ro_vat_on_payment_fp(self):
        """
        Get the fiscal position for VAT on Payment.
        :param company: The company for which to get the fiscal position.
        :param partner: The partner for which to get the fiscal position.
        :return: The fiscal position with VAT on Payment.
        """
        company = self.company_id
        partner = self.partner_id
        if partner:
            partner = partner._find_accounting_partner(partner)
        ctx = dict(self._context)
        if self.invoice_date:
            ctx.update({"check_date": self.invoice_date})
        else:
            ctx.update({"check_date": date.today()})
        vatp = company.partner_id.with_context(**ctx)._check_vat_on_payment()
        if not vatp and self.is_purchase_document() and partner:
            vatp = partner.with_context(**ctx)._check_vat_on_payment()
        fptvainc = False
        if vatp and self.move_type != "entry":
            fptvainc = company.l10n_ro_property_vat_on_payment_position_id
        return fptvainc

    def _inverse_partner_id(self):
        res = super()._inverse_partner_id()
        for record in self:
            if record.is_l10n_ro_record and record.is_purchase_document(
                include_receipts=True
            ):
                vatp = record.get_l10n_ro_vat_on_payment_fp()
                if vatp:
                    record.fiscal_position_id = vatp
                    record.action_update_fpos_values()
        return res

    def _inverse_company_id(self):
        res = super()._inverse_company_id()
        for record in self:
            if record.is_l10n_ro_record and record.is_sale_document(
                include_receipts=True
            ):
                vatp = record.get_l10n_ro_vat_on_payment_fp()
                if vatp:
                    record.fiscal_position_id = vatp
                    record.action_update_fpos_values()
        return res

    def _compute_always_tax_exigible(self):
        self_ro = self.filtered(lambda line: line.is_l10n_ro_record)
        self_no_ro = self - self_ro
        for record in self_ro:
            record.always_tax_exigible = (
                record.is_invoice(True) and record._collect_tax_cash_basis_values()
            )
        return super(AccountMove, self_no_ro)._compute_always_tax_exigible()
