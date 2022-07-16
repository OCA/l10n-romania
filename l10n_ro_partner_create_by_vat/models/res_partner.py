# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

import requests

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

CEDILLATRANS = bytes.maketrans(
    "\u015f\u0163\u015e\u0162".encode("utf8"),
    "\u0219\u021b\u0218\u021a".encode("utf8"),
)

headers = {
    "User-Agent": "Mozilla/5.0 (compatible; MSIE 7.01; Windows NT 5.0)",
    "Content-Type": "application/json;",
}

# anaf syncron url https://static.anaf.ro/static/10/Anaf/Informatii_R/doc_WS_V5.txt
ANAF_URL = "https://webservicesp.anaf.ro/PlatitorTvaRest/api/v6/ws/tva"


AnafFiled_OdooField_Overwrite = [
    ("nrc", "nrRegCom", "over_all_the_time"),
    ("zip", "codPostal", "over_all_the_time"),
    ("comment", "stare_inregistrare", "write_if_empty&add_date"),
    ("phone", "telefon", "write_if_empty"),
]


class ResPartner(models.Model):
    _inherit = "res.partner"

    old_name = fields.Char(default="")

    @api.model
    def _get_Anaf(self, cod, data=False):
        """
        Function to retrieve data from ANAF for one vat number
        at certain date

        :param str cod:  vat number without country code or a list of codes
        :param date data: date of the interogation
        :return dict result: cost of the body's operation
        {'cui': 30834857,
        'data': '2021-04-14',
        'denumire': 'FOREST AND BIOMASS ROMÂNIA S.A.',
        'adresa': 'JUD. TIMIŞ, MUN. TIMIŞOARA, STR. CIPRIAN PORUMBESCU,
        NR.12, ZONA NR.3, ETAJ 1',
        'nrRegCom': 'J35/2622/2012',
        'telefon': '0356179038',
        "fax": "-- Fax --",
        'codPostal': '307225',
        "act": "-- Act autorizare --",
        "stare_inregistrare": "-- Stare Societate --", 'INREGISTRAT din data 26.10.2012',
        "scpTVA": true -pentru platitor in scopuri de tva / false in cazul in care nu
                    e platitor  in scopuri de TVA la data cautata
        "data_inceput_ScpTVA": " ", --Data înregistrării în scopuri de TVA anterioară
                '2012-12-04'
        "data_sfarsit_ScpTVA": " ", --Data anulării înregistrării în scopuri de TVA
        "data_anul_imp_ScpTVA": " ",--Data operarii anularii înregistrării în scopuri de TVA
        "mesaj_ScpTVA": "---MESAJ:(ne)platitor de TVA la data cautata---",
        "dataInceputTvaInc": " ", --Data de la care aplică sistemul TVA la încasare
        "dataSfarsitTvaInc": " ", --Data până la care aplică sistemul TVA la încasare
        "dataActualizareTvaInc": " ", --Data actualizarii
        "dataPublicareTvaInc": " ", --Data publicarii
        "tipActTvaInc": " ", --Tip actualizare    'Radiere',
        "statusTvaIncasare":  true -pentru platitor TVA la incasare/ false in cazul in
                         care nu e platitor de TVA la incasare la data cautata
        "dataInactivare": " ",
        "dataReactivare": " ",
        "dataPublicare": " ",
        "dataRadiere": " ",
        "statusInactivi": true -pentru inactiv / false in cazul in care nu este inactiv
                             la data cautata
        "dataInceputSplitTVA": " ",
        "dataAnulareSplitTVA": " ",
        "statusSplitTVA": true -aplica plata defalcata a Tva / false - nu aplica plata
                         defalcata a Tva la data cautata
        "iban": "--- contul IBAN ---"
        "statusRO_e_Factura": true - figureaza in Registrul RO e-Factura / false
                        - nu figureaza in Registrul RO e-Factura la data cautata
        """
        if not data:
            data = fields.Date.to_string(fields.Date.today())
        if type(cod) in [list, tuple]:
            json_data = [{"cui": x, "data": data} for x in cod]
        else:
            json_data = [{"cui": cod, "data": data}]
        try:
            res = requests.post(ANAF_URL, json=json_data, headers=headers)
        except Exception as ex:
            return _("ANAF Webservice not working. Exeption=%s.") % ex, {}

        result = {}
        anaf_error = ""
        if (
            res.status_code == 200
            and res.headers.get("content-type") == "application/json"
        ):
            resjson = res.json()
            if type(cod) in [list, tuple]:
                result = resjson
            else:
                if resjson.get("found") and resjson["found"][0]:
                    result = resjson["found"][0]
                if not result or not result.get("denumire"):
                    anaf_error = _("Anaf didn't find any company with VAT=%s !") % cod
        else:
            anaf_error = _(
                "Anaf request error: \nresponse=%(response)s \nreason=%(reason)s"
                " \ntext=%(text)s",
                response=res,
                reason=res.reason,
                text=res.text,
            )
        return anaf_error, result

    @api.model
    def _Anaf_to_Odoo(self, result):
        if not result.get("denumire") or result["denumire"].upper() == self.old_name:
            # if no name means that anaf didn't return anything
            return {}
        res = {
            "name": result["denumire"].upper(),
            "vat_subjected": result["scpTVA"],
            "company_type": "company",
        }
        for field in AnafFiled_OdooField_Overwrite:
            anaf_value = result.get(field[1], "")
            if field[2] == "over_all_the_time":
                res[field[0]] = anaf_value
            elif field[2] == "write_if_empty&add_date" and anaf_value:
                if not getattr(
                    self, field[0], None
                ):  # we are only writing if is not already a value
                    res[field[0]] = ("UTC %s:" % fields.datetime.now()) + anaf_value
            elif field[2] == "write_if_empty" and anaf_value:
                if not getattr(self, field[0], None):
                    res[field[0]] = anaf_value

        res = self.get_result_address(result, res)

        if "city_id" in self._fields and res["state_id"] and res["city"]:
            res["city_id"] = (
                self.env["res.city"]
                .search(
                    [
                        ("state_id", "=", res["state_id"].id),
                        ("name", "ilike", res["city"]),
                    ],
                    limit=1,
                )
                .id
            )
        return res

    def get_result_address(self, result, res):
        addr = city = ""
        state = False
        if result.get("adresa"):
            sector = False
            address = result["adresa"].replace("NR,", "NR.").upper()
            if "SECTOR " in address and "BUCUREŞTI" in address:
                sector = True
            lines = [x for x in address.split(",") if x]
            for line in lines:
                line = line.encode("utf8").translate(CEDILLATRANS).decode("utf8")
                if "JUD." in line:
                    state = self.env["res.country.state"].search(
                        [("name", "=", line.replace("JUD.", "").strip().title())],
                        limit=1,
                    )
                elif "MUN." in line:
                    city = line.replace("MUN.", "").strip().title()
                elif sector and "MUNICIPIUL" in line:
                    state = self.env["res.country.state"].search(
                        [("name", "=", line.replace("MUNICIPIUL", "").strip().title())],
                        limit=1,
                    )
                elif not sector and "MUNICIPIUL" in line:
                    city = line.replace("MUNICIPIUL", "").strip().title()
                elif sector and "SECTOR " in line:
                    city = line.strip().title()
                elif "ORȘ." in line:
                    city = line.replace("ORȘ.", "").strip().title()
                elif "COM." in line:
                    city += " " + line.strip().title()
                elif " SAT " in line:
                    city += " " + line.strip().title()
                else:
                    addr += line.replace("STR.", "").strip().title() + " "
        res["city"] = city.replace("-", " ").title().strip()
        res["state_id"] = state
        res["street"] = addr.strip()
        return res

    @api.onchange("vat", "country_id")
    def ro_vat_change(self):
        for partner in self:
            ret = {}
            if not partner.vat:
                return ret
            res = {}
            vat = partner.vat.strip().upper()
            original_vat_country, vat_number = partner._split_vat(vat)
            vat_country = original_vat_country.upper()
            if not vat_country and partner.country_id:
                vat_country = self._map_vat_country_code(
                    partner.country_id.code.upper()
                )
                if not vat_number:
                    vat_number = partner.vat
            if vat_country == "RO":
                anaf_error, result = partner._get_Anaf(vat_number)
                if not anaf_error:
                    res = partner._Anaf_to_Odoo(result)
                    res["country_id"] = (
                        self.env["res.country"]
                        .search([("code", "ilike", vat_country)])[0]
                        .id
                    )
                    partner.with_context(skip_ro_vat_change=True).update(res)
                else:
                    ret["warning"] = {"message": anaf_error}
        return ret
