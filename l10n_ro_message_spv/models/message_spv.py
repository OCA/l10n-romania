# Copyright (C) 2024 Dorin Hongu <dhongu(@)gmail(.)com
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import io
import logging
import re
import zipfile
from base64 import b64decode

import requests
from lxml import etree

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
session = requests.Session()


class MessageSPV(models.Model):
    _name = "l10n.ro.message.spv"
    _description = "Message SPV"
    _order = "date desc"
    _check_company_auto = True

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

    invoice_id = fields.Many2one("account.move", string="Invoice", check_company=True)
    partner_id = fields.Many2one("res.partner", string="Partner", check_company=True)

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
    download_attempts = fields.Integer(default=0)
    last_download_date = fields.Date()
    file_name = fields.Char()
    attachment_id = fields.Many2one(
        "ir.attachment", string="Attachment", check_company=True
    )
    # The signed ANAF ZIP (attachment_id) is the only stored file. The XML
    # and the PDFs are derived from it on demand; these fields only expose
    # what was materialized on the invoice (the XML import source and the
    # embedded PDF preview).
    # They are computed and not stored, so they carry no `check_company`:
    # nothing is written through them, and their company consistency is
    # already guaranteed by `invoice_id` (they can only point to attachments
    # of that invoice, which is itself company-checked).
    attachment_xml_id = fields.Many2one(
        "ir.attachment", string="XML", compute="_compute_derived_attachments"
    )
    attachment_anaf_pdf_id = fields.Many2one(
        "ir.attachment", string="ANAF PDF", compute="_compute_derived_attachments"
    )
    attachment_embedded_pdf_id = fields.Many2one(
        "ir.attachment",
        string="Embedded PDF",
        compute="_compute_derived_attachments",
    )
    amount = fields.Monetary()
    invoice_amount = fields.Monetary()

    company_id = fields.Many2one(
        "res.company", "Company", default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id
    )

    _unique_name = models.Constraint(
        "unique(name)",
        "Message ID must be unique.",
    )

    @api.onchange("invoice_id")
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

    @api.depends("invoice_id", "request_id")
    def _compute_derived_attachments(self):
        attachment_obj = self.env["ir.attachment"].sudo()
        for message in self:
            xml = anaf_pdf = embedded_pdf = attachment_obj.browse()
            if message.invoice_id and message.request_id:
                # The UBL import moves the source XML into the invoice's
                # ubl_cii_xml_file binary field, so include res_field
                # attachments in the search (they are filtered out by
                # default).
                attachments = attachment_obj.search(
                    [
                        ("res_model", "=", "account.move"),
                        ("res_id", "=", message.invoice_id.id),
                        "|",
                        ("res_field", "=", False),
                        ("res_field", "=", "ubl_cii_xml_file"),
                    ]
                )
                xml_name = f"{message.request_id}.xml"
                pdf_name = f"{message.request_id}.pdf"
                xml = attachments.filtered(lambda a, n=xml_name: a.name == n)[:1]
                anaf_pdf = attachments.filtered(lambda a, n=pdf_name: a.name == n)[:1]
                embedded_pdf = attachments.filtered(
                    lambda a, n=pdf_name: a.mimetype == "application/pdf"
                    and a.name != n
                    and "Generated by Odoo" not in a.name
                )[:1]
            message.attachment_xml_id = xml
            message.attachment_anaf_pdf_id = anaf_pdf
            message.attachment_embedded_pdf_id = embedded_pdf

    def _get_xml_bytes(self):
        """Extract the invoice XML from the stored ZIP, in memory.

        Returns a (file_name, xml_bytes) tuple, or (False, False) when the
        ZIP is missing or holds no invoice XML.
        """
        self.ensure_one()
        attachment = self.attachment_id.sudo()
        if not attachment:
            return False, False
        try:
            zip_ref = zipfile.ZipFile(io.BytesIO(attachment.raw))
        except zipfile.BadZipFile:
            return False, False
        xml_files = [f for f in zip_ref.namelist() if "semnatura" not in f]
        if not xml_files:
            return False, False
        file_name = xml_files[0]
        recovering_parser = etree.XMLParser(recover=True)
        root = etree.parse(zip_ref.open(file_name), parser=recovering_parser)
        xml_bytes = etree.tostring(
            root, pretty_print=True, xml_declaration=True, encoding="UTF-8"
        )
        return file_name, xml_bytes

    def _extract_embedded_pdf(self, xml_bytes):
        """Return (name, base64 datas) of the PDF embedded in the XML."""
        self.ensure_one()
        recovering_parser = etree.XMLParser(recover=True)
        xml_tree = etree.fromstring(xml_bytes, parser=recovering_parser)
        for document in xml_tree.findall("./{*}AdditionalDocumentReference"):
            attachment_name = document.find("{*}ID")
            attachment_data = document.find(
                "{*}Attachment/{*}EmbeddedDocumentBinaryObject"
            )
            if (
                attachment_name is not None
                and attachment_data is not None
                and attachment_data.attrib.get("mimeCode") == "application/pdf"
            ):
                text = attachment_data.text or ""
                name = (attachment_name.text or "invoice").split("\\")[-1].split("/")[
                    -1
                ].split(".")[0] + ".pdf"
                return name, text + "=" * (len(text) % 3)  # Fix incorrect padding
        return False, False

    def download_from_spv(self):
        """Rutina de descarcare a fisierelor de la SPV"""
        session = requests.Session()

        for message in self.filtered(lambda m: not m.attachment_id):
            today = fields.Date.today()
            # La o redescărcare manuală a unui mesaj căzut în eroare repornim
            # contorul de încercări de la zero.
            if message.state == "error":
                message.write(
                    {
                        "state": "draft",
                        "download_attempts": 0,
                        "last_download_date": False,
                    }
                )

            # Numărăm încercările pe zi: dacă ultima descărcare a fost într-o zi
            # anterioară, repornim contorul la 1.
            attempts = message.download_attempts + 1
            if message.last_download_date != today:
                attempts = 1
            message.write({"download_attempts": attempts, "last_download_date": today})

            response = self.env["l10n_ro_edi.document"]._request_ciusro_download_zip(
                company=message.company_id,
                key_download=message.name,
                session=session,
            )

            error = response.get("error", "")

            if error:
                # ANAF limitează la 10 descărcări/zi pe mesaj. Reîncercarea oarbă
                # doar epuizează cota și spamează logul, așa că marcăm mesajul ca
                # eroare după 3 încercări într-o zi - domeniul cron-ului exclude
                # state="error", deci nu mai e reselectat în aceeași zi. Resetul
                # zilnic error→draft din res.company îl readuce în coadă a doua zi.
                vals = {"error": str(error)}
                if message.download_attempts >= 3:
                    vals["state"] = "error"
                message.write(vals)
                continue
            if message.message_type == "message":
                info_message = message.check_anaf_message_xml(response["content"])
                message.write({"message": info_message})

            file_name = f"{message.request_id}.zip"
            attachment_value = {
                "name": file_name,
                "raw": response["content"],
                "mimetype": "application/zip",
                "company_id": message.company_id.id,
            }
            attachment = self.env["ir.attachment"].sudo().create(attachment_value)

            if message.attachment_id:
                message.attachment_id.sudo().unlink()
            message.write({"file_name": file_name, "attachment_id": attachment.id})
            if message.state == "draft":
                message.state = "downloaded"

            message.get_xml_fom_zip()

    def get_xml_fom_zip(self):
        """Parse the invoice XML from the ZIP and update the message
        metadata. The XML is processed in memory — no attachment is
        created here."""
        for message in self:
            _file_name, xml_bytes = message._get_xml_bytes()
            if not xml_bytes:
                continue

            recovering_parser = etree.XMLParser(recover=True)
            xml_tree = etree.fromstring(xml_bytes, parser=recovering_parser)

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
                "{urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2}CreditNote"  # noqa
            )
            if xml_tree.tag == xml_tag_credit_note:
                amount = -1 * amount

            message.write(
                {
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
            _logger.exception(f"Error when converting the xml content to etree: {e}")
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
            invoices = self.env["account.move"].search(
                [("l10n_ro_edi_index", "in", request_ids)]
            )
            for message in messages_with_error:
                invoice = invoices.filtered(
                    lambda i, m=message: i.l10n_ro_edi_index == m.request_id
                )
                if not invoice:
                    continue
                message.write(
                    {
                        "invoice_id": invoice.id,
                    }
                )
                edi_docs = invoice.l10n_ro_edi_document_ids
                domain = [
                    ("res_model", "=", "account.move"),
                    (
                        "res_field",
                        "in",
                        ["ubl_cii_xml_file", "invoice_pdf_report_file"],
                    ),
                    ("res_id", "=", invoice.id),
                ]
                attachments = self.env["ir.attachment"].sudo().search(domain)
                attachments.unlink()
                for edi_doc in edi_docs:
                    edi_doc.write(
                        {"state": "invoice_refused", "message": message.error}
                    )
                invoice.write({"l10n_ro_edi_state": False})

        messages_without_invoice = self.filtered(lambda m: not m.invoice_id)
        message_ids = messages_without_invoice.mapped("name")
        request_ids = messages_without_invoice.mapped("request_id")
        invoices = self.env["account.move"].search(
            [
                "|",
                "|",
                ("l10n_ro_edi_download", "in", message_ids),
                ("l10n_ro_edi_transaction", "in", request_ids),
                # facturi create automat de l10n_ro_edi core (v19)
                ("l10n_ro_edi_index", "in", request_ids),
            ]
        )
        messages_with_ref = messages_without_invoice.filtered(lambda m: m.ref)
        domain = [("name", "in", messages_with_ref.mapped("ref"))]
        invoices |= self.env["account.move"].search(domain)
        invoices = invoices.filtered(lambda i: i.state != "cancel")
        for message in messages_without_invoice:
            invoice = invoices.filtered(
                lambda i, m=message: i.l10n_ro_edi_download == m.name
                or i.l10n_ro_edi_transaction == m.request_id
                or i.l10n_ro_edi_index == m.request_id
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
                # Only the ZIP is owned by the message; the XML and the
                # embedded PDF are created directly on the invoice.
                message.attachment_id.sudo().write(
                    {"res_id": message.invoice_id.id, "res_model": "account.move"}
                )

                if not message.invoice_id.l10n_ro_edi_document_ids:
                    if message.message_type == "error":
                        edi_state = "invoice_refused"
                    else:
                        # The document is already in the SPV — the very
                        # existence of the message proves it — and the invoice
                        # carries no EDI document, so this instance never
                        # uploaded anything. The correct state is the terminal
                        # one, invoice_validated:
                        #
                        # - for received bills, l10n_ro_edi core deduplicates on
                        #   l10n_ro_edi_state == 'invoice_validated'; with
                        #   invoice_sent the imported bill is no longer found at
                        #   dedup time and the import cron recreates it
                        #   (duplicate bills);
                        # - for our own invoices (including self-billed ones the
                        #   customer issued in our name), invoice_sent would
                        #   queue the document for the fetch-status cron, which
                        #   queries ANAF with l10n_ro_edi_index — empty, since we
                        #   did not upload it. The fetch fails on every run, logs
                        #   in the chatter, and re-triggers itself every 2
                        #   minutes for as long as an invoice_sent invoice
                        #   exists, so the loop never ends.
                        #
                        # Invoices this instance did upload already have an EDI
                        # document holding the index, so they never reach this
                        # branch: their normal sent -> validated flow (and the
                        # signature retrieval) is untouched.
                        edi_state = "invoice_validated"

                    self.env["l10n_ro_edi.document"].create(
                        {
                            "invoice_id": message.invoice_id.id,
                            "state": edi_state,
                        }
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
                "company_id": message.company_id.id,
            }
            if "extract_state" in move_obj._fields:
                invoice_values["extract_state"] = "no_extract_requested"
            new_invoice = move_obj.with_context(default_move_type="in_invoice").create(
                invoice_values
            )
            new_invoice = new_invoice.with_context(
                disable_onchange_name_predictive=True
            )
            file_name, xml_bytes = message._get_xml_bytes()
            if not xml_bytes:
                new_invoice.unlink()
                message.write(
                    {
                        "state": "error",
                        "error": "No XML found in the downloaded ZIP.",
                    }
                )
                continue
            # The XML is materialized only here, directly on the invoice:
            # it is the import source and must stay on the bill. The UBL
            # decoder then moves it into the invoice's ubl_cii_xml_file
            # binary field and imports the embedded PDF (or generates a
            # substitute preview) by itself.
            attachment_xml = (
                self.env["ir.attachment"]
                .sudo()
                .create(
                    {
                        "name": file_name,
                        "raw": xml_bytes,
                        "mimetype": "application/xml",
                        "res_model": "account.move",
                        "res_id": new_invoice.id,
                        "company_id": message.company_id.id,
                    }
                )
            )
            files_data = new_invoice._to_files_data(attachment_xml)

            try:
                new_invoice._extend_with_attachments(files_data)
            except Exception as e:
                message.write({"state": "error", "error": str(e)})
                continue

            _logger.info(
                "Search existing invoice: ref=%s, partner=%s",
                new_invoice.ref,
                new_invoice.commercial_partner_id.id,
            )
            exist_invoice = move_obj.search(
                [
                    ("ref", "=", new_invoice.ref),
                    ("move_type", "in", ("in_invoice", "in_receipt")),
                    ("state", "!=", "cancel"),
                    (
                        "commercial_partner_id",
                        "=",
                        new_invoice.commercial_partner_id.id,
                    ),
                    ("id", "!=", new_invoice.id),
                ],
                limit=1,
            )
            _logger.info("Exist invoice found: %s", exist_invoice.ids)
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

    def _render_anaf_pdf_bytes(self, no_validate=None):
        """Convert the invoice XML to PDF via the ANAF webservice.

        Returns the PDF bytes; nothing is stored."""
        self.ensure_one()
        _file_name, xml = self._get_xml_bytes()
        if not xml:
            raise UserError(self.env._("No XML found in the downloaded ZIP."))
        headers = {"Content-Type": "text/plain"}
        val1 = "FACT1"
        if b"<CreditNote" in xml:
            val1 = "FCN"

        url = f"https://webservicesp.anaf.ro/prod/FCTEL/rest/transformare/{val1}"
        if no_validate:
            url = f"https://webservicesp.anaf.ro/prod/FCTEL/rest/transformare/{val1}/DA"

        try:
            res = requests.post(url, data=xml, headers=headers, timeout=25)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            raise UserError(
                self.env._("Could not connect to ANAF service. Please try again later.")
            ) from e
        except requests.exceptions.RequestException as e:
            raise UserError(
                self.env._("An error occurred while connecting to ANAF service: %s", e)
            ) from e

        if "The requested URL was rejected" in res.text:
            raise UserError(
                self.env._("ANAF service unable to generate PDF from this XML.")
            )

        if res.status_code == 200:
            return res.content
        if no_validate is None:
            return self._render_anaf_pdf_bytes(no_validate=True)
        raise UserError(
            self.env._("ANAF service unable to generate PDF from this XML.")
        )

    def _get_embedded_pdf_bytes(self):
        """Return (name, pdf bytes) of the PDF embedded in the invoice XML.

        The PDF is extracted in memory from the ZIP; nothing is stored."""
        self.ensure_one()
        _file_name, xml_bytes = self._get_xml_bytes()
        if not xml_bytes:
            return False, False
        name, datas = self._extract_embedded_pdf(xml_bytes)
        if not datas:
            return False, False
        return name, b64decode(datas)

    def action_download_attachment(self):
        self.ensure_one()
        return self._action_download(self.attachment_id.id)

    def action_download_xml(self):
        self.ensure_one()
        if self.attachment_xml_id:
            return self._action_download(self.attachment_xml_id.id)
        return self._action_download_derived("xml")

    def action_download_anaf_pdf(self):
        self.ensure_one()
        if self.attachment_anaf_pdf_id:
            return self._action_download(self.attachment_anaf_pdf_id.id)
        return self._action_download_derived("anaf_pdf")

    def action_download_embedded_pdf(self):
        self.ensure_one()
        if self.attachment_embedded_pdf_id:
            return self._action_download(self.attachment_embedded_pdf_id.id)
        _name, pdf_bytes = self._get_embedded_pdf_bytes()
        if not pdf_bytes:
            raise UserError(
                self.env._("This invoice's XML does not contain an embedded PDF.")
            )
        return self._action_download_derived("embedded_pdf")

    def _action_download(self, attachment_field_id):
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment_field_id}?download=true",
            "target": "self",
        }

    def _action_download_derived(self, kind):
        """Download a file derived on the fly from the stored ZIP."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/l10n_ro/message_spv/{self.id}/{kind}",
            "target": "self",
        }

    def get_partner(self):
        partner_obj = self.env["res.partner"]
        for message in self.filtered(lambda m: not m.partner_id):
            if message.cif:
                # The CIF may reach us with or without the "RO" prefix, while
                # the partner in Odoo can hold the other spelling: try both.
                cif_clean = re.sub(r"^RO", "", message.cif.strip().upper())
                partner = partner_obj.browse()
                for variant in (cif_clean, "RO" + cif_clean):
                    partner = partner_obj.search(
                        [
                            ("vat", "=ilike", variant),
                            ("is_company", "=", True),
                            "|",
                            ("company_id", "=", message.company_id.id),
                            ("company_id", "=", False),
                        ],
                        limit=1,
                    )
                    if partner:
                        break
                if not partner:
                    partner = partner_obj.create(
                        {
                            "name": message.cif,
                            "vat": message.cif,
                            "is_company": True,
                            "company_id": message.company_id.id,
                        }
                    )
                message.write({"partner_id": partner.id})

    def refresh(self):
        l10n_ro_refresh_message_days = int(
            self.env.company.l10n_ro_refresh_message_days or 1
        )
        self.env.company._l10n_ro_download_message_spv(
            no_days=l10n_ro_refresh_message_days
        )

    def show_invoice(self):
        invoices = self.mapped("invoice_id")
        action = {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "list",
            "views": [(False, "list"), (False, "form")],
            "domain": [("id", "in", invoices.ids)],
        }

        return action
