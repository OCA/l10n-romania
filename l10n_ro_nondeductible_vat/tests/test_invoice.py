# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from .common import TestNondeductibleCommon

_logger = logging.getLogger(__name__)


class TestNonDeductibleInvoice(TestNondeductibleCommon):
    def test_invoice(self):
        self.make_purchase_notdeductible()
        self.check_account_valuation(10, self.account_vat_deductible)
        self.check_account_valuation(-5, self.account_vat_colected)
        self.check_account_valuation(50, self.account_expense)
        self.check_account_valuation(55, self.account_expense_nondeductible)
        self.check_account_valuation(5, self.account_expense_vat_nondeductible)
