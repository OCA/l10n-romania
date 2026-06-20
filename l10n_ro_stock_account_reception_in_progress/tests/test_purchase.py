# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
import os
from contextlib import closing

from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestROStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockReceptionInProgress(TestROStockCommon):
    @classmethod
    @TestROStockCommon.setup_country("ro")
    def setUpClass(cls):
        super().setUpClass()
        cls.log_checks = False
        cls.l10n_ro_approved_price_difference = True
        cls.env.company.l10n_ro_stock_acc_price_diff = True
        # Account used to hold the value of the goods while the reception is
        # in progress (Romanian account 327 "Goods being received").
        cls.acc_327 = cls.env["account.account"].search(
            [
                ("code", "=", "327000"),
                ("company_ids", "in", cls.env.company.id),
            ],
            limit=1,
        )
        if not cls.acc_327:
            cls.acc_327 = cls.env["account.account"].create(
                {
                    "code": "327000",
                    "name": "Marfuri in curs de aprovizionare",
                    "account_type": "asset_current",
                    "company_ids": [(6, 0, cls.env.company.ids)],
                }
            )
        cls.account_valuation.l10n_ro_reception_in_progress_account_id = cls.acc_327

    def test_reception_in_progress(self):
        module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        filename = "test_reception_in_progress.csv"
        test_cases = self.read_test_cases_from_csv_file(filename, module_dir=module_dir)
        for _key, case in test_cases.items():
            _logger.info(
                "Running test case: %s - %s", case.get("code"), case.get("name")
            )
            with self.subTest(case=case), closing(self.cr.savepoint()):
                self.test_case(case)
