# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from datetime import date

from odoo import api, fields, models, tools


class ResPartnerAnafScptva(models.Model):
    _name = "res.partner.anaf.scptva"
    _description = "ANAF History about company scpTVA "
    _order = "data desc"

    cui = fields.Integer(help="Just the number 1234 from vat like RO1234 ", index=True)
    data = fields.Date(
        index=True,
        help="The date for anaf interogation and data for validity of this record",
    )
    data_inceput_ScpTVA = fields.Date()
    data_sfarsit_ScpTVA = fields.Date()
    data_anul_imp_ScpTVA = fields.Date()
    mesaj_ScpTVA = fields.Char(help="---MESAJ:(ne)platitor de TVA la data cautata---")
    scpTVA = fields.Boolean(
        help="true -pentru platitor in scopuri de tva / false in cazul in care nu e platitor  in scopuri de TVA la data cautata"
    )
