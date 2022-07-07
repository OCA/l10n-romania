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

    def _get_cirus_ro_name(self):
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

    def _retry_edi_documents_error_hook(self):
        # OVERRIDE
        # For RO, remove the l10n_ro_edi_transaction to force re-send
        # (otherwise this only triggers a check_status)
        cirus_ro = self.env.ref("l10n_ro_edi_ubl.edi_ubl_cirus_ro")
        self.filtered(
            lambda m: m._get_edi_document(cirus_ro).blocking_level == "error"
        ).l10n_ro_edi_transaction = None
