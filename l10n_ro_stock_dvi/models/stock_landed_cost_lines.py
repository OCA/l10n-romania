# 2022 Nexterp
# ©  2008-2020 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com

from odoo import fields, models


class LandedCostLines(models.Model):
    _inherit = "stock.landed.cost.lines"

    l10n_ro_tax_id = fields.Many2one(
        "account.tax",
        help="VAT tax for this product. Used to put the base in jorunal entry."
        " Tax value is included landed_cost l10n_ro_tax_value ",
    )
