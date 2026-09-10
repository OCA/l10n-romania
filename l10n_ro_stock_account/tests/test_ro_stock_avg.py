# Copyright (C) 2020 Terrabit
# Copyright (C) 2025 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from contextlib import closing

_logger = logging.getLogger(__name__)


class StockAvgCases:
    def test_ro_stock_product_avg(self):
        filename = "test_cases_avg.csv"
        test_cases = self.read_test_cases_from_csv_file(filename)
        for _key, case in test_cases.items():
            _logger.info(
                "Running test case: %s - %s", case.get("code"), case.get("name")
            )
            with self.subTest(case=case), closing(self.cr.savepoint()):
                self.run_test_case(case)
