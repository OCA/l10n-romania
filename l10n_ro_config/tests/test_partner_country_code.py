# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import common


class TestPartnerVATSubjected(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestPartnerVATSubjected, cls).setUpClass()
        cls.mainpartner = cls.env.ref("base.res_partner_1")


class TestPartnerVAT(TestPartnerVATSubjected):
    def test_onchange_l10n_ro_vat_subjected(self):
        """Check onchange vat subjected and country."""
        # test setting l10n_ro_vat_subjected as True
        self.mainpartner.vat = "4264242"
        self.mainpartner.country_id = self.env.ref("base.ro")
        self.mainpartner.l10n_ro_vat_subjected = True
        self.mainpartner.onchange_l10n_ro_vat_subjected()
        # Test setting l10n_ro_vat_subjected as False
        self.assertEqual(self.mainpartner.vat, "RO4264242")
        self.mainpartner.l10n_ro_vat_subjected = False
        self.mainpartner.onchange_l10n_ro_vat_subjected()
        self.assertEqual(self.mainpartner.vat, "RO4264242")
        # Check split vat with no country code in vat
        vat_country, l10n_ro_vat_number = self.mainpartner._split_vat(
            self.mainpartner.vat
        )
        self.assertEqual(vat_country, "ro")
        self.assertEqual(l10n_ro_vat_number, "4264242")
