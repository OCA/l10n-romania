# Copyright (C) 2022 cbssolutions.ro
# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from ast import literal_eval

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n.ro.mixin"]

    l10n_ro_bill_for_picking = fields.Many2one(
        "stock.picking",
        help="If this field is set, "
        "means that the reception picking (that is not notice) valuation is given by this bill",
        readonly=0,
        copy=0,
        tracking=1,
    )

    @api.constrains("l10n_ro_bill_for_picking", "state", "move_type")
    def _check_unique_l10n_ro_bill_for_picking(self):
        for rec in self:
            if rec.state == "done" and rec.l10n_ro_bill_for_picking:
                if rec.move_type not in ["in_invoice", "in_recepit"]:
                    raise ValidationError(
                        _(
                            f"For invoice=({rec.id},{rec.name}) move_type must be 'in_invoice', 'in_recepit' but is {rec.move_type}. You have picking l10n_ro_bill_for_picking=({self.id},{self.name})."
                        )
                    )
                other_inv = self.search(
                    [
                        ("id", "!=", rec.id),
                        (
                            "l10n_ro_bill_for_picking",
                            "==",
                            rec.l10n_ro_bill_for_picking.id,
                        ),
                    ]
                )
                if other_inv:
                    raise ValidationError(
                        _(
                            f"For invoice=({rec.id},{rec.name}) can only have a invoice per picking l10n_ro_bill_for_picking=({self.id},{self.name}) you have also {other_inv}!"
                        )
                    )

    def action_view_stock_valuation_layers(self):
        self.ensure_one()
        domain = [("id", "in", self.stock_valuation_layer_ids.ids)]
        action = self.env["ir.actions.actions"]._for_xml_id(
            "stock_account.stock_valuation_layer_action"
        )
        context = literal_eval(action["context"])
        context.update(self.env.context)
        context["no_at_date"] = True
        return dict(action, domain=domain, context=context)

    def _stock_account_prepare_anglo_saxon_in_lines_vals(self):
        # we do not create price difference at reception
        # we can not have price difference invoice price must be the svl price
        invoices = self
        for move in self:
            if move.is_l10n_ro_record:
                invoices -= move
        return super(
            AccountMove, invoices
        )._stock_account_prepare_anglo_saxon_in_lines_vals()

    def _stock_account_prepare_anglo_saxon_out_lines_vals(self):
        # nu se mai face descarcarea de gestiune la facturare
        invoices = self
        for move in self:
            if move.is_l10n_ro_record:
                invoices -= move
        return super(
            AccountMove, invoices
        )._stock_account_prepare_anglo_saxon_out_lines_vals()

    def action_post(self):
        # for a invoice that is made from a reception picking -has l10n_ro_bill_for_picking
        # we have the qty in reception and price in invoice (qty must be from picking)
        # in svl from picking we are going to set invoice date to curent svl, and create a value
        precision = self.env["decimal.precision"].precision_get(
            "Product Unit of Measure"
        )
        for move in self.filtered(lambda r: r.is_l10n_ro_record):
            if move.move_type not in ["in_invoice", "in_recepit"]:
                continue
            picking = move.l10n_ro_bill_for_picking
            if not picking:
                continue
            text_error = f"For Bill:({move.id},{move.ref}) "
            invoice_product_line = move.line_ids.filtered(
                lambda r: r.product_id.type == "product"
                and r.product_id.valuation == "real_time"
                and r.quantity != 0
            )

            if len(invoice_product_line) != len(
                picking.move_lines.stock_valuation_layer_ids.filtered(
                    lambda r: not r.stock_valuation_layer_id
                )
            ):
                # svl with stock_valuation_layer_id can be landed cost .. and should not be taken into consideration
                raise ValidationError(
                    _(
                        text_error
                        + " we have different products with real time valuation (invoice lines products compared with picking(svl))"
                    )
                )
            for line in invoice_product_line:
                text_error += (
                    f" product=({line.product_id.id},{line.product_id.name}) "
                    f"qty = {line.quantity}"
                )
                line_qty = line.quantity
                stock_move = picking.move_lines.filtered(
                    lambda r: r.product_id == line.product_id
                    and r.quantity_done != 0
                    and r.stock_valuation_layer_ids
                )
                if len(stock_move) != 1:
                    raise UserError(
                        _(
                            text_error
                            + f" we did not found one stock_move (that has svl). "
                            f"found stock_move={stock_move}"
                        )
                    )
                stock_move_qty = stock_move.product_uom_qty
                if (
                    float_compare(line_qty, stock_move_qty, precision_digits=precision)
                    != 0
                ):
                    raise UserError(
                        _(
                            text_error
                            + f" the reception has invoice line_qty={line_qty} that is not equal with stock_move_qty={stock_move_qty}"
                        )
                    )
                svl = stock_move.stock_valuation_layer_ids.filtered(
                    lambda r: not r.stock_valuation_layer_id
                )
                # we filter the stock_valuation_layer_id that are in general landed costs
                if len(svl) != 1:
                    raise UserError(
                        _(
                            text_error
                            + f" for move={stock_move} we need to have one svl, but svl={svl}"
                        )
                    )
                if svl.remaining_qty == 0:
                    # we are not going to create any svl, we are not going to use in line the stock account
                    # but the expense account for consumtion
                    line.write(
                        {
                            "account_id": line.product_id._get_product_accounts()[
                                "expense"
                            ].id,
                            "name": line.name
                            + f"(Expensed account because in picking=({picking.id},{picking.name}) svl={svl} has 0 remaining qty)",
                        }
                    )
                else:
                    created_svl = (
                        self.env["stock.valuation.layer"]
                        .sudo()
                        .create(
                            {
                                "description": f"Reception inv=({move.id},{move.ref}) picking=({picking.id},{picking.name})",
                                "account_move_id": move.id,
                                #                                "stock_move_id": stock_move.id,
                                "product_id": line.product_id.id,
                                "company_id": move.company_id.id,
                                "unit_cost": 0,
                                "value": line.balance,
                                "remaining_value": 0,
                                "l10n_ro_bill_accounting_date": move.date,
                                "quantity": 0,
                                "remaining_qty": 0,
                                "l10n_ro_valued_type": "reception",
                                "stock_valuation_layer_id": svl.id,
                            }
                        )
                    )
                    svl.write(
                        {
                            "remaining_value": svl.remaining_value + line.balance,
                            "l10n_ro_bill_accounting_date": move.date,
                            "unit_cost": (svl.remaining_value + line.balance)
                            / svl.remaining_qty
                            if svl.remaining_qty
                            else 0,
                        }
                    )

        res = super(AccountMove, self).action_post()

        return res


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ["account.move.line", "l10n.ro.mixin"]

    def _get_computed_account(self):
        res = super(AccountMoveLine, self)._get_computed_account()
        # Take accounts from stock location in case the category allow changing
        # accounts and the picking is not notice
        if (
            self.product_id.categ_id.l10n_ro_stock_account_change
            and self.product_id.type == "product"
            and self.move_id.is_l10n_ro_record
        ):
            fiscal_position = self.move_id.fiscal_position_id
            if self.move_id.is_purchase_document():
                stock_moves = self.purchase_line_id.move_ids
                for stock_move in stock_moves.filtered(lambda m: m.state == "done"):
                    if (
                        stock_move.location_dest_id.l10n_ro_property_stock_valuation_account_id
                    ):
                        location = stock_move.location_dest_id
                        res = location.l10n_ro_property_stock_valuation_account_id
            if self.move_id.is_sale_document():
                sales = self.sale_line_ids.filtered(lambda s: s.move_ids)
                for stock_move in sales.move_ids:
                    if (
                        stock_move.location_id.l10n_ro_property_account_income_location_id
                    ):
                        location = stock_move.location_id
                        res = location.l10n_ro_property_account_income_location_id
            if fiscal_position:
                res = fiscal_position.map_account(res)
        return res
