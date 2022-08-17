# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_ro_mean_transp = fields.Char(
        string="Mean transport",
        help="Visible only in pickings, and can be modify only from there;"
        "is keeping all the time the last not null value",
    )
