# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo import api, fields, models


class Partner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "l10n.ro.mixin"]

    city_id = fields.Many2one("res.city", domain="[('state_id','=',state_id)]")

    @api.onchange("state_id")
    def onchange_state(self):
        if self.is_l10n_ro_record:
            if self.city_id and self.city_id.state_id != self.state_id:
                self.city_id = None
