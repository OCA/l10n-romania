# Copyright (C) 2022 cbssolutions.ro
# Copyright (C) 2022 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    # we created 2 fields to be more clear in fields and at selection without so much code
    l10n_ro_invoice_for_pickings_ids = fields.One2many(
        "stock.picking",
        "l10n_ro_notice_invoice_id",
        help="If this field is set,means that this is the invoice "
        "for set notice pickings. A notice picking can be invoiced only on one invoice!",
        string="For notice delivery pickings",
        readonly=0,
        copy=0,
        tracking=1,
    )
    l10n_ro_bill_for_pickings_ids = fields.One2many(
        "stock.picking",
        "l10n_ro_notice_bill_id",
        string="For notice reception pickings",
        help="If this field is set,means that this is the bill "
        "for set notice pickings. A notice picking can be billed only on one bill!",
        readonly=0,
        copy=0,
        tracking=1,
    )

    @api.constrains(
        "l10n_ro_bill_for_picking",
        "line_ids",
        "l10n_ro_bill_for_pickings_ids",
        "l10n_ro_invoice_for_pickings_ids",
    )
    def _check_pickings(self):
        for rec in self:
            if rec.l10n_ro_bill_for_picking and (
                rec.l10n_ro_bill_for_pickings_ids
                or rec.l10n_ro_invoice_for_pickings_ids
            ):
                raise ValidationError(
                    _(
                        f"For invoice/bill=({rec.id},{rec.name}) you must choose to be for a picking or for notice pickings not both."
                    )
                )
            if (
                rec.l10n_ro_bill_for_pickings_ids
                and rec.l10n_ro_invoice_for_pickings_ids
            ):
                raise ValidationError(
                    _(
                        f"For invoice/bill=({rec.id},{rec.name}) you can not have in same time l10n_ro_invoice_for_pickings_ids and l10n_ro_bill_for_pickings_ids."
                    )
                )
            if (
                rec.l10n_ro_bill_for_pickings_ids
                or rec.l10n_ro_invoice_for_pickings_ids
            ) and rec.invoice_line_ids:
                products = self.env["product.product"]
                for line in rec.invoice_line_ids.filtered(
                    lambda r: not r.l10n_ro_notice_invoice_difference
                ):
                    product = line.product_id
                    if product.type == "product" and product.valuation == "real_time":
                        if product in products:
                            raise ValidationError(
                                _(
                                    f"For invoice/bill=({rec.id},{rec.name}) because you have notice pickings, you can not have more lines of same product. Duplicate product=({product.id},{product.name}) "
                                )
                            )
                        products |= product

    @api.onchange("l10n_ro_bill_for_pickings_ids", "l10n_ro_invoice_for_pickings_ids")
    def _onchange_l10n_ro_for_pickings(self):
        if self.invoice_line_ids and (
            self.l10n_ro_bill_for_pickings_ids or self.l10n_ro_invoice_for_pickings_ids
        ):
            self.invoice_line_ids = False
            return {
                "warning": {
                    "title": _("Warning"),
                    "message": _(
                        "By having bill/invoice_for_pickings_ids is expected that products to have 408 418 accounts. The account_move_lines were deleted because should be other accounts and eventually price difference. "
                    ),
                },
            }

    def action_post(self):
        # we are adding lines to corect the notice pickings
        for rec in self:
            pickings = rec.l10n_ro_bill_for_pickings_ids
            is_bill_not_invoice = True
            if rec.l10n_ro_invoice_for_pickings_ids:
                pickings = rec.l10n_ro_invoice_for_pickings_ids
                is_bill_not_invoice = False
            if pickings:
                # bills for notice reception pickings
                lines = rec.invoice_line_ids
                svls = pickings.move_lines.stock_valuation_layer_ids
                # a product can be in more pickings. we are adding qty and values
                product_qty_value_svls = defaultdict(
                    lambda: {"qty": 0, "value": 0, "account_id": False}
                )
                for svl in svls:
                    product_qty_value_svls[svl.product_id]["qty"] += svl.quantity
                    if svl.l10n_ro_modified_value:
                        # case when notice svl was modified ( from draft than posted again, only for bill)
                        value = svl.l10n_ro_modified_value
                    else:
                        value = svl.value
                    if svl.account_move_id.state != "posted":
                        raise ValidationError(
                            _(
                                f"For Bill/Invoice=({rec.id,rec.name}), with pickings={pickings} for product=({svl.product_id.id, svl.product_id.name}) "
                                f"for svl={svl} you have account_move={svl.account_move_id} that is not posted"
                            )
                        )

                    if is_bill_not_invoice:  # credit account
                        account = svl.account_move_id.line_ids.filtered(
                            lambda r: r.product_id == svl.product_id and r.credit != 0
                        )[0].account_id
                    else:  # debit account
                        svl_account_move_line = svl.account_move_id.line_ids
                        delivery_price_line = svl_account_move_line.filtered(
                            lambda r: r.product_id == svl.product_id
                            and r.debit != 0
                            and r.name[:8] == "delivery"
                        )[0]
                        account = delivery_price_line[0].account_id
                        value = delivery_price_line[0].debit

                    product_qty_value_svls[svl.product_id]["value"] += value
                    if (
                        product_qty_value_svls[svl.product_id]["account_id"]
                        and product_qty_value_svls[svl.product_id]["account_id"]
                        != account
                    ):
                        raise ValidationError(
                            _(
                                f"For Bill/Invoice=({rec.id,rec.name}), with pickings={pickings} for product=({svl.product_id.id, svl.product_id.name}) "
                                f"for svl={svl} you have account={account} that is diffrent than in another svl form pickings"
                            )
                        )
                    product_qty_value_svls[svl.product_id]["account_id"] = account

                for product, qty_value in product_qty_value_svls.items():
                    product_line = lines.filtered(lambda r: r.product_id == product)
                    if len(product_line) != 1:
                        raise ValidationError(
                            _(
                                f"For Bill/Invoice=({rec.id,rec.name}), with pickings={pickings} for product=({product.id, product.name}) you do not have one invoice line product_line={product_line}."
                            )
                        )
                    balance = product_line.balance
                    invoice_notice_diff = balance - qty_value["value"]
                    if not is_bill_not_invoice:
                        qty_value["qty"] *= -1
                        invoice_notice_diff = (
                            qty_value["value"] + balance
                        )  # balance is negative
                    if qty_value["qty"] != product_line.quantity:
                        raise ValidationError(
                            _(
                                f"For Bill/Invoice=({rec.id,rec.name}), with pickings={pickings}for product=({product.id, product.name}) you have invoice line qty={product_line.quantity} that is different than pickings_qty={qty_value['qty']}"
                            )
                        )
                    if qty_value["account_id"] != product_line.account_id:
                        raise ValidationError(
                            _(
                                f"For Bill/invoice=({rec.id,rec.name}), with pickings={pickings} for product=({product.id, product.name}) you have account in invoice line {product_line.account_id} that is different than account move for svl={qty_value['account_id']}"
                            )
                        )
                    if not invoice_notice_diff:
                        continue
                    if rec.currency_id != rec.company_id.currency_id:
                        # 665 "Cheltuieli cu diferentele de curs valutar"
                        # 765 "Venituri din diferente de curs valutar"
                        if is_bill_not_invoice:
                            negative_dif_acc = (
                                rec.company_id.l10n_ro_property_notice_bill_positive
                            )
                            positive_dif_acc = (
                                rec.company_id.l10n_ro_property_notice_bill_negative
                            )
                        else:
                            positive_dif_acc = (
                                rec.company_id.l10n_ro_property_revenues_from_exchange_rate
                            )
                            negative_dif_acc = (
                                rec.company_id.l10n_ro_property_expensed_from_exchange_rate
                            )
                    else:
                        # 609 = “Reduceri comerciale primite“
                        # 348 “Diferente de pret la produse”
                        if is_bill_not_invoice:
                            negative_dif_acc = (
                                rec.company_id.l10n_ro_property_notice_bill_positive
                            )
                            positive_dif_acc = (
                                rec.company_id.l10n_ro_property_notice_bill_negative
                            )
                        else:
                            positive_dif_acc = (
                                rec.company_id.l10n_ro_property_notice_invoice_positive
                            )
                            negative_dif_acc = (
                                rec.company_id.l10n_ro_property_notice_invoice_negative
                            )
                    account = (
                        positive_dif_acc
                        if invoice_notice_diff > 0
                        else negative_dif_acc
                    )
                    if not account:
                        raise ValidationError(
                            _(
                                f"For Bill=({rec.id,rec.name}), with "
                                f"pickings={pickings}"
                                f" for product=({product.id, product.name}) you have invoice"
                                f"_value-notice_value={invoice_notice_diff}. "
                                "You not not have set the difference account. "
                                "Go to Settings/General Settings"
                                "/Romanaia & set the account."
                            )
                        )
                    rec.write(
                        {
                            "line_ids": [
                                (
                                    0,
                                    0,
                                    {
                                        "name": f"Difference product={product.id,product.name} invoice-notice={invoice_notice_diff}",
                                        "debit": invoice_notice_diff
                                        if invoice_notice_diff > 0
                                        else 0,
                                        "credit": abs(invoice_notice_diff)
                                        if invoice_notice_diff < 0
                                        else 0,
                                        "product_id": product.id,
                                        "account_id": account.id,
                                        "l10n_ro_notice_invoice_difference": True,
                                        "exclude_from_invoice_tab": True,
                                    },
                                ),
                                (
                                    0,
                                    0,
                                    {
                                        "name": f"Difference product={product.id,product.name} invoice-notice={invoice_notice_diff}",
                                        "credit": invoice_notice_diff
                                        if invoice_notice_diff > 0
                                        else 0,
                                        "debit": abs(invoice_notice_diff)
                                        if invoice_notice_diff < 0
                                        else 0,
                                        "product_id": product.id,
                                        "account_id": qty_value["account_id"].id,
                                        "l10n_ro_notice_invoice_difference": True,
                                        "exclude_from_invoice_tab": True,
                                    },
                                ),
                            ]
                        }
                    )

        res = super().action_post()
        return res

    def _get_reception_account(self):
        # what the hell is doing this?
        self.ensure_one()
        account = self.env["account.account"]
        if not self.is_l10n_ro_record:
            return account

        acc_payable = self.company_id.l10n_ro_property_stock_picking_payable_account_id
        valuation_stock_moves = self.env["stock.move"].search(
            [
                (
                    "purchase_line_id",
                    "in",
                    self.line_ids.mapped("purchase_line_id").ids,
                ),
                ("state", "=", "done"),
                ("picking_id.notice", "=", True),
                ("product_qty", "!=", 0.0),
            ]
        )
        if valuation_stock_moves:
            acc_moves = valuation_stock_moves.mapped("account_move_ids")
            lines = self.env["account.move.line"].search(
                [("move_id", "in", acc_moves.ids)]
            )
            lines_diff_acc = lines.mapped("account_id").filtered(
                lambda a: a != acc_payable
            )
            if lines_diff_acc:
                account = lines_diff_acc[0]
        return account
