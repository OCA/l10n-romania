# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def action_l10n_ro_receipt_print(self):
        """Print the receipt associated with the bank statement line"""
        self.ensure_one()
        return self.env.ref("account.action_report_payment_receipt").report_action(
            self.payment_id
        )
