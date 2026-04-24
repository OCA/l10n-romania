# Copyright (C) 2025 Dorin Hongu <dhongu(@)gmail(.)com
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import models


class AccountEdiXmlUBLRO(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_ro"

    def _import_ubl_invoice_line_add_product_values(self, collected_values):
        # EXTENDS account.edi.xml.ubl_ro
        res = super()._import_ubl_invoice_line_add_product_values(collected_values)

        line_tree = collected_values["line_tree"]

        vendor_code = line_tree.findtext(
            ".//{*}Item/{*}SellersItemIdentification/{*}ID"
        )
        if not vendor_code:
            vendor_code = line_tree.findtext(
                ".//{*}Item/{*}StandardItemIdentification/{*}ID"
            )

        if vendor_code:
            # Store vendor_code in product_values so the search plan can use it
            collected_values["product_values"]["l10n_ro_vendor_code"] = vendor_code
            # Store also for later use in _create_values
            collected_values["l10n_ro_vendor_code"] = vendor_code

        return res

    def _import_ubl_invoice_line_get_product_base_line_kwargs(self, collected_values):
        # EXTENDS account.edi.xml.ubl_ro
        base_line_kwargs = (
            super()._import_ubl_invoice_line_get_product_base_line_kwargs(
                collected_values
            )
        )

        if vendor_code := collected_values.get("l10n_ro_vendor_code"):
            base_line_kwargs["_create_values"]["l10n_ro_vendor_code"] = vendor_code

        return base_line_kwargs
