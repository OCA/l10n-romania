# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import Command, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _reconcile_payments(self, to_process, edit_mode=False):
        to_process_standard = [
            vals
            for vals in to_process
            if vals["payment"].move_id or not vals["payment"].is_l10n_ro_record
        ]
        super()._reconcile_payments(to_process_standard, edit_mode=edit_mode)

        # reconciliere factura direct cu payment.l10n_ro_statement_line_id
        to_process_without_move = [
            vals
            for vals in to_process
            if (vals["payment"].is_l10n_ro_record and not vals["payment"].move_id)
        ]
        domain = [
            ("parent_state", "=", "posted"),
            (
                "account_type",
                "in",
                self.env["account.payment"]._get_valid_payment_account_types(),
            ),
            ("reconciled", "=", False),
        ]
        for vals in to_process_without_move:
            payment = vals["payment"]
            if payment.l10n_ro_statement_line_id:
                statement_line = payment.l10n_ro_statement_line_id
                _st_liquidity_lines, st_suspense_lines, _st_other_lines = (
                    statement_line.with_context(
                        skip_account_move_synchronization=True
                    )._seek_for_lines()
                )
                lines = vals["to_reconcile"]
                st_suspense_lines.account_id = lines[0].account_id

                payment_lines = statement_line.move_id.line_ids.filtered_domain(domain)

                lines = vals["to_reconcile"]
                extra_context = (
                    {"forced_rate_from_register_payment": vals["rate"]}
                    if "rate" in vals
                    else {}
                )

                for account in payment_lines.account_id:
                    (payment_lines + lines).with_context(
                        **extra_context
                    ).filtered_domain(
                        [
                            ("account_id", "=", account.id),
                            ("reconciled", "=", False),
                            ("parent_state", "=", "posted"),
                        ]
                    ).reconcile()
                lines.move_id.matched_payment_ids = [Command.link(payment.id)]
