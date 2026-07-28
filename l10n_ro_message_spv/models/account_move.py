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
                                "product_uom_id": line.product_uom_id.id,
                            }
                        )
                    else:
                        supplier_info = supplier_info.filtered(
                            lambda s: not s.product_code
                        )
                        supplier_info.write({"product_code": line.l10n_ro_vendor_code})

        return res

    def unlink(self):
        # Detach the signed ANAF ZIP so it survives the invoice deletion —
        # it is the legal proof and stays on the SPV message. The derived
        # files (XML, PDFs) live only on the invoice and are deleted with
        # it; they can be re-derived from the ZIP at any time.
        domain = [("invoice_id", "in", self.ids)]
        message_spv_ids = self.env["l10n.ro.message.spv"].search(domain)
        attachments = message_spv_ids.mapped("attachment_id")
        attachments.sudo().write({"res_id": False, "res_model": False})
        # Facturile de achizitie venite din SPV primesc un document
        # l10n_ro_edi.document (vezi message_spv._confirm), al carui invoice_id e
        # required => ondelete restrict. El blocheaza stergerea facturii (ex.
        # achizitie ciorna sau anulata adusa automat din SPV). Documentul e
        # sintetic, creat doar pentru controlul dedup-ului; urma reala SPV ramane
        # pe l10n.ro.message.spv + atasamente. Il curatam strict pentru facturile
        # de achizitie (factura/nota de credit) cu origine SPV, aflate in ciorna
        # sau anulate (singurele stari in care Odoo permite oricum stergerea), ca
        # sa nu atingem documentele-audit ale facturilor proprii trimise la
        # e-Factura.
        spv_moves = self.filtered(
            lambda m: m.l10n_ro_message_spv_ids
            and m.move_type in ("in_invoice", "in_refund")
            and m.state in ("draft", "cancel")
        )
        spv_moves.l10n_ro_edi_document_ids.sudo().unlink()
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

    def _l10n_ro_is_spv_bill(self):
        """Vendor bill whose content was imported from an SPV XML.

        Both SPV stacks are covered: bills created by this module
        (``l10n_ro_edi_download``) and bills created by the standard
        ``l10n_ro_edi`` SPV fetch (``l10n_ro_edi_index``).
        """
        self.ensure_one()
        if self.move_type not in self.get_purchase_types():
            return False
        return bool(
            self.l10n_ro_edi_download
            or self.l10n_ro_edi_transaction
            or self.l10n_ro_edi_index
            or self.l10n_ro_message_spv_ids
        )


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_ro_vendor_code = fields.Char(string="Vendor Code", copy=False)

    def _l10n_ro_is_spv_imported_line(self):
        """Line brought in from the SPV XML, as opposed to one keyed in by hand.

        The values of such a line (description, unit price) are the ones the
        supplier legally issued, so they must survive the user correcting the
        product. Lines added manually on the same bill keep the standard Odoo
        behaviour.
        """
        self.ensure_one()
        move = self.move_id
        if not move or not move._l10n_ro_is_spv_bill():
            return False
        # ``is_imported`` is set by the core on every line created from an
        # imported attachment; the vendor code covers lines imported before
        # this flag existed.
        return bool(self.is_imported or self.l10n_ro_vendor_code)

    def _compute_name(self):
        # Keep the description received from SPV when the product is corrected.
        lines = self.filtered(
            lambda line: line.name and line._l10n_ro_is_spv_imported_line()
        )

        return super(AccountMoveLine, self - lines)._compute_name()

    def _compute_price_unit(self):
        # Keep the unit price received from SPV when the product is corrected.
        lines = self.filtered(lambda line: line._l10n_ro_is_spv_imported_line())

        return super(AccountMoveLine, self - lines)._compute_price_unit()
