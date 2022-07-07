from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_ro_edi_token = fields.Char(
        related="company_id.l10n_ro_edi_token", readonly=False, string="Token"
    )
    l10n_ro_edi_test_mode = fields.Boolean(
        related="company_id.l10n_ro_edi_test_mode", readonly=False, string="Test mode"
    )
