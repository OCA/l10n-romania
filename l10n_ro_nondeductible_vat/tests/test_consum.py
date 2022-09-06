# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo.tests import tagged

from .common import TestNondeductibleCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockConsumNondeductible(TestNondeductibleCommon):
    def test_consume(self):
        self.make_purchase()
        self.check_account_valuation(19, self.account_vat_deductible)
        self.check_account_valuation(100, self.account_valuation)

        _logger.info("Start consum produse")
        self.make_consume()
        _logger.info("Consum facut")

        _logger.info("Start verificare balanta consum")
        self.check_account_valuation(18.5, self.account_vat_deductible)
        self.check_account_valuation(90, self.account_valuation)
        self.check_account_valuation(5, self.account_expense)
        self.check_account_valuation(5, self.account_expense_nondeductible)
        self.check_account_valuation(0.5, self.account_expense_vat_nondeductible)
