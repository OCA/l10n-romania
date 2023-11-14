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

    l10n_ro_e_transport_uit = fields.Char(string="UIT", readonly=True)
    l10n_ro_vehicle = fields.Char(string="Vehicle")

    def _export_e_transport(self):
        self.ensure_one()
        # Create file content.
        xml_declaration = markupsafe.Markup("<?xml version='1.0' encoding='UTF-8'?>\n")

        render_values = {
            "doc": self,
            "company": self.company_id,
            "STATE_CODES": STATE_CODES,
        }
        xml_content = self.env.ref("l10n_ro_etransport.e_transport")._render(
            render_values
        )
        xml_name = "%s_e_transport.xml" % (self.name.replace("/", "_"))
        xml_content = xml_declaration + xml_content

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
        attachment = self._export_e_transport()
        self._export_e_transport_data(attachment.raw)
        action = self.env["ir.attachment"].action_get()
        action.update(
            {"res_id": attachment.id, "views": False, "view_mode": "form,tree"}
        )
        return action

    @api.model
    def _export_e_transport_data(self, data):
        anaf_config = self.company_id.l10n_ro_account_anaf_sync_id
        params = {}
        standard = "ETRANSP"
        cif = self.company_id.partner_id.vat.replace("RO", "")

        func = f"/upload/{standard}/{cif}/2"
        content, status_code = anaf_config._l10n_ro_etransport_call(func, params, data)
        if status_code != 200:
            raise UserError(_("Error %s") % status_code)

        errors = content.get("Errors", [])
        error_message = "".join([error.get("errorMessage", "") for error in errors])
        if error_message:
            raise UserError(error_message)

        _logger.info(content)
        _logger.info(status_code)
