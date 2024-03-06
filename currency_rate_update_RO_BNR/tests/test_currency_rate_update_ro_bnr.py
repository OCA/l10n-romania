from odoo import fields
from odoo.tests.common import SavepointCase


class TestCurrencyRateUpdateRoBnr(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.Company = cls.env["res.company"]
        cls.CurrencyRate = cls.env["res.currency.rate"]
        cls.CurrencyRateProvider = cls.env["res.currency.rate.provider"]

        cls.today = fields.Date.today()
        cls.eur_currency = cls.env.ref("base.EUR")
        cls.usd_currency = cls.env.ref("base.USD")
        cls.ron_currency = cls.env.ref("base.RON")
        cls.ron_currency.write({"active": True, "rate": 1.0})
        # Create another company.
        cls.company = cls.env["res.company"].search([], limit=1)
        cls.company.currency_id = cls.ron_currency

        # By default, tests are run with the current user set
        # on the first company.
        cls.env.user.company_id = cls.company
        cls.bnr_provider = cls.CurrencyRateProvider.create(
            {
                "service": "RO_BNR",
                "currency_ids": [(4, cls.usd_currency.id), (4, cls.ron_currency.id)],
            }
        )
        cls.CurrencyRate.search([]).unlink()

    def test_supported_currencies_RO_BNR(self):
        self.bnr_provider._get_supported_currencies()

    def test_update_RO_BNR_today(self):
        """No checks are made since today may not be a banking day"""
        self.bnr_provider._update(self.today, self.today)
        self.CurrencyRate.search([("currency_id", "=", self.usd_currency.id)]).unlink()
