# Copyright (C) 2015 Deltatech
# Copyright (C) 2015 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import Command, models


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

    def _prepare_session_closing_extra_line_commands(
        self, orders, refund, payments=None
    ):
        """Keep the closing entry from posting the goods issue a second time.

        Odoo 19 accumulated the cost of goods of a session into buckets that
        ``_accumulate_amounts`` could empty. Odoo 20 removed them: ``pos_stock``
        appends an expense/stock pair straight onto the closing entry, one per
        stock move of the session. The Romanian stock move posts that entry
        itself, so the pair books the same goods a second time.

        Core offers no seam to keep ``pos_stock`` out of the chain, so its pairs
        are taken off again here -- recognised by the move they come from
        already carrying its own accounting entry. The moves keep their value,
        which is where the cost of goods is read from anyway.
        """
        lines = super()._prepare_session_closing_extra_line_commands(
            orders, refund, payments if payments is not None else []
        )
        if not self._l10n_ro_stock_move_posts_goods_issue():
            return lines
        posted = (self.picking_ids | orders.picking_ids).move_ids.filtered(
            "account_move_id"
        )
        if not posted:
            return lines
        names = set(posted.product_id.mapped("display_name"))
        accounts = set()
        for move in posted:
            product_accounts = move.with_company(
                move.company_id
            ).product_id._get_product_accounts()
            accounts.update(
                account.id
                for account in (
                    product_accounts.get("expense"),
                    product_accounts.get("stock_valuation"),
                )
                if account
            )
        return [
            command
            for command in lines
            if not (
                command[0] == Command.CREATE
                and command[2].get("name") in names
                and command[2].get("account_id") in accounts
            )
        ]
