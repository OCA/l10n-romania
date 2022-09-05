# Copyright (C) 2022 cbssolutions.ro
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from ast import literal_eval

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    #  keep the stock value account 3xx at same value as stock_valuation
    # at setting to draft/reposted account_moves (invoices and not) that have valuation on them
    # can be the case of reception, inventory  ..

    _inherit = "account.move"

    def action_post(self):
        # post again of account_moves with svl ( before were set to draft)
        # the bills that have l10n_ro_bill_for_picking are not taken into consideration
        #    because is like in the case from the first posting the invoice
        # is for example case of a journal_entry for inventory_plus
        precision = self.env["decimal.precision"].precision_get(
            "Product Unit of Measure"
        )

        for move in self.filtered(
            lambda r: r.is_l10n_ro_record
            and r.stock_valuation_layer_ids
            and not r.l10n_ro_bill_for_picking
        ):

            for svl in move.stock_valuation_layer_ids.filtered(lambda r: r.quantity):
                # we only take the svl that have qty on them, others are: landed cost, the move setting to draft
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
                    f"For AccountMove:({move.id}, {move.ref}) at "
                    f"product=({svl.product_id.id}, {svl.product_id.name}) "
                    f"qty = {svl.quantity}"
                )
                accounts = svl.product_id._get_product_accounts()
                move_line = move.line_ids.filtered(
                    lambda r: r.product_id == svl.product_id
                    and r.account_id == accounts["stock_valuation"]
                )
                if len(move_line) != 1:
                    raise UserError(
                        _(
                            text_error
                            + f" something is wrong. We should have one line with stock_account for this svl  "
                            f"svl={svl} move_line={move_line}"
                        )
                    )

                line_qty = (
                    move_line.quantity
                )  # HERE I THINK I MUST CONVERT THE POSIBLE QTY IN PRODUCT QTY
                if not svl.remaining_qty:
                    raise UserError(
                        _(
                            text_error
                            + f" we do not have left any unit of quanty from this product  "
                            f"svl={svl}. You can not validate the invoice because is going to "
                            "create value in 3xx but with no product to add the value in stock"
                            " you can validate the only if you select a account diffrent than "
                            "product stocK_validation usualy 3xx"
                        )
                    )
                if svl.quantity != line_qty:
                    # can be also without this, and is should not get here
                    raise UserError(
                        _(
                            text_error
                            + f" in bill line you have qty={line_qty} you have qty={svl.quantity }. "
                            "Quantities must be equal. If you can not see the qty is hiden :("
                        )
                    )
                balance = move_line.balance
                # we create a svl with new posted valuation
                # ( at draft the initial value is substrcted like it was never put)
                created_svl = svl.sudo().create(
                    {
                        "description": "RePosted " + svl.description,
                        "product_id": svl.product_id.id,
                        "account_move_id": move.id,
                        "quantity": 0,
                        "remaining_value": 0,
                        "value": balance,
                        "unit_cost": 0,
                        "company_id": svl.company_id.id,
                        "stock_valuation_layer_id": svl.id,
                        "l10n_ro_bill_accounting_date": move.date,
                    }
                )
                svl.write(
                    {
                        "remaining_value": svl.remaining_value + balance,
                        "l10n_ro_bill_accounting_date": move.date,
                        "unit_cost": (svl.remaining_value + balance)
                        / svl.remaining_qty,
                        "l10n_ro_modified_value": balance,  # used in l10n_ro_stock_picing
                    }
                )

            # for stock landed cost reposting the account_move
            if hasattr(move, "landed_costs_ids"):
                for line in move.line_ids:
                    product = line.product_id
                    accounts = product._get_product_accounts()
                    if line.account_id != accounts["stock_valuation"]:
                        continue
                    draft_svl = move.stock_valuation_layer_ids.filtered(
                        lambda r: r.l10n_ro_draft_svl_id
                    )
                    if not draft_svl:
                        continue  # is first posting
                    before_created_svl = draft_svl.filtered(
                        lambda r: r.product_id == product
                    )[0]
                    text_error = (
                        f"For Landed Cost AccountMove:({move.id}, {move.ref}) at "
                        f"product=({product.id}, {product.name}) "
                        f"balance={line.balance}"
                    )
                    if not before_created_svl:
                        raise UserError(
                            _(
                                text_error
                                + ", you do not have before created svl that was set to draft (has l10n_ro_draft_svl_id) "
                            )
                        )
                    svl_to_modify = before_created_svl.stock_valuation_layer_id
                    if not svl_to_modify:
                        raise UserError(
                            _(
                                text_error
                                + f"before_created_svl={before_created_svl.id}{before_created_svl.desciption}"
                                " does not have stock_valuation_layer_id"
                            )
                        )
                    if not svl_to_modify.remaining_qty:
                        raise UserError(
                            _(
                                text_error
                                + f" we do not have left any unit of quanty from this product  "
                                f"svl_to_modify={svl_to_modify}. You can not revalidate the account_mvoe because is going to "
                                "create value in 3xx but with no product to add the value in stock"
                                " you can validate the only if you select a account diffrent than "
                                "product stocK_validation usualy 3xx (and take out the product_id)"
                            )
                        )
                    slc = before_created_svl.stock_landed_cost_id
                    if slc.state == "draft":
                        raise UserError(
                            _(
                                text_error
                                + f"before_created_svl={before_created_svl.id}{before_created_svl.description}"
                                f" has stock_landed_cost=({slc.id}, {slc.name}) that is in draft state. Make the operation from landed cost (or create another one)!"
                            )
                        )

                    balance = line.balance
                    created_svl = before_created_svl.sudo().create(
                        {
                            "description": "RePosted " + before_created_svl.description,
                            "product_id": product.id,
                            "account_move_id": move.id,
                            "quantity": 0,
                            "remaining_value": 0,
                            "value": balance,
                            "unit_cost": 0,
                            "company_id": move.company_id.id,
                            "stock_valuation_layer_id": svl_to_modify.id,
                            "l10n_ro_bill_accounting_date": move.date,
                        }
                    )
                    svl_to_modify.write(
                        {
                            "remaining_value": svl_to_modify.remaining_value + balance,
                            "l10n_ro_bill_accounting_date": move.date,
                            "unit_cost": (svl_to_modify.remaining_value + balance)
                            / svl_to_modify.remaining_qty,
                        }
                    )
        res = super().action_post()

        return res

    def button_draft(self):
        # we are are creating the oposite svl values, and set to original l10n_ro_draft
        for move in self:
            if (
                move.is_l10n_ro_record
                and move.stock_valuation_layer_ids
                and move.state != "cancel"
            ):
                for svl in move.stock_valuation_layer_ids.filtered(
                    lambda r: not r.l10n_ro_draft_svl_id
                    and not (r.l10n_ro_draft_svl_ids and r.quantity == 0)
                ):
                    text_error = (
                        f"For AccountMove=({move.ref},{move.id}) at "
                        f"product=({svl.product_id.name},{svl.product_id.id}) "
                        f"svl={svl} qty={svl.quantity}"
                    )
                    to_do_error = (
                        "You are not allowed to put to draft this bill, "
                        "because is going to create difference between account 3xx and "
                        "stock value. Create a journal entry to fix what you need. "
                        "Or make the return and add a credit note."
                    )
                    if svl.quantity < 0:
                        raise UserError(
                            _(
                                text_error
                                + f" svl quantity is less than 0, is a out move with value from stock. You are not allowed to do it because were modifed also other svl (their value is taken from other svl). Make a inverse operation, or a manual journal entry."
                            )
                        )

                    if move.move_type != "entry":
                        # is bill/invoice
                        if svl.quantity == 0:
                            if (
                                svl.stock_valuation_layer_id
                                and svl.stock_valuation_layer_id.remaining_qty <= 0
                            ):
                                raise UserError(
                                    _(
                                        text_error
                                        + f" Linked_svl={svl.stock_valuation_layer_id} quantity is less than 0."
                                        + to_do_error
                                    )
                                )
                            elif (
                                not svl.stock_valuation_layer_id
                                and svl.remaining_qty == 0
                                and svl.quantity == 0
                            ):
                                raise UserError(
                                    _(
                                        text_error
                                        + f" This was a manual SVL entry, that had modify the values of svl with stock when was added. Create the oposite svl entry"
                                    )
                                )

                        if svl.stock_valuation_layer_ids:
                            raise UserError(
                                _(
                                    text_error
                                    + f" you have more valuation layers={svl.stock_valuation_layer_ids}"
                                    + to_do_error
                                )
                            )
                        if svl.stock_valuation_layer_id:
                            svl_to_modify = svl.stock_valuation_layer_id
                        else:
                            svl_to_modify = svl
                        value = svl.value
                        l10n_ro_draft_svl_id = svl
                    else:
                        # is account_move with valuation from inventory plus
                        # it should be one product_id and svl per account_mvoe
                        svl_to_modify = svl
                        if svl.quantity == 0:
                            if not svl.stock_valuation_layer_id:
                                raise UserError(
                                    _(
                                        text_error
                                        + " This is a Manual stock valuation that when"
                                        " was posted gave value to one or more svl. "
                                        "You can not set it to draft. Create another one."
                                    )
                                )
                            else:
                                if hasattr(svl, "stock_landed_cost_id"):
                                    # is landed cost, and we are setting to draft the account_move
                                    # we must create another valuation with oposite value
                                    svl_to_modify = svl.stock_valuation_layer_id
                                    if not svl_to_modify.remaining_qty:
                                        raise UserError(
                                            _(
                                                text_error
                                                + f" svl remaing quantity is zero. Is not posible to set to draft this account_move resulted form LandedCost"
                                                + to_do_error
                                            )
                                        )
                                    value = -1 * svl.value
                                    svl.copy(
                                        {
                                            "value": value,
                                            "l10n_ro_draft_svl_id": svl.id,
                                            "description": "Draft:" + svl.description,
                                        }
                                    )
                                    svl_to_modify.write(
                                        {
                                            "remaining_value": svl_to_modify.remaining_value
                                            - value,
                                            "unit_cost": (
                                                svl_to_modify.remaining_value - value
                                            )
                                            / svl_to_modify.remaining_qty
                                            if svl_to_modify.remaining_qty
                                            else 0,
                                        }
                                    )
                                    continue
                                else:
                                    # is a value for stock that is going to be taken into account in next line
                                    continue
                        account_move_line_qty = move.line_ids.filtered(
                            lambda r: r.product_id == svl.product_id
                        )[0].quantity
                        if svl.remaining_qty != account_move_line_qty:
                            raise UserError(
                                _(
                                    text_error
                                    + f" svl remaing quantity is less than the quantity form product line={account_move_line_qty}."
                                    "You can not set to draft this entry - recreate a inventoy"
                                )
                            )

                        if not svl.l10n_ro_draft_svl_ids:
                            # case when we modify the original inventory_plus move
                            l10n_ro_draft_svl_id = svl
                        else:
                            # case when we modify the last posted inventory_plus move
                            # others should have something in l10n_ro_draft_svl_id/s
                            l10n_ro_draft_svl_id = (
                                svl.stock_valuation_layer_ids.filtered(
                                    lambda r: not r.l10n_ro_draft_svl_id
                                    and not r.l10n_ro_draft_svl_ids
                                )
                            )
                            if len(l10n_ro_draft_svl_id) != 1:
                                raise UserError(
                                    _(
                                        text_error
                                        + " we didn't one stock_valuation_layer_ids that are not for set to draft that are giving value. Found"
                                        f" l10n_ro_draft_svl_id={l10n_ro_draft_svl_id}"
                                    )
                                )

                        value = l10n_ro_draft_svl_id.value

                    # we are creating a svl with the - value of entry that was set to draft
                    corected_svl = svl.create(
                        {
                            "description": f"Setting to draft inv=({move.id},{move.name})",
                            "remaining_value": 0,
                            "account_move_id": move.id,
                            "product_id": svl.product_id.id,
                            "company_id": svl.company_id.id,
                            "unit_cost": 0,
                            "value": -1 * value,
                            "remaining_value": 0,
                            "quantity": 0,
                            "remaining_qty": 0,
                            "l10n_ro_bill_accounting_date": svl.l10n_ro_bill_accounting_date,
                            "l10n_ro_valued_type": svl.l10n_ro_valued_type,
                            "stock_valuation_layer_id": svl.id,
                            "l10n_ro_draft_svl_id": l10n_ro_draft_svl_id.id,
                        }
                    )

                    svl_to_modify.write(
                        {
                            "remaining_value": svl_to_modify.remaining_value - value,
                            "unit_cost": (svl_to_modify.remaining_value - value)
                            / svl_to_modify.remaining_qty
                            if svl_to_modify.remaining_qty
                            else 0,
                        }
                    )

        return super().button_draft()
