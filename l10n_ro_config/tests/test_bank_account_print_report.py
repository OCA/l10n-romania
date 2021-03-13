# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import common


class TestBankAccount(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestBankAccount, cls).setUpClass()
        cls.bank = cls.env["res.partner.bank"].create(
            {
                "acc_number": "NL46ABNA0499998748",
                "partner_id": cls.env.ref("base.main_partner").id,
                "company_id": cls.env.ref("base.main_company").id,
                "bank_id": cls.env.ref("base.res_bank_1").id,
            }
        )

    def test_journal_bank_creation(self):
        self.assertEqual(self.bank.print_report, False)
        journal = self.env["account.journal"].create(
            {
                "name": "Bank Journal",
                "code": "TBNKCAMT",
                "type": "bank",
                "bank_account_id": self.bank.id,
                "print_report": True,
            }
        )
        self.assertEqual(journal.bank_account_id.id, self.bank.id)
        self.assertEqual(self.bank.print_report, True)
        self.assertEqual(journal.print_report, True)

    def test_journal_bank_write(self):
        self.assertEqual(self.bank.print_report, False)
        journal = self.env["account.journal"].create(
            {
                "name": "Bank Journal",
                "code": "TBNKCAMT",
                "type": "bank",
                "bank_account_id": self.bank.id,
            }
        )
        self.assertEqual(self.bank.print_report, False)
        journal.write({"print_report": True})
        self.assertEqual(journal.bank_account_id.id, self.bank.id)
        self.assertEqual(journal.print_report, True)
        self.assertEqual(self.bank.print_report, True)
