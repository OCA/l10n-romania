# ©  2023 Deltatech
# See README.rst file on addons root folder for license details

import logging

import markupsafe
from lxml import etree

from odoo import _, api, fields, models
from odoo.modules.module import get_module_resource

_logger = logging.getLogger(__name__)


# cod	Semnificatie	tarajudet	țara	nume	codjudet
# 1	Alba	RO_AB	ro	Alba	AB	ADEVĂRAT
# 2	Arad	RO_AR	ro	Arad	AR	ADEVĂRAT
# 3	Argeș	RO_AG	ro	Argeș	AG	ADEVĂRAT
# 4	Bacău	RO_BC	ro	Bacău	BC	ADEVĂRAT
# 5	Bihor	RO_BH	ro	Bihor	BH	ADEVĂRAT
# 6	Bistrița-Năsăud	RO_BN	ro	Bistrița-Năsăud	BN	ADEVĂRAT
# 7	Botoșani	RO_BT	ro	Botoșani	BT	ADEVĂRAT
# 8	Brașov	RO_BV	ro	Brașov	BV	ADEVĂRAT
# 9	Brăila	RO_BR	ro	Brăila	BR	ADEVĂRAT
# 10	Buzău	RO_BZ	ro	Buzău	BZ	ADEVĂRAT
# 11	Caraș-Severin	RO_CS	ro	Caraș Severin	CS	FALS
# 12	Cluj	RO_CJ	ro	Cluj	CJ	ADEVĂRAT
# 13	Constanța	RO_CT	ro	Constanța	CT	ADEVĂRAT
# 14	Covasna	RO_CV	ro	Covasna	CV	ADEVĂRAT
# 15	Dâmbovița	RO_DB	ro	Dâmbovița	DB	ADEVĂRAT
# 16	Dolj	RO_DJ	ro	Dolj	DJ	ADEVĂRAT
# 17	Galați	RO_GL	ro	Galați	GL	ADEVĂRAT
# 18	Gorj	RO_GJ	ro	Gorj	GJ	ADEVĂRAT
# 19	Harghita	RO_HR	ro	Harghita	HR	ADEVĂRAT
# 20	Hunedoara	RO_HD	ro	Hunedoara	HD	ADEVĂRAT
# 21	Ialomița	RO_IL	ro	Ialomița	IL	ADEVĂRAT
# 22	Iași	RO_IS	ro	Iași	IS	ADEVĂRAT
# 23	Ilfov	RO_IF	ro	Ilfov	IF	ADEVĂRAT
# 24	Maramureș	RO_MM	ro	Maramureș	MM	ADEVĂRAT
# 25	Mehedinți	RO_MH	ro	Mehedinți	MH	ADEVĂRAT
# 26	Mureș	RO_MS	ro	Mureș	MS	ADEVĂRAT
# 27	Neamț	RO_NT	ro	Neamț	NT	ADEVĂRAT
# 28	Olt	RO_OT	ro	Olt	OT	ADEVĂRAT
# 29	Prahova	RO_PH	ro	Prahova	PH	ADEVĂRAT
# 30	Satu Mare	RO_SM	ro	Satu Mare	SM	ADEVĂRAT
# 31	Sălaj	RO_SJ	ro	Sălaj	SJ	ADEVĂRAT
# 32	Sibiu	RO_SB	ro	Sibiu	SB	ADEVĂRAT
# 33	Suceava	RO_SV	ro	Suceava	SV	ADEVĂRAT
# 34	Teleorman	RO_TR	ro	Teleorman	TR	ADEVĂRAT
# 35	Timiș	RO_TM	ro	Timiș	TM	ADEVĂRAT
# 36	Tulcea	RO_TL	ro	Tulcea	TL	ADEVĂRAT
# 37	Vaslui	RO_VS	ro	Vaslui	VS	ADEVĂRAT
# 38	Vâlcea	RO_VL	ro	Vâlcea	VL	ADEVĂRAT
# 39	Vrancea	RO_VN	ro	Vrancea	VN	ADEVĂRAT
# 40	București	RO_B	ro	București	B	ADEVĂRAT
# 51	Călărași	RO_CL	ro	Călărași	CL	ADEVĂRAT
# 52	Giurgiu	RO_GR	ro	Giurgiu	GR	ADEVĂRAT

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

    l10n_ro_e_transport_uit = fields.Char(string="UIT")
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

        xml_doc = etree.fromstring(xml_content)
        schema_file_path = get_module_resource(
            "l10n_ro_etransport", "static/schemas", "eTransport.xsd"
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
