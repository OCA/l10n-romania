# Copyright (C) 2024 Dorin Hongu <dhongu(@)gmail(.)com
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import io
import logging
import zipfile
from base64 import b64encode

import requests
from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
session = requests.Session()


class MessageSPV(models.Model):
    _name = "l10n.ro.message.spv"
    _description = "Message SPV"
    _order = "date desc"

    name = fields.Char(string="Message ID")  # id
    cif = fields.Char()  # cif
    message_type = fields.Selection(
        [
            ("in_invoice", "In Invoice"),
            ("out_invoice", "Out Invoice"),
            ("out_receipt", "Out Receipt"),
            ("in_receipt", "In Receipt"),
            ("message", "Message"),
            ("error", "Error"),
        ],
        string="Type",
    )  # tip
    date = fields.Datetime()  # data_creare
    invoice_date = fields.Date()  # data_factura
    details = fields.Char()  # detalii
    error = fields.Text()  # eroare
    message = fields.Text()  # mesaj
    request_id = fields.Char(string="Request ID")  # id_solicitare
    ref = fields.Char(string="Reference")  # referinta

    # campuri suplimentare

    invoice_id = fields.Many2one("account.move", string="Invoice")
    partner_id = fields.Many2one("res.partner", string="Partner")

    # draft - starea initiala a mesajului descarcat din SPV
    # downloaded - fisierul a fost descarcat cu succes
    # invoice - factura a fost creata cu succes
    # done - factura a fost creata si validata cu succes
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("downloaded", "Downloaded"),
            ("invoice", "Invoice"),
            ("error", "Error"),
            ("done", "Done"),
        ],
        default="draft",
    )
    file_name = fields.Char()
    attachment_id = fields.Many2one("ir.attachment", string="Attachment")
    attachment_xml_id = fields.Many2one("ir.attachment", string="XML")
    attachment_anaf_pdf_id = fields.Many2one("ir.attachment", string="ANAF PDF")
    attachment_embedded_pdf_id = fields.Many2one("ir.attachment", string="Embedded PDF")
    amount = fields.Monetary()
    invoice_amount = fields.Monetary()

    company_id = fields.Many2one(
        "res.company", "Company", default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id
    )

    _sql_constraints = [("unique_name", "unique(name)", "Message ID must be unique.")]

    @api.onchange("invoice_id", "invoice_id.state")
    def _onchange_invoice_id(self):
        for message in self:
            if message.invoice_id:
                if message.invoice_id.move_type in ("in_refund", "out_refund"):
                    message.invoice_amount = -1 * message.invoice_id.amount_total
                else:
                    message.invoice_amount = message.invoice_id.amount_total
                message.partner_id = message.invoice_id.commercial_partner_id
                if message.invoice_id.state == "posted":
                    message.state = "done"

    def download_from_spv(self):
        """Rutina de descarcare a fisierelor de la SPV"""
        session = requests.Session()

        for message in self.filtered(lambda m: not m.attachment_id):
            # anaf_config = message.company_id.sudo()._l10n_ro_get_anaf_sync(
            #     scope="e-factura"
            # )
            # if not anaf_config:
            #     raise UserError(_("ANAF configuration is missing."))

            # params = {"id": message.name}

            response = self.env["l10n_ro_edi.document"]._request_ciusro_download_zip(
                company=message.company_id,
                key_download=message.name,
                session=session,
            )

            error = response.get("error", "")

            if error:
                message.write({"error": error})
                continue
            if message.message_type == "message":
                info_message = message.check_anaf_message_xml(response["content"])
                message.write({"message": info_message})

            file_name = f"{message.request_id}.zip"
            attachment_value = {
                "name": file_name,
                "raw": response["content"],
                "mimetype": "application/zip",
            }
            attachment = self.env["ir.attachment"].sudo().create(attachment_value)

            if message.attachment_id:
                message.attachment_id.sudo().unlink()
            message.write({"file_name": file_name, "attachment_id": attachment.id})
            if message.state == "draft":
                message.state = "downloaded"

            message.get_xml_fom_zip()

    def get_xml_fom_zip(self):
        for message in self:
            attachment = message.attachment_id.sudo()
            if not attachment:
                continue
            zip_ref = zipfile.ZipFile(io.BytesIO(attachment.raw))
            xml_file = [f for f in zip_ref.namelist() if "semnatura" not in f]
            file_name = f"{message.request_id}.xml"
            if xml_file:
                file_name = xml_file[0]
                xml_bytes = zip_ref.open(file_name)
                # xml_file = zip_ref.read(file_name)
            if not xml_bytes:
                continue

            # xml_bytes = zip_ref.open(xml_file)
            recovering_parser = etree.XMLParser(recover=True)

            root = etree.parse(xml_bytes, parser=recovering_parser)

            xml_file = etree.tostring(
                root, pretty_print=True, xml_declaration=True, encoding="UTF-8"
            )
            attachment_value = {
                "name": file_name,
                "raw": xml_file,
                "mimetype": "application/xml",
            }
            attachment_xml = self.env["ir.attachment"].sudo().create(attachment_value)
            if message.attachment_xml_id:
                message.attachment_xml_id.sudo().unlink()

            xml_tree = etree.fromstring(xml_file, parser=recovering_parser)

            type_code_node = xml_tree.find("./{*}InvoiceTypeCode")
            if type_code_node is not None:
                type_code = type_code_node.text
                if type_code == "751":
                    if message.message_type == "in_invoice":
                        message.message_type = "in_receipt"
                    elif message.message_type == "out_invoice":
                        message.message_type = "out_receipt"

            ref_node = xml_tree.find("./{*}ID")
            ref = message.ref
            if ref_node is not None:
                ref = ref_node.text

            invoice_date_node = xml_tree.find("./{*}IssueDate")
            invoice_date = message.invoice_date
            if invoice_date_node is not None:
                invoice_date = invoice_date_node.text

            currency = message.currency_id
            currency_node = xml_tree.find("./{*}DocumentCurrencyCode")
            if currency_node is not None:
                currency_code = currency_node.text
                currency = self.env["res.currency"].search(
                    [("name", "=", currency_code)]
                )

            amount = False
            amount_note = xml_tree.find(
                ".//{*}LegalMonetaryTotal/{*}TaxInclusiveAmount"
            )

            if amount_note is not None:
                amount = float(amount_note.text)

            xml_tag_credit_note = (
                "{urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2}CreditNote"
            )  # noqa
            if xml_tree.tag == xml_tag_credit_note:
                amount = -1 * amount

            message.write(
                {
                    "attachment_xml_id": attachment_xml.id,
                    "ref": ref,
                    "amount": amount,
                    "invoice_date": invoice_date,
                    "currency_id": currency.id or message.currency_id.id,
                }
            )

    def _decode_xml(self, filename, content):
        to_process = []
        try:
            xml_tree = etree.fromstring(content)
        except Exception as e:
            _logger.exception("Error when converting the xml content to etree: %s" % e)
            return to_process
        if len(xml_tree):
            to_process.append(
                {
                    "filename": filename,
                    "content": content,
                    "type": "xml",
                    "xml_tree": xml_tree,
                }
            )
        return to_process

    def check_anaf_error_xml(self, zip_content):
        self.ensure_one()

        err_msg = ""
        try:
            zip_ref = zipfile.ZipFile(io.BytesIO(zip_content))
            err_file = [f for f in zip_ref.namelist() if f"{self.request_id}.xml" == f]
            if err_file:
                err_cont = zip_ref.read(err_file[0])
                decode_xml = self._decode_xml(err_file[0], err_cont)
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

    def check_anaf_message_xml(self, zip_content):
        self.ensure_one()
        info_msg = ""
        try:
            zip_ref = zipfile.ZipFile(io.BytesIO(zip_content))
            info_file = [f for f in zip_ref.namelist() if f"{self.request_id}.xml" == f]
            if info_file:
                message_cont = zip_ref.read(info_file[0])
                tree = etree.fromstring(message_cont)
                info_msg += tree.attrib.get("message")

        except Exception as e:
            _logger.warning(f"Error while checking the Zipped XML file: {e}")
        return info_msg

    def get_invoice_from_move(self):
        self.get_partner()

        messages_with_error = self.filtered(lambda m: m.message_type == "error")
        if messages_with_error:
            request_ids = messages_with_error.mapped("request_id")
            domain = [("key_loading", "in", request_ids)]
            edi_docs = self.env["l10n_ro_edi.document"].search(domain)
            for message in messages_with_error:
                edi_doc = edi_docs.filtered(
                    lambda e, m=message: e.key_loading == m.request_id
                )
                if not edi_doc:
                    continue
                message.write(
                    {
                        "invoice_id": edi_doc.invoice_id.id,
                    }
                )
                if not edi_doc.key_loading:
                    edi_doc.write(
                        {
                            "key_loading": message.request_id,
                            "state": "invoice_sent",
                        }
                    )
                domain = [
                    ("res_model", "=", "account.move"),
                    (
                        "res_field",
                        "in",
                        ["ubl_cii_xml_file", "invoice_pdf_report_file"],
                    ),
                    ("res_id", "=", edi_doc.invoice_id.id),
                ]
                attachments = self.env["ir.attachment"].sudo().search(domain)
                attachments.unlink()
                edi_doc.write(
                    {"state": "invoice_sending_failed", "message": message.error}
                )
                edi_doc.invoice_id.write({"l10n_ro_edi_state": False})

        messages = self.filtered(lambda m: not m.invoice_id)
        messages_without_invoice = messages.filtered(lambda m: not m.invoice_id)
        message_ids = messages_without_invoice.mapped("name")
        request_ids = messages_without_invoice.mapped("request_id")
        messages_without_invoice = self.filtered(lambda m: not m.invoice_id)
        invoices = self.env["account.move"].search(
            [
                "|",
                ("l10n_ro_edi_download", "in", message_ids),
                ("l10n_ro_edi_transaction", "in", request_ids),
            ]
        )
        messages_with_ref = messages_without_invoice.filtered(lambda m: m.ref)
        domain = [("name", "in", messages_with_ref.mapped("ref"))]
        invoices |= self.env["account.move"].search(domain)
        invoices = invoices.filtered(lambda i: i.state == "posted")
        for message in messages_without_invoice:
            invoice = invoices.filtered(
                lambda i, m=message: i.l10n_ro_edi_download == m.name
                or i.l10n_ro_edi_transaction == m.request_id
                or i.ref == m.ref
                or i.name == m.ref
            )
            if not invoice and message.ref:
                if message.message_type == "in_invoice":
                    move_type = ("in_invoice", "in_refund")
                else:
                    move_type = ("out_invoice", "out_refund")

                domain = [
                    ("commercial_partner_id", "=", message.partner_id.id),
                    ("ref", "=", message.ref),
                    ("move_type", "in", move_type),
                ]
                invoice = self.env["account.move"].search(domain, limit=1)

            if invoice:
                message.write({"invoice_id": invoice[0].id})

        self.get_data_from_invoice()

    def get_data_from_invoice(self):
        self.get_partner()
        for message in self:
            if not message.invoice_id:
                continue
            state = "invoice"
            if message.invoice_id.state == "posted":
                state = "done"

            if message.invoice_id.move_type in ("in_refund", "out_refund"):
                invoice_amount = -1 * message.invoice_id.amount_total
            else:
                invoice_amount = message.invoice_id.amount_total

            message.write(
                {
                    "partner_id": message.invoice_id.commercial_partner_id.id
                    or message.partner_id.id,
                    "invoice_amount": invoice_amount,
                    "state": state,
                    "invoice_date": message.invoice_id.invoice_date,
                }
            )
        for message in self:
            if message.invoice_id:
                attachments = self.env["ir.attachment"]
                attachments += message.attachment_id
                attachments += message.attachment_xml_id
                attachments += message.attachment_anaf_pdf_id
                attachments += message.attachment_embedded_pdf_id
                attachments.sudo().write(
                    {"res_id": message.invoice_id.id, "res_model": "account.move"}
                )

    def create_invoice(self):
        self.get_partner()
        for message in self.filtered(lambda m: not m.invoice_id):
            if message.message_type not in ("in_invoice", "in_receipt"):
                continue
            message.get_invoice_from_move()
            if message.invoice_id:
                continue

            move_obj = self.env["account.move"].with_company(message.company_id)
            invoice_values = {
                "name": "/",
                "ref": message.ref,
                "partner_id": message.partner_id.id,
                "l10n_ro_edi_download": message.name,
                "l10n_ro_edi_transaction": message.request_id,
            }
            if "extract_state" in move_obj._fields:
                invoice_values["extract_state"] = "no_extract_requested"
            new_invoice = move_obj.with_context(default_move_type="in_invoice").create(
                invoice_values
            )
            new_invoice = new_invoice.with_context(
                disable_onchange_name_predictive=True
            )
            try:
                new_invoice._extend_with_attachments(message.attachment_xml_id.sudo())
            except Exception as e:
                message.write({"state": "error", "error": str(e)})
                continue

            exist_invoice = move_obj.search(
                [
                    ("ref", "=", new_invoice.ref),
                    ("move_type", "in", ("in_invoice", "in_receipt")),
                    ("state", "=", "posted"),
                    (
                        "commercial_partner_id",
                        "=",
                        new_invoice.commercial_partner_id.id,
                    ),
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

            state = "invoice"

            message.write({"invoice_id": new_invoice.id, "state": state})

    def render_anaf_pdf(self):
        for message in self:
            if not message.attachment_id:
                continue
            if not message.attachment_xml_id:
                message.get_xml_fom_zip()

            xml_file = message.attachment_xml_id.sudo().raw
            headers = {"Content-Type": "text/plain"}
            xml = xml_file
            val1 = "FACT1"
            if b"<CreditNote" in xml:
                val1 = "FCN"
            val2 = "DA"

            res = requests.post(
                f"https://webservicesp.anaf.ro/prod/FCTEL/rest/transformare/{val1}/{val2}",
                data=xml,
                headers=headers,
                timeout=25,
            )
            if "The requested URL was rejected" in res.text:
                raise UserError(_("ANAF service unable to generate PDF from this XML."))

            if res.status_code == 200:
                pdf = b64encode(res.content)
                pdf = pdf + b"=" * (len(pdf) % 3)  # Fix incorrect padding
                file_name = f"{message.request_id}.pdf"

                attachment_value = {
                    "name": file_name,
                    "datas": pdf,
                    "type": "binary",
                    "mimetype": "application/pdf",
                }

                attachment_pdf = (
                    self.env["ir.attachment"].sudo().create(attachment_value)
                )
                if message.attachment_anaf_pdf_id:
                    message.attachment_anaf_pdf_id.sudo().unlink()
                message.write({"attachment_anaf_pdf_id": attachment_pdf.id})

    def get_embedded_pdf(self):
        for message in self:
            if not message.attachment_id:
                message.download_from_spv()
            if not message.attachment_xml_id:
                message.get_xml_fom_zip()

            xml_file = message.attachment_xml_id.sudo().raw
            xml_tree = etree.fromstring(xml_file)
            additional_docs = xml_tree.findall("./{*}AdditionalDocumentReference")  # noqa: B950
            for document in additional_docs:
                attachment_name = document.find("{*}ID")
                attachment_data = document.find(
                    "{*}Attachment/{*}EmbeddedDocumentBinaryObject"
                )
                if (
                    attachment_name is not None
                    and attachment_data is not None
                    and attachment_data.attrib.get("mimeCode") == "application/pdf"
                ):
                    text = attachment_data.text

                    name = (attachment_name.text or "invoice").split("\\")[-1].split(
                        "/"
                    )[-1].split(".")[0] + ".pdf"
                    attachment = (
                        self.env["ir.attachment"]
                        .sudo()
                        .create(
                            {
                                "name": name,
                                "datas": text
                                + "=" * (len(text) % 3),  # Fix incorrect padding
                                "type": "binary",
                                "mimetype": "application/pdf",
                            }
                        )
                    )
                    if message.attachment_embedded_pdf_id:
                        message.attachment_embedded_pdf_id.sudo().unlink()
                    message.write({"attachment_embedded_pdf_id": attachment.id})

    def action_download_attachment(self):
        self.ensure_one()
        return self._action_download(self.attachment_id.id)

    def action_download_xml(self):
        self.ensure_one()
        return self._action_download(self.attachment_xml_id.id)

    def action_download_anaf_pdf(self):
        self.ensure_one()
        return self._action_download(self.attachment_anaf_pdf_id.id)

    def action_download_embedded_pdf(self):
        self.ensure_one()
        return self._action_download(self.attachment_embedded_pdf_id.id)

    def _action_download(self, attachment_field_id):
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment_field_id}?download=true",
            "target": "self",
        }

    def get_partner(self):
        for message in self.filtered(lambda m: not m.partner_id):
            if message.cif:
                domain = [("vat", "like", message.cif), ("is_company", "=", True)]
                partner = self.env["res.partner"].search(domain, limit=1)
                if not partner:
                    partner = self.env["res.partner"].create(
                        {
                            "name": message.cif,
                            "vat": message.cif,
                            "is_company": True,
                        }
                    )
                message.write({"partner_id": partner.id})

    def refresh(self):
        self.env.company._l10n_ro_download_message_spv(no_days=1)

    def show_invoice(self):
        invoices = self.mapped("invoice_id")
        action = {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "tree",
            "views": [(False, "list"), (False, "form")],
            "domain": [("id", "in", invoices.ids)],
        }

        return action
