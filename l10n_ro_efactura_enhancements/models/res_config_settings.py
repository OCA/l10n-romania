from odoo import models, fields, api, _

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_ro_download_einvoices_days = fields.Integer(related='company_id.l10n_ro_download_einvoices_days', string="Maximum number of days to download e-invoices.", readonly=False)