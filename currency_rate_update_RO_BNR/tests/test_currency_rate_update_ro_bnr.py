# Copyright 2018 Forest and Biomass Romania
# Copyright 2020 OdooERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from unittest import mock

from odoo import fields
from odoo.tests import tagged

from odoo.addons.account.tests.account_test_savepoint import AccountingSavepointCase

_module_ns = "odoo.addons.currency_rate_update_RO_BNR"
_file_ns = _module_ns + ".models.res_currency_rate_provider_RO_BNR"
_RO_BNR_provider_class = _file_ns + ".ResCurrencyRateProviderROBNR"


@tagged("post_install", "-at_install")
class TestCurrencyRateUpdateRoBnr(AccountingSavepointCase):
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
        cls.company_data = cls.setup_company_data("Test company")
        cls.company = cls.company_data["company"]
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

    def test_error_RO_BNR(self):
        with mock.patch(_RO_BNR_provider_class + "._obtain_rates", return_value=None):
            self.bnr_provider._update(self.today, self.today)

    def test_update_RO_BNR_today(self):
        """No checks are made since today may not be a banking day"""
        self.bnr_provider._update(self.today, self.today)
        self.CurrencyRate.search([("currency_id", "=", self.usd_currency.id)]).unlink()

    def test_update_RO_BNR_scheduled(self):
        self.bnr_provider.interval_type = "days"
        self.bnr_provider.interval_number = 1
        self.bnr_provider.next_run = self.today
        self.bnr_provider._scheduled_update()

        rates = self.CurrencyRate.search(
            [("currency_id", "=", self.usd_currency.id)], limit=1
        )
        self.assertTrue(rates)

        self.CurrencyRate.search([("currency_id", "=", self.usd_currency.id)]).unlink()
