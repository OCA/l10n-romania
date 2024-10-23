# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json
import logging
from datetime import datetime, timedelta

import requests
from dateutil import parser
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT

from odoo.addons.l10n_ro_efactura.models.ciusro_document import make_efactura_request

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ro_edi_residence = fields.Integer(string="Period of Residence", default=5)
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
    l10n_ro_credit_note_einvoice = fields.Boolean(
        string="Credit Note on e-invoice", default=False
    )
    l10n_ro_edi_error_notify_users = fields.Many2many(
        "res.users",
        relation="res_company_res_users_edi_notify_rel",
        string="EDI Error Notify Users",
        help="Add users to receive EDI Error messages",
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

    def _l10n_ro_get_anaf_efactura_messages(self, **kwargs):
        zile = kwargs.get("zile", None)
        start = kwargs.get("start", None)
        end = kwargs.get("end", None)
        pagina = kwargs.get("pagina", 1)
        filtru = kwargs.get("filtru", "")
        messages = kwargs.get("messages", [])

        company_messages = []
        start_time = end_time = 0
        now = then = datetime.now()
        no_days = int(zile or self.l10n_ro_download_einvoices_days or "60")
        if not start:
            now = end and parser.parse(end) or datetime.now() - timedelta(seconds=60)
            then = now - relativedelta(days=no_days)
        elif start:
            then = parser.parse(start)
            now = end and parser.parse(end) or (then + relativedelta(days=no_days))
            now = min(now, (datetime.now() - timedelta(seconds=60)))
        start_time = str(then.timestamp() * 1e3).split(".")[0]
        end_time = str(now.timestamp() * 1e3).split(".")[0]

        params = {
            "cif": self.partner_id.l10n_ro_vat_number,
            "pagina": pagina,
            "startTime": start_time,
            "endTime": end_time,
        }
        if filtru:
            params["filtru"] = filtru
        result = make_efactura_request(
            session=requests,
            company=self,
            endpoint="listaMesajePaginatieFactura",
            method="GET",
            params=params,
        )
        if "error" in result:
            return result
        content = result.get("content")
        if content:
            doc = json.loads(content.decode("utf-8"))
            company_messages = list(
                filter(
                    lambda m: m.get("cif") == self.partner_id.l10n_ro_vat_number,
                    doc.get("mesaje") or [],
                )
            )
        messages += company_messages
        numar_total_pagini = doc.get("numar_total_pagini", 0)

        if pagina < numar_total_pagini:
            return self._l10n_ro_get_anaf_efactura_messages(
                zile=zile,
                start=start,
                end=end,
                pagina=pagina + 1,
                filtru=filtru,
                messages=messages,
            )
        return messages

    @api.model
    def _l10n_ro_create_anaf_efactura(self):
        # method to be used in cron job to auto download e-invoices from ANAF
        ro_companies = self.search([]).filtered(
            lambda c: c.country_id.code == "RO"
            and c.l10n_ro_edi_access_token
            and c.l10n_ro_download_einvoices
        )
        for company in ro_companies:
            move_obj = self.env["account.move"].with_company(company)
            company_messages = company._l10n_ro_get_anaf_efactura_messages(filtru="P")
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
                new_invoice = move_obj.search(
                    [("l10n_ro_edi_download", "=", message.get("id"))]
                )
                if not new_invoice:
                    new_invoice = move_obj.with_context(
                        default_move_type="in_invoice"
                    ).create(
                        {
                            "l10n_ro_edi_download": message.get("id"),
                            "l10n_ro_edi_transaction": message.get("id_solicitare"),
                        }
                    )
                    try:
                        new_invoice.l10n_ro_download_zip_anaf()
                    except Exception as e:
                        new_invoice.message_post(
                            body=_("Error downloading e-invoice: %s") % str(e)
                        )
