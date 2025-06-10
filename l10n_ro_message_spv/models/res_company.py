# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
import re
from datetime import datetime

import pytz

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ro_download_einvoices_days = fields.Integer(
        string="Maximum number of days to download e-invoices.", default=60
    )

    def l10n_ro_download_message_spv(self):
        # method to be used in cron job to auto download e-invoices from ANAF
        domain = [("l10n_ro_edi_access_token", "!=", False)]
        ro_companies = self or self.env["res.company"].sudo().search(domain)
        return ro_companies._l10n_ro_download_message_spv()

    def _l10n_ro_get_partner_from_cif(self, cif):
        self.ensure_one()
        company_id = self.id
        domain = [
            ("vat", "like", cif),
            ("is_company", "=", True),
            ("company_id", "=", company_id),
        ]
        partner = self.env["res.partner"].search(domain, limit=1)
        if not partner:
            domain = [("vat", "like", cif), ("is_company", "=", True)]
            partner = self.env["res.partner"].search(domain, limit=1)
        if not partner:
            domain = [("vat", "like", cif)]
            partner = self.env["res.partner"].search(domain, limit=1)
        if not partner:
            partner = self.env["res.partner"].create(
                {
                    "name": "Unknown",
                    "vat": cif,
                    "company_id": company_id,
                    "country_id": self.env.ref("base.ro").id,
                    "is_company": True,
                }
            )
        return partner

    def _l10n_ro_download_message_spv(self, no_days=0, download_zip=True):
        pattern_in = r"cif_emitent=(\d+)"
        pattern_out = r"cif_beneficiar=(\d+)"

        romania_tz = pytz.timezone("Europe/Bucharest")
        obj_message_spv = self.env["l10n.ro.message.spv"]
        obj_edi_document = self.env["l10n_ro_edi.document"]

        for company in self:
            # stergere erorile vechi
            domain = [("company_id", "=", company.id), ("message_type", "=", "error")]
            error_messages = obj_message_spv.with_company(company).search(domain)
            error_messages.unlink()
            days = no_days or company.l10n_ro_download_einvoices_days or no_days
            # company_messages = company._l10n_ro_get_anaf_efactura_messages()
            company_messages = obj_edi_document._request_ciusro_download_messages_spv(
                company, no_days=days
            )
            message_spv_obj = obj_message_spv.with_company(company).sudo()

            for message in company_messages:
                domain = [("name", "=", message["id"])]
                if not message_spv_obj.search(domain, limit=1):
                    date = datetime.strptime(message.get("data_creare"), "%Y%m%d%H%M")
                    localized_date = romania_tz.localize(date)
                    # Convertim data și ora la GMT
                    gmt_tz = pytz.timezone("GMT")
                    gmt_date = localized_date.astimezone(gmt_tz)
                    partner = self.env["res.partner"]
                    cif = message["cif"]
                    message_type = False
                    if message["tip"] == "FACTURA PRIMITA":
                        message_type = "in_invoice"
                        match = re.search(pattern_in, message["detalii"])
                        if match:
                            cif = match.group(1)
                            partner = company._l10n_ro_get_partner_from_cif(cif)

                    elif message["tip"] == "FACTURA TRIMISA":
                        message_type = "out_invoice"
                        match = re.search(pattern_out, message["detalii"])
                        if match:
                            cif = match.group(1)
                            partner = company._l10n_ro_get_partner_from_cif(cif)
                    elif message["tip"] == "ERORI FACTURA":
                        message_type = "error"
                    elif "MESAJ" in message["tip"]:
                        message_type = "message"
                    else:
                        _logger.error("Unknown message type: %s", message["tip"])

                    spv_message = message_spv_obj.create(
                        {
                            "name": message["id"],
                            "cif": cif,
                            "message_type": message_type,
                            "date": gmt_date.strftime("%Y-%m-%d %H:%M:%S"),
                            "details": message["detalii"],
                            "request_id": message["id_solicitare"],
                            "company_id": company.id,
                            "partner_id": partner.id,
                            "state": "draft",
                        }
                    )
                    if download_zip:
                        try:
                            spv_message.download_from_spv()
                            if spv_message.message_type in ["error", "message"]:
                                spv_message.get_invoice_from_move()
                        except Exception as e:
                            _logger.info(str(e))

        return True
