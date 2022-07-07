# ©  2008-2022 Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ro_edi_access_token = fields.Char(string="Token")
    l10n_ro_edi_test_mode = fields.Boolean(string="Test mode", default=True)
