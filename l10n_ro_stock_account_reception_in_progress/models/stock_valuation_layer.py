# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models


class StockValuationLayer(models.Model):
    _name = "stock.valuation.layer"
    _inherit = ["stock.valuation.layer", "l10n.ro.mixin"]

    def _l10n_ro_can_use_invoice_line_account(self, account):
        self.ensure_one()
        if (
            self.l10n_ro_valued_type in ("reception", "reception_return")
            and self.l10n_ro_invoice_line_id
        ):
            inv_line_account = self.l10n_ro_invoice_line_id.account_id
            if inv_line_account == account.l10n_ro_reception_in_progress_account_id:
                return False

        return super()._l10n_ro_can_use_invoice_line_account(account)
