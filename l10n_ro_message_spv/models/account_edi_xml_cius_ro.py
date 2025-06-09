# Copyright (C) 2025 Dorin Hongu <dhongu(@)gmail(.)com
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import models


class AccountEdiXmlUBLRO(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_20"  #  "account.edi.xml.ubl_ro"

    def _import_fill_invoice_line_form(self, tree, invoice_line, qty_factor):
        res = super()._import_fill_invoice_line_form(tree, invoice_line, qty_factor)

        vendor_code = self._find_value(
            "./cac:Item/cac:SellersItemIdentification/cbc:ID", tree
        )
        if not vendor_code:
            vendor_code = self._find_value(
                "./cac:Item/cac:StandardItemIdentification/cbc:ID", tree
            )

        if vendor_code:
            invoice = invoice_line.move_id
            invoice_line.l10n_ro_vendor_code = vendor_code
            domain = [
                ("seller_ids.product_code", "=", vendor_code),
                ("seller_ids.partner_id", "=", invoice.partner_id.id),
            ]
            product = self.env["product.product"].search(domain, limit=1)
            if product:
                invoice_line.product_id = product

        return res
