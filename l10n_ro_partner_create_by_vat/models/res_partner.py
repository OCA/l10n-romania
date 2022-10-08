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

CEDILLATRANS = bytes.maketrans(
    "\u015f\u0163\u015e\u0162\u00e2\u00c2\u00ee\u00ce\u0103\u0102".encode("utf8"),
    "\u0219\u021b\u0218\u021a\u00e2\u00c2\u00ee\u00ce\u0103\u0102".encode("utf8"),
)

headers = {
    "User-Agent": "Mozilla/5.0 (compatible; MSIE 7.01; Windows NT 5.0)",
    "Content-Type": "application/json;",
}

# anaf syncron url https://static.anaf.ro/static/10/Anaf/Informatii_R/doc_WS_V6.txt
ANAF_URL = "https://webservicesp.anaf.ro/PlatitorTvaRest/api/v6/ws/tva"

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
    ("l10n_ro_e_invoice", "statusRO_e_Factura", "over_all_the_time"),
]


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_ro_old_name = fields.Char(
        string="Romania - Old Name",
        default="",
        help="To be completed manually with previous name of the company in case on change."
        "If the field in completed, when fetching the datas from ANAF website,"
        "if the name received is the old name set, than the partner will not be updated.",
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
        "cui": "-- codul fiscal --",
        "data": "-- data pentru care se efectueaza cautarea --",
        "denumire": "-- denumire --",
        "adresa": "-- adresa --",
        "nrRegCom": "-- numar de inmatriculare la Registrul Comertului --",
        "telefon": "-- Telefon --",
        "fax": "-- Fax --",
        "codPostal": "-- Codul Postal --",
        "act": "-- Act autorizare --",
        "stare_inregistrare": "-- Stare Societate --",
        "scpTVA": " -- true -pentru platitor in scopuri de tva / false in cazul in
                       care nu e platitor  in scopuri de TVA la data cautata  --",
        "data_inceput_ScpTVA": " -- Data înregistrării în scopuri de TVA anterioară --",
        "data_sfarsit_ScpTVA": " -- Data anulării înregistrării în scopuri de TVA --",
        "data_anul_imp_ScpTVA": "-- Data operarii anularii înregistrării în scopuri de TVA --",
        "mesaj_ScpTVA": "-- MESAJ:(ne)platitor de TVA la data cautata --",
        "dataInceputTvaInc": " -- Data de la care aplică sistemul TVA la încasare -- ",
        "dataSfarsitTvaInc": " -- Data până la care aplică sistemul TVA la încasare --",
        "dataActualizareTvaInc": "-- Data actualizarii --",
        "dataPublicareTvaInc": "-- Data publicarii --""
        "tipActTvaInc": " --Tip actualizare --",
        "statusTvaIncasare": " -- true -pentru platitor TVA la incasare/ false in
                               cazul in care nu e platitor de TVA la incasare la
                               data cautata --",
        "dataInactivare": " --     -- ",
        "dataReactivare": " --     -- ",
        "dataPublicare": " --     -- ",
        "dataRadiere": " -- Data radiere -- ",
        "statusInactivi": " -- true -pentru inactiv / false in cazul in care nu este
                               inactiv la data cautata -- ",
        "dataInceputSplitTVA": "--     --",
        "dataAnulareSplitTVA": "--     --",
        "statusSplitTVA": "-- true -aplica plata defalcata a Tva / false - nu aplica
                             plata defalcata a Tva la data cautata  --",
        "iban": "-- contul IBAN --",
        "statusRO_e_Factura": "-- true - figureaza in Registrul RO e-Factura / false
                             - nu figureaza in Registrul RO e-Factura la data cautata  --",
        "sdenumire_Strada": "-- Denumire strada sediu --",
        "snumar_Strada": "-- Numar strada sediu --",
        "sdenumire_Localitate": "-- Denumire localitate sediu --",
        "scod_Localitate": "-- Cod localitate sediu --",
        "sdenumire_Judet": "-- Denumire judet sediu --",
        "scod_Judet": "-- Cod judet sediu --",
        "stara": "-- Denumire tara sediu -- ",
        "sdetalii_Adresa": "-- Detalii adresa sediu --",
        "scod_Postal": "-- Cod postal sediu --",
        "ddenumire_Strada":  -- Denumire strada domiciliu fiscal --",
        "dnumar_Strada": "-- Numar strada domiciliu fiscal --",
        "ddenumire_Localitate": "-- Denumire localitate domiciliu fiscal --",
        "dcod_Localitate": "-- Cod localitate domiciliu fiscal --",
        "ddenumire_Judet": "-- Denumire judet domiciliu fiscal --",
        "dcod_Judet": "-- Cod judet domiciliu fiscal --",
        "dtara": "-- Denumire tara domiciliu fiscal --",
        "ddetalii_Adresa": "-- Detalii adresa domiciliu fiscal --",
        "dcod_Postal": "-- Cod postal domiciliu fiscal --",
        "data_inregistrare": "-- Data inregistrare -- ",
        "cod_CAEN": "-- Cod CAEN --",
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
        if (
            not result.get("denumire")
            or result["denumire"].upper() == self.l10n_ro_old_name
        ):
            # if no name means that anaf didn't return anything
            return {}
        res = {
            "name": result["denumire"].upper(),
            "l10n_ro_vat_subjected": result["scpTVA"],
            "company_type": "company",
        }

        result = self.get_result_address(result)
        result["vat"] = "%s%s" % (
            result.get("scpTVA", False) and "RO" or "",
            result.get("cui"),
        )
        if "city_id" in self._fields and result["state_id"] and result["city"]:
            domain = [
                ("state_id", "=", result["state_id"].id),
                ("name", "ilike", result["city"]),
            ]
            result["city_id"] = self.env["res.city"].search(domain, limit=1).id
        for field in AnafFiled_OdooField_Overwrite:
            if field[1] not in result:
                continue
            anaf_value = result.get(field[1], "")
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
        if result.get("adresa"):
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
            result["city"] = get_city(result.get("ddenumire_Localitate"))
            state_name = get_city(result.get("ddenumire_Judet"))
            if state_name:
                state = self.env["res.country.state"].search(
                    [("name", "=", state_name)],
                    limit=1,
                )
        result["state_id"] = state
        return result

    @api.onchange("vat", "country_id")
    def ro_vat_change(self):
        res = {}
        if self.is_l10n_ro_record:
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
                        res = self._update_l10n_ro_anaf_status(res, result)
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
            same_date_record = self.l10n_ro_active_anaf_line_ids.filtered(
                lambda r: str(r.date) == self.get_date_from_anaf(result.get("data", ""))
            )
            if not same_date_record and self.l10n_ro_active_anaf_line_ids:
                # Check if we have lines already added NewId
                for line in self.l10n_ro_active_anaf_line_ids:
                    if isinstance(line.id, models.NewId):
                        same_date_record = True
            if not same_date_record and not res.get("l10n_ro_active_anaf_line_ids"):
                res["l10n_ro_active_anaf_line_ids"] = [
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

    def _update_l10n_ro_anaf_scptva(self, res, result):
        self.ensure_one()
        if not res:
            res = {}
        if result:
            same_date_record = self.l10n_ro_vat_subjected_anaf_line_ids.filtered(
                lambda r: str(r.date) == self.get_date_from_anaf(result.get("data", ""))
            )
            if not same_date_record and self.l10n_ro_vat_subjected_anaf_line_ids:
                # Check if we have lines already added NewId
                for line in self.l10n_ro_vat_subjected_anaf_line_ids:
                    if isinstance(line.id, models.NewId):
                        same_date_record = True
            if not same_date_record and not res.get(
                "l10n_ro_vat_subjected_anaf_line_ids"
            ):
                res["l10n_ro_vat_subjected_anaf_line_ids"] = [
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
