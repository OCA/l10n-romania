# Copyright (C) 2024 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountEdiDocument(models.Model):
    _inherit = "account.edi.document"

    def write(self, vals):
        res = super(AccountEdiDocument, self).write(vals)
        cius_ro = self.env.ref("l10n_ro_account_edi_ubl.edi_ubl_cius_ro")
        if vals.get("attachment_id") and cius_ro in self.mapped("edi_format_id"):
            cius_invoices = self.filtered(
                lambda x: x.edi_format_id == cius_ro
                and x.move_id.company_id.l10n_ro_edi_cius_embed_pdf
                and cius_ro._is_required_for_invoice(x.move_id)
            ).mapped("move_id")
            cius_invoices._l10n_ro_add_pdf_to_xml()
        return res
