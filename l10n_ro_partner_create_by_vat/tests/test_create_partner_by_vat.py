# Copyright  2017 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import common


class TestCreatePartnerBase(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestCreatePartnerBase, cls).setUpClass()
        cls.mainpartner = cls.env.ref('base.res_partner_1')


class TestCreatePartner(TestCreatePartnerBase):
    def test_vat_anaf(self):
        ''' Check methods vat from ANAF.'''
        # Test retrive information from ANAF
        result = self.mainpartner._get_Anaf('30834857')
        if result:
            res = self.mainpartner._Anaf_to_Odoo(result)
            self.assertEqual(res['name'], 'FOREST AND BIOMASS ROMÂNIA S.A.')
            self.assertEqual(res['street'],
                             'Cal. Buziașului Nr.11 A Corp B Zona Nr.2 Et.3')
            self.assertEqual(res['state_id'], self.env.ref('l10n_ro.RO_TM').id)
            self.assertEqual(res['city'], 'Timișoara')

    def test_onchange_vat_anaf(self):
        ''' Check onchange vat from ANAF.'''
        # Test onchange from ANAF
        with self.env.do_in_onchange():
            self.mainpartner.vat = 'RO30834857'
            self.mainpartner.vies_vat_change()
            self.assertEqual(self.mainpartner.name,
                             'FOREST AND BIOMASS ROMÂNIA S.A.')
            self.assertEqual(self.mainpartner.street,
                             'Cal. Buziașului Nr.11 A Corp B Zona Nr.2 Et.3')
            self.assertEqual(self.mainpartner.state_id,
                             self.env.ref('l10n_ro.RO_TM'))
            self.assertEqual(self.mainpartner.city, 'Timișoara')
            self.assertEqual(self.mainpartner.country_id,
                             self.env.ref('base.ro'))
            # Check inactive vatnumber
            self.mainpartner.vat = 'RO27193515'
            self.mainpartner.vies_vat_change()
            self.assertEqual(self.mainpartner.name,
                             'FOREST AND BIOMASS SERVICES ROMANIA S.A.')
            self.assertEqual(self.mainpartner.street,
                             'Cal. Buziașului Nr.11 A Corp B Zona Nr.1 Etaj 3')
            self.assertEqual(self.mainpartner.state_id,
                             self.env.ref('l10n_ro.RO_TM'))
            self.assertEqual(self.mainpartner.city, 'Timișoara')
            self.assertEqual(self.mainpartner.country_id,
                             self.env.ref('base.ro'))
            # Check address from commune
            self.mainpartner.vat = 'RO8235738'
            self.mainpartner.vies_vat_change()
            self.assertEqual(self.mainpartner.name,
                             'HOLZINDUSTRIE ROMANESTI S.R.L.')
            self.assertEqual(self.mainpartner.street,
                             'Principala Românești Nr.69/A')
            self.assertEqual(self.mainpartner.state_id,
                             self.env.ref('l10n_ro.RO_TM'))
            self.assertEqual(self.mainpartner.city,
                             'Sat Românești Com. Tomești')
            self.assertEqual(self.mainpartner.country_id,
                             self.env.ref('base.ro'))
