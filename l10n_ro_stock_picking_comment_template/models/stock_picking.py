# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = ["stock.picking", "comment.template"]
    _name = "stock.picking"

    delegate_id = fields.Many2one("res.partner", string="Delegate")
    mean_transp = fields.Char(string="Mean transport")

    @api.onchange("delegate_id")
    def on_change_delegate_id(self):
        if self.delegate_id:
            self.mean_transp = self.delegate_id.mean_transp

    def write(self, vals):
        "if modified the mean_transp will write into delegate"
        mean_transp = vals.get("mean_transp", False)
        delegate_id = vals.get("delegate_id", False)
        if mean_transp and delegate_id:
            if (
                mean_transp
                != self.env["res.partner"].sudo().browse(delegate_id).mean_transp
            ):
                self.env["res.partner"].sudo().browse(delegate_id).write(
                    {"mean_transp": mean_transp}
                )
        return super().write(vals)
