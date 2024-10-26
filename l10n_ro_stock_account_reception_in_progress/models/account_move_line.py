# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ["account.move.line", "l10n.ro.mixin"]

    def _compute_account_id(self):
        remaining = self
        reception_in_progress_lines = self.env["account.move.line"].with_context(
            l10n_ro_reception_in_progress=True, valued_type="reception_in_progress"
        )
        for linie in self:
            if linie.product_id.type == "product" and linie.is_l10n_ro_record:
                if linie.move_id.is_purchase_document():
                    purchase = linie.purchase_order_id
                    if (
                        purchase
                        and purchase.l10n_ro_reception_in_progress
                        and linie.product_id.purchase_method == "receive"
                    ):
                        reception_in_progress_lines |= linie
                        remaining -= linie
        if reception_in_progress_lines:
            super(AccountMoveLine, reception_in_progress_lines)._compute_account_id()
        return super(AccountMoveLine, remaining)._compute_account_id()
