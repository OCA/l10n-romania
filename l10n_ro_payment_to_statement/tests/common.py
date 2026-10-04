# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestPaymenttoStatement(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.l10n_ro_accounting = True

        # the journal of the common setup was created before the company was
        # romanian, so it has none of the romanian sequences
        cls.cash_journal = cls.env["account.journal"].create(
            {
                "name": "Cash register",
                "code": "CSHRO",
                "type": "cash",
                "company_id": cls.env.company.id,
            }
        )
        cls.cash_account = cls.cash_journal.default_account_id
        cls.bank_journal = cls.company_data["default_journal_bank"]

        cls.transit_account = cls.env["account.account"].create(
            {
                "name": "Internal transfers",
                "code": "581000",
                "account_type": "asset_current",
                "reconcile": True,
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Test partner"})

        # A Romanian cash journal keeps a cash register, and the register line
        # brings the money in from the account of the payment method. Odoo 20
        # gives a new payment method line the journal's own account, which
        # leaves nothing to bring in, so the transit account is set here - the
        # way every cash register test configures it. The one test that wants
        # the refusal puts the cash account back itself.
        cls._set_payment_account(cls.cash_journal, cls.transit_account)

    @classmethod
    def _set_payment_account(cls, journal, account):
        """Account taken by the payments of a journal (the outstanding one)."""
        lines = (
            journal.inbound_payment_method_line_ids
            | journal.outbound_payment_method_line_ids
        )
        lines.payment_account_id = account

    def _create_payment(self, **vals):
        payment = self.env["account.payment"].create(
            {
                "amount": 100.0,
                "date": "2024-01-15",
                "payment_type": "inbound",
                "partner_type": "customer",
                "journal_id": self.cash_journal.id,
                "partner_id": self.partner.id,
                **vals,
            }
        )
        return payment

    def _post_payment(self, **vals):
        payment = self._create_payment(**vals)
        payment.action_post()
        return payment

    def _statements(self, journal=None):
        return self.env["account.bank.statement"].search(
            [("journal_id", "=", (journal or self.cash_journal).id)]
        )
