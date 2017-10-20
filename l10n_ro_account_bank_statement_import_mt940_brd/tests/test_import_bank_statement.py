# -*- coding: utf-8 -*-
# ©  2016 Forest and Biomass Services Romania
# See README.rst file on addons root folder for license details

from openerp.tests.common import TransactionCase
from openerp.modules.module import get_module_resource


class TestBRDImport(TransactionCase):
    """Run test to import MT940 BRD import."""

    def setUp(self):
        super(TestBRDImport, self).setUp()
        self.statement_import_model = self.env['account.bank.statement.import']
        self.bank_statement_model = self.env['account.bank.statement']

    def test_statement_import(self):
        """Test correct creation of single statement."""
        brd_file_path = get_module_resource(
            'l10n_ro_account_bank_statement_import_mt940_brd',
            'test_files', 'test_brd_940.txt')
        brd_file = open(brd_file_path, 'rb').read().encode('base64')
        bank_statement = self.statement_import_model.create(
            dict(data_file=brd_file))
        bank_statement.import_file()
        bank_st_record = self.bank_statement_model.search(
            [('name', '=', '00138/1')])[0]
        self.assertEquals(bank_st_record.balance_start, 3885.24)
        self.assertEquals(bank_st_record.balance_end_real, 3671.88)

        line = bank_st_record.line_ids[0]
        self.assertEquals(line.name, 'PLATA FACT 4603309')
        self.assertEquals(line.amount, -210.60)
