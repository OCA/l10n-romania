# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class RetailMarkupLine(models.Model):
    _inherit = "l10n.ro.retail.markup.line"

    price_change_id = fields.Many2one(
        "l10n.ro.retail.price.change",
        string="Price Change",
        index="btree_not_null",
        ondelete="set null",
    )
