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

from odoo.addons.l10n_ro_edi.models.utils import NS_HEADER

_logger = logging.getLogger(__name__)


def make_efactura_request(
    session, company, endpoint, params, data=None
) -> dict[str, str | bytes]:
    """
    Make an API request to the Romanian SPV
    Copy form  odoo.addons.l10n_ro_edi.models.utils.make_efactura_request

    """
    send_mode = "test" if company.l10n_ro_edi_test_env else "prod"
    url = f"https://api.anaf.ro/{send_mode}/FCTEL/rest/{endpoint}"
    if endpoint in ["upload", "uploadb2c", "transformare"]:
        method = "POST"
    elif endpoint in [
        "stareMesaj",
        "descarcare",
        "listaMesajeFactura",
        "listaMesajePaginatieFactura",
    ]:
        method = "GET"
    else:
        return {"error": company.env._("Unknown endpoint.")}
    headers = {
        "Content-Type": "application/xml",
        "Authorization": f"Bearer {company.l10n_ro_edi_access_token}",
    }
    if endpoint == "transformare":
        url = "https://webservicesp.anaf.ro/prod/FCTEL/rest/transformare/FACT1/DA"
        headers = {"Content-Type": "text/plain"}

    try:
        response = session.request(
            method=method,
            url=url,
            params=params,
            data=data,
            headers=headers,
            timeout=60,
        )
    except requests.HTTPError as e:
        return {"error": e}
    except (requests.ConnectionError, requests.Timeout):
        return {
            "error": company.env._(
                "Timeout while sending to SPV."
                " Use Synchronise to SPV to update the status."
            ),
            "timeout": True,
        }

    if response.status_code == 204:
        return {
            "error": company.env._(
                "You reached the limit of requests. Please try again later."
            )
        }
    if response.status_code == 400:
        error_json = response.json()
        return {"error": error_json["message"]}
    if response.status_code == 401:
        return {"error": company.env._("Access token is unauthorized.")}
    if response.status_code == 403:
        return {"error": company.env._("Access token is forbidden.")}
    if response.status_code == 500:
        return {
            "error": company.env._(
                "There is something wrong with the SPV. Please try again later."
            )
        }

    return {"content": response.content}


class L10nRoEdiDocument(models.Model):
    _inherit = "l10n_ro_edi.document"

    @api.model
    def _request_ciusro_download_zip(self, company, key_download, session):
        result = make_efactura_request(
            session=session,
            company=company,
            endpoint="descarcare",
            params={"id": key_download},
        )
        if result.get("error", False):
            return result

        content = result["content"]
        # ANAF poate răspunde cu HTTP 200 dar corp JSON de eroare (ex: limita de
        # 10 descărcări/zi pe mesaj atinsă) în loc de arhiva ZIP. Tratăm explicit
        # această condiție de business, fără a încerca parsarea ca ZIP și fără a
        # o loga ca eroare de cod.
        if content[:1] in (b"{", b"["):
            try:
                error_json = json.loads(content.decode("utf-8"))
            except Exception:
                error_json = None
            if isinstance(error_json, dict) and error_json.get("eroare"):
                _logger.warning(
                    "ANAF download refused for id=%s: %s",
                    key_download,
                    error_json["eroare"],
                )
                return {"error": error_json["eroare"]}

        # E-Factura gives download response in ZIP format
        try:
            zip_ref = zipfile.ZipFile(io.BytesIO(content))
        except Exception as e:
            _logger.error(f"Error {e} while parsing ZIP file: {content}")
            return {"error": "Error while parsing ZIP file"}

        xml_file = next(
            (file for file in zip_ref.namelist() if "semnatura" not in file), None
        )
        if not xml_file:
            return {"error": "No XML file found in ZIP archive"}
        xml_bytes = zip_ref.open(xml_file)

        recovering_parser = etree.XMLParser(recover=True)

        root = etree.parse(xml_bytes, parser=recovering_parser)
        error_element = root.find(".//ns:Error", namespaces=NS_HEADER)
        if error_element is not None:
            return {"error": error_element.get("errorMessage")}

        return result

    @api.model
    def _request_ciusro_download_messages_spv(
        self, company, no_days=60, start=None, end=None, page=1, filtru=""
    ):
        messages = []

        numar_total_pagini = 0
        now = then = datetime.now()

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
            "pagina": page,
            "startTime": start_time,
            "endTime": end_time,
        }
        if filtru:
            params["filtru"] = filtru

        result = make_efactura_request(
            session=requests,
            company=company,
            endpoint="listaMesajePaginatieFactura",
            params=params,
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
            others_messages = list(
                filter(
                    lambda m: m.get("cif") != cif,
                    doc.get("mesaje") or [],
                )
            )
            _logger.info(f"Other messages: {others_messages}")
            messages += company_messages
            numar_total_pagini = doc.get("numar_total_pagini", 0)

        if page < numar_total_pagini:
            messages += self._request_ciusro_download_messages_spv(
                company=company,
                no_days=no_days,
                start=start,
                end=end,
                page=page + 1,
                filtru=filtru,
            )
        return messages
