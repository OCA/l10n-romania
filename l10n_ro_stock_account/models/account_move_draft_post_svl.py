# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from ast import literal_eval
from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    # try to keep the stock value account 3xx at same value as stock_valuation
    # at setting to draft account_moves that have valuation on them
    # can be the case of reception or + inventory

    _inherit = "account.move"

    def action_post(self):
        # post again of account_moves with svl ( before were set to draft)
        precision = self.env["decimal.precision"].precision_get(
            "Product Unit of Measure"
        )

        for move in self.filtered(
            lambda r: r.is_l10n_ro_record and r.stock_valuation_layer_ids
        ):

            for svl in move.stock_valuation_layer_ids:
                text_error = (
                    f"For AccountMove:({move.ref},{move.id}) at "
                    f"product=({svl.product_id.name},{svl.product_id.id}) "
                    f"svl={svl} qty = {svl.quantity}"
                )
                if svl.quantity <= 0:
                    raise UserError(
                        _(
                            text_error
                            + f" svl quantity is less than 0, is a out move with value from stock. You are not allowed to do it because were modifed also other svl "
                        )
                    )

                text_error = (
                    f"For AccountMove:({move.ref},{move.id}) at "
                    f"product=({svl.product_id.name},{svl.product_id.id}) "
                    f"qty = {svl.quantity}"
                )
                move_line = move.line_ids.filtered(
                    lambda r: r.product_id == svl.product_id
                )
                line_qty = (
                    move_line.quantity
                )  # HERE I THINK I MUST CONVERT THE POSIBLE QTY IN PRODUCT QTY
                if len(move_line) not in [1, 2]:  # 1 at invoice, 2 a entry
                    raise UserError(
                        _(
                            text_error
                            + f" something is wrong. We should have one line for this svl  "
                            f"svl={svl} move_line={move_line}"
                        )
                    )
                # we are going to modify the existing svl with values form confiremd bill
                if not svl.quantity:
                    raise UserError(
                        _(
                            text_error
                            + f" we do not have any unit of quanty from this product  "
                            f"svl={svl}. You can not validate the invoice because is going to "
                            "create value in 3xx but with no value to put in stock (qty =0),"
                            " you can validate the bill with a non sotable product instead of this"
                        )
                    )
                if svl.quantity != line_qty:
                    raise UserError(
                        _(
                            text_error
                            + f" in bill line you have qty={line_qty} you have qty={svl.quantity }. "
                            "Quantities must be equal"
                        )
                    )
                balance = move_line[0].balance
                unit_cost = balance / line_qty
                remaining_value = svl.remaining_value + balance
                svl.write(
                    {
                        "remaining_value": remaining_value,
                        # can be diff because landed cost
                        "value": balance,
                        "unit_cost": unit_cost,  # maybe with ..
                        "l10n_ro_bill_accounting_date": move.date,
                        "l10n_ro_draft_history": (
                            f"{fields.datetime.now()} POSTED "
                            f"Bill={move.name} bill_id={move.id} "
                            f"balance={balance} unit_cost={unit_cost} "
                            f"old remaining_value={svl.remaining_value} "
                            f"new remaining_value={remaining_value} "
                            "\n"
                        )
                        + (svl.l10n_ro_draft_history or ""),
                    }
                )

        res = super(AccountMove, self).action_post()

        return res

    def button_draft(self):
        # we are deleting the created svl if the stock is intact
        # if not we are blocking the operation because is going to create
        # diffrence beteen account 3xx and stock value
        for move in self:
            if (
                move.is_l10n_ro_record
                and move.stock_valuation_layer_ids
                and move.state != "cancel"
            ):
                for svl in move.stock_valuation_layer_ids:
                    text_error = (
                        f"For AccountMove=({move.ref},{move.id}) at "
                        f"product=({svl.product_id.name},{svl.product_id.id}) "
                        f"svl={svl} qty={svl.quantity}"
                    )
                    if svl.quantity <= 0 and svl.value != 0:
                        raise UserError(
                            _(
                                text_error
                                + f" svl quantity is less than 0 and value != 0, is a out move with value from stock. You are not allowed to do it because were modifed also other svl (their value is taken from other svl). Make a inverse operation, or a manual journal entry."
                            )
                        )

                    to_do_error = (
                        "You are not allowed to put to draft this bill, "
                        "because is going to create difference between account 3xx and "
                        "stock value. Create a journal entry to fix what you need. "
                        "Or make the return and add a credit note."
                    )
                    if svl.stock_valuation_layer_ids:
                        raise UserError(
                            _(
                                text_error
                                + f" you have more valuation layers={svl.stock_valuation_layer_ids}"
                                + to_do_error
                            )
                        )
                    if svl.quantity != svl.remaining_qty or (
                        svl.remaining_value and svl.value != svl.remaining_value
                    ):
                        raise UserError(
                            _(
                                text_error
                                + f" you have diffrence between remaining quantity={svl.remaining_qty} or "
                                f"remaining value={svl.remaining_value}." + to_do_error
                            )
                        )
                    svl.write(
                        {
                            "remaining_value": svl.remaining_value
                            - svl.value,  # can be diff because landed cost
                            "value": 0,
                            "unit_cost": 0,
                            "l10n_ro_draft_history": (
                                f"{fields.datetime.now()} Set DRAFT"
                                f"bill: {move.name} bill_id={move.id} "
                                f"value={svl.value} unit_cost={svl.unit_cost} "
                                f"remaining_value={svl.remaining_value}"
                                "\n"
                            )
                            + (svl.l10n_ro_draft_history or ""),
                        }
                    )
        return super().button_draft()
