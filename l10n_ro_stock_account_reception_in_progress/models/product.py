# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ["product.template", "l10n.ro.mixin"]

    def _get_product_accounts(self):
        accounts = super()._get_product_accounts()

        company = (
            self.env["res.company"].browse(self._context.get("force_company"))
            or self.env.company
        )
        if not self.env["res.company"]._check_is_l10n_ro_record(company.id):
            return accounts

        valued_type = self.env.context.get("valued_type", "indefinite")

        # in nir si factura se ca utiliza 327 sau contul setat in account
        if self.env.context.get("l10n_ro_reception_in_progress"):
            if valued_type == "reception_in_progress":
                account = accounts["stock_input"]
                if account.l10n_ro_reception_in_progress_account_id:
                    accounts[
                        "stock_input"
                    ] = account.l10n_ro_reception_in_progress_account_id
        return accounts
