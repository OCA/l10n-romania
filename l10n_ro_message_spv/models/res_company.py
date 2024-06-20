# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json
import logging
import re
from datetime import datetime, timedelta

import pytz
from dateutil import parser
from dateutil.relativedelta import relativedelta

from odoo import api, models

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def l10n_ro_download_message_spv(self):
        # method to be used in cron job to auto download e-invoices from ANAF
        ro_companies = self.env.user.company_ids.filtered(
            lambda c: c._l10n_ro_get_anaf_sync(scope="e-factura")
        )

        pattern_in = r"cif_emitent=(\d+)"
        pattern_out = r"cif_beneficiar=(\d+)"

        romania_tz = pytz.timezone("Europe/Bucharest")

        for company in ro_companies:
            company_messages = company._l10n_ro_get_anaf_efactura_messages()
            for message in company_messages:
                domain = [
                    ("name", "=", message["id"]),
                    ("company_id", "=", company.id),
                ]
                if not self.env["l10n.ro.message.spv"].search(domain, limit=1):
                    date = datetime.strptime(message.get("data_creare"), "%Y%m%d%H%M")
                    localized_date = romania_tz.localize(date)
                    # Convertim data și ora la GMT
                    gmt_tz = pytz.timezone("GMT")
                    gmt_date = localized_date.astimezone(gmt_tz)
                    partner = self.env["res.partner"]
                    cif = message["cif"]
                    message_type = False
                    if message["tip"] == "FACTURA PRIMITA":
                        message_type = "in_invoice"
                        match = re.search(pattern_in, message["detalii"])
                        if match:
                            cif = match.group(1)
                            partner = self.env["res.partner"].search(
                                [("vat", "like", cif)], limit=1
                            )

                    elif message["tip"] == "FACTURA TRIMISA":
                        message_type = "out_invoice"
                        match = re.search(pattern_out, message["detalii"])
                        if match:
                            cif = match.group(1)
                            domain = [("vat", "like", cif), ("is_company", "=", True)]
                            partner = self.env["res.partner"].search(domain, limit=1)
                    elif message["tip"] == "ERORI FACTURA":
                        message_type = "error"
                    elif "MESAJ" in message["tip"]:
                        message_type = "message"
                    else:
                        _logger.error("Unknown message type: %s", message["tip"])

                    self.env["l10n.ro.message.spv"].sudo().create(
                        {
                            "name": message["id"],
                            "cif": cif,
                            "message_type": message_type,
                            "date": gmt_date.strftime("%Y-%m-%d %H:%M:%S"),
                            "details": message["detalii"],
                            "request_id": message["id_solicitare"],
                            "company_id": company.id,
                            "partner_id": partner.id,
                            "state": "draft",
                        }
                    )
        return True

    def _l10n_ro_get_anaf_efactura_messages(self, **kwargs):
        zile = kwargs.get("zile", None)
        start = kwargs.get("start", None)
        end = kwargs.get("end", None)
        pagina = kwargs.get("pagina", 1)
        filtru = kwargs.get("filtru", "")
        messages = kwargs.get("messages", [])

        company_messages = []
        anaf_config = self._l10n_ro_get_anaf_sync(scope="e-factura")
        if not anaf_config:
            _logger.warning("No ANAF configuration for company %s", self.name)
            return company_messages
        token = anaf_config.anaf_sync_id.access_token
        if not token:
            _logger.warning("No access token for company %s", self.name)
            return company_messages
        start_time = end_time = 0
        now = then = datetime.now()
        # no_days = int(zile or self.l10n_ro_download_einvoices_days or "60")
        no_days = int(zile or 60)
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
        content, status_code = anaf_config._l10n_ro_einvoice_call(
            "/listaMesajePaginatieFactura", params, method="GET"
        )
        if status_code == 200:
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
