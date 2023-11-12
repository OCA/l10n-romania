# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ro_edi_manual = fields.Boolean(
        string="E-Invoice Manual submission", default=True
    )

    l10n_ro_edi_residence = fields.Integer(string="Period of Residence", default=5)
