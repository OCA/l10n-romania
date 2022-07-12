# ©  2008-2022 Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_ro_e_invoice = fields.Boolean(
        "E Invoice", help="Enrolled in the e-invoice system"
    )
