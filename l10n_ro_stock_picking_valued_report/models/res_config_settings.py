# Copyright (C) 2026 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_ro_print_aviz_with_prices = fields.Boolean(
        related="company_id.l10n_ro_print_aviz_with_prices",
        readonly=False,
    )
