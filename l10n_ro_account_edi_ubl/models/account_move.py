# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import io
import logging
import zipfile

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ro_edi_transaction = fields.Char(
        "Transaction ID (RO)",
        help="Technical field used to track the status of a submission.",
        copy=False,
    )
    l10n_ro_edi_download = fields.Char(
        "ID Download ANAF (RO)",
        help="ID used to download the ZIP file from ANAF.",
        copy=False,
    )

    l10n_ro_show_edi_fields = fields.Boolean(
        compute="_compute_l10n_ro_show_edi_fields",
        string="Show ANAF EDI Fields",
    )

    l10n_ro_show_anaf_download_edi_buton = fields.Boolean(
        compute="_compute_l10n_ro_show_anaf_download_edi_buton",
        string="Show ANAF Download EDI Button",
    )

    @api.depends("edi_state", "move_type")
    def _compute_l10n_ro_show_edi_fields(self):
        cius_ro = self.env.ref("l10n_ro_account_edi_ubl.edi_ubl_cius_ro")
        for invoice in self:
            show_button = False
            if (
                cius_ro._is_required_for_invoice(invoice)
                and invoice.edi_state == "sent"
            ):
                show_button = True
            elif invoice.move_type in ("in_invoice", "in_refund"):
                show_button = True
            invoice.l10n_ro_show_edi_fields = show_button

    @api.depends("l10n_ro_edi_download", "edi_state", "move_type")
    def _compute_l10n_ro_show_anaf_download_edi_buton(self):
        cius_ro = self.env.ref("l10n_ro_account_edi_ubl.edi_ubl_cius_ro")
        for invoice in self:
            show_button = False
            if invoice.l10n_ro_edi_download:
                if (
                    cius_ro._is_required_for_invoice(invoice)
                    and invoice.edi_state == "sent"
                ):
                    show_button = True
                elif invoice.move_type in ("in_invoice", "in_refund"):
                    show_button = True
            invoice.l10n_ro_show_anaf_download_edi_buton = show_button

    @api.constrains("l10n_ro_edi_download")
    def _check_unique_edi_download_number(self):
        moves = self.filtered(lambda m: m.l10n_ro_edi_download)
        if not moves:
            return

        self.flush(["l10n_ro_edi_download"])

        self._cr.execute(
            """
            SELECT move2.id, move2.name
            FROM account_move move
            INNER JOIN account_move move2 ON
                move2.l10n_ro_edi_download = move.l10n_ro_edi_download
            WHERE move.id IN %s and move2.id != move.id
        """,
            [tuple(moves.ids)],
        )
        res = self._cr.fetchall()
        if res:
            raise ValidationError(
                _(
                    "You already have one invoice with the same ANAF download.\n"
                    "Invoice(s) Ids: %(ids)s\n"
                    "Invoice(s) Numbers: %(numbers)s\n"
                )
                % {
                    "ids": ", ".join(str(r[0]) for r in res),
                    "numbers": ", ".join(r[1] for r in res),
                }
            )

    def get_l10n_ro_edi_invoice_needed(self):
        self.ensure_one()
        cius_ro = self.env.ref("l10n_ro_account_edi_ubl.edi_ubl_cius_ro")
        return cius_ro._is_required_for_invoice(self)

    def button_draft(self):
        # OVERRIDE
        for move in self:
            edi_documents_with_error = move.edi_document_ids.filtered(lambda x: x.error)
            if (
                move.l10n_ro_edi_transaction
                and move.get_l10n_ro_edi_invoice_needed()
                and not edi_documents_with_error
            ):
                raise UserError(
                    _(
                        "You can't edit the following journal entry %s "
                        "because an electronic document has already been "
                        "sent to ANAF. To edit this entry, you need to "
                        "create a Credit Note for the invoice and "
                        "create a new invoice.",
                        move.display_name,
                    )
                )
        return super().button_draft()

    def button_cancel_posted_moves(self):
        # OVERRIDE
        sent_e_invoices = self.filtered(
            lambda move: move.l10n_ro_edi_transaction
            and move.get_l10n_ro_edi_invoice_needed()
        )
        if sent_e_invoices:
            raise UserError(
                _(
                    "Invoices with this document type always need to be"
                    " cancelled through a credit note. "
                    "There is no possibility to cancel."
                )
            )

        return super().button_cancel_posted_moves()

    def _retry_edi_documents_error_hook(self):
        # OVERRIDE
        # For RO, remove the l10n_ro_edi_transaction to force re-send
        # (otherwise this only triggers a check_status)
        cius_ro = self.env.ref("l10n_ro_account_edi_ubl.edi_ubl_cius_ro")
        invoice_errors = self.filtered(
            lambda m: m._get_edi_document(cius_ro).blocking_level == "error"
        )
        for invoice in invoice_errors:
            invoice.l10n_ro_edi_transaction = None
            edi_document = invoice._get_edi_document(cius_ro)
            if edi_document:
                old_attachment = edi_document.attachment_id
                if old_attachment:
                    edi_document.attachment_id = False
                    old_attachment.sudo().unlink()

        return super()._retry_edi_documents_error_hook()

    def action_process_edi_web_services(self):
        if len(self) == 1:
            if not self.l10n_ro_edi_transaction:
                self = self.with_context(l10n_ro_edi_manual_action=True)
        return super().action_process_edi_web_services()

    def attach_ubl_xml_file_button(self):
        self.ensure_one()
        assert self.get_l10n_ro_edi_invoice_needed()
        assert self.state == "posted"

        cius_ro = self.env.ref("l10n_ro_account_edi_ubl.edi_ubl_cius_ro")

        errors = cius_ro._check_move_configuration(self)
        if errors:
            raise UserError("\n".join(errors))
        attachment = cius_ro._export_cius_ro(self)
        doc = self._get_edi_document(cius_ro)
        # In case of error, the attachment is a list of string
        if not isinstance(attachment, models.Model):
            doc.write({"error": attachment, "blocking_level": "warning"})
            self.message_post(body=attachment)
            message = _("There are some errors when generating the XMl file.")
            body = message + _("\n\nError:\n<p>%s</p>") % attachment
            self.activity_schedule(
                "mail.mail_activity_data_warning",
                summary=message,
                note=body,
                user_id=self.invoice_user_id.id,
            )
        else:
            doc.write({"attachment_id": attachment.id})
            action = self.env["ir.attachment"].action_get()
            action.update(
                {"res_id": attachment.id, "views": False, "view_mode": "form,tree"}
            )
            return action

    def get_l10n_ro_high_risk_nc_codes(self):
        high_risk_nc = (
            "0701,0702,0703,0704,0705,0706,0707,0708,0709,0710,0711,0712,"
            "0713,0714,0801,0802,0803,0804,0805,0806,0807,0808,0809,0810,"
            "0811,0812,0813,0814,2201,2202,2203,2204,2205,2206,2207,2208,"
            "2505,2515,2516,2517,6401,6402,6403,6404,6405,6101,6102,6103,"
            "6104,6105,6106,6107,6108,6109,6110,6111,6112,6113,5903,5906,"
            "5907,6114,6115,6116,6117,6201,6202,6203,6204,6205,6206,6207,"
            "6208,6209,6210,6211,62126214,6215,6216,6217"
        )
        high_risk_nc_list = high_risk_nc.split(",")
        return high_risk_nc_list

    def _l10n_ro_prepare_invoice_for_download(self):
        self.ensure_one()
        return self

    def l10n_ro_download_zip_anaf(self, anaf_config=False, return_error=False):
        if not anaf_config:
            anaf_config = self.env.company.sudo()._l10n_ro_get_anaf_sync(
                scope="e-factura"
            )
        if not anaf_config:
            raise UserError(
                _("The ANAF configuration is not set. Please set it and try again.")
            )
        for invoice in self:
            if not invoice.l10n_ro_edi_download:
                continue

            params = {"id": invoice.l10n_ro_edi_download}
            response, status_code = anaf_config._l10n_ro_einvoice_call(
                "/descarcare", params, method="GET"
            )
            eroare = ""
            if isinstance(response, dict):
                eroare = response.get("eroare", "")
            if status_code == "400":
                eroare = response.get("message")
            elif status_code == 200 and isinstance(response, dict):
                eroare = response.get("eroare")
            cius_ro = self.env.ref("l10n_ro_account_edi_ubl.edi_ubl_cius_ro")
            edi_doc = invoice._get_edi_document(cius_ro)
            nok_error = False
            if edi_doc:
                nok_error = invoice.l10n_ro_check_anaf_error_xml(response)
            if nok_error:
                eroare = nok_error
            if eroare:
                if edi_doc:
                    edi_doc.write({"blocking_level": "warning", "error": eroare})
                else:
                    _logger.warning(eroare)
                    raise UserError(eroare)
            if return_error:
                return eroare
            else:
                edi_doc.write({"blocking_level": "info", "error": ""})
                invoice.l10n_ro_process_anaf_zip_file(response)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Downloaded ZIP file from ANAF",
                "message": "The file downloaded from ANAF has been attached to the invoice.",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def l10n_ro_check_anaf_error_xml(self, zip_content):
        self.ensure_one()
        cius_ro = self.env.ref("l10n_ro_account_edi_ubl.edi_ubl_cius_ro")
        err_msg = ""
        try:
            zip_ref = zipfile.ZipFile(io.BytesIO(zip_content))
            err_file = [
                f
                for f in zip_ref.namelist()
                if f"{self.l10n_ro_edi_transaction}.xml" == f
            ]
            if err_file:
                err_cont = zip_ref.read(err_file[0])
                decode_xml = cius_ro._decode_xml(err_file[0], err_cont)
                if decode_xml:
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

    def l10n_ro_process_anaf_zip_file(self, zip_content):
        self.ensure_one()
        self.l10n_ro_save_file(
            "%s.zip" % self.l10n_ro_edi_transaction, zip_content, "application/zip"
        )
        attachment = self.l10n_ro_save_anaf_xml_file(zip_content)
        cius_ro = self.env.ref("l10n_ro_account_edi_ubl.edi_ubl_cius_ro")
        edi_doc = self._get_edi_document(cius_ro)
        if edi_doc:
            edi_doc.attachment_id = attachment
        else:
            edi_format_cius = self.env["account.edi.format"].search(
                [("code", "=", "cius_ro")]
            )
            if not self.invoice_line_ids:
                edi_format_cius._update_invoice_from_attachment(attachment, self)
            else:
                raise UserError(
                    _(
                        "The invoice already have invoice lines, "
                        "you cannot update them again from the XMl downloaded file."
                    )
                )

    def l10n_ro_get_xml_file(self, zip_ref):
        file_name = xml_file = False
        xml_file = [f for f in zip_ref.namelist() if "semnatura" not in f]
        if xml_file:
            file_name = xml_file[0]
            xml_file = zip_ref.read(file_name)
        return file_name, xml_file

    def l10n_ro_save_anaf_xml_file(self, zip_content):
        """Process a ZIP containing the sending and official XML signed
        document. This will only be available for invoices that have
        been successfully validated by ANAF and the government.
        """
        self.ensure_one()
        file_name = xml_file = False
        try:
            zip_ref = zipfile.ZipFile(io.BytesIO(zip_content))
            file_name, xml_file = self.l10n_ro_get_xml_file(zip_ref)
        except Exception as e:
            # In case the file is not zip, we will try to read it as XML
            _logger.warning(f"Error while processing the Zipped XML file: {e}")
            try:
                xml_file = zip_content
                file_name = f"{self.l10n_ro_edi_transaction}.xml"
            except Exception as e:
                _logger.warning(f"Error while processing the XML file: {e}")
        if not xml_file:
            return self.env["ir.attachment"]
        xml_file = xml_file.replace(
            b'xmlns:schemaLocation="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2 http://docs.oasis-open.org/ubl/os-UBL-2.1/xsd/maindoc/UBL-Invoice-2.1.xsd"',  # noqa: B950
            b'xsi:schemaLocation="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2 ../../UBL-2.1(1)/xsd/maindoc/UBL-Invoice-2.1.xsd"',  # noqa: B950
        )
        attachment = self.l10n_ro_save_file(file_name, xml_file)

        return attachment

    def l10n_ro_save_file(self, file_name, file_content, mimetype="application/xml"):
        self.ensure_one()
        domain = [
            ("name", "=", file_name),
            ("res_model", "=", "account.move"),
            ("res_id", "=", self.id),
        ]
        attachments = self.env["ir.attachment"].search(domain)
        if attachments:
            attachments.unlink()
        attachment = self.env["ir.attachment"].create(
            {
                "name": file_name,
                "raw": file_content,
                "res_model": "account.move",
                "res_id": self.id,
                "mimetype": mimetype,
            }
        )
        return attachment


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_computed_price_unit(self):
        self.ensure_one()
        if (
            self.move_id.move_type not in ["in_invoice", "in_refund"]
            or not self.move_id.l10n_ro_edi_download
        ):
            return super()._get_computed_price_unit()
        else:
            return self.price_unit
