# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ro_message_spv_ids = fields.One2many(
        "l10n.ro.message.spv",
        "invoice_id",
        string="Romania - E-invoice messages",
        help="E-invoice messages related to this invoice.",
    )

    l10n_ro_edi_transaction = fields.Char(
        "Transaction ID (RO)",
        help="Technical field used to track the status of a submission.",
        copy=False,
    )
    l10n_ro_edi_download = fields.Char(
        "ID Download ANAF (RO)",
        help="ID used to download the ZIP file from ANAF.",
        copy=False,
    )

    def action_post(self):
        res = super().action_post()
        invoices = self.filtered(
            lambda inv: inv.move_type in ["in_invoice", "in_refund"]
        )
        for invoice in invoices:
            for line in invoice.invoice_line_ids:
                if line.l10n_ro_vendor_code and line.product_id:
                    supplier_info = line.product_id.seller_ids.filtered(
                        lambda s, i=invoice: s.partner_id.id == i.partner_id.id
                    )
                    if not supplier_info:
                        self.env["product.supplierinfo"].create(
                            {
                                "partner_id": invoice.partner_id.id,
                                "product_name": line.name,
                                "product_code": line.l10n_ro_vendor_code,
                                "product_id": line.product_id.id,
                                "price": line.price_unit,
                                "currency_id": invoice.currency_id.id,
                                "product_uom": line.product_uom_id.id,
                            }
                        )
                    else:
                        supplier_info = supplier_info.filtered(
                            lambda s: not s.product_code
                        )
                        supplier_info.write({"product_code": line.l10n_ro_vendor_code})

        return res

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

    # def _get_edi_decoder(self, file_data, new=False):
    #
    #     return super()._get_edi_decoder(file_data, new=new)

    def _compute_show_reset_to_draft_button(self):
        res = super()._compute_show_reset_to_draft_button()
        for move in self:
            if not move.show_reset_to_draft_button:
                if move.move_type in ["in_invoice", "in_refund"]:
                    move.show_reset_to_draft_button = True
        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_ro_vendor_code = fields.Char(string="Vendor Code", copy=False)

    def _compute_name(self):
        lines = self.filtered(
            lambda line: line.move_id.move_type in ["in_invoice", "in_refund"]
            and line.move_id.l10n_ro_edi_download
        )

        return super(AccountMoveLine, self - lines)._compute_name()

    def _compute_price_unit(self):
        lines = self.filtered(
            lambda line: line.move_id.move_type in ["in_invoice", "in_refund"]
            and line.move_id.l10n_ro_edi_download
        )

        return super(AccountMoveLine, self - lines)._compute_price_unit()
