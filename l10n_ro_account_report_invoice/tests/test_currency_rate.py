# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import datetime

from odoo import tools
from odoo.modules.module import get_resource_path
from odoo.tests.common import SavepointCase


class TestInvoiceCurrencyRate(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Company = cls.env["res.company"]
        cls.CurrencyRate = cls.env["res.currency.rate"]
        cls.partner_model = cls.env["res.partner"]
        cls.invoice_model = cls.env["account.move"]
        cls.usd_currency = cls.env.ref("base.USD")
        cls.ron_currency = cls.env.ref("base.RON")
        cls.usd_currency.write({"rate": 1.0})
        cls.ron_currency.write({"active": True, "rate": 1.0})
        # load account_minimal_test.xml file for chart of account in configuration
        tools.convert_file(
            cls.cr,
            "l10n_ro_account_report_invoice",
            get_resource_path("account", "test", "account_minimal_test.xml"),
            {},
            "init",
            False,
            "test",
            cls.registry._assertion_report,
        )
        cls.curr_year = datetime.date.today().year
        cls.prev_year = cls.curr_year - 1

        # By default, tests are run with the current user set
        # on the first company.
        cls.partner1 = cls.partner_model.create(
            {"name": "NextERP Romania", "vat": "RO39187746"}
        )
        default_line_account = cls.env["account.account"].search(
            [
                ("internal_type", "=", "other"),
                ("deprecated", "=", False),
                ("company_id", "=", cls.env.user.company_id.id),
            ],
            limit=1,
        )
        cls.invoice_line = [
            (
                0,
                False,
                {
                    "name": "Test description #1",
                    "product_id": cls.env.ref("product.product_delivery_01").id,
                    "account_id": default_line_account.id,
                    "quantity": 1.0,
                    "price_unit": 100.0,
                },
            )
        ]
        cls.invoice = cls.invoice_model.create(
            {
                "partner_id": cls.partner1.id,
                "type": "in_invoice",
                "invoice_date": datetime.date(cls.curr_year, 1, 1),
                "invoice_line_ids": cls.invoice_line,
            }
        )

    def test_invoice_currency_rate(self):
        """Test download file and partner link."""
        self.env["res.currency.rate"].search([]).unlink()
        date_to = datetime.date(self.prev_year, 12, 31)
        today = datetime.date.today()
        self.env["res.currency.rate"].create(
            dict(currency_id=self.usd_currency.id, name=date_to, rate=2)
        )
        self.env["res.currency.rate"].create(
            dict(currency_id=self.usd_currency.id, name=today, rate=4)
        )
        self.invoice.currency_id = self.usd_currency
        self.assertEqual(self.invoice.currency_rate, 0.5)
        self.invoice.invoice_date = today
        self.assertEqual(self.invoice.currency_rate, 0.25)
