# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class StockInventory(models.Model):
    _inherit = "stock.inventory"

    acc_move_line_ids = fields.One2many(
        "account.move.line",
        "stock_inventory_id",
        string="Generated accounting lines",
        help="A field just to be easier to see the generated " "accounting entries ",
    )

    def post_inventory(self):
        "just to have the acc_move_line_ids used in view. can be also without this fields"
        res = super(StockInventory, self).post_inventory()
        for inv in self:
            acc_move_line_ids = self.env["account.move.line"]
            for move in inv.move_ids:
                for acc_move in move.account_move_ids:
                    acc_move_line_ids |= acc_move.line_ids
            acc_move_line_ids.write({"stock_inventory_id": inv.id})
        return res
