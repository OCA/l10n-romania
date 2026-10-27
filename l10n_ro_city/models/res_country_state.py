# Copyright (C) 2023 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class ResCountryState(models.Model):
    _inherit = "res.country.state"

    l10n_ro_prefix_zip = fields.Char(string="Romania - Prefix Zip")
