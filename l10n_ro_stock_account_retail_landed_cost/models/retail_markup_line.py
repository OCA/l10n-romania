# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class RetailMarkupLine(models.Model):
    _inherit = "l10n.ro.retail.markup.line"

    landed_cost_id = fields.Many2one(
        "stock.landed.cost",
        string="Landed Cost",
        index="btree_not_null",
        ondelete="set null",
    )
