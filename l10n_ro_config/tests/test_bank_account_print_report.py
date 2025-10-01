# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo.tests import common, tagged


@tagged("post_install", "-at_install")
class TestBankAccount(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bank = cls.env["res.partner.bank"].create(
            {
                "acc_number": "NL46ABNA0499998748",
                "partner_id": cls.env.ref("base.main_partner").id,
                "company_id": cls.env.ref("base.main_company").id,
                "bank_id": cls.env.ref("base.res_bank_1").id,
            }
        )

        cls.partner1 = cls.env["res.partner"].create(
            {
                "name": "Partner 1",
                "street": "Street 1",
                "city": "City 1",
                "country_id": cls.env.ref("base.ro").id,
            }
        )
        cls.partner2 = cls.env["res.partner"].create(
            {
                "name": "Partner 2",
                "street": "Street 2",
                "city": "City 2",
                "country_id": cls.env.ref("base.ro").id,
            }
        )
        cls.bank_test = cls.env["res.bank"].create(
            {
                "name": "Bank 1",
                "bic": "BIC 1",
            }
        )

    # def test_journal_bank_creation(self):
    #     self.assertEqual(self.bank.l10n_ro_print_report, False)
    #     journal = self.env["account.journal"].create(
    #         {
    #             "name": "Bank Journal",
    #             "code": "TBNKCAMT",
    #             "type": "bank",
    #             "bank_account_id": self.bank.id,
    #             "l10n_ro_print_report": True,
    #         }
    #     )
    #     self.assertEqual(journal.bank_account_id.id, self.bank.id)
    #     self.assertEqual(self.bank.l10n_ro_print_report, True)
    #     self.assertEqual(journal.l10n_ro_print_report, True)

    # def test_journal_bank_write(self):
    #     self.assertEqual(self.bank.l10n_ro_print_report, False)
    #     journal = self.env["account.journal"].create(
    #         {
    #             "name": "Bank Journal",
    #             "code": "TBNKCAMT",
    #             "type": "bank",
    #             "bank_account_id": self.bank.id,
    #         }
    #     )
    #     self.assertEqual(self.bank.l10n_ro_print_report, False)
    #     journal.write({"l10n_ro_print_report": True})
    #     self.assertEqual(journal.bank_account_id.id, self.bank.id)
    #     self.assertEqual(journal.l10n_ro_print_report, True)
    #     self.assertEqual(self.bank.l10n_ro_print_report, True)

    def test_create_bank_account_ro(self):
        company = self.env["res.company"].create(
            {
                "name": "Company 1",
                "street": "Street 1",
                "city": "City 1",
                "country_id": self.env.ref("base.ro").id,
                "l10n_ro_accounting": True,
            }
        )
        self.env["res.partner.bank"].create(
            {
                "acc_number": "NL46ABNA0499998749",
                "partner_id": self.partner1.id,
                "company_id": company.id,
                "bank_id": self.bank_test.id,
                "acc_type": "iban",
            }
        )
        self.env["res.partner.bank"].create(
            {
                "acc_number": "NL46ABNA0499998749",
                "partner_id": self.partner2.id,
                "company_id": company.id,
                "bank_id": self.bank_test.id,
                "acc_type": "iban",
            }
        )

    # def test_create_bank_account_ro2(self):
    #     company2 = self.env["res.company"].create(
    #         {
    #             "name": "Company 2",
    #             "street": "Street 2",
    #             "city": "City 2",
    #             "country_id": self.env.ref("base.ro").id,
    #             "l10n_ro_accounting": False,
    #         }
    #     )
    #     self.env["res.partner.bank"].create(
    #         {
    #             "acc_number": "NL46ABNA0499998749",
    #             "partner_id": self.partner1.id,
    #             "company_id": company2.id,
    #             "bank_id": self.bank_test.id,
    #             "acc_type": "iban",
    #         }
    #     )
    #     with self.assertRaises(psycopg2.errors.UniqueViolation):
    #         self.env["res.partner.bank"].create(
    #             {
    #                 "acc_number": "NL46ABNA0499998749",
    #                 "partner_id": self.partner1.id,
    #                 "company_id": company2.id,
    #                 "bank_id": self.bank_test.id,
    #                 "acc_type": "iban",
    #             }
    #         )
