# ©  2008-2020 Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    module_l10n_ro_intrastat = fields.Boolean(string="Intrastat RO")
    company_country_id = fields.Many2one(
        "res.country",
        string="Company country",
        readonly=True,
        related="company_id.country_id",
    )

    incoterm_id = fields.Many2one(
        "account.incoterms",
        string="Default incoterm for Intrastat",
        related="company_id.incoterm_id",
        readonly=False,
        help="International Commercial Terms are a series of predefined"
        " commercial terms used in international transactions.",
    )

    intrastat_transaction_id = fields.Many2one(
        "l10n_ro_intrastat.transaction",
        "Default Transaction Type",
        help="Intrastat nature of transaction",
        related="company_id.intrastat_transaction_id",
        readonly=False,
    )

    transport_mode_id = fields.Many2one(
        "l10n_ro_intrastat.transport_mode",
        "Default Transport Mode",
        related="company_id.transport_mode_id",
        readonly=False,
    )
