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

    l10n_ro_e_transport_operation_type_id = fields.Many2one(
        "l10n.ro.e.transport.operation",
        string="Operation type",
        default=lambda self: self.env.ref(
            "l10n_ro_etransport.operation_30", raise_if_not_found=False
        ),
    )

    l10n_ro_e_transport_scope_id = fields.Many2one(
        "l10n.ro.e.transport.scope", string="Scope"
    )

    l10n_ro_e_transport_customs_id = fields.Many2one(
        "l10n.ro.e.transport.customs", string="Border crossing point"
    )

    l10n_ro_vehicle = fields.Char(string="Vehicle")

    def _export_e_transport(self):
        def get_country_code(country_code):
            if country_code == "GR":
                country_code = "EL"
            return country_code

        def get_instastat_code(product):
            intrastat_code = "00000000"  # 08031010
            if "hs_code" in product._fields:
                intrastat_code = product.hs_code or intrastat_code
            if "intrastat_code_id" in product._fields:
                intrastat_code = product.intrastat_code_id.code or intrastat_code

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
        View = self.env["ir.ui.view"].sudo()
        xml_content = View._render_template(
            "l10n_ro_etransport.e_transport", render_values
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
            raise UserError(message)

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
            anaf_config = self.company_id._l10n_ro_get_anaf_sync(scope="e-transport")
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

            if stare == "ok":
                self.write({"l10n_ro_e_transport_status": stare})
            if stare == "nok":
                errors = content.get("Errors", [])
                error_message = "".join(
                    [error.get("errorMessage", "") for error in errors]
                )
                message = _("The document is not ok. Errors: %s") % error_message
                self.write(
                    {
                        "l10n_ro_e_transport_status": "nok",
                        "l10n_ro_e_transport_message": message,
                    }
                )
            if stare == "in prelucrare":
                message = _("The document was in processing at %s.") % content.get(
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

        anaf_config = self.company_id._l10n_ro_get_anaf_sync(scope="e-transport")
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

        message = _("The document was uploaded successfully, check the status.")
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
