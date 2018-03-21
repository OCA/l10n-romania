# © 2017 Comunitea
# © 2018 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import common


class TestCurrencyRateUpdateRoBnr(common.SavepointCase):

    def setUp(self):
        super(TestCurrencyRateUpdateRoBnr, self).setUp()
        self.usd = self.env.ref('base.USD')
        self.euro = self.env.ref('base.EUR')
        self.ron = self.env.ref('base.RON')
        self.ron.write({'active': True})
        currency_rates = self.env['res.currency.rate'].search(
            [('currency_id', '=', self.usd.id)])
        currency_rates.unlink()
        currency_rates = self.env['res.currency.rate'].search(
            [('currency_id', '=', self.euro.id)])
        currency_rates.unlink()
        currency_rates = self.env['res.currency.rate'].search(
            [('currency_id', '=', self.ron.id)])
        currency_rates.unlink()
        self.main_currency = self.env.user.company_id.currency_id
        self.update_service = self.env['currency.rate.update.service'].create({
            'service': 'RO_BNR',
            'currency_to_update': [(6, 0,
                                    [self.euro.id, self.ron.id, self.usd.id])]
        })

    def test_currency_rate_update_USD_RON(self):
        curr = self.ron
        if self.main_currency.name == 'RON':
            curr = self.usd
        self.update_service.refresh_currency()
        currency_rates = self.env['res.currency.rate'].search(
            [('currency_id', '=', curr.id)])
        self.assertTrue(currency_rates)

    def test_currency_rate_update_USD_EUR(self):
        curr = self.euro
        if self.main_currency.name == 'EUR':
            curr = self.ron
        self.update_service.refresh_currency()
        currency_rates = self.env['res.currency.rate'].search(
            [('currency_id', '=', curr.id)])
        self.assertTrue(currency_rates)
