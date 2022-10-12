# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import datetime

from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestInvoiceCurrencyRateEdit(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        ro_template_ref = "l10n_ro.ro_chart_template"
        super().setUpClass(chart_template_ref=ro_template_ref)
        cls.env.company.l10n_ro_accounting = True

        cls.invoice = cls.init_invoice("in_invoice", products=cls.product_a)
        cls.usd_currency = cls.env.ref("base.USD")
        cls.ron_currency = cls.env.ref("base.RON")
        cls.usd_currency.write({"rate": 1.0})
        cls.ron_currency.write({"active": True, "rate": 1.0})
        cls.curr_year = datetime.date.today().year
        cls.prev_year = cls.curr_year - 1

    def test_invoice_currency_rate(self):
        self.env["res.currency.rate"].search([]).unlink()
        date_to = datetime.date(self.prev_year, 12, 31)
        today = datetime.date.today()
        self.env["res.currency.rate"].create(
            dict(currency_id=self.usd_currency.id, name=date_to, rate=0.2)
        )
        self.env["res.currency.rate"].create(
            dict(currency_id=self.usd_currency.id, name=today, rate=0.1)
        )
        move_form = Form(self.invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 1
            line_form.price_unit = 100
            line_form.tax_ids.clear()

        move_form.partner_id = self.partner_a
        move_form.invoice_date = date_to
        move_form.currency_id = self.usd_currency
        move_form.save()
        self.assertEqual(self.invoice.amount_total_signed, -500)

        move_form.invoice_date = today
        move_form.save()
        self.assertEqual(self.invoice.amount_total_signed, -1000)

        # edit currency rate
        move_form.l10n_ro_currency_rate = 5

        move_form.save()
        self.assertEqual(self.invoice.amount_total_signed, -500)

        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 2
            line_form.price_unit = 100
        move_form.save()
        self.assertEqual(self.invoice.amount_total_signed, -1000)

        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit = 50
            line_form.quantity = 2
        move_form.save()
        self.assertEqual(self.invoice.amount_total_signed, -500)

        move_form.invoice_date = date_to
        move_form.save()
        self.assertEqual(self.invoice.l10n_ro_currency_rate, 5)
        self.assertEqual(self.invoice.amount_total_signed, -500)

    def test_invoice_currency_rate_with_tax_line(self):
        self.env["res.currency.rate"].search([]).unlink()
        date_to = datetime.date(self.prev_year, 12, 31)
        today = datetime.date.today()
        self.env["res.currency.rate"].create(
            dict(currency_id=self.usd_currency.id, name=date_to, rate=0.1)
        )
        self.env["res.currency.rate"].create(
            dict(currency_id=self.usd_currency.id, name=today, rate=0.2)
        )
        move_form = Form(self.invoice)
        move_form.partner_id = self.partner_a
        move_form.invoice_date = today
        move_form.currency_id = self.usd_currency
        move_form.save()
        self.assertEqual(self.invoice.l10n_ro_currency_rate, 5)

        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 1
            line_form.price_unit = 100
            line_form.tax_ids.clear()
            line_form.tax_ids.add(self.tax_purchase_a)  # 19% tax rate
        move_form.save()
        self.assertEqual(self.invoice.amount_total_signed, -595)

        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 2
            line_form.price_unit = 100
        move_form.l10n_ro_currency_rate = 10
        move_form.save()
        self.assertEqual(self.invoice.amount_total_signed, -2380)
