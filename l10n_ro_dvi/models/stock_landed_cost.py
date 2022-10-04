# Copyright (C) 2020 Terrabit
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LandedCost(models.Model):
    _inherit = "stock.landed.cost"

    l10n_ro_cost_type = fields.Selection(
        selection_add=[("dvi", "DVI")], ondelete={"dvi": "set default"}
    )
    l10n_ro_tax_id = fields.Many2one(
        "account.tax",
        string="Romania - DVI Tax",
        copy=False,
        states={"done": [("readonly", True)]},
        help="VAT tax for products and customs cost",
    )
    l10n_ro_base_tax_value = fields.Float(
        "Romania - Base VAT amount",
        states={"done": [("readonly", True)]},
        copy=False,
        help="Base VAT amount, calculated from invoice base amount, customs and commision.",
    )
    l10n_ro_tax_value = fields.Float(
        "Romania - VAT amount paid at customs",
        states={"done": [("readonly", True)]},
        copy=False,
        help="VAT amount, calculated from invoice base amount and customs.",
    )
    l10n_ro_account_dvi_id = fields.Many2one(
        "l10n.ro.account.dvi",
        string="Romania - DVI",
    )
    l10n_ro_dvi_bill_ids = fields.Many2many(
        "account.move",
        relation="account_move_stock_landed_cost_rel",
        readonly=True,
        string="Romania - DVI Invoices",
    )

    def button_validate(self):
        res = super(LandedCost, self).button_validate()
        for cost in self.filtered(lambda c: c.l10n_ro_tax_value and c.l10n_ro_tax_id):
            if (
                cost.l10n_ro_cost_type == "dvi"
                and not cost.l10n_ro_account_dvi_id.invoice_ids
            ):
                raise UserError(
                    _(
                        "You cannot create a DVI landed cost without reference to an invoice."
                    )
                )
            if not self.env.context.get("dvi_revert"):
                if not cost.account_move_id:
                    cost.account_move_id = self.env["account.move"].create(
                        {
                            "journal_id": cost.account_journal_id.id,
                            "date": cost.date,
                            "ref": cost.name,
                            "line_ids": [],
                            "move_type": "entry",
                        }
                    )
                customs_duty_product = (
                    cost.company_id._l10n_ro_get_or_create_custom_duty_product()
                )
                if not customs_duty_product:
                    raise UserError(_("The product Custom Duty not found"))
                tax = cost.l10n_ro_tax_id
                if cost.l10n_ro_dvi_bill_ids[0].move_type == "in_invoice":
                    tax_repartition_line = tax.invoice_repartition_line_ids.filtered(
                        lambda r: r.repartition_type == "tax"
                    )
                else:
                    tax_repartition_line = tax.refund_repartition_line_ids.filtered(
                        lambda r: r.repartition_type == "tax"
                    )
                accounts_data = (
                    customs_duty_product.product_tmpl_id.get_product_accounts()
                )
                tax_values = cost.l10n_ro_tax_id.compute_all(
                    cost.l10n_ro_base_tax_value
                )
                aml = [
                    {
                        "name": _("VAT paid at customs"),
                        "debit": cost.l10n_ro_tax_value,
                        "credit": 0.0,
                        "account_id": tax_values["taxes"][0]["account_id"],
                        "move_id": cost.account_move_id.id,
                        "tax_line_id": tax.id,
                        "tax_repartition_line_id": tax_repartition_line.id,
                        "tax_tag_ids": [(6, 0, tax_repartition_line.tag_ids.ids)],
                        "tax_base_amount": cost.l10n_ro_base_tax_value,
                    },
                    {
                        "name": _("VAT paid at customs expense"),
                        "debit": 0.0,
                        "credit": cost.l10n_ro_tax_value,
                        "account_id": accounts_data["expense"].id,
                        "move_id": cost.account_move_id.id,
                    },
                ]
                self.env["account.move.line"].create(aml)
                if cost.account_move_id and cost.account_move_id.state != "posted":
                    cost.account_move_id._post()
        return res


class AdjustmentLines(models.Model):
    _inherit = "stock.valuation.adjustment.lines"

    def _create_account_move_line(
        self, move, credit_account_id, debit_account_id, qty_out, already_out_account_id
    ):
        if self._context.get("dvi_revert"):
            return []
        else:
            res = super()._create_account_move_line(
                move,
                credit_account_id,
                debit_account_id,
                qty_out,
                already_out_account_id,
            )
            customs_duty_product = (
                self.cost_id.company_id._l10n_ro_get_or_create_custom_duty_product()
            )
            if (
                self.is_l10n_ro_record
                and self.cost_line_id.product_id == customs_duty_product
            ):
                tax = customs_duty_product.supplier_taxes_id[0]
                if self.cost_id.l10n_ro_dvi_bill_ids[0].move_type == "in_invoice":
                    tax_repartition_line = tax.invoice_repartition_line_ids.filtered(
                        lambda r: r.repartition_type == "base"
                    )
                else:
                    tax_repartition_line = tax.refund_repartition_line_ids.filtered(
                        lambda r: r.repartition_type == "base"
                    )
                # Add base tags to debit lines.
                for line in res:
                    line_dict = line[2]
                    if line_dict.get("account_id") == debit_account_id:
                        line_dict["tax_ids"] = tax.ids
                        line_dict["tax_tag_ids"] = [
                            (6, 0, tax_repartition_line["tag_ids"].ids)
                        ]
            return res
