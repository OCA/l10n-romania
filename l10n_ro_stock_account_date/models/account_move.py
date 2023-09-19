# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import _, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        res = super(AccountMove, self).action_post()

        for move in self.filtered("is_l10n_ro_record"):
            invoice_lines = move.invoice_line_ids.filtered(
                lambda l: not l.display_type and l.product_id.type == "product"
            )
            if not invoice_lines:
                continue

            ok = False
            product = self.env["product.product"]
            for line in invoice_lines:
                product = line.product_id
                stock_moves = line._l10n_ro_get_valuation_stock_moves()
                for stock_move in stock_moves:
                    has_notice = getattr(stock_move.picking_id, "l10n_ro_notice", False)
                    if has_notice and stock_move.picking_id.l10n_ro_notice:
                        ok = True
                        break
                    if stock_move.date.date() == move.date:
                        ok = True
                        break
            if not ok:
                message = _(
                    "There is no stock move with date %(date)s for product %(product)s",
                    date=move.date,
                    product=product.name,
                )

                _logger.warning(message)
                move.sudo().activity_schedule(
                    "mail.mail_activity_data_warning",
                    summary=_("Incorrect Date"),
                    note=message,
                    user_id=move.user_id.id,
                )
        return res
