# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

import requests

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

CEDILLATRANS = bytes.maketrans(
    "\u015f\u0163\u015e\u0162".encode("utf8"),
    "\u0219\u021b\u0218\u021a".encode("utf8"),
)

headers = {
    "User-Agent": "Mozilla/5.0 (compatible; MSIE 7.01; Windows NT 5.0)",
    "Content-Type": "application/json;",
}

ANAF_URL = "https://webservicesp.anaf.ro/PlatitorTvaRest/api/v6/ws/tva"


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _get_Anaf(self, cod, data=False):
        """
        Function to retrieve data from ANAF for one vat number
        at certain date

        :param str cod:  vat number without country code
        :param date data: date of the interogation
        :return dict result: cost of the body's operation
        {'cui': 30834857,
        'data': '2021-04-14',
        'denumire': 'FOREST AND BIOMASS ROMÂNIA S.A.',
        'adresa': 'JUD. TIMIŞ, MUN. TIMIŞOARA, STR. CIPRIAN PORUMBESCU,
        NR.12, ZONA NR.3, ETAJ 1',
        'nrRegCom': 'J35/2622/2012',
        'telefon': '0356179038',
        'codPostal': '307225',
        'stare_inregistrare': 'INREGISTRAT din data 26.10.2012',
        'scpTVA': True,
        'data_inceput_ScpTVA': '2012-12-04',
        'data_sfarsit_ScpTVA': ' ',
        'data_anul_imp_ScpTVA': ' ',
        'mesaj_ScpTVA': 'platitor IN SCOPURI de TVA la data cautata',
        'dataInceputTvaInc': '2013-02-01',
        'dataSfarsitTvaInc': '2013-08-01',
        'dataActualizareTvaInc': '2013-07-11',
        'dataPublicareTvaInc': '2013-07-12',
        'tipActTvaInc': 'Radiere',
        'statusTvaIncasare': False,
        'dataInactivare': ' ',
        'dataReactivare': ' ',
        'dataPublicare': ' ',
        'dataRadiere': ' ',
        'statusInactivi': False,
        'dataInceputSplitTVA': '',
        'dataAnulareSplitTVA': '',
        'statusSplitTVA': False, 'iban': ''}
        """
        if not data:
            data = fields.Date.to_string(fields.Date.today())
        res = requests.post(
            ANAF_URL, json=[{"cui": cod, "data": data}], headers=headers
        )
        result = {}
        if res.status_code == 200:
            res = res.json()
            if res.get("found") and res["found"][0]:
                result = res["found"][0]
        return result

    @api.model
    def _Anaf_to_Odoo(self, result):
        AnafFiled_OdooField_Overwrite = [
            ("nrc", "nrRegCom", "over_all_the_time"),
            ("zip", "codPostal", "over_all_the_time"),
            ("comment", "stare_inregistrare", "if_empty+date"),
            ("phone", "telefon", "if_empty"),
        ]
        res = {
            "name": result["denumire"].upper(),
            "vat_subjected": result["scpTVA"],
            "company_type": "company",
        }
        for field in AnafFiled_OdooField_Overwrite:
            anaf_value = result.get(field[1], "")
            if field[2] == "over_all_the_time":
                res[field[0]] = anaf_value
            elif field[2] == "if_empty+date" and anaf_value:
                if not getattr(
                    self, field[0], None
                ):  # we are only writing if is not already a value
                    res[field[0]] = f"UTC: {fields.datetime.now()}: " + anaf_value
            elif field[2] == "if_empty" and anaf_value:
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
                try:
                    result = partner._get_Anaf(vat_number)
                    if result:
                        res = partner._Anaf_to_Odoo(result)
                except Exception as ex:
                    warning = f"ANAF Webservice not working. Or exception={ex}."
                    _logger.info(warning)
                    ret["warning"] = {"message": warning}
                if res:
                    res["country_id"] = (
                        self.env["res.country"]
                        .search([("code", "ilike", vat_country)])[0]
                        .id
                    )
                    partner.with_context(skip_ro_vat_change=True).update(res)
        return ret
