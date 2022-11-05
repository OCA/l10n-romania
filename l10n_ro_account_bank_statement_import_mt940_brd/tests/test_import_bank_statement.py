# Copyright (C) 2016 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import base64
from odoo.modules.module import get_module_resource
from odoo.tests.common import SavepointCase

class TestGenerateBankStatement(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        bank = cls.env["res.partner.bank"].create(
            {
                "acc_number": "RO56BRDE360SV52474653600",
                "partner_id": cls.env.ref("base.main_partner").id,
                "company_id": cls.env.ref("base.main_company").id,
                "bank_id": cls.env.ref("base.res_bank_1").id,
            }
        )
        cls.env["res.partner.bank"].create(
            {
                "acc_number": "RO89RZBR0000060003480121",
                "partner_id": cls.env.ref("base.main_partner").id,
                "company_id": cls.env.ref("base.main_company").id,
                "bank_id": cls.env.ref("base.res_bank_1").id,
            }
        )
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Bank Journal - (test mt940 brd)",
                "code": "TBNKBRD",
                "type": "bank",
                "bank_account_id": bank.id,
                "currency_id": cls.env.ref("base.RON").id,
            }
        )

    def _load_statement(self):
        testfile = get_module_resource(
            "l10n_ro_account_bank_statement_import_mt940_brd", "test_files", "test_brd_940.txt"
        )
        with open(testfile, "rb") as datafile:
            camt_file = base64.b64encode(datafile.read())
            self.env["account.statement.import"].create(
                {
                    "statement_filename": "test import",
                    "statement_file": camt_file,
                }
            ).import_file_button()
            bank_st_record = self.env["account.bank.statement"].search(
                [("name", "=", "00138/1")], limit=1
            )
            return bank_st_record

    def test_statement_import(self):
        """Test correct creation of single statement."""
        bank_st_record = self._load_statement()
        self.assertEquals(bank_st_record.balance_start, 3885.24)
        self.assertEquals(bank_st_record.balance_end_real, 3671.88)

        line = bank_st_record.line_ids[-1]
        self.assertEquals(line.name, 'PLATA FACT 4603309')
        self.assertEquals(line.amount, -210.60)
