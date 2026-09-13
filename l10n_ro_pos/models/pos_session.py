# Copyright (C) 2015 Deltatech
# Copyright (C) 2015 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import models

# Buckets accumulated by core for the goods issue of the uninvoiced orders.
# "stock_valuation" belongs here even though it is consumed separately by
# _create_stock_valuation_lines (called from _create_account_move): its
# counterpart is "stock_expense", so the two have to go together or the closing
# entry ends up unbalanced by exactly the cost of goods of those orders.
L10N_RO_STOCK_KEYS = ("stock_expense", "stock_return", "stock_valuation")


class PosSession(models.Model):
    _inherit = "pos.session"

    def _l10n_ro_stock_move_posts_goods_issue(self):
        """Is the goods issue already posted by the stock move itself?

        l10n_ro_stock_account makes every Romanian stock move create its own
        accounting entry, whatever the product valuation is, so the session
        closing entry would post the goods issue a second time.  With only
        l10n_ro_config installed nothing posts it and the closing entry stays
        the sole source of it, so the check is on the module, not on the
        company.
        """
        self.ensure_one()
        return (
            self.company_id.l10n_ro_accounting
            and "l10n_ro_move_type" in self.env["stock.move"]._fields
        )

    def _accumulate_amounts(self, data):
        data = super()._accumulate_amounts(data)
        if not self._l10n_ro_stock_move_posts_goods_issue():
            return data
        # The amounts themselves stay correct -- they are the cost of goods of
        # the session -- so keep them under l10n_ro_* keys for reporting and
        # for modules building on top of them; only the accounting lines must
        # not be generated.
        for key in L10N_RO_STOCK_KEYS:
            data[f"l10n_ro_{key}"] = data[key]
            data[key] = {}
        return data
