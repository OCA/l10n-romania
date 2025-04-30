# Copyright (C) 2025 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ["account.move.line", "l10n.ro.mixin"]

    def _compute_account_id(self):
        res = super()._compute_account_id()
        for linie in self:
            if linie.product_id.type == "consu" and linie.is_l10n_ro_record:
                if linie.move_id.is_purchase_document():
                    purchase = linie.purchase_order_id
                    if (
                        purchase
                        and purchase.l10n_ro_reception_in_progress
                        and linie.product_id.purchase_method == "receive"
                    ):
                        account_stock_input = linie.product_id._get_product_accounts()[
                            "stock_valuation"
                        ]
                        if account_stock_input.l10n_ro_reception_in_progress_account_id:
                            linie.account_id = account_stock_input.l10n_ro_reception_in_progress_account_id  # noqa E501
        return res
