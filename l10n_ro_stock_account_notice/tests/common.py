from odoo.addons.l10n_ro_stock_account.tests.common import TestStockCommon
from odoo.tests import tagged


from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import (
    ValuationReconciliationTestCommon,
)

@tagged("post_install", "-at_install")
class TestStockCommon(ValuationReconciliationTestCommon):
    @classmethod
    def setUpAccounts(cls):
        def get_account(code):
            account = cls.env["account.account"].search([("code", "=", code)], limit=1)
            return account
        
        cls.stock_picking_payable_account_id = (
            cls.env.user.company_id.property_stock_picking_payable_account_id
        )
        if not cls.stock_picking_payable_account_id:
            cls.stock_picking_payable_account_id = get_account("408000")

        cls.env.user.company_id.property_stock_picking_payable_account_id = (
            cls.stock_picking_payable_account_id
        )

        cls.stock_picking_receivable_account_id = (
            cls.env.user.company_id.property_stock_picking_receivable_account_id
        )
        if not cls.stock_picking_receivable_account_id:
            cls.stock_picking_receivable_account_id = get_account("418000")

        cls.env.user.company_id.property_stock_picking_receivable_account_id = (
            cls.stock_picking_receivable_account_id
        )
        super(TestStockCommon, cls).setUpAccounts()

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super(TestStockCommon, cls).setUpClass(chart_template_ref=chart_template_ref)