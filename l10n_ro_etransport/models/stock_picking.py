# ©  2023 Deltatech
# See README.rst file on addons root folder for license details

import logging

import markupsafe
from lxml import etree

from odoo import _, api, fields, models
from odoo.modules.module import get_module_resource

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    l10n_ro_e_transport_uit = fields.Char(string="UIT")

    def _export_e_transport(self):
        self.ensure_one()
        # Create file content.
        xml_declaration = markupsafe.Markup("<?xml version='1.0' encoding='UTF-8'?>\n")

        render_values = {
            "doc": self,
            "company": self.company_id,
        }
        xml_content = self.env.ref("l10n_ro_etransport.e_transport")._render(
            render_values
        )
        xml_name = "%s_e_transport.xml" % (self.name.replace("/", "_"))

        xml_doc = etree.fromstring(xml_content)
        schema_file_path = get_module_resource(
            "l10n_ro_etransport", "static/schemas", "schema.xsd"
        )
        xml_schema = etree.XMLSchema(etree.parse(open(schema_file_path)))

        is_valid = xml_schema.validate(xml_doc)

        if not is_valid:
            message = _("Validation Error: %s") % xml_schema.error_log.last_error
            _logger.error(message)

        xml_content = xml_declaration + xml_content
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
                "raw": xml_content.encode(),
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
        self.env["ir.config_parameter"].sudo().get_param
