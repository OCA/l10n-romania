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

# Fereastra maxima pe care ANAF o serveste pe endpointurile de lista de mesaje:
# mesajele sunt pastrate 60 de zile, iar `startTime` nu poate fi mai vechi de atat
# fata de momentul requestului.
SPV_MESSAGES_RETENTION_DAYS = 60

# Marje fata de capetele ferestrei. Ambele capete sunt judecate pe ceasul ANAF, iar
# o secunda de dezacord respinge tot intervalul, deci nu cerem niciodata fereastra
# exact pe limita.
SPV_WINDOW_START_MARGIN = timedelta(minutes=5)
SPV_WINDOW_END_MARGIN = timedelta(seconds=60)

# ANAF serveste maximum 500 de mesaje pe pagina. Garda ne apara de o bucla lunga
# daca `numar_total_pagini` vine absurd: 200 de pagini = 100.000 de mesaje, mult
# peste orice volum real pe 60 de zile.
SPV_MAX_PAGES = 200

# Note pe care ANAF le trimite in cheia `eroare` desi nu sunt erori.
SPV_NO_RESULTS_HINTS = ("nu exista mesaje",)


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
    def _request_ciusro_window_spv(self, no_days=60, start=None, end=None):
        """Intervalul cerut ANAF, retras inauntrul limitelor pe care le impune.

        :return: tuple ``(then, now)`` de ``datetime``
        """
        if not start:
            now = end and parser.parse(end) or datetime.now() - SPV_WINDOW_END_MARGIN
            then = now - relativedelta(days=no_days)
        else:
            then = parser.parse(start)
            now = end and parser.parse(end) or (then + relativedelta(days=no_days))
            now = min(now, datetime.now() - SPV_WINDOW_END_MARGIN)

        # ANAF respinge tot intervalul daca `startTime` e mai vechi de 60 de zile
        # fata de momentul requestului, judecat pe ceasul lor. O fereastra cerută
        # exact pe limita — cazul `no_days=60`, adica implicitul de pe companie —
        # sta pe granita si poate cadea din cauza diferentei de ceas, iar raspunsul
        # de eroare e greu de distins de „nu sunt mesaje". Retragem startul cu o
        # marja inauntrul limitei.
        oldest = (
            datetime.now()
            - relativedelta(days=SPV_MESSAGES_RETENTION_DAYS)
            + SPV_WINDOW_START_MARGIN
        )
        if then < oldest:
            _logger.info(
                "SPV: startul cerut (%s) e in afara ferestrei de %s zile; "
                "il retrag la %s.",
                then,
                SPV_MESSAGES_RETENTION_DAYS,
                oldest,
            )
            then = oldest
        return then, now

    @api.model
    def _request_ciusro_download_messages_spv(
        self, company, no_days=60, start=None, end=None, page=1, filtru=""
    ):
        """Lista mesajelor din SPV pentru `company`, pe toate paginile.

        Foloseste endpointul paginat (`listaMesajePaginatieFactura`), fiindca cel
        nepaginat refuza cu totul intervalele de peste 500 de mesaje — un volum
        atins de o singura zi la clientii mari.

        Paginile se parcurg in bucla, nu recursiv, ca sa nu depindem de limita de
        recursivitate la un numar mare de pagini, si se opresc la `SPV_MAX_PAGES`.

        Orice pagina care nu poate fi citita (eroare de transport, corp neparsabil,
        eroare de business a ANAF) opreste parcurgerea si e **logata**: paginile
        deja citite se pastreaza, dar rezultatul e partial. Fara logare, o lista
        goala din cauza unei erori arata exact ca „nu sunt mesaje" si importul pare
        ca a rulat cu succes.

        :return: lista mesajelor ANAF ale companiei (posibil partiala la eroare)
        """
        messages = []
        then, now = self._request_ciusro_window_spv(
            no_days=no_days, start=start, end=end
        )
        start_time = str(then.timestamp() * 1e3).split(".")[0]
        end_time = str(now.timestamp() * 1e3).split(".")[0]

        cif = company.vat.replace("RO", "")
        current = page
        last_page = page + SPV_MAX_PAGES - 1
        while current <= last_page:
            params = {
                "cif": cif,
                "pagina": current,
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
            if "error" in result:
                _logger.error(
                    "SPV: pagina %s pentru CIF %s a esuat (%s). "
                    "Rezultat partial: %s mesaje.",
                    current,
                    cif,
                    result["error"],
                    len(messages),
                )
                break

            try:
                doc = json.loads(result["content"].decode("utf-8"))
            except ValueError:
                _logger.error(
                    "SPV: raspuns neparsabil pe pagina %s pentru CIF %s. "
                    "Rezultat partial: %s mesaje.",
                    current,
                    cif,
                    len(messages),
                )
                break

            if str(doc.get("status") or "") == "401":
                _logger.error(
                    "SPV: 401 Unauthorized pe pagina %s pentru CIF %s. "
                    "Rezultat partial: %s mesaje.",
                    current,
                    cif,
                    len(messages),
                )
                break

            # ANAF trimite pe HTTP 200, in aceeasi cheie `eroare`, atat erorile
            # reale cat si nota „nu exista mesaje in intervalul selectat".
            eroare = doc.get("eroare")
            if eroare:
                if any(hint in eroare.lower() for hint in SPV_NO_RESULTS_HINTS):
                    _logger.info("SPV: %s (CIF %s).", eroare, cif)
                else:
                    _logger.error(
                        "SPV: eroare pe pagina %s pentru CIF %s: %s. "
                        "Rezultat partial: %s mesaje.",
                        current,
                        cif,
                        eroare,
                        len(messages),
                    )
                break

            page_messages = doc.get("mesaje") or []
            company_messages = [m for m in page_messages if m.get("cif") == cif]
            others = len(page_messages) - len(company_messages)
            if others:
                # Mesajele altor CIF-uri nu ne privesc; le numaram, nu le varsam
                # in log — la 500 de mesaje pe pagina ar inunda jurnalul.
                _logger.debug(
                    "SPV: pagina %s conține %s mesaje ale altor CIF-uri.",
                    current,
                    others,
                )
            messages += company_messages

            numar_total_pagini = doc.get("numar_total_pagini") or 0
            if current >= numar_total_pagini:
                break
            current += 1
        else:
            _logger.error(
                "SPV: garda de %s pagini atinsa pentru CIF %s; "
                "rezultat trunchiat la %s mesaje.",
                SPV_MAX_PAGES,
                cif,
                len(messages),
            )

        return messages
