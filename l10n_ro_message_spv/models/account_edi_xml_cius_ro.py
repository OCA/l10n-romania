# Copyright (C) 2025 Dorin Hongu <dhongu(@)gmail(.)com
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import models


class AccountEdiXmlUBLRO(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_ro"

    def _retrieve_invoice_line_vals(self, tree, document_type=False, qty_factor=1):
        res = super()._retrieve_invoice_line_vals(tree, document_type, qty_factor)

        vendor_code = self._find_value(
            "./cac:Item/cac:SellersItemIdentification/cbc:ID", tree
        )
        if not vendor_code:
            vendor_code = self._find_value(
                "./cac:Item/cac:StandardItemIdentification/cbc:ID", tree
            )

        if vendor_code:
            res["l10n_ro_vendor_code"] = vendor_code
            domain = [("seller_ids.product_code", "=", vendor_code)]

            # Try to find the partner to make the product search more specific
            invoice_tree = tree.getroottree().getroot()
            # In UBL 2.1, the partner is under
            # AccountingSupplierParty (for vendor bills)
            # or AccountingCustomerParty (for customer invoices)
            # Since we are usually importing vendor bills in this context:
            partner_vals = self._import_retrieve_partner_vals(
                invoice_tree, "AccountingSupplier"
            )
            partner, _logs = self.with_company(self.env.company)._import_partner(
                self.env.company, **partner_vals
            )

            if partner:
                domain.append(("seller_ids.partner_id", "=", partner.id))

            product = self.env["product.product"].search(domain, limit=1)
            if product:
                res["product_id"] = product.id

        return res
