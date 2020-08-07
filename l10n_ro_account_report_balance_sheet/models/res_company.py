# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    company_type = fields.Selection(
        selection=[
            ("BL", "S1002 BL Societati Mari Mijloci"),
            ("BS", "S1003 BS Societati Mici"),
            ("SL", "S1004 SL IFRS Societati mari mijloci"),
            ("UL", "S1005 UL Microintreprinedri"),
        ],
        default="BL",
        required=True,
        help="Type of romanian company by accounting low",
    )
