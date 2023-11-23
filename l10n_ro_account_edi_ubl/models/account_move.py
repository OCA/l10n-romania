# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import io
import zipfile

from odoo import _, fields, models
from odoo.exceptions import UserError


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

    def button_draft(self):
        # OVERRIDE
        for move in self:
            if move.l10n_ro_edi_transaction:
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
        sent_e_invoices = self.filtered(lambda move: move.l10n_ro_edi_transaction)
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
        self.filtered(
            lambda m: m._get_edi_document(cius_ro).blocking_level == "error"
        ).l10n_ro_edi_transaction = None

    def send_to_anaf_e_invoice(self):
        for move in self:
            move.with_context(
                l10n_ro_edi_manual_action=True
            ).action_process_edi_web_services()

    def attach_ubl_xml_file_button(self):
        self.ensure_one()
        assert self.move_type in ("out_invoice", "out_refund")
        assert self.state == "posted"

        cius_ro = self.env.ref("l10n_ro_account_edi_ubl.edi_ubl_cius_ro")

        errors = cius_ro._check_move_configuration(self)
        if errors:
            raise UserError("\n".join(errors))
        attachment = cius_ro._export_cius_ro(self)
        doc = self._get_edi_document(cius_ro)
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

    def l10n_ro_download_zip_anaf(self):
        anaf_config = self.env.company.l10n_ro_account_anaf_sync_id.sudo()
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
            if status_code == "400":
                eroare = response.get("message")
            elif status_code == 200 and type(response) == "dict":
                eroare = response.get("eroare")
            cius_ro = self.env.ref("l10n_ro_account_edi_ubl.edi_ubl_cius_ro")
            edi_doc = invoice._get_edi_document(cius_ro)
            if eroare:
                edi_doc.write({"blocking_level": "warning", "error": eroare})
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

    def l10n_ro_process_anaf_zip_file(self, zip_content):
        self.ensure_one()
        attachment = self.l10n_ro_save_anaf_xml_file(zip_content)
        cius_ro = self.env.ref("l10n_ro_account_edi_ubl.edi_ubl_cius_ro")
        edi_doc = self._get_edi_document(cius_ro)
        if edi_doc:
            edi_doc.attachment_id = attachment
        else:
            edi_format_cius = self.env["account.edi.format"].search(
                [("code", "=", "cius_ro")]
            )
            edi_format_cius._update_invoice_from_attachment(attachment, self)

    def l10n_ro_save_anaf_xml_file(self, zip_content):
        """Process a ZIP containing the sending and official XML signed
        document. This will only be available for invoices that have
        been successfully validated by ANAF and the government.
        """
        self.ensure_one()

        zip_ref = zipfile.ZipFile(io.BytesIO(zip_content))
        xml_file = [f for f in zip_ref.namelist() if "semnatura" in f]
        if not xml_file:
            return self.env["ir.attachment"]

        file_name = xml_file[0]
        xml_file = zip_ref.read(file_name)

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
                "raw": xml_file,
                "res_model": "account.move",
                "res_id": self.id,
                "mimetype": "application/xml",
            }
        )
        return attachment
