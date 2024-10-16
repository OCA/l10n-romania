# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = ["stock.picking", "comment.template"]
    _name = "stock.picking"

    l10n_ro_delegate_id = fields.Many2one("res.partner", string="Delegate")
    l10n_ro_mean_transp = fields.Char(string="Mean transport")

    @api.onchange("l10n_ro_delegate_id")
    def on_change_delegate_id(self):
        if self.l10n_ro_delegate_id:
            self.l10n_ro_mean_transp = self.l10n_ro_delegate_id.l10n_ro_mean_transp

    def write(self, vals):
        "if modified the l10n_ro_mean_transp will write into delegate"
        l10n_ro_mean_transp = vals.get("l10n_ro_mean_transp", False)
        l10n_ro_delegate_id = vals.get("l10n_ro_delegate_id", False)
        if l10n_ro_mean_transp and l10n_ro_delegate_id:
            if (
                l10n_ro_mean_transp
                != self.env["res.partner"]
                .sudo()
                .browse(l10n_ro_delegate_id)
                .l10n_ro_mean_transp
            ):
                self.env["res.partner"].sudo().browse(l10n_ro_delegate_id).write(
                    {"l10n_ro_mean_transp": l10n_ro_mean_transp}
                )
        return super().write(vals)

    @api.depends("picking_type_id")
    def _compute_comment_template_ids(self):
        res = super()._compute_comment_template_ids()
        for record in self.filtered(lambda r: not r.comment_template_ids):
            templates = self.env["base.comment.template"].search(
                [
                    ("partner_ids", "=", False),
                    ("models", "=", self._name),
                ]
            )
            for template in templates:
                domain = safe_eval(template.domain)
                if not domain or record.filtered_domain(domain):
                    record.comment_template_ids = [(4, template.id)]
        return res
