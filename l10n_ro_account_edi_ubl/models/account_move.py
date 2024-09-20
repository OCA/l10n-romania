# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ro_edi_transaction = fields.Char(
        "Transaction ID (RO)",
        help="Technical field used to track the status of a submission.",
        copy=False,
        compute="_compute_l10n_ro_edi_fields",
        store=True,
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
    l10n_ro_edi_fields_readonly = fields.Boolean(
        compute="_compute_l10n_ro_show_edi_fields",
        string="Make ANAF EDI Fields readonly",
    )

    l10n_ro_show_anaf_download_edi_buton = fields.Boolean(
        compute="_compute_l10n_ro_show_anaf_download_edi_buton",
        string="Show ANAF Download EDI Button",
    )

    l10n_ro_edi_previous_transaction = fields.Char(
        "Previous Transactions or Download (RO)",
        help="Technical field used to track previous transactions or "
        "download ID's received from ANAF. Useful in case the invoice "
        "was sent and had errors, we could find the invoice based on "
        "old data, since on reset to draft they are removed.",
        copy=False,
    )

    @api.constrains("l10n_ro_edi_download")
    def _check_unique_edi_download_number(self):
        moves = self.filtered(lambda m: m.l10n_ro_edi_download)
        if not moves:
            return

        self.flush_model(["l10n_ro_edi_download"])

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

    @api.depends("l10n_ro_edi_state", "l10n_ro_edi_document_ids")
    def _compute_l10n_ro_edi_fields(self):
        for invoice in self:
            key_loading_docs = invoice.l10n_ro_edi_document_ids.filtered(
                lambda doc: doc.key_loading
            )
            if key_loading_docs:
                invoice.l10n_ro_edi_transaction = key_loading_docs[0].key_loading

    @api.depends("l10n_ro_edi_document_ids", "l10n_ro_edi_download")
    def _compute_l10n_ro_show_edi_fields(self):
        for invoice in self:
            show_fields = readonly_fields = False
            if invoice.l10n_ro_edi_document_ids:
                if invoice.l10n_ro_edi_transaction:
                    show_fields = True
                    readonly_fields = True
            else:
                if invoice.move_type in ("in_invoice", "in_refund"):
                    show_fields = True
                    readonly_fields = True if invoice.state == "posted" else False
            invoice.l10n_ro_show_edi_fields = show_fields
            invoice.l10n_ro_edi_fields_readonly = readonly_fields

    @api.depends("l10n_ro_edi_download", "move_type")
    def _compute_l10n_ro_show_anaf_download_edi_buton(self):
        for invoice in self:
            show_button = False
            if (
                invoice.l10n_ro_edi_download
                and invoice.move_type in ("in_invoice", "in_refund")
                and not invoice.line_ids
            ):
                show_button = True
            invoice.l10n_ro_show_anaf_download_edi_buton = show_button

    def is_l10n_ro_autoinvoice(self):
        return (
            self.is_purchase_document()
            and self.journal_id.l10n_ro_sequence_type == "autoinv2"
            and self.journal_id.l10n_ro_partner_id
            and self.journal_id.l10n_ro_partner_id.ubl_cii_format == "ciusro"
        )

    def _need_ubl_cii_xml(self):
        self.ensure_one()
        if (
            not self.invoice_pdf_report_id
            and not self.ubl_cii_xml_id
            and self.is_l10n_ro_autoinvoice()
        ):
            return True
        return super()._need_ubl_cii_xml()

    def _l10n_ro_edi_create_document_invoice_sending_failed(
        self, message, attachment_raw=None
    ):
        res = super()._l10n_ro_edi_create_document_invoice_sending_failed(
            message, attachment_raw
        )
        if message:
            self.l10n_ro_edi_post_message(self, message, res)

    @api.model
    def l10n_ro_edi_post_message(self, invoice, message, res):
        body = message
        if 'error' in res.message:
            body += _("\n\nError:\n<p>%s</p>") % res["error"]
        users = (
            invoice.company_id.l10n_ro_edi_error_notify_users or invoice.invoice_user_id
        )
        for user in users:
            mail_activity = invoice.activity_ids.filtered(
                lambda a: a.summary == message and a.user_id == user
            )
            if mail_activity:
                mail_activity.write(
                    {
                        "date_deadline": fields.Date.today(),
                        "note": body,
                    }
                )
            else:
                invoice.activity_schedule(
                    "mail.mail_activity_data_warning",
                    summary=message,
                    note=body,
                    user_id=user.id,
                )

    def write(self, vals):
        if vals.get("l10n_ro_edi_download"):
            self.l10n_ro_complete_old_transaction(vals["l10n_ro_edi_download"])
        if vals.get("l10n_ro_edi_transaction"):
            self.l10n_ro_complete_old_transaction(vals["l10n_ro_edi_transaction"])
        res = super().write(vals)
        return res

    def l10n_ro_complete_old_transaction(self, old_transaction):
        if not old_transaction:
            return
        for move in self:
            if not move.l10n_ro_edi_previous_transaction:
                move.l10n_ro_edi_previous_transaction = old_transaction
            elif old_transaction not in move.l10n_ro_edi_previous_transaction:
                move.l10n_ro_edi_previous_transaction += ", %s" % old_transaction

    def _l10n_ro_edi_fetch_invoice_sending_documents(self):
        """
        Inherit to store key download to the invoice
        """
        res = super()._l10n_ro_edi_fetch_invoice_sending_documents()

        session = requests.Session()
        invoices_to_fetch = self.filtered(
            lambda inv: inv.l10n_ro_edi_state == "invoice_sent" and not inv.l10n_ro_edi_download
        )

        for invoice in invoices_to_fetch:
            result = self.env["l10n_ro_edi.document"]._request_ciusro_fetch_status(
                company=invoice.company_id,
                key_loading=invoice.l10n_ro_edi_transaction,
                session=session,
            )
            if result.get("key_download"):
                invoice.l10n_ro_edi_download = result["key_download"]
        return res

    def l10n_ro_download_zip_anaf(self):
        for invoice in self:
            if not invoice.l10n_ro_edi_download:
                continue
            result = self.env["l10n_ro_edi.document"]._request_ciusro_download_zipfile(
                company=invoice.company_id,
                key_download=invoice.l10n_ro_edi_download,
                session=requests,
            )
            active_sending_document = invoice.l10n_ro_edi_document_ids.filtered(lambda d: d.state == 'invoice_sending')
            if active_sending_document:
                active_sending_document = active_sending_document[0]
                previous_raw = active_sending_document.attachment_id.sudo().raw
                if "error" in result:
                    
                    invoice._l10n_ro_edi_create_document_invoice_sending_failed(
                        result["error"], previous_raw
                    )
            attachment_zip = (
                self.env["ir.attachment"]
                .sudo()
                .create(
                    self._l10n_ro_edi_create_attachment_values(
                        result["attachment_zip"]
                    )
                )
            )
            attachment = (
                self.env["ir.attachment"]
                .sudo()
                .create(
                    self._l10n_ro_edi_create_attachment_values(
                        result["attachment_raw"]
                    )
                )
            )
            if invoice.invoice_line_ids:
               raise UserError(
                    _(
                        "The invoice already have invoice lines, "
                        "you cannot update them again from the XMl downloaded file."
                    )
                )
            invoice._extend_with_attachments(attachment)

    @api.model
    def _get_ubl_cii_builder_from_xml_tree(self, tree):
        customization_id = tree.find("{*}CustomizationID")
        if customization_id is not None and "CIUS-RO" in customization_id.text:
            return self.env["account.edi.xml.ubl_ro"]
        return super()._get_ubl_cii_builder_from_xml_tree(tree)

    def _generate_pdf_and_send_invoice(
        self,
        template,
        force_synchronous=True,
        allow_fallback_pdf=True,
        bypass_download=False,
        **kwargs,
    ):
        res = super()._generate_pdf_and_send_invoice(
            template, force_synchronous, allow_fallback_pdf, bypass_download, **kwargs
        )
        if self.env.context.get("test_data"):
            return self.env.context["test_data"]
        return res
