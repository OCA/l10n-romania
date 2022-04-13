# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from datetime import date

from odoo import api, fields, models, tools


class ResPartnerAnafStatus(models.Model):
    _name = "res.partner.anaf.status"
    _description = "ANAF History about company status active/inactive"
    _order = "data desc"

    cui = fields.Integer(help="Just the number 1234 from vat like RO1234 ", index=True)
    data = fields.Date(
        index=True,
        help="The date for anaf interogation and data for validity of this record",
    )
    act = fields.Char(
        "Act autorizare",
    )
    stare_inregistrare = fields.Char(
        "Stare Societate",
    )
    dataInactivare = fields.Date()
    dataReactivare = fields.Date()
    dataPublicare = fields.Date()
    dataRadiere = fields.Date()
    statusInactivi = fields.Boolean(
        help=" true -pentru inactiv / false"
        " in cazul in care nu este inactiv la data cautata"
    )
