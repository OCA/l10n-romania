# Copyright (C) 2022 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class StockValuationLayer(models.Model):
    _name = "stock.valuation.layer"
    _inherit = ["stock.valuation.layer", "l10n.ro.mixin"]

    def _check_company(self, fnames=None):
        for svl in self:
            if svl.is_l10n_ro_record:
                if (
                    fnames is None
                    and svl.company_id.parent_id == svl.account_move_id.company_id
                ):
                    fnames = dict(self._fields)
                    fnames.pop("account_move_id")
            super(StockValuationLayer, svl)._check_company(fnames)
