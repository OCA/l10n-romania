# Copyright (C) 2026 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ro_print_aviz_with_prices = fields.Boolean(
        string="Print delivery note (aviz) with prices",
        default=True,
        help=(
            "When enabled, the outgoing delivery note (aviz) prints its "
            "price and value columns. Reception notes and internal transfers "
            "are unaffected."
        ),
    )
