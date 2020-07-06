# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero


class AccountMove(models.Model):
    _inherit = "account.move"

    def _stock_account_prepare_anglo_saxon_in_lines_vals(self):
        """ Can be done simpler by comparing the accounting notes like in version from 6-10 June
        ORIGINAL FROM PURCHASE_STOCK (is adding lines at purchase) that is overridden of stock_account
        _stock_account_prepare_anglo_saxon_in_lines_vals (that is adding accounting lines at sale)
        """
        lines_vals_list = []
        ro_chart = self.env["ir.model.data"].get_object_reference(
            "l10n_ro", "ro_chart_template"
        )[1]
        for move in self:
            if not move.company_id.chart_template_id.id == ro_chart:
                super(
                    AccountMove, self
                )._stock_account_prepare_anglo_saxon_in_lines_vals()
            if move.type not in ("in_invoice", "in_refund", "in_receipt"):
                continue
            move = move.with_context(force_company=move.company_id.id)
            move_inv_lines = move.invoice_line_ids.filtered(
                lambda line: line.product_id.type == "product"
                and line.product_id.valuation == "real_time"
            )
            for line in move_inv_lines:
                # is not a invoice from a purchase
                if not line.purchase_line_id:
                    continue
                # Retrieve stock valuation moves.
                valuation_st_moves = self.env["stock.move"].search(
                    [
                        ("purchase_line_id", "=", line.purchase_line_id.id),
                        ("state", "=", "done"),
                        ("product_qty", "!=", 0.0),
                    ]
                )
                if not valuation_st_moves:
                    continue
                acc_move_ids = self.env["account.move"].search(
                    [("stock_move_id", "in", valuation_st_moves.ids)]
                )
                if not acc_move_ids:
                    continue  # if there are no accounting entries we are not going to put price differences

                # Retrieve accounts needed to generate the price difference.
                # default must be 348000 Diferenţe de preţ la produse
                product = line.product_id
                categ = product.categ_id
                debit_pdiff_account = (
                    product.property_account_creditor_price_difference
                    or categ.property_account_creditor_price_difference_categ
                )
                if not debit_pdiff_account:
                    raise UserError(
                        _(
                            "You have to define "
                            "property_account_creditor_price_difference for "
                            "product %s or its category. %s"
                            % (product.name, categ.name)
                        )
                    )

                debit_pdiff_account = move.fiscal_position_id.map_account(
                    debit_pdiff_account
                )

                if line.product_id.cost_method != "standard" and line.purchase_line_id:
                    po_currency = line.purchase_line_id.currency_id
                    po_company = line.purchase_line_id.company_id

                    if move.type == "in_refund":
                        valuation_st_moves = valuation_st_moves.filtered(
                            lambda stock_move: stock_move._is_out()
                        )
                    else:
                        valuation_st_moves = valuation_st_moves.filtered(
                            lambda stock_move: stock_move._is_in()
                        )

                    if valuation_st_moves:
                        valuation_price_unit_total = 0
                        valuation_total_qty = 0
                        for val_stock_move in valuation_st_moves:
                            # In case val_stock_move is a return move, its valuation entries have been made with the
                            # currency rate corresponding to the original stock move
                            valuation_date = (
                                val_stock_move.origin_returned_move_id.date
                                or val_stock_move.date
                            )
                            svl = val_stock_move.mapped(
                                "stock_valuation_layer_ids"
                            ).filtered(lambda l: l.quantity)
                            layers_qty = sum(svl.mapped("quantity"))
                            layers_values = sum(svl.mapped("value"))
                            valuation_price_unit_total += line.company_currency_id._convert(
                                layers_values,
                                move.currency_id,
                                move.company_id,
                                valuation_date,
                                round=False,
                            )
                            valuation_total_qty += layers_qty
                        valuation_price_unit = (
                            valuation_price_unit_total / valuation_total_qty
                        )
                        valuation_price_unit = line.product_id.uom_id._compute_price(
                            valuation_price_unit, line.product_uom_id
                        )

                    elif line.product_id.cost_method == "fifo":
                        # In this condition, we have a real price-valuated product which has not yet been received
                        valuation_price_unit = po_currency._convert(
                            line.purchase_line_id.price_unit,
                            move.currency_id,
                            po_company,
                            move.date,
                            round=False,
                        )
                    else:
                        # For average/fifo/lifo costing method, fetch real cost price from incoming moves.
                        price_unit = line.purchase_line_id.product_uom._compute_price(
                            line.purchase_line_id.price_unit, line.product_uom_id
                        )
                        valuation_price_unit = po_currency._convert(
                            price_unit,
                            move.currency_id,
                            po_company,
                            move.date,
                            round=False,
                        )

                else:
                    # Valuation_price unit is always expressed in invoice currency, so that it can always be computed with the good rate
                    price_unit = line.product_id.uom_id._compute_price(
                        line.product_id.standard_price, line.product_uom_id
                    )
                    valuation_price_unit = line.company_currency_id._convert(
                        price_unit,
                        move.currency_id,
                        move.company_id,
                        fields.Date.today(),
                        round=False,
                    )

                invoice_cur_prec = move.currency_id.decimal_places

                price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                if line.tax_ids:
                    is_refund = True if move.type == "in_refund" else False
                    price_unit = line.tax_ids.compute_all(
                        price_unit,
                        currency=move.currency_id,
                        quantity=1.0,
                        is_refund=is_refund,
                    )["total_excluded"]

                if (
                    float_compare(
                        valuation_price_unit,
                        price_unit,
                        precision_digits=invoice_cur_prec,
                    )
                    != 0
                    and float_compare(
                        line["price_unit"],
                        line.price_unit,
                        precision_digits=invoice_cur_prec,
                    )
                    == 0
                ):

                    price_unit_val_dif = price_unit - valuation_price_unit

                    if (
                        move.currency_id.compare_amounts(
                            price_unit, valuation_price_unit
                        )
                        != 0
                        and debit_pdiff_account
                    ):
                        # Add price difference account line.
                        vals = {
                            "name": line.name[:64],
                            "move_id": move.id,
                            "currency_id": line.currency_id.id,
                            "product_id": line.product_id.id,
                            "product_uom_id": line.product_uom_id.id,
                            "quantity": line.quantity,
                            "price_unit": price_unit_val_dif,
                            "price_subtotal": line.quantity * price_unit_val_dif,
                            "account_id": debit_pdiff_account.id,
                            "analytic_account_id": line.analytic_account_id.id,
                            "analytic_tag_ids": [(6, 0, line.analytic_tag_ids.ids)],
                            "exclude_from_invoice_tab": True,
                            "is_anglo_saxon_line": True,
                        }
                        vals.update(
                            line._get_fields_onchange_subtotal(
                                price_subtotal=vals["price_subtotal"]
                            )
                        )
                        lines_vals_list.append(vals)

                        # Correct the amount of the current line.
                        vals = {
                            "name": line.name[:64],
                            "move_id": move.id,
                            "currency_id": line.currency_id.id,
                            "product_id": line.product_id.id,
                            "product_uom_id": line.product_uom_id.id,
                            "quantity": line.quantity,
                            "price_unit": -price_unit_val_dif,
                            "price_subtotal": line.quantity * -price_unit_val_dif,
                            "account_id": line.account_id.id,
                            "analytic_account_id": line.analytic_account_id.id,
                            "analytic_tag_ids": [(6, 0, line.analytic_tag_ids.ids)],
                            "exclude_from_invoice_tab": True,
                            "is_anglo_saxon_line": True,
                        }
                        vals.update(
                            line._get_fields_onchange_subtotal(
                                price_subtotal=vals["price_subtotal"]
                            )
                        )
                        lines_vals_list.append(vals)
        return lines_vals_list
