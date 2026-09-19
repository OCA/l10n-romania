# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import html2plaintext


class PosOrder(models.Model):
    _inherit = "pos.order"

    l10n_ro_payment_disposal_id = fields.Many2one(
        "account.bank.statement.line",
        string="Romania - Payment Disposal",
        readonly=True,
        copy=False,
        help="Cash statement line paying the customer back for this refund. "
        "It is the payment disposal handed over at the till.",
    )

    def _l10n_ro_is_refund_order(self):
        """A refund of a Romanian company: it owes the customer a credit note."""
        self.ensure_one()
        return self.is_refund and self.is_l10n_ro_record

    def _l10n_ro_missing_partner_error(self):
        self.ensure_one()
        return ValidationError(
            self.env._(
                "Refund %(order)s needs a customer: both the credit note and "
                "the payment disposal are issued in the customer's name.",
                order=self.name,
            )
        )

    @api.constrains("partner_id", "is_refund", "state")
    def _check_l10n_ro_refund_partner(self):
        for order in self:
            if order.state in ("draft", "cancel") or order.partner_id:
                continue
            if order._l10n_ro_is_refund_order():
                raise order._l10n_ro_missing_partner_error()

    def _process_saved_order(self, draft):
        self.ensure_one()
        is_ro_refund = not draft and self._l10n_ro_is_refund_order()
        if is_ro_refund:
            if not self.partner_id:
                # The constraint below only fires when the state changes, which
                # a re-synced order does not do; check here so the refund never
                # reaches the invoice without a customer.
                raise self._l10n_ro_missing_partner_error()
            # A refunded receipt is settled with a credit note in Romania, so
            # the choice the cashier made in the UI does not apply.
            self.to_invoice = True
        res = super()._process_saved_order(draft)
        if is_ro_refund:
            self._l10n_ro_check_credit_note_is_printable()
            self._l10n_ro_create_payment_disposal()
        return res

    def _l10n_ro_check_credit_note_is_printable(self):
        """Refuse a refund whose credit note came out as a proforma.

        When the documents cannot be generated -- an e-Factura that will not
        build over a partner missing its county, say -- core attaches a
        proforma instead and carries on. A proforma reverses nothing, and the
        customer would walk out of the shop holding it as if it did, so take
        the whole refund back rather than hand it over.

        This is only about the printed document: an e-Factura that builds but
        cannot reach the SPV still leaves a real credit note behind, and that
        refund goes through -- the upload is retried from the back office.
        """
        self.ensure_one()
        if not self.env.context.get("generate_pdf", True):
            # Same condition core generates the documents under; nothing was
            # attempted, so there is no proforma to catch.
            return
        credit_note = self.account_move
        if not credit_note or credit_note.invoice_pdf_report_id:
            return
        raise UserError(
            self.env._(
                "The credit note for %(order)s could not be issued, only a "
                "proforma, which reverses nothing. The refund was not made.\n\n"
                "%(reason)s",
                order=self.name,
                reason=self._l10n_ro_credit_note_error(credit_note),
            )
        )

    def _l10n_ro_credit_note_error(self, credit_note):
        """Why the documents failed, as core logged it on the credit note.

        The credit note was created moments ago in this same transaction and
        core posts the failure last, so its newest message is the reason.
        """
        message = credit_note.message_ids[:1]
        return html2plaintext(message.body) if message.body else ""

    def _get_payments(self):
        payments = super()._get_payments()
        # The cash handed back is settled by the payment disposal statement
        # line, which reconciles the credit note itself; core must not also
        # create a POS payment move for it.
        return payments - payments._l10n_ro_payment_disposals()

    def _l10n_ro_create_payment_disposal(self):
        """Pay the credit note out of the till with its own cash statement line.

        That line is the payment disposal the customer signs for, and it is
        what moves the cash: the POS payment behind it is excluded from the
        session's cash flow (see pos.session).
        """
        self.ensure_one()
        if self.l10n_ro_payment_disposal_id:
            return self.l10n_ro_payment_disposal_id

        statement_line = self.env["account.bank.statement.line"]
        payments = self.payment_ids._l10n_ro_payment_disposals()
        credit_note = self.account_move
        if not payments or not credit_note:
            return statement_line

        journal = payments.payment_method_id.journal_id
        if len(journal) != 1:
            raise UserError(
                self.env._(
                    "Refund %(order)s is paid in cash through several journals, "
                    "so no single payment disposal can be issued for it.",
                    order=self.name,
                )
            )
        receivable_lines = credit_note.line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
        )
        if not receivable_lines:
            raise UserError(
                self.env._(
                    "Credit note %(move)s has no receivable line to settle with "
                    "a payment disposal.",
                    move=credit_note.display_name,
                )
            )
        if len(receivable_lines.account_id) != 1:
            raise UserError(
                self.env._(
                    "Credit note %(move)s spreads over several receivable "
                    "accounts, so no single payment disposal can settle it.",
                    move=credit_note.display_name,
                )
            )

        statement_line = (
            self.env["account.bank.statement.line"]
            .sudo()
            .with_context(no_retrieve_partner=True)
            .create(
                {
                    "pos_session_id": self.session_id.id,
                    "journal_id": journal.id,
                    "date": fields.Date.context_today(self, self.date_order),
                    # Refund payments are already negative: cash out of the till.
                    "amount": sum(payments.mapped("amount")),
                    "payment_ref": self._l10n_ro_payment_disposal_ref(credit_note),
                    "partner_id": self.partner_id.id,
                    # Settle the credit note directly instead of parking the
                    # amount on the journal's suspense account.
                    "counterpart_account_id": receivable_lines.account_id.id,
                }
            )
        )
        self.l10n_ro_payment_disposal_id = statement_line
        payments.l10n_ro_payment_disposal_id = statement_line

        counterpart_lines = statement_line.move_id.line_ids.filtered(
            lambda line: line.account_id == receivable_lines.account_id
        )
        to_reconcile = (counterpart_lines | receivable_lines).filtered(
            lambda line: not line.reconciled
        )
        if receivable_lines.account_id.reconcile:
            to_reconcile.reconcile()
        return statement_line

    def _l10n_ro_payment_disposal_ref(self, credit_note):
        self.ensure_one()
        return self.env._(
            "Refund %(order)s - %(move)s", order=self.name, move=credit_note.name
        )

    def _l10n_ro_payment_disposal_report_action(self):
        self.ensure_one()
        return self.env.ref(
            "l10n_ro_payment_receipt_report.action_report_bank_statement_line_payment"
            # config=False: a cashier handing cash back must get the document,
            # not the "configure your document layout" wizard core offers an
            # admin whose company has no layout set yet.
        ).report_action(self.l10n_ro_payment_disposal_id, config=False)

    def l10n_ro_get_payment_disposal_report(self):
        """Report action for the payment disposal, or False when there is none.

        Called from the Point of Sale, which prints it right after the credit
        note so the customer signs for the cash before leaving the till.
        """
        self.ensure_one()
        if not self.l10n_ro_payment_disposal_id:
            return False
        return self._l10n_ro_payment_disposal_report_action()

    def action_l10n_ro_print_payment_disposal(self):
        self.ensure_one()
        if not self.l10n_ro_payment_disposal_id:
            raise UserError(
                self.env._(
                    "There is no payment disposal for %(order)s.", order=self.name
                )
            )
        return self._l10n_ro_payment_disposal_report_action()
