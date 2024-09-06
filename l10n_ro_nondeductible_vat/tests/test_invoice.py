# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo.tests import tagged

from .common import TestNondeductibleCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestNonDeductibleInvoice(TestNondeductibleCommon):
    def test_invoice(self):
        self.make_purchase_notdeductible()
        self.check_account_valuation(5, self.account_vat_deductible)
        self.check_account_valuation(50, self.account_expense)
        self.check_account_valuation(50, self.account_expense_nondeductible)
        self.check_account_valuation(5, self.account_expense_vat_nondeductible)

    def test_invoice_cash_basis(self):
        self.make_purchase_notdeductible(fiscal_position=self.fptvainc)
        line = self.invoice.invoice_line_ids[0]
        self.assertEqual(line.tax_ids, self.tax_10_nondeductible_cash_basis)
        self.check_no_move_lines(self.account_vat_deductible)
        self.check_account_valuation(50, self.account_expense)
        self.check_account_valuation(50, self.account_expense_nondeductible)
        self.check_no_move_lines(self.account_expense_vat_nondeductible)
        self.check_account_valuation(10, self.uneligible_deductible_tax_account_id)

        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=self.invoice.ids
        ).create(
            {
                "payment_date": self.invoice.date,
            }
        )._create_payments()
        _logger.info("Factura platita")
        self.check_account_valuation(5, self.account_vat_deductible)
        self.check_account_valuation(50, self.account_expense)
        self.check_account_valuation(50, self.account_expense_nondeductible)
        self.check_account_valuation(5, self.account_expense_vat_nondeductible)
        self.check_account_valuation(0, self.uneligible_deductible_tax_account_id)
