# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json
import logging
from datetime import datetime

from odoo import _, api, fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ro_edi_residence = fields.Integer(string="Period of Residence", default=5)
    l10n_ro_edi_cius_embed_pdf = fields.Boolean(
        string="Embed PDF in CIUS", default=False
    )
    l10n_ro_default_cius_pdf_report = fields.Many2one(
        "ir.actions.report",
        string="Default PDF Report",
        help="Default PDF report to be attached to xml e-invoice.",
    )
    l10n_ro_download_einvoices = fields.Boolean(
        string="Download e-invoices from ANAF", default=False
    )
    l10n_ro_download_einvoices_start_date = fields.Date(
        string="Start date to download e-invoices"
    )
    l10n_ro_download_einvoices_days = fields.Integer(
        string="Maximum number of days to download e-invoices.", default=10
    )

    @api.constrains("l10n_ro_edi_residence", "l10n_ro_download_einvoices_days")
    def _check_l10n_ro_edi_residence(self):
        for company in self:
            if company.l10n_ro_edi_residence < 0 or company.l10n_ro_edi_residence > 5:
                raise models.ValidationError(
                    _("The period of residence must be between 0 and 5.")
                )
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

    def _l10n_ro_get_anaf_efactura_messages(self):
        company_messages = []
        anaf_config = self.l10n_ro_account_anaf_sync_id
        if not anaf_config:
            _logger.warning("No ANAF configuration for company %s", self.name)
            return company_messages
        if not anaf_config.access_token:
            _logger.warning("No access token for company %s", self.name)
            return company_messages
        no_days = self.l10n_ro_download_einvoices_days or "60"
        params = {
            "zile": no_days,
            "cif": self.partner_id.l10n_ro_vat_number,
        }
        content, status_code = anaf_config._l10n_ro_einvoice_call(
            "/listaMesajeFactura", params, method="GET"
        )
        if status_code == 200:
            doc = json.loads(content.decode("utf-8"))
            company_messages = list(
                filter(
                    lambda m: m.get("cif") == self.partner_id.l10n_ro_vat_number
                    and m.get("tip") == "FACTURA PRIMITA",
                    doc.get("mesaje") or [],
                )
            )
        return company_messages

    @api.model
    def _l10n_ro_create_anaf_efactura(self):
        # method to be used in cron job to auto download e-invoices from ANAF
        ro_companies = self.search([]).filtered(
            lambda c: c.country_id.code == "RO"
            and c.l10n_ro_account_anaf_sync_id
            and c.l10n_ro_download_einvoices
        )
        new_invoices = self.env["account.move"]
        for company in ro_companies:
            move_obj = self.env["account.move"].with_company(company)
            company_messages = company._l10n_ro_get_anaf_efactura_messages()
            for message in company_messages:
                if company.l10n_ro_download_einvoices_start_date:
                    if message.get("data_creare"):
                        message_date = datetime.strptime(
                            message.get("data_creare")[:8], "%Y%m%d"
                        ).strftime(DATE_FORMAT)
                        if (
                            fields.Date.from_string(message_date)
                            < company.l10n_ro_download_einvoices_start_date
                        ):
                            continue
                invoice = move_obj.search(
                    [("l10n_ro_edi_download", "=", message.get("id"))]
                )
                if not invoice:
                    new_invoice = move_obj.with_context(
                        default_move_type="in_invoice"
                    ).create(
                        {
                            "l10n_ro_edi_download": message.get("id"),
                            "l10n_ro_edi_transaction": message.get("id_solicitare"),
                        }
                    )
                    new_invoice.l10n_ro_download_zip_anaf(
                        company.l10n_ro_account_anaf_sync_id
                    )
                    new_invoices += new_invoice
