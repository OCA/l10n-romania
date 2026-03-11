# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

import requests

from odoo import api, fields, models
from odoo.api import NewId

_logger = logging.getLogger(__name__)

CEDILLATRANS = bytes.maketrans(
    "\u015f\u0163\u015e\u0162".encode(),
    "\u0219\u021b\u0218\u021a".encode(),
)

CEDILLATRANS = bytes.maketrans(
    "\u015f\u0163\u015e\u0162\u00e2\u00c2\u00ee\u00ce\u0103\u0102".encode(),
    "\u0219\u021b\u0218\u021a\u00e2\u00c2\u00ee\u00ce\u0103\u0102".encode(),
)

headers = {
    "User-Agent": "Mozilla/5.0 (compatible; MSIE 7.01; Windows NT 5.0)",
    "Content-Type": "application/json;",
}

# anaf syncron url
# https://static.anaf.ro/static/10/Anaf/Informatii_R/Servicii_web/doc_WS_V8.txt
ANAF_URL = "https://webservicesp.anaf.ro/api/PlatitorTvaRest/v9/tva"

AnafFiled_OdooField_Overwrite = [
    ("vat", "vat", "over_all_the_time"),
    ("nrc", "nrRegCom", "over_all_the_time"),
    ("street", "street", "over_all_the_time"),
    ("street2", "street2", "over_all_the_time"),
    ("city", "city", "over_all_the_time"),
    ("city_id", "city_id", "over_all_the_time"),
    ("state_id", "state_id", "over_all_the_time"),
    ("zip", "codPostal", "over_all_the_time"),
    ("phone", "telefon", "write_if_empty"),
    ("l10n_ro_caen_code", "cod_CAEN", "over_all_the_time"),
]


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_ro_old_name = fields.Char(
        string="Romania - Old Name",
        default="",
        help="To be completed manually with previous name of the company "
        "in case on change."
        "If the field in completed, when fetching the datas from ANAF website,"
        "if the name received is the old name set, "
        "than the partner will not be updated.",
    )
    l10n_ro_active_anaf_line_ids = fields.One2many(
        "l10n.ro.res.partner.anaf.status",
        "partner_id",
        string="Romania - Partner Active Anaf Status",
        help="will add entries only if differs as statusInactivi from previos"
        " or after entries",
        copy=False,
    )
    l10n_ro_vat_subjected_anaf_line_ids = fields.One2many(
        "l10n.ro.res.partner.anaf.scptva",
        "partner_id",
        string="Romania - Anaf Company scpTVA Records",
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
            "date_generale": {
                "data": "2025-10-01",
                "cui": 30834857,
                "denumire": "FOREST AND BIOMASS ROMÂNIA S.A.",
                "adresa": "JUD. TIMIŞ, SAT GIULVĂZ COM. GIULVĂZ,  , FERMA 5-6",
                "telefon": "0356179038",
                "fax": "",
                "codPostal": "307225",
                "act": "",
                "stare_inregistrare": "INREGISTRAT din data 26.10.2012",
                "data_inreg_Reg_RO_e_Factura": "",
                "organFiscalCompetent": "Administraţia Fiscală pentru
                    Contribuabili Mijlocii - Timiş",
                "forma_de_proprietate": "PROPR.PRIVATA-CAPITAL PRIVAT
                    AUTOHTON SI STRAIN",
                "forma_organizare": "PERSOANA JURIDICA",
                "forma_juridica": "SOCIETATE COMERCIALĂ PE ACŢIUNI",
                "statusRO_e_Factura": False,
                "data_inregistrare": "2012-10-26",
                "nrRegCom": "J2012002622359",
                "cod_CAEN": "119",
                "iban": ""
            },
            "inregistrare_scop_Tva": {
                "scpTVA": True,
                "perioade_TVA": [
                    {
                        "data_inceput_ScpTVA": "2012-12-04",
                        "data_sfarsit_ScpTVA": "",
                        "data_anul_imp_ScpTVA": "",
                        "mesaj_ScpTVA": ""
                    }
                ]
            },
            "inregistrare_RTVAI": {
                "dataActualizareTvaInc": "2013-07-11",
                "dataPublicareTvaInc": "2013-07-12",
                "dataInceputTvaInc": "2013-02-01",
                "dataSfarsitTvaInc": "2013-08-01",
                "tipActTvaInc": "Radiere",
                "statusTvaIncasare": False
            },
            "stare_inactiv": {
                "dataInactivare": "",
                "dataReactivare": "",
                "dataPublicare": "",
                "dataRadiere": "",
                "statusInactivi": False
            },
            "inregistrare_SplitTVA": {
                "dataInceputSplitTVA": "",
                "dataAnulareSplitTVA": "",
                "statusSplitTVA": False
            },
            "adresa_sediu_social": {
                "sdenumire_Localitate": "Sat Giulvăz Com. Giulvăz",
                "sdenumire_Strada": " ",
                "snumar_Strada": "",
                "scod_Localitate": "170",
                "sdenumire_Judet": "TIMIŞ",
                "scod_Judet": "35",
                "scod_JudetAuto": "TM",
                "sdetalii_Adresa": "FERMA 5-6",
                "scod_Postal": "307225",
                "stara": ""
            },
            "adresa_domiciliu_fiscal": {
                "dcod_Localitate": "170",
                "ddenumire_Strada": " ",
                "dnumar_Strada": "",
                "ddenumire_Localitate": "Sat Giulvăz Com. Giulvăz",
                "ddenumire_Judet": "TIMIŞ",
                "dcod_Judet": "35",
                "dcod_JudetAuto": "TM",
                "ddetalii_Adresa": "FERMA 5-6",
                "dcod_Postal": "307225",
                "dtara": ""
            }
        },
        """

        anaf_error = ""
        if "anaf_data" in self.env.context and isinstance(cod, str):
            test_data = self.env.context.get("anaf_data")
            result = test_data.get(cod, {})
            anaf_error = result.get("error", "")
            if result:
                return anaf_error, test_data[cod]

        get_param = self.env["ir.config_parameter"].sudo().get_param
        anaf_url = get_param("l10n_ro_partner_create_by_vat.anaf_url", ANAF_URL)
        if not data:
            data = fields.Date.to_string(fields.Date.today())
        if type(cod) in [list, tuple]:
            json_data = [{"cui": x, "data": data} for x in cod]
        else:
            json_data = [{"cui": cod, "data": data}]
        try:
            res = requests.post(anaf_url, json=json_data, headers=headers, timeout=30)
        except Exception as ex:
            error = self.env._(
                "ANAF Webservice not working. Exception raised: %(error)s", error=ex
            )
            return error, {}

        result = {}

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
                if not result or not result.get("date_generale"):
                    anaf_error = self.env._(
                        "Anaf didn't find any company with VAT=%(vat)s !", vat=cod
                    )
        else:
            anaf_error = self.env._(
                "Anaf request error: \nresponse=%(response)s "
                "\nreason=%(reason)s \ntext=%(text)s",
                response=res,
                reason=res.reason,
                text=res.text,
            )
        return anaf_error, result

    @api.model
    def _Anaf_to_Odoo(self, result):
        # From ANAf API v7 the structure changed with the following fields:
        odoo_result = result.get("date_generale", {})
        odoo_result.update(result.get("inregistrare_scop_Tva", {}))
        odoo_result.update(result.get("inregistrare_RTVAI", {}))
        odoo_result.update(result.get("stare_inactiv", {}))
        odoo_result.update(result.get("inregistrare_SplitTVA", {}))
        odoo_result.update(result.get("adresa_sediu_social", {}))
        odoo_result.update(result.get("adresa_domiciliu_fiscal", {}))
        if (
            not odoo_result.get("denumire")
            or odoo_result["denumire"].upper() == self.l10n_ro_old_name
        ):
            # if no name means that anaf didn't return anything
            return {}
        res = {
            "name": odoo_result["denumire"].upper(),
            "l10n_ro_vat_subjected": odoo_result.get("scpTVA"),
            "company_type": "company",
        }

        odoo_result = self.get_result_address(odoo_result)
        prefix = odoo_result.get("scpTVA", False) and "RO" or ""
        odoo_result["vat"] = prefix + str(odoo_result.get("cui", ""))

        if (
            "city_id" in self._fields
            and odoo_result["state_id"]
            and odoo_result["city"]
        ):
            domain = [
                ("state_id", "=", odoo_result["state_id"].id),
                ("name", "=ilike", odoo_result["city"]),
            ]
            city = self.env["res.city"].search(domain, limit=1)
            if city:
                odoo_result["city_id"] = city.id

        if odoo_result["state_id"] == self.env.ref("base.RO_B"):
            if odoo_result.get("codPostal") and odoo_result["codPostal"][0] != "0":
                odoo_result["codPostal"] = "0" + odoo_result["codPostal"]
        for field in AnafFiled_OdooField_Overwrite:
            if field[1] not in odoo_result:
                continue
            anaf_value = odoo_result.get(field[1], "")
            if type(self._fields[field[0]]) in [fields.Date, fields.Datetime]:
                if not anaf_value.strip():
                    anaf_value = False
            if field[2] == "over_all_the_time":
                res[field[0]] = anaf_value
            elif field[2] == "write_if_empty&add_date" and anaf_value:
                # we are only writing if is not already a value
                if not getattr(self, field[0], None):
                    now = fields.datetime.now()
                    res[field[0]] = (f"UTC {now}:") + anaf_value
            elif field[2] == "write_if_empty" and anaf_value:
                if not getattr(self, field[0], None):
                    res[field[0]] = anaf_value

        return res

    def get_result_address(self, result):
        # Take address from domiciliu fiscal
        def get_city(text):
            city = text.replace(".", "").upper()
            remove_str = ["MUNICIPIUL", "MUN", "ORȘ", "JUD"]
            if "SECTOR" in city and "MUN" in city:
                city = city.split("MUN")[0]
            for tag in remove_str:
                city = city.replace(tag, "")
            return city.strip().title()

        state = False
        for tag in [
            "ddenumire_Strada",
            "dnumar_Strada",
            "ddetalii_Adresa",
            "ddenumire_Localitate",
            "ddenumire_Judet",
        ]:
            result[tag] = (
                result[tag]
                .encode("utf8")
                .translate(CEDILLATRANS)
                .decode("utf8")
                .strip()
            )
        result["street"] = result.get("ddenumire_Strada")
        if result.get("dnumar_Strada"):
            result["street"] += " Nr. " + result.get("dnumar_Strada")
        result["street"] = result["street"].strip().title()
        result["street2"] = result.get("ddetalii_Adresa", " ").strip().title()
        if not result["street"] and result["street2"]:
            result["street"] = result["street2"]
            result["street2"] = ""
        result["zip"] = result.get("dcod_Postal", "").strip()
        result["city"] = get_city(result.get("ddenumire_Localitate"))
        state_name = get_city(result.get("ddenumire_Judet"))
        state_code = result.get("dcod_JudetAuto")

        if state_code:
            domain = [
                ("code", "=", state_code),
                ("country_id", "=", self.env.ref("base.ro").id),
            ]
            state = self.env["res.country.state"].search(domain, limit=1)

        if not state and state_name:
            domain = [("name", "=", state_name)]
            state = self.env["res.country.state"].search(domain, limit=1)

        result["state_id"] = state
        return result

    @api.onchange("vat", "country_id")
    def ro_vat_change(self):
        res = {}
        if self.is_l10n_ro_record and not self.parent_id:
            if not self.env.context.get("skip_ro_vat_change"):
                if not self.vat:
                    return res
                vat = self.vat.strip().upper()
                original_vat_country, vat_number = self._split_vat(vat)
                vat_country = original_vat_country.upper()
                if not vat_country and self.country_id:
                    vat_country = self._l10n_ro_map_vat_country_code(
                        self.country_id.code.upper()
                    )
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
                        if (
                            not isinstance(self, NewId)
                            and not self.l10n_ro_active_anaf_line_ids
                        ):
                            res = self._update_l10n_ro_anaf_status(res, result)
                        if (
                            not isinstance(self, NewId)
                            and not self.l10n_ro_anaf_history
                        ):
                            res = self._update_l10n_ro_anaf_scptva(res, result)
                        self.with_context(skip_ro_vat_change=True).update(res)
                    else:
                        res["warning"] = {"message": anaf_error}
        return res

    def get_date_from_anaf(self, date_string):
        date_str = date_string.strip()
        if date_str:
            return fields.Date.from_string(date_str)
        return False

    def _update_l10n_ro_anaf_status(self, res, result):
        self.ensure_one()
        if not res:
            res = {}
        if result:
            date_generale = result.get("date_generale", {})
            inactive_res = result.get("stare_inactiv", {})
            if inactive_res:
                same_date_record = self.l10n_ro_active_anaf_line_ids.filtered(
                    lambda r: str(r.start_date)
                    == inactive_res.get("dataReactivare", "")
                    and str(r.end_date) == inactive_res.get("dataInactivare", "")
                    and str(r.publish_date) == inactive_res.get("dataPublicare", "")
                    and str(r.delete_date) == inactive_res.get("dataRadiere", "")
                    and r.active_status == inactive_res.get("statusInactivi")
                )
                if not same_date_record and not res.get("l10n_ro_active_anaf_line_ids"):
                    res["l10n_ro_active_anaf_line_ids"] = [
                        (
                            0,
                            0,
                            {
                                "vat_number": date_generale.get("cui"),
                                "act": date_generale.get("act"),
                                "status": date_generale.get("stare_inregistrare"),
                                "start_date": self.get_date_from_anaf(
                                    inactive_res.get("dataReactivare", "")
                                ),
                                "end_date": self.get_date_from_anaf(
                                    inactive_res.get("dataInactivare", "")
                                ),
                                "publish_date": self.get_date_from_anaf(
                                    inactive_res.get("dataPublicare", "")
                                ),
                                "delete_date": self.get_date_from_anaf(
                                    inactive_res.get("dataRadiere", "")
                                ),
                                "active_status": inactive_res.get("statusInactivi"),
                            },
                        )
                    ]
        return res

    def _update_l10n_ro_anaf_scptva(self, res, result):
        self.ensure_one()
        if not res:
            res = {}
        if result:
            date_generale = result.get("date_generale", {})
            vat_res = result.get("inregistrare_scop_Tva", {})
            if vat_res:
                for vat_period in vat_res.get("perioade_TVA", [{}]):
                    same_date_record = (
                        self.l10n_ro_vat_subjected_anaf_line_ids.filtered(
                            lambda r, vat_period=vat_period: str(r.start_date)
                            == vat_period.get("data_inceput_ScpTVA", "")
                            and str(r.end_date)
                            == vat_period.get("data_sfarsit_ScpTVA", "")
                            and str(r.year_date)
                            == vat_period.get("data_anul_imp_ScpTVA", "")
                            and r.message == vat_period.get("mesaj_ScpTVA")
                        )
                    )
                    if not same_date_record:
                        res["l10n_ro_vat_subjected_anaf_line_ids"] = [
                            (
                                0,
                                0,
                                {
                                    "vat_number": date_generale.get("cui"),
                                    "start_date": self.get_date_from_anaf(
                                        vat_period.get("data_inceput_ScpTVA", "")
                                    ),
                                    "end_date": self.get_date_from_anaf(
                                        vat_period.get("data_sfarsit_ScpTVA", "")
                                    ),
                                    "year_date": self.get_date_from_anaf(
                                        vat_period.get("data_anul_imp_ScpTVA", "")
                                    ),
                                    "message": vat_period.get("mesaj_ScpTVA"),
                                },
                            )
                        ]
        return res
