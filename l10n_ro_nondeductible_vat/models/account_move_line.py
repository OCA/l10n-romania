# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import _, api, models, fields


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ["account.move.line", "l10n.ro.mixin"]

    l10n_ro_non_deductible_line_id = fields.Many2one(
        "account.move.line", string="Romania - Non Deductible Line", copy=False
    )

    def _compute_is_storno(self):
        res = super()._compute_is_storno()
        nd_ro_lines = self.filtered(
            lambda l: l.move_id.country_code == "RO" and l.display_type == "non_deductible_product" and l.name != _('private part')
        )
        nd_ro_lines.is_storno = True
        return res

