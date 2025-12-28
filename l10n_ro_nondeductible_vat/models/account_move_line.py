# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ["account.move.line", "l10n.ro.mixin"]

    l10n_ro_non_deductible_line_id = fields.Many2one(
        "account.move.line", copy=False, string="Romania - Non Deductible Line"
    )
    display_type = fields.Selection(
        selection_add=[("non_deductible_tax_ro", "Romania - Non Deductible Tax")],
        ondelete={"non_deductible_tax_ro": "cascade"},
    )

    def _compute_is_storno(self):
        res = super()._compute_is_storno()
        nd_ro_lines = self.filtered(
            lambda move_line: move_line.move_id.country_code == "RO"
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
            res = super()._constrains_deductible_amount()
        for line in ro_move_lines:
            if line.deductible_amount not in (0, 50, 100):
                raise ValidationError(
                    self.env._("The deductibility must be a value between 0 and 100.")
                )
            if line.move_id.is_sale_document():
                raise ValidationError(
                    self.env._(
                        "Sales document doesn't allow for deductibility of "
                        "product/services."
                    )
                )
            if line.move_id.stock_move_ids:
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
