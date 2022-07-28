from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_ro_edi_access_token = fields.Char(
        related="company_id.l10n_ro_edi_access_token",
        readonly=False,
        string="Access Token",
    )
    l10n_ro_edi_test_mode = fields.Boolean(
        related="company_id.l10n_ro_edi_test_mode", readonly=False, string="Test mode"
    )
    l10n_ro_edi_manual = fields.Boolean(
        related="company_id.l10n_ro_edi_manual",
        readonly=False,
        string="Manual submission",
    )
