# Copyright (C) 2020 Terrabit
# Copyright (C) 2025 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
import os
from contextlib import closing

from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestROStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockAvg(TestROStockCommon):
    @TestROStockCommon.setup_country("ro")
    def setUp(cls):
        super().setUp()

    def test_ro_stock_product_avg(self):
        module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        filename = "test_cases_avg.csv"
        test_cases = self.read_test_cases_from_csv_file(filename, module_dir=module_dir)
        for _key, case in test_cases.items():
            _logger.info(
                "Running test case: %s - %s", case.get("code"), case.get("name")
            )
            with self.subTest(case=case), closing(self.cr.savepoint()):
                self.test_case(case)
