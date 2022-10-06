# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


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
            "6104,6105,6106,6107,6108,6109,61106111,6112,6113,5903,5906,"
            "5907,6114,6115,6116,6117,6201,6202,6203,6204,6205,6206,6207,"
            "6208,6209,6210,6211,62126214,6215,6216,6217"
        )
        high_risk_nc_list = high_risk_nc.split(",")
        return high_risk_nc_list
