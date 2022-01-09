# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from .common import TestNondeductibleCommon

_logger = logging.getLogger(__name__)


class TestStockInventoryNondeductible(TestNondeductibleCommon):
    def test_minus_inventory(self):
        self.make_purchase()
        self.check_account_valuation(19, self.account_vat_deductible)
        self.check_account_valuation(100, self.account_valuation)

        _logger.info("Start inventar produse")
        self.make_inventory()
        _logger.info("Inventar facut")

        _logger.info("Start verificare balanta consum")
        self.check_account_valuation(19, self.account_vat_deductible)
        self.check_account_valuation(50, self.account_valuation)
        self.check_account_valuation(-2.5, self.account_vat_colected)
        self.check_account_valuation(25, self.account_expense)
        self.check_account_valuation(27.5, self.account_expense_nondeductible)
