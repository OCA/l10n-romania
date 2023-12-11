from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from odoo import fields

from odoo.addons.base.tests.common import SavepointCaseWithUserDemo


class TestCurrencyRateUpdateRoBnr(SavepointCaseWithUserDemo):
    def setUp(self):
        super().setUp()

        self.Company = self.env["res.company"]
        self.CurrencyRate = self.env["res.currency.rate"]
        self.CurrencyRateProvider = self.env["res.currency.rate.provider"]

        self.today = fields.Date.today()
        self.eur_currency = self.env.ref("base.EUR")
        self.usd_currency = self.env.ref("base.USD")
        self.ron_currency = self.env.ref("base.RON")
        self.ron_currency.write({"active": True, "rate": 1.0})
        # Create another company.
        self.company = self.env["res.company"].search([], limit=1)
        self.company.currency_id = self.ron_currency

        # By default, tests are run with the current user set
        # on the first company.
        self.env.user.company_id = self.company
        self.bnr_provider = self.CurrencyRateProvider.search(
            [
                ("company_id", "=", self.company.id),
                ("service", "=", "RO_BNR"),
            ]
        )
        if not self.bnr_provider:
            self.bnr_provider = self.CurrencyRateProvider.create(
                {
                    "service": "RO_BNR",
                }
            )
        self.bnr_provider.currency_ids = [
            (4, self.usd_currency.id),
            (4, self.ron_currency.id),
        ]
        self.CurrencyRate.search([]).unlink()

    def test_supported_currencies_RO_BNR(self):
        self.bnr_provider._get_supported_currencies()

    def test_update_RO_BNR_today(self):
        """No checks are made since today may not be a banking day"""
        self.bnr_provider._update(self.today, self.today)
        self.CurrencyRate.search([("currency_id", "=", self.usd_currency.id)]).unlink()

    def test_update_RO_BNR_day_in_past(self):
        "we test a know date in past and should give us a result"
        self.bnr_provider._update(date(2022, 4, 8), date(2022, 4, 8))
        rate = self.CurrencyRate.search(
            [("currency_id", "=", self.usd_currency.id), ("name", "=", "2022-04-08")]
        )
        self.assertTrue(rate)
        rate.unlink()

    def test_update_RO_BNR_month(self):
        self.bnr_provider._update(self.today - relativedelta(months=1), self.today)

        rates = self.CurrencyRate.search(
            [("currency_id", "=", self.usd_currency.id)], limit=1
        )
        self.assertTrue(rates)

        self.CurrencyRate.search([("currency_id", "=", self.usd_currency.id)]).unlink()

    def test_update_RO_BNR_scheduled(self):
        self.bnr_provider.interval_type = "days"
        self.bnr_provider.interval_number = 1

        next_run = self.today
        if next_run.weekday() == 0:
            next_run = next_run - timedelta(days=2)

        self.bnr_provider.next_run = next_run
        self.bnr_provider._scheduled_update()

        rates = self.CurrencyRate.search(
            [("currency_id", "=", self.usd_currency.id)], limit=1
        )
        self.assertTrue(rates)

        self.CurrencyRate.search([("currency_id", "=", self.usd_currency.id)]).unlink()
