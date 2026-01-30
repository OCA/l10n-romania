from odoo import models, fields, api, _

class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ro_download_einvoices_days = fields.Integer(
        string="Maximum number of days to download e-invoices.", default=60
    )

    @api.constrains("l10n_ro_download_einvoices_days")
    def _check_l10n_ro_download_einvoices_days(self):
        for company in self:
            if (
                company.l10n_ro_download_einvoices_days < 0
                or company.l10n_ro_download_einvoices_days > 60
            ):
                raise models.ValidationError(
                    _(
                        "The maximum number of days to download e-invoices "
                        "must be between 0 and 60."
                    )
                )