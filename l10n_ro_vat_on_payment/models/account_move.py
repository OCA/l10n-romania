# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import date

from odoo import api, models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n.ro.mixin"]

    @api.depends("partner_id", "partner_shipping_id", "company_id", "move_type")
    def _compute_fiscal_position_id(self):
        """Set the VAT on Payment fiscal position when the company (or, for
        purchase documents, the supplier) is registered as VAT on Payment.

        This is done in the compute (not only in an onchange) so that it also
        applies when moves are created programmatically - e.g. from
        subscriptions, imports or direct ``create()`` calls - where onchanges
        never run. ``no_insert=True`` avoids triggering the ANAF subprocess
        during the compute; the history is kept up to date by the daily cron
        and by res.partner create/write.
        """
        res = super()._compute_fiscal_position_id()
        for move in self:
            if not move.is_l10n_ro_record or move.move_type == "entry":
                continue
            company = move.company_id
            fptvainc = company.l10n_ro_property_vat_on_payment_position_id
            if not fptvainc:
                continue
            partner = (
                self.env["res.partner"]._find_accounting_partner(move.partner_id)
                or move.partner_id
            )
            # TVA la încasare este un regim intern: se aplică doar în relația
            # cu parteneri români. La operațiuni intracomunitare / export
            # (partener cu țară străină) nu se aplică. Partenerii fără țară
            # completată sunt tratați ca interni (național / nespecificat).
            if partner.country_id and partner.country_id.code != "RO":
                continue
            ctx = {
                "no_insert": True,
                "check_date": move.invoice_date or date.today(),
            }
            vatp = company.partner_id.with_context(**ctx)._check_vat_on_payment()
            if not vatp and move.is_purchase_document() and partner:
                vatp = partner.with_context(**ctx)._check_vat_on_payment()
            if vatp:
                move.fiscal_position_id = fptvainc
        return res

    # urmatoerele linii strica inchiderea standard de TVA
    # @api.depends("line_ids.account_id.account_type")
    # def _compute_always_tax_exigible(self):
    #     self_ro = self.filtered(lambda line: line.is_l10n_ro_record)
    #     self_no_ro = self - self_ro
    #     for record in self_ro:
    #         record.always_tax_exigible = (
    #             record.is_invoice(True) or record._collect_tax_cash_basis_values()
    #         )
    #     return super(AccountMove, self_no_ro)._compute_always_tax_exigible()
