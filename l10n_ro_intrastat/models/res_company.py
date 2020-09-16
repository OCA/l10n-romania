# ©  2008-2020 Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    intrastat_transaction_id = fields.Many2one(
        "l10n_ro_intrastat.transaction",
        "Default Transaction Type",
        help="Intrastat nature of transaction",
    )

    transport_mode_id = fields.Many2one(
        "l10n_ro_intrastat.transport_mode", "Default Transport Mode"
    )

    incoterm_id = fields.Many2one(
        "account.incoterms",
        "Default Incoterm ",
        help="International Commercial Terms are a series of "
        "predefined commercial terms used in international transactions.",
    )
