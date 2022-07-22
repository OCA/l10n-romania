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

# anaf syncron url https://static.anaf.ro/static/10/Anaf/Informatii_R/doc_WS_V6.txt
ANAF_URL = "https://webservicesp.anaf.ro/PlatitorTvaRest/api/v6/ws/tva"

AnafFiled_OdooField_Overwrite = [
    ("nrc", "nrRegCom", "over_all_the_time"),
    ("zip", "codPostal", "over_all_the_time"),
    ("phone", "telefon", "write_if_empty"),
    ("city", "city", "over_all_the_time"),
    ("state_id", "state_id", "over_all_the_time"),
    ("street", "street", "over_all_the_time"),
    ("city_id", "city_id", "write_if_empty"),
    ("caen_code", "cod_CAEN", "over_all_the_time"),
    ("l10n_ro_e_invoice", "statusRO_e_Factura", "over_all_the_time"),
    ("vat", "vat", "over_all_the_time"),
]


class ResPartner(models.Model):
    _inherit = "res.partner"

    old_name = fields.Char(
        string="Old Name",
        default="",
        help="To be completed manually with previous name of the company in case on change."
        "If the field in completed, when fetching the datas from ANAF website,"
        "if the name received is the old name set, than the partner will not be updated.",
    )
    # l10n_ro_einvoice_state = fields.Boolean(string="Ro E-Invoicing", copy=False)
    active_anaf_line_ids = fields.One2many(
        "res.partner.anaf.status",
        "partner_id",
        string="Partner Active Anaf Status",
        help="will add entries only if differs as statusInactivi from previos"
        " or after entries",
        copy=False,
    )
    vat_subjected_anaf_line_ids = fields.One2many(
        "res.partner.anaf.scptva",
        "partner_id",
        string="Anaf Company scpTVA Records",
        help="will add entries only if differs as scpTVA from previos or after entries",
        copy=False,
    )

    @api.model
    def _get_Anaf(self, cod, data=False):
        """
        Function to retrieve data from ANAF for one vat number
        at certain date

        :param str cod:  vat number without country code or a list of codes
        :param date data: date of the interogation
        :return dict result: cost of the body's operation
        {
        'cui': 30834857,
        'data': '2022-07-21',
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
        'statusSplitTVA': False,
        'iban': '',
        'statusRO_e_Factura': False,
        'sdenumire_Strada': ' ',
        'snumar_Strada': ' ',
        'sdenumire_Localitate': 'Sat Giulvăz Com. Giulvăz',
        'scod_Localitate': '170',
        'sdenumire_Judet': 'TIMIŞ',
        'scod_Judet': '35',
        'stara': ' ',
        'sdetalii_Adresa': 'FERMA 5-6',
        'scod_Postal': '307225',
        'ddenumire_Strada': 'Str. Ciprian Porumbescu',
        'dnumar_Strada': '12',
        'ddenumire_Localitate': 'Mun. Timişoara',
        'dcod_Localitate': '355',
        'ddenumire_Judet': 'TIMIŞ',
        'dcod_Judet': '35',
        'dtara': ' ',
        'ddetalii_Adresa': 'ZONA NR.3, Etaj 1',
        'dcod_Postal': ' ',
        'data_inregistrare': '2012-10-26',
        'cod_CAEN': '119'}
        }
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
            return _("ANAF Webservice not working. Exeption=%s." % ex), {}

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
                    anaf_error = _("Anaf didn't find any company with VAT=%s !" % cod)
        else:
            anaf_error = _(
                "Anaf request error: \nresponse=%s \nreason=%s"
                " \ntext=%s" % (res, res.reason, res.text)
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

        result = self.get_result_address(result)

        if "city_id" in self._fields and result["state_id"] and result["city"]:
            domain = [
                ("state_id", "=", result["state_id"].id),
                ("name", "ilike", result["city"]),
            ]
            result["city_id"] = self.env["res.city"].search(domain, limit=1).id

        for field in AnafFiled_OdooField_Overwrite:
            anaf_value = result.get(field[1], "")
            if not anaf_value:
                continue
            if type(self._fields[field[0]]) in [fields.Date, fields.Datetime]:
                if not anaf_value.strip():
                    anaf_value = False
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

        return res

    def get_result_address(self, result):
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
                elif "ORȘ." in line.upper():
                    city = line.replace("ORȘ.", "").strip().title()
                elif "COM." in line.upper():
                    city += " " + line.strip().title()
                elif " SAT " in line.upper():
                    city += " " + line.strip().title()
                else:
                    addr += line.replace("STR.", "").strip().title() + " "

        result["vat"] = "%s%s" % (
            result.get("scpTVA", False) and "RO" or "",
            result.get("cui"),
        )
        result["city"] = city.replace("-", " ").title().strip()
        result["state_id"] = state
        result["street"] = addr.strip()
        return result

    @api.onchange("vat")
    def ro_vat_change(self):
        res = {}
        if not self.env.context.get("skip_ro_vat_change"):
            if not self.vat:
                return res
            vat = self.vat.strip().upper()
            original_vat_country, vat_number = self._split_vat(vat)
            vat_country = original_vat_country.upper()
            if not vat_country and self.country_id:
                vat_country = self._map_vat_country_code(self.country_id.code.upper())
                if not vat_number:
                    vat_number = self.vat
            if vat_country == "RO":
                anaf_error, result = self._get_Anaf(vat_number)
                if not anaf_error:
                    res = self._Anaf_to_Odoo(result)
                    res["country_id"] = (
                        self.env["res.country"]
                        .search([("code", "ilike", vat_country)])[0]
                        .id
                    )
                    # Update ANAF history for vat_subjected and active status
                    res = self._update_anaf_status(res, result)
                    res = self._update_anaf_scptva(res, result)
                    self.with_context(skip_ro_vat_change=True).update(res)
                else:
                    res["warning"] = {"message": anaf_error}
        return res

    def get_date_from_anaf(self, date_string):
        date_str = date_string.strip()
        if date_str:
            return fields.Date.from_string(date_str)
        return False

    def _update_anaf_status(self, res, result):
        self.ensure_one()
        if not res:
            res = {}
        if result:
            same_date_record = self.active_anaf_line_ids.filtered(
                lambda r: str(r.date) == self.get_date_from_anaf(result.get("data", ""))
            )
            if not same_date_record and not res.get("active_anaf_line_ids"):
                res["active_anaf_line_ids"] = [
                    (
                        0,
                        0,
                        {
                            "vat_number": result.get("cui"),
                            "date": self.get_date_from_anaf(result.get("data", "")),
                            "act": result.get("act"),
                            "status": result.get("stare_inregistrare"),
                            "start_date": self.get_date_from_anaf(
                                result.get("dataReactivare", "")
                            ),
                            "end_date": self.get_date_from_anaf(
                                result.get("dataInactivare", "")
                            ),
                            "publish_date": self.get_date_from_anaf(
                                result.get("dataPublicare", "")
                            ),
                            "delete_date": self.get_date_from_anaf(
                                result.get("dataRadiere", "")
                            ),
                            "active_status": result.get("statusInactivi"),
                        },
                    )
                ]
        return res

    def _update_anaf_scptva(self, res, result):
        self.ensure_one()
        if not res:
            res = {}
        if result:
            same_date_record = self.vat_subjected_anaf_line_ids.filtered(
                lambda r: str(r.date) == self.get_date_from_anaf(result.get("data", ""))
            )
            if not same_date_record and not res.get("vat_subjected_anaf_line_ids"):
                res["vat_subjected_anaf_line_ids"] = [
                    (
                        0,
                        0,
                        {
                            "vat_number": result.get("cui"),
                            "date": self.get_date_from_anaf(result.get("data", "")),
                            "start_date": self.get_date_from_anaf(
                                result.get("data_inceput_ScpTVA", "")
                            ),
                            "end_date": self.get_date_from_anaf(
                                result.get("data_sfarsit_ScpTVA", "")
                            ),
                            "year_date": self.get_date_from_anaf(
                                result.get("data_anul_imp_ScpTVA", "")
                            ),
                            "message": result.get("mesaj_ScpTVA"),
                            "vat_subjected": result.get("scpTVA"),
                        },
                    )
                ]
        return res
