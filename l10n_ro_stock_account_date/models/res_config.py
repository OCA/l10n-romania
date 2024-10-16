# Copyright (C) 2024 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _name = "res.config.settings"
    _inherit = ["res.config.settings", "l10n.ro.mixin"]

    l10n_ro_account_move_activity = fields.Boolean(
        "Add notification when posting invoice/entry if it's not linked to stock_move",
        config_parameter="account_move_activity",
    )
