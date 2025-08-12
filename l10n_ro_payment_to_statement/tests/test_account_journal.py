# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from .common import TestPaymenttoStatement


@tagged("post_install", "-at_install")
class TestAccountJournal(TestPaymenttoStatement):
    def test_l10n_ro_update_cash_vals(self):
        journal = self.env["account.journal"].create(
            {
                "name": "Test cash",
                "code": "TST",
                "type": "cash",
                "company_id": self.env.company.id,
            }
        )

        self.assertTrue(journal.l10n_ro_statement_sequence_id)
        self.assertTrue(journal.l10n_ro_cash_in_sequence_id)
        self.assertTrue(journal.l10n_ro_cash_out_sequence_id)
        self.assertTrue(journal.l10n_ro_customer_cash_in_sequence_id)
