from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_ro_download_einvoices_days = fields.Integer(
        related="company_id.l10n_ro_download_einvoices_days",
        readonly=False,
    )
