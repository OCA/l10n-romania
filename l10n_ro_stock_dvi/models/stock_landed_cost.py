# 2022 Nexterp
# ©  2008-2020 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com

import logging
from collections import defaultdict

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_is_zero

_logger = logging.getLogger(__name__)


class LandedCost(models.Model):
    _inherit = "stock.landed.cost"

    # original landed_cost fields
    vendor_bill_id = fields.Many2one(
        states={"done": [("readonly", True)]},
    )

    # new l10n_ro_dvi fields
    l10n_ro_landed_type = fields.Selection(
        [("standard", "Standard"), ("dvi", "DVI")],
        default="standard",
        states={"done": [("readonly", True)]},
    )
    l10n_ro_tax_value = fields.Float(
        "Total DVI VAT paid at customs", states={"done": [("readonly", True)]}
    )
    l10n_ro_tax_id = fields.Many2one(
        "account.tax",
        help="VAT tax type for products and custom",
        states={"done": [("readonly", True)]},
        string="DVI tax_id",
    )

    def button_validate(self):
        """
        on invoice is already done: factura 3xx=401

        we will create a journal entry with custom duty, custom commision
        dvi tax vamala 3xx =406 taxa vamala     will have base tag to be in reports
        dvi tax vamala 3xx =407 comision vama
        dvi tva in vama 4426=446 tva in vama  will have vat tag to be in reports

        """
        self.ensure_one()
        if (
            not self.company_id.l10n_ro_accounting
            or self.l10n_ro_landed_type != "dvi"
            or self._context.get("is_landed_cost_revert_do_not_make_account_moves")
        ):
            return super(LandedCost, self).button_validate()
        if self.account_move_id:
            raise UserError(
                _(
                    f"For DVI (Landed Cost) = ({self.id}, {self.name}), you already have a Journal Entry. You can NOT revalidate. Create another Landed Cost (the reason is that you'll have old svl with this landed cost) "
                )
            )

        if not self.cost_lines:
            raise UserError(_("This dvi does not have cost lines."))
        if not self.l10n_ro_tax_id:
            raise UserError(_("You have a vat in custom but no tax_id."))
        if not self.vendor_bill_id.state == "posted":
            raise UserError(_("You can create a DVI only on a posted invoice."))
        if not self.picking_ids.filtered(lambda r: r.state == "done"):
            raise UserError(
                _("You can create a DVI that does ont have transfers in done state.")
            )

        self = self.with_company(self.company_id)
        move = self.env["account.move"]
        move_vals = {
            "journal_id": self.account_journal_id.id,
            "date": self.date,
            "ref": self.name + f" DVI for {self.vendor_bill_id.name}",
            "line_ids": [],
            "move_type": "entry",
        }
        valuation_layer_ids = []
        cost_to_add_byproduct = defaultdict(lambda: 0.0)
        self.compute_landed_cost()

        aml = []  # account_move_line
        for line in self.valuation_adjustment_lines.filtered(lambda line: line.move_id):
            remaining_qty = sum(
                line.move_id.stock_valuation_layer_ids.mapped("remaining_qty")
            )
            if remaining_qty <= 0:
                raise ValidationError(
                    _(
                        f"For product {line.move_id.product_id.name} "
                        "you have remaining qty <=0. We can not create accounting and "
                        "svl because we do not have stock anymore to put this values"
                        "add this dvi on other pickings;"
                    )
                )

            linked_layer = line.move_id.stock_valuation_layer_ids[:1]

            # Prorate the value at what's still in stock
            cost_to_add = (
                remaining_qty / line.move_id.product_qty
            ) * line.additional_landed_cost
            if not self.company_id.currency_id.is_zero(cost_to_add):
                valuation_layer = self.env["stock.valuation.layer"].create(
                    {
                        "value": cost_to_add,
                        "unit_cost": 0,
                        "quantity": 0,
                        "remaining_qty": 0,
                        "stock_valuation_layer_id": linked_layer.id,
                        "description": self.name + f" DVI {line.product_id.name}",
                        "stock_move_id": line.move_id.id,
                        "product_id": line.move_id.product_id.id,
                        "stock_landed_cost_id": self.id,
                        "company_id": self.company_id.id,
                    }
                )
                linked_layer.remaining_value += cost_to_add
                valuation_layer_ids.append(valuation_layer.id)
            # Update the AVCO
            product = line.move_id.product_id
            if product.cost_method == "average":
                cost_to_add_byproduct[product] += cost_to_add
            # Products with manual inventory valuation are ignored because they
            # do not need to create journal entries.
            if product.valuation != "real_time":
                continue
            # `remaining_qty` is negative if the move is out and
            # delivered proudcts that were not in stock.
            accounts = line.product_id.product_tmpl_id.get_product_accounts()
            base_tags_ids = line.cost_line_id.l10n_ro_tax_id.ids
            # should be +24_1 - BAZA
            aml += [
                {
                    "name": line.name,
                    "product_id": line.product_id.id,
                    "quantity": 0,
                    "debit": cost_to_add,
                    "credit": 0.0,
                    "account_id": accounts.get("stock_valuation")
                    and accounts["stock_valuation"].id
                    or False,
                    "tax_tag_ids": [(6, 0, base_tags_ids)],
                },
                {
                    "name": line.name,
                    "product_id": line.product_id.id,
                    "quantity": 0,
                    "debit": 0.0,
                    "credit": cost_to_add,
                    "account_id": accounts.get("expense")
                    and accounts["expense"].id
                    or False,
                },
            ]

        # batch standard price computation avoid recompute quantity_svl at each iteration
        products = self.env["product.product"].browse(
            p.id for p in cost_to_add_byproduct.keys()
        )
        for (
            product
        ) in products:  # iterate on recordset to prefetch efficiently quantity_svl
            if not float_is_zero(
                product.quantity_svl, precision_rounding=product.uom_id.rounding
            ):
                product.with_company(self.company_id).sudo().with_context(
                    disable_auto_svl=True
                ).standard_price += (
                    cost_to_add_byproduct[product] / product.quantity_svl
                )

        move_vals["stock_valuation_layer_ids"] = [(6, None, valuation_layer_ids)]

        # we create the paid VAT account move lines
        tax_tag_custom = self.l10n_ro_tax_id.invoice_repartition_line_ids.filtered(
            lambda r: r.repartition_type == "tax"
        )[0].tag_ids
        # should be +24_1 - TVA
        tax_values = self.l10n_ro_tax_id.compute_all(1)
        custom_duty_cost = self.cost_lines.filtered(
            lambda r: r.product_id.l10n_ro_custom_duty
        )[0]
        accounts = custom_duty_cost.product_id.product_tmpl_id.get_product_accounts()
        aml += [
            {
                "name": _("VAT paid at customs for DVI"),
                "debit": self.l10n_ro_tax_value,
                "credit": 0.0,
                "account_id": tax_values["taxes"][0][
                    "account_id"
                ],  # 4426 tva deductibila
                "tax_tag_ids": [(6, 0, tax_tag_custom[0].ids)],
            },
            {
                "name": _("VAT paid at customs for DVI"),
                "debit": 0.0,
                "credit": self.l10n_ro_tax_value,
                "account_id": accounts[
                    "expense"
                ].id,  # "446.tva"  xx aici e gresit trebuie sa schimb
            },
        ]
        move_vals["line_ids"] = [(0, 0, x) for x in aml]

        move = move.create(move_vals)
        self.update({"account_move_id": move.id})

        self.write({"state": "done"})
        if self.account_move_id:
            move._post()

        return True
