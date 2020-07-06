# Copyright 2018 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    invoice_no_signature_text = fields.Text("Legal Invoice Text", translate=True)
