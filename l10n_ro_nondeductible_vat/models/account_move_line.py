# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ["account.move.line", "l10n.ro.mixin"]

    l10n_ro_nondeductible_percent = fields.Selection(
        [("0", "Deductible"), ("50", "50% Nondeductible"), ("100", "Nondeductible")],
        string="Romania - Non Deductible Percent",
        compute="_compute_l10n_ro_nondeductible_amount",
        inverse="_inverse_l10n_ro_nondeductible_amount",
        store=True,
        readonly=False,
    )
    l10n_ro_non_deductible_line_id = fields.Many2one(
        "account.move.line", copy=False, string="Romania - Non Deductible Line"
    )
    display_type = fields.Selection(
        selection_add=[("non_deductible_tax_ro", "Romania - Non Deductible Tax")],
        ondelete={"non_deductible_tax_ro": "cascade"},
    )

    @api.depends("deductible_amount")
    def _compute_l10n_ro_nondeductible_amount(self):
        for line in self:
            ded_perc = int(100 - line.deductible_amount)
            if ded_perc in (50, 100):
                line.l10n_ro_nondeductible_percent = str(ded_perc)
            else:
                line.l10n_ro_nondeductible_percent = "0"

    @api.onchange("l10n_ro_nondeductible_percent")
    def _inverse_l10n_ro_nondeductible_amount(self):
        for line in self:
            if line.l10n_ro_nondeductible_percent:
                line.deductible_amount = 100 - int(line.l10n_ro_nondeductible_percent)

    def _compute_is_storno(self):
        res = super()._compute_is_storno()
        nd_ro_lines = self.filtered(
            lambda move_line: move_line.company_id.l10n_ro_accounting
            and move_line.display_type == "non_deductible_product"
            and move_line.name != self.env._("private part")
        )
        nd_ro_lines.is_storno = True
        return res

    @api.constrains("deductible_amount")
    def _constrains_deductible_amount(self):
        ro_move_lines = self.filtered(
            lambda line: line.move_id.company_id.l10n_ro_accounting
        )
        res = False
        if self - ro_move_lines:
            res = super(
                AccountMoveLine, self - ro_move_lines
            )._constrains_deductible_amount()
        for line in ro_move_lines:
            if line.deductible_amount not in (0, 50, 100):
                raise ValidationError(
                    self.env._("The deductibility must be a value between 0 and 100.")
                )
            if line.move_id.is_sale_document() and line.deductible_amount != 100:
                raise ValidationError(
                    self.env._(
                        "Sales document doesn't allow for deductibility of "
                        "product/services."
                    )
                )
            if line.move_id.stock_move_ids and line.tax_ids:
                # We need to check this validation since when setting up
                # deductible_amount, the stock move is not linked with
                # the account move, this is done after.
                if hasattr(line.move_id.stock_move_ids, "l10n_ro_move_type"):
                    l10n_ro_move_type = line.move_id.stock_move_ids.l10n_ro_move_type
                    types_allow_ndeductibility = [
                        "minus_inventory",
                        "consumption",
                        "consumption_return",
                        "usage_giving",
                        "usage_giving_return",
                    ]

                    if l10n_ro_move_type not in types_allow_ndeductibility:
                        raise ValidationError(
                            self.env._(
                                "Only stock moves of type %(types)s allow for "
                                "non-deductibility of product/services.",
                                types=", ".join(types_allow_ndeductibility),
                            )
                        )
        return res

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        to_remove_lines = self.env["account.move.line"]
        for line in lines.filtered(lambda aml: aml.company_id.l10n_ro_accounting):
            # Remove the lines marked to be removed from stock non deductible
            tax_rep_line = line.tax_repartition_line_id
            if self.env.context.get("l10n_ro_exclude_from_stock"):
                if tax_rep_line.l10n_ro_exclude_from_stock:
                    to_remove_lines |= line
        lines -= to_remove_lines
        to_remove_lines.with_context(dynamic_unlink=True).sudo().unlink()
        return lines
