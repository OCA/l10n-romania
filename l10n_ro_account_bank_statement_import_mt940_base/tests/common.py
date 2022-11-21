# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64

from odoo.tests.common import SavepointCase


class TestMT940BankStatementImport(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def create_partner_bank(self, bank_acc):
        bank = self.env["res.partner.bank"].create(
            {
                "acc_number": bank_acc,
                "partner_id": self.env.ref("base.main_partner").id,
                "company_id": self.env.ref("base.main_company").id,
                "bank_id": self.env.ref("base.res_bank_1").id,
            }
        )
        return bank

    def create_journal(self, code, partner_bank, currency):
        journal = self.env["account.journal"].create(
            {
                "name": partner_bank.acc_number,
                "code": code,
                "type": "bank",
                "bank_account_id": partner_bank.id,
                "currency_id": currency.id,
            }
        )
        return journal

    def _load_statement(self, testfile, mt940_type="mt940_general"):
        with open(testfile, "rb") as datafile:
            stmt_file = base64.b64encode(datafile.read())
            self.env["account.statement.import"].with_context(type=mt940_type).create(
                {
                    "statement_filename": "test import",
                    "statement_file": stmt_file,
                }
            ).import_file_button()

    def get_statements(self, journal):
        return self.env["account.bank.statement"].search([("journal_id", "=", journal)])
