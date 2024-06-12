# Copyright (C) 2024 Dorin Hongu <dhongu(@)gmail(.)com
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import io
import logging
import zipfile

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MessageSPV(models.Model):
    _name = "l10n.ro.message.spv"
    _description = "Message SPV"

    name = fields.Char(string="Message ID")  # id
    cif = fields.Char(string="CIF")  # cif
    message_type = fields.Selection(
        [
            ("in_invoice", "In Invoice"),
            ("out_invoice", "Out Invoice"),
            ("error", "Error"),
        ],
        string="Type",
    )  # tip
    date = fields.Datetime(string="Date")  # data_creare
    details = fields.Char(string="Details")  # detalii
    error = fields.Text(string="Error")  # eroare
    request_id = fields.Char(string="Request ID")  # id_solicitare

    # campuri suplimentare
    company_id = fields.Many2one("res.company", string="Company")
    invoice_id = fields.Many2one("account.move", string="Invoice")
    partner_id = fields.Many2one("res.partner", string="Partner")

    state = fields.Selection(
        [("draft", "Draft"), ("downloaded", "Downloaded"), ("done", "Done")],
        string="State",
        default="draft",
    )
    file_name = fields.Char(string="File Name")
    attachment_id = fields.Many2one("ir.attachment", string="Attachment")

    def download_from_spv(self):
        for message in self:
            anaf_config = message.company_id.sudo()._l10n_ro_get_anaf_sync(
                scope="e-factura"
            )
            if not anaf_config:
                raise UserError(_("ANAF configuration is missing."))

            params = {"id": message.name}
            response, status_code = anaf_config._l10n_ro_einvoice_call(
                "/descarcare", params, method="GET"
            )
            error = ""
            if type(response) == dict:
                error = response.get("eroare", "")
            if status_code == "400":
                error = response.get("message")
            elif status_code == 200 and type(response) == dict:
                error = response.get("eroare")
            if not error:
                error = message.l10n_ro_check_anaf_error_xml(response)
            if error:
                message.write({"error": error})
                continue

            file_name = f"{message.name}.zip"
            attachment = (
                self.env["ir.attachment"]
                .sudo()
                .create(
                    {
                        "name": file_name,
                        "raw": response,
                        "mimetype": "application/zip",
                    }
                )
            )
            message.write({"file_name": file_name, "attachment_id": attachment.id})
            if message.state == "draft":
                message.state = "downloaded"

    def l10n_ro_check_anaf_error_xml(self, zip_content):
        self.ensure_one()
        cius_ro = self.env.ref("l10n_ro_account_edi_ubl.edi_ubl_cius_ro")
        err_msg = ""
        try:
            zip_ref = zipfile.ZipFile(io.BytesIO(zip_content))
            err_file = [f for f in zip_ref.namelist() if f"{self.request_id}.xml" == f]
            if err_file:
                err_cont = zip_ref.read(err_file[0])
                decode_xml = cius_ro._decode_xml(err_file[0], err_cont)
                if not decode_xml:
                    return err_msg
                tree = decode_xml[0]["xml_tree"]
                error_tag = "Error"
                for _index, err in enumerate(tree.findall("./{*}" + error_tag)):
                    err_msg += f"{err.attrib.get('errorMessage')}<br/>"
                if err_msg:
                    err_msg = "Erori validare ANAF:<br/>" + err_msg
                    return err_msg
        except Exception as e:
            _logger.warning(f"Error while checking the Zipped XML file: {e}")
        return err_msg

    def get_invoice_from_move(self):
        messages_without_invoice = self.filtered(lambda m: not m.invoice_id)
        message_ids = messages_without_invoice.mapped("name")
        request_ids = messages_without_invoice.mapped("request_id")
        invoices = self.env["account.move"].search(
            [
                "|",
                ("l10n_ro_edi_download", "in", message_ids),
                ("l10n_ro_edi_transaction", "in", request_ids),
            ]
        )
        for message in self:
            invoice = invoices.filtered(
                lambda i: i.l10n_ro_edi_download == message.name
                or i.l10n_ro_edi_transaction == message.request_id
            )
            if invoice:
                message.write(
                    {
                        "invoice_id": invoice.id,
                        "partner_id": invoice.commercial_partner_id.id,
                    }
                )
                if invoice.edi_state == "sent":
                    message.state = "done"

    def create_invoice(self):
        for message in self:
            if message.message_type == "out_invoice":
                self.get_invoice_from_move()
            if not message.message_type == "in_invoice":
                continue

            move_obj = self.env["account.move"].with_company(message.company_id)
            new_invoice = move_obj.with_context(default_move_type="in_invoice").create(
                {
                    "name": "/",
                    "l10n_ro_edi_download": message.name,
                    "l10n_ro_edi_transaction": message.request_id,
                }
            )
            new_invoice = new_invoice._l10n_ro_prepare_invoice_for_download()
            try:
                new_invoice.l10n_ro_download_zip_anaf(
                    message.company_id._l10n_ro_get_anaf_sync(scope="e-factura")
                )
            except Exception as e:
                new_invoice.message_post(
                    body=_("Error downloading e-invoice: %s") % str(e)
                )

            exist_invoice = move_obj.search(
                [
                    ("ref", "=", new_invoice.ref),
                    ("move_type", "=", "in_invoice"),
                    ("state", "=", "posted"),
                    ("partner_id", "=", new_invoice.partner_id.id),
                    ("id", "!=", new_invoice.id),
                ],
                limit=1,
            )
            if exist_invoice:
                domain = [
                    ("res_model", "=", "account.move"),
                    ("res_id", "=", new_invoice.id),
                ]
                attachments = self.env["ir.attachment"].sudo().search(domain)
                attachments.write({"res_id": exist_invoice.id})
                new_invoice.unlink()
                exist_invoice.write(
                    {
                        "l10n_ro_edi_download": message.name,
                        "l10n_ro_edi_transaction": message.request_id,
                    }
                )
                new_invoice = exist_invoice

            message.write({"invoice_id": new_invoice.id})
