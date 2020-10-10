# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import datetime

from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestInvoiceCurrencyRate(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.invoice = cls.init_invoice(
            "in_invoice", products=cls.product_a + cls.product_b
        )
        cls.usd_currency = cls.env.ref("base.USD")
        cls.ron_currency = cls.env.ref("base.RON")
        cls.usd_currency.write({"rate": 1.0})
        cls.ron_currency.write({"active": True, "rate": 1.0})
        cls.curr_year = datetime.date.today().year
        cls.prev_year = cls.curr_year - 1

    def test_invoice_currency_rate(self):
        """Test download file and partner link."""
        self.env["res.currency.rate"].search([]).unlink()
        date_to = datetime.date(self.prev_year, 12, 31)
        today = datetime.date.today()
        self.env["res.currency.rate"].create(
            dict(currency_id=self.ron_currency.id, name=date_to, rate=2)
        )
        self.env["res.currency.rate"].create(
            dict(currency_id=self.ron_currency.id, name=today, rate=4)
        )
        move_form = Form(self.invoice)
        move_form.partner_id = self.partner_a
        move_form.invoice_date = date_to
        move_form.currency_id = self.ron_currency
        move_form.save()
        self.assertEqual(self.invoice.currency_rate, 0.5)
        move_form.invoice_date = today
        move_form.save()
        self.assertEqual(self.invoice.currency_rate, 0.25)
