# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from ast import literal_eval
from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n.ro.mixin"]

    l10n_ro_bill_for_picking = fields.Many2one(
        "stock.picking",
        help="If this field is set, "
        "means that the picking valuation is given by this bill",
        readonly=1,
        default="",
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
        # we have the qty in reception and price in invoice (qty must be from picking)
        precision = self.env["decimal.precision"].precision_get(
            "Product Unit of Measure"
        )

        for move in self.filtered(lambda r: r.is_l10n_ro_record):
            if move.move_type not in ["in_invoice", "in_recepit"]:
                continue
            if move.l10n_ro_bill_for_picking or move.stock_valuation_layer_ids:
                continue  #
            picking = self.env["stock.picking"]
            for line in move.line_ids:
                if (
                    line.product_id.type != "product"
                    or line.product_id.valuation != "real_time"
                ):
                    continue
                text_error = (
                    f"For Bill:({move.ref},{move.id}) at "
                    f"product=({line.product_id.name},{line.product_id.id}) "
                    f"qty = {line.quantity}"
                )
                if not line.purchase_line_id:
                    raise UserError(
                        _(
                            text_error + " we do not have a puchase line."
                            "We can not continue because will create a accunt 3xx value "
                            "without stock_value for it"
                        )
                    )
                domain = [
                    ("purchase_line_id", "=", line.purchase_line_id.id),
                    ("product_qty", "!=", 0.0),
                    ("state", "=", "done"),  # drafts can be backorders
                ]
                # HERE I THINK I MUST CONVERT THE purchase QTY IN PRODUCT QTY
                line_qty = line.quantity
                stock_moves = self.env["stock.move"].search(domain)
                stock_moves_without_svl = stock_moves.filtered(
                    lambda r: not r.stock_valuation_layer_ids
                )
                if stock_moves and not stock_moves_without_svl:
                    # should be a notice picking ( has svl done at reception)
                    break
                if len(stock_moves_without_svl) != 1:
                    raise UserError(
                        _(
                            text_error
                            + f" the reception must have one done stock_move without svl. "
                            f"stock_moves_without_svl={stock_moves_without_svl}"
                        )
                    )
                if not stock_moves_without_svl.picking_id:
                    raise UserError(
                        _(
                            text_error
                            + f" stock_move_id={stock_moves[0].id} does not have a picking"
                        )
                    )
                if not picking:
                    picking = stock_moves_without_svl.picking_id
                elif picking != stock_moves_without_svl.picking_id:
                    raise UserError(
                        _(
                            f"For bill=({move.ref},{move.id}), exist more picking={picking}"
                            f" You recorded a reception based on bill, go in each reception and a bill"
                        )
                    )

                stock_move_qty = stock_moves_without_svl.product_uom_qty
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
                svl = (
                    self.env["stock.valuation.layer"]
                    .sudo()
                    .create(
                        {
                            "description": f"Reception inv=({move.ref},{move.id}) picking=({picking.name},{picking.id})",
                            "account_move_id": move.id,
                            "stock_move_id": stock_moves_without_svl[0].id,
                            "product_id": line.product_id.id,
                            "company_id": move.company_id.id,
                            "unit_cost": line.balance / line.quantity,
                            "value": line.balance,
                            "remaining_value": line.balance,
                            "l10n_ro_bill_accounting_date": move.date,
                            "quantity": line.quantity,
                            "remaining_qty": line.quantity,
                            "unit_cost": line.balance / line.quantity,
                            "l10n_ro_valued_type": "reception",
                        }
                    )
                )
            if picking:
                move.write({"l10n_ro_bill_for_picking": picking.id})

        res = super(AccountMove, self).action_post()

        return res


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ["account.move.line", "l10n.ro.mixin"]

    def _get_computed_account(self):
        res = super(AccountMoveLine, self)._get_computed_account()
        # Take accounts from stock location in case the category allow changinc
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
