# ©  2023 Deltatech
# See README.rst file on addons root folder for license details

import logging

import markupsafe
from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.modules.module import get_module_resource

_logger = logging.getLogger(__name__)


STATE_CODES = {
    "AB": "1",
    "AR": "2",
    "AG": "3",
    "BC": "4",
    "BH": "5",
    "BN": "6",
    "BT": "7",
    "BV": "8",
    "BR": "9",
    "BZ": "10",
    "CS": "11",
    "CJ": "12",
    "CT": "13",
    "CV": "14",
    "DB": "15",
    "DJ": "16",
    "GL": "17",
    "GJ": "18",
    "HR": "19",
    "HD": "20",
    "IL": "21",
    "IS": "22",
    "IF": "23",
    "MM": "24",
    "MH": "25",
    "MS": "26",
    "NT": "27",
    "OT": "28",
    "PH": "29",
    "SM": "30",
    "SJ": "31",
    "SB": "32",
    "SV": "33",
    "TR": "34",
    "TM": "35",
    "TL": "36",
    "VS": "37",
    "VL": "38",
    "VN": "39",
    "B": "40",
    "CL": "51",
    "GR": "52",
}
TIP_OPERATIE = [
    ("10", "Achiziţie intracomunitară"),
    ("12", "Operaţiuni în sistem lohn (UE) - intrare"),
    ("14", "Stocuri la dispoziţia clientului (Call-off stock) - intrare"),
    ("20", "Livrare intracomunitară"),
    ("22", "Operaţiuni în sistem lohn (UE) - ieşire"),
    ("24", "Stocuri la dispoziţia clientului (Call-off stock) - ieşire"),
    ("30", "Transport pe teritoriul naţional"),
    ("40", "Import"),
    ("50", "Export"),
    ("60", "Tranzacţie intracomunitară - Intrare pentru depozitare"),
    ("70", "Tranzacţie intracomunitară - Ieşire după depozitare"),
]


class StockPicking(models.Model):
    _inherit = "stock.picking"

    l10n_ro_e_transport_uit = fields.Char(string="UIT", copy=False)
    l10n_ro_e_transport_status = fields.Selection(
        [
            ("draft", "Draft"),
            ("sent", "Sent"),
            ("ok", "Ok"),
            ("nok", "Not OK"),
            ("in_processing", "In processing"),
        ],
        default="draft",
    )
    l10n_ro_e_transport_download = fields.Char(
        "ID Download ANAF ",
        copy=False,
    )
    l10n_ro_e_transport_message = fields.Text("ANAF Message")

    l10n_ro_e_transport_tip_operatie = fields.Selection(
        TIP_OPERATIE,
        string="Tip operatie",
        default="30",
    )

    l10n_ro_e_transport_scop = fields.Selection(
        [
            ("101", "Comercializare"),
            ("201", "Producție"),
            ("301", "Gratuități"),
            ("401", "Echipament comercial"),
            ("501", "Mijloace fixe"),
            ("601", "Consum propriu"),
            ("703", "Operațiuni de livrare cu instalare"),
            ("704", "Transfer între gestiuni"),
            ("705", "Bunuri puse la dispoziția clientului"),
            ("801", "Leasing financiar/operațional"),
            ("802", "Bunuri în garanție"),
            ("901", "Operațiuni scutite"),
            ("1001", "Investiție în curs"),
            ("1101", "Donații, ajutoare"),
            ("9901", "Altele"),
            ("9999", "Același cu operațiunea"),
        ],
        default="101",
        string="Scop",
    )

    l10n_ro_e_transport_vama = fields.Selection(
        [
            ("1", "Petea (HU)"),
            ("2", "Borș(HU)"),
            ("3", "Vărșand(HU)"),
            ("4", "Nădlac(HU)"),
            ("5", "Calafat (BG)"),
            ("6", "Bechet(BG)"),
            ("7", "Turnu Măgurele(BG)"),
            ("8", "Zimnicea(BG)"),
            ("9", "Giurgiu(BG)"),
            ("10", "Ostrov(BG)"),
            ("11", "Negru Vodă(BG)"),
            ("12", "Vama Veche(BG)"),
            ("13", "Călărași(BG)"),
            ("14", "Corabia(BG)"),
            ("15", "Oltenița(BG)"),
            ("16", "Carei  (HU)"),
            ("17", "Cenad (HU)"),
            ("18", "Episcopia Bihor (HU)"),
            ("19", "Salonta (HU)"),
            ("20", "Săcuieni (HU)"),
            ("21", "Turnu (HU)"),
            ("22", "Urziceni (HU)"),
            ("23", "Valea lui Mihai (HU)"),
            ("24", "Vladimirescu (HU)"),
            ("25", "Porțile de Fier 1 (RS)"),
            ("26", "Naidăș(RS)"),
            ("27", "Stamora Moravița(RS)"),
            ("28", "Jimbolia(RS)"),
            ("29", "Halmeu (UA)"),
            ("30", "Stânca Costești (MD)"),
            ("31", "Sculeni(MD)"),
            ("32", "Albița(MD)"),
            ("33", "Oancea(MD)"),
            ("34", "Galați Giurgiulești(MD)"),
            ("35", "Constanța Sud Agigea"),
            ("36", "Siret  (UA)"),
            ("37", "Nădlac 2 - A1 (HU)"),
            ("38", "Borș 2 - A3 (HU)"),
        ],
        string="Punct trece vamala",
    )

    l10n_ro_vehicle = fields.Char(string="Vehicle")

    def _export_e_transport(self):
        def get_country_code(country_code):
            if country_code == "GR":
                country_code = "EL"
            return country_code

        def get_instastat_code(product):
            intrastat_code = False
            if "intrastat_id" in product._fields:
                intrastat_code = product.intrastat_id.code
            else:
                _logger.warning(
                    "Product %s does not have intrastat_id field", product.name
                )
                intrastat_code = "00000000"  # 08031010
            return intrastat_code

        self.ensure_one()
        # Create file content.
        xml_declaration = markupsafe.Markup("<?xml version='1.0' encoding='UTF-8'?>\n")

        render_values = {
            "doc": self,
            "company": self.company_id,
            "STATE_CODES": STATE_CODES,
            "get_country_code": get_country_code,
            "get_instastat_code": get_instastat_code,
        }
        xml_content = self.env.ref("l10n_ro_etransport.e_transport")._render(
            render_values
        )
        xml_name = "%s_e_transport.xml" % (self.name.replace("/", "_"))
        xml_content = xml_declaration + xml_content

        _logger.info(xml_content)
        xml_doc = etree.fromstring(xml_content.encode())
        schema_file_path = get_module_resource(
            "l10n_ro_etransport", "static/schemas", "eTransport.xsd"
        )
        xml_schema = etree.XMLSchema(etree.parse(open(schema_file_path)))

        is_valid = xml_schema.validate(xml_doc)

        if not is_valid:
            message = _("Validation Error: %s") % xml_schema.error_log.last_error
            _logger.error(message)

        domain = [
            ("name", "=", xml_name),
            ("res_model", "=", "stock.picking"),
            ("res_id", "=", self.id),
        ]
        attachments = self.env["ir.attachment"].search(domain)
        attachments.unlink()

        return self.env["ir.attachment"].create(
            {
                "name": xml_name,
                "raw": xml_content,
                "res_model": "stock.picking",
                "res_id": self.id,
                "mimetype": "application/xml",
            }
        )

    def export_e_transport_button(self):
        if self.l10n_ro_e_transport_status in ["draft", "nok"]:
            attachment = self._export_e_transport()
            self._export_e_transport_data(attachment.raw)
        elif self.l10n_ro_e_transport_status in ["sent", "in_processing"]:
            anaf_config = self.company_id.l10n_ro_account_anaf_sync_id
            params = {}
            func = f"/stareMesaj/{self.l10n_ro_e_transport_download}"
            content, status_code = anaf_config._l10n_ro_etransport_call(
                func, params, method="GET"
            )
            if status_code != 200:
                raise UserError(
                    _("Error %(status_code)s:%(content)s")
                    % {"status_code": status_code, "content": content}
                )
            _logger.info(content)
            stare = content.get("stare")

            if stare in ["ok", "nok"]:
                self.write({"l10n_ro_e_transport_status": stare})
            if stare == "in prelucrare":
                message = "Documentul UIT la data %s era in prelucrare." % content.get(
                    "dateResponse"
                )
                self.write(
                    {
                        "l10n_ro_e_transport_status": "in_processing",
                        "l10n_ro_e_transport_message": message,
                    }
                )

    @api.model
    def _export_e_transport_data(self, data):
        anaf_config = self.company_id.l10n_ro_account_anaf_sync_id
        params = {}
        standard = "ETRANSP"
        cif = self.company_id.partner_id.vat.replace("RO", "")

        func = f"/upload/{standard}/{cif}/2"
        content, status_code = anaf_config._l10n_ro_etransport_call(func, params, data)
        if status_code != 200:
            raise UserError(
                _("Error %(status_code)s:%(content)s")
                % {"status_code": status_code, "content": content}
            )

        errors = content.get("Errors", [])
        error_message = "".join([error.get("errorMessage", "") for error in errors])
        if error_message:
            raise UserError(error_message)

        message = "Documentul a fost incarcat cu succes, verificati starea."

        self.write(
            {
                "l10n_ro_e_transport_uit": content.get("UIT"),
                "l10n_ro_e_transport_status": "sent",
                "l10n_ro_e_transport_download": content.get("index_incarcare"),
                "l10n_ro_e_transport_message": message,
            }
        )

        _logger.info(content)
        _logger.info(status_code)
