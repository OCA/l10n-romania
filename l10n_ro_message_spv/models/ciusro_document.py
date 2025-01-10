import io
import json
import logging
import zipfile
from datetime import datetime, timedelta

import requests
from dateutil import parser
from dateutil.relativedelta import relativedelta
from lxml import etree

from odoo import api, models

from odoo.addons.l10n_ro_efactura.models import ciusro_document

_logger = logging.getLogger(__name__)


class L10nRoEdiDocument(models.Model):
    _inherit = "l10n_ro_edi.document"

    @api.model
    def _request_ciusro_download_zip(self, company, key_download, session):
        result = ciusro_document.make_efactura_request(
            session=session,
            company=company,
            endpoint="descarcare",
            method="GET",
            params={"id": key_download},
        )
        if result.get("error", False):
            return result

        content = result["content"]
        # E-Factura gives download response in ZIP format
        try:
            zip_ref = zipfile.ZipFile(io.BytesIO(content))
        except Exception as e:
            _logger.error(f"Error {e} while parsing ZIP file: {content}")
            return {"error": "Error while parsing ZIP file"}

        xml_file = next(file for file in zip_ref.namelist() if "semnatura" not in file)
        xml_bytes = zip_ref.open(xml_file)
        root = etree.parse(xml_bytes)
        error_element = root.find(".//ns:Error", namespaces=ciusro_document.NS_HEADER)
        if error_element is not None:
            return {"error": error_element.get("errorMessage")}

        return result

    @api.model
    def _request_ciusro_download_messages_spv(self, company, **kwargs):
        zile = kwargs.get("zile", None)
        start = kwargs.get("start", None)
        end = kwargs.get("end", None)
        pagina = kwargs.get("pagina", 1)
        filtru = kwargs.get("filtru", "")
        messages = kwargs.get("messages", [])

        company_messages = []

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

        cif = company.vat.replace("RO", "")
        params = {
            "cif": cif,
            "pagina": pagina,
            "startTime": start_time,
            "endTime": end_time,
        }
        if filtru:
            params["filtru"] = filtru

        result = ciusro_document.make_efactura_request(
            session=requests,
            company=company,
            endpoint="listaMesajePaginatieFactura",
            params=params,
            method="GET",
        )

        if "error" not in result:
            content = result["content"]
            doc = json.loads(content.decode("utf-8"))
            if doc.get("status", False) == "401":
                _logger.error("401 Unauthorized")
                return False
            company_messages = list(
                filter(
                    lambda m: m.get("cif") == cif,
                    doc.get("mesaje") or [],
                )
            )
        messages += company_messages
        numar_total_pagini = doc.get("numar_total_pagini", 0)

        if pagina < numar_total_pagini:
            return self._request_ciusro_download_messages_spv(
                company=company,
                zile=zile,
                start=start,
                end=end,
                pagina=pagina + 1,
                filtru=filtru,
                messages=messages,
            )
        return messages
