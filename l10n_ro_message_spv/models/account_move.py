# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ro_message_spv_ids = fields.One2many(
        "l10n.ro.message.spv",
        "invoice_id",
        string="Romania - E-invoice messages",
        help="E-invoice messages related to this invoice.",
    )

    def unlink(self):
        domain = [("invoice_id", "in", self.ids)]
        message_spv_ids = self.env["l10n.ro.message.spv"].search(domain)
        attachments = self.env["ir.attachment"]
        attachments += message_spv_ids.mapped("attachment_id")
        attachments += message_spv_ids.mapped("attachment_xml_id")
        attachments += message_spv_ids.mapped("attachment_anaf_pdf_id")
        attachments += message_spv_ids.mapped("attachment_embedded_pdf_id")
        attachments.sudo().write({"res_id": False, "res_model": False})
        return super().unlink()
