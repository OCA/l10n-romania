# ©  2008-2022 Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


import re

from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ro_edi_transaction = fields.Char(
        "Transaction ID (RO)",
        help="Technical field used to track the status of a submission.",
        copy=False,
    )
    l10n_ro_send_state = fields.Selection(
        [
            ("new", "New"),
            ("other", "Other"),
            ("to_send", "Not yet send"),
            ("sent", "Sent, waiting for response"),
            ("invalid", "Sent, but invalid"),
            ("delivered", "This invoice is delivered"),
        ],
        default="to_send",
        copy=False,
        string="Invoice XML Send State",
    )

    def _get_cius_ro_name(self):
        self.ensure_one()
        vat = self.company_id.partner_id.commercial_partner_id.vat
        return "ubl_b2g_{}{}{}".format(
            vat or "", "_" if vat else "", re.sub(r"[\W_]", "", self.name)
        )

    def _send_only_when_ready(self):
        return super(AccountMove, self)._send_only_when_ready()

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
        ro_edi_format = self.env.ref("l10n_ro_edi_ubl.edi_ubl_cirus_ro")
        ro_invoices = self.filtered(
            lambda move: ro_edi_format._is_required_for_invoice(move)
        )
        if ro_invoices:
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
        cius_ro = self.env.ref("l10n_ro_edi_ubl.edi_ubl_cius_ro")
        self.filtered(
            lambda m: m._get_edi_document(cius_ro).blocking_level == "error"
        ).l10n_ro_edi_transaction = None

    def action_process_edi_web_services(self):
        return super(
            AccountMove, self.with_context(edi_manual_action=True)
        ).action_process_edi_web_services()

    def send_to_anaf_e_invoice(self):
        for move in self:
            move.with_context(edi_manual_action=True).action_process_edi_web_services()

    def attach_ubl_xml_file_button(self):
        self.ensure_one()
        assert self.move_type in ("out_invoice", "out_refund")
        assert self.state == "posted"

        cius_ro = self.env.ref("l10n_ro_edi_ubl.edi_ubl_cius_ro")

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
