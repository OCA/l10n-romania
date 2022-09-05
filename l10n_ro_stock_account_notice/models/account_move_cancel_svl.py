# Copyright (C) 2022 cbssolutions.ro
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    # we can not set the draft the notice reception svl/account_move when exist recived bill
    # if we want, first we must set to draft the recived bill
    _inherit = "account.move"

    def button_draft(self):
        res = super().button_draft()
        for move in self:
            if move.is_l10n_ro_record:
                if move.stock_valuation_layer_ids:
                    svls = move.stock_valuation_layer_ids.filtered(
                        lambda r: not r.l10n_ro_draft_svl_id
                        and not (r.l10n_ro_draft_svl_ids and r.quantity == 0)
                    )
                    pickings = svls.stock_move_id.picking_id
                    posted_bills_for_notice = pickings.l10n_ro_notice_bill_id.filtered(
                        lambda r: r.state == "posted"
                    )
                    if posted_bills_for_notice:
                        raise UserError(
                            _(
                                f"You can not set to draft this entry=({move.id, move.name}),  "
                                f"because you have a posted bill=({posted_bills_for_notice},{posted_bills_for_notice[0].name}) for picking notice. "
                                "First set to draft that bill (it contains diffrence between notice value and bill value)."
                            )
                        )
                # at setting to draft we are deleting the diferences with notice pickings because will be recomputed at post
                move.line_ids.filtered(
                    lambda r: r.l10n_ro_notice_invoice_difference
                ).unlink()
        return res
