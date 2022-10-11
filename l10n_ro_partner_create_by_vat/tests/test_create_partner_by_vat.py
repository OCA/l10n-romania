# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_ro_partner_create_by_vat.models import res_partner


@tagged("post_install", "-at_install")
class TestCreatePartnerBase(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        ro_template_ref = "l10n_ro.ro_chart_template"
        super(TestCreatePartnerBase, cls).setUpClass(chart_template_ref=ro_template_ref)
        cls.env.company.l10n_ro_accounting = True
        cls.mainpartner = cls.env["res.partner"].create({"name": "Test partner"})


@tagged("post_install", "-at_install")
class TestCreatePartner(TestCreatePartnerBase):
    def test_vat_anaf(self):
        """Check methods vat from ANAF."""
        # Test retrieve information from ANAF
        error, result = self.mainpartner._get_Anaf("30834857")
        if not error and result:
            res = self.mainpartner._Anaf_to_Odoo(result)
            self.assertEqual(res["name"], "FOREST AND BIOMASS ROMÂNIA S.A.")
            self.assertEqual(res["l10n_ro_vat_subjected"], True)
            self.assertEqual(res["company_type"], "company")
            self.assertEqual(res["nrc"], "J35/2622/2012")
            self.assertEqual(res["street"], "Str. Ciprian Porumbescu Nr. 12")
            self.assertEqual(res["street2"], "Zona Nr.3, Etaj 1")
            self.assertEqual(res["state_id"], self.env.ref("base.RO_TM"))
            self.assertEqual(res["city"], "Timișoara")
            self.assertEqual(res["zip"], "307225")
            self.assertEqual(res["phone"], "0356179038")

    def test_vat_anaf_error(self):
        """Check methods vat from ANAF."""
        # Test retrieve information from ANAF
        cod = "3083485711"
        error, result = self.mainpartner._get_Anaf(cod)
        self.assertTrue(len(error) > 3)
        cod = ["30834857", "3083485711"]
        error, result = self.mainpartner._get_Anaf(cod)
        if result:
            self.assertTrue(result.get("cod"))

    def test_onchange_vat_anaf(self):
        """Check onchange vat from ANAF."""
        # Test onchange from ANAF
        self.mainpartner.vat = "RO30834857"
        self.mainpartner.ro_vat_change()
        self.assertEqual(self.mainpartner.name, "FOREST AND BIOMASS ROMÂNIA S.A.")
        self.assertEqual(self.mainpartner.street, "Str. Ciprian Porumbescu Nr. 12")
        self.assertEqual(self.mainpartner.street2, "Zona Nr.3, Etaj 1")
        self.assertEqual(self.mainpartner.state_id, self.env.ref("base.RO_TM"))
        self.assertEqual(self.mainpartner.city, "Timișoara")
        self.assertEqual(self.mainpartner.country_id, self.env.ref("base.ro"))
        # Check inactive vatnumber
        self.mainpartner.vat = "RO27193515"
        self.mainpartner.ro_vat_change()
        self.assertEqual(
            self.mainpartner.name, "FOREST AND BIOMASS SERVICES ROMANIA S.A."
        )
        self.assertEqual(self.mainpartner.street, "Cal. Buziașului Nr. 11 A")
        self.assertEqual(self.mainpartner.street2, "Corp B, Zona Nr.1, Etaj 3")
        self.assertEqual(self.mainpartner.state_id, self.env.ref("base.RO_TM"))
        self.assertEqual(self.mainpartner.city, "Timișoara")
        self.assertEqual(self.mainpartner.country_id, self.env.ref("base.ro"))
        # Check address from commune
        self.mainpartner.vat = "RO8235738"
        self.mainpartner.ro_vat_change()
        self.assertEqual(self.mainpartner.name, "HOLZINDUSTRIE ROMANESTI S.R.L.")
        self.assertEqual(self.mainpartner.street, "Românești Nr. 69/A")
        self.assertEqual(self.mainpartner.state_id, self.env.ref("base.RO_TM"))
        self.assertEqual(self.mainpartner.city, "Sat Românești Com Tomești")
        self.assertEqual(self.mainpartner.country_id, self.env.ref("base.ro"))
        # Check address from vat without country code - vat subjected
        self.mainpartner.vat = "4264242"
        self.mainpartner.country_id = False
        self.mainpartner.ro_vat_change()
        self.assertEqual(self.mainpartner.name, "HOLZINDUSTRIE ROMANESTI S.R.L.")
        # Check address from vat without country code - vat subjected
        self.mainpartner.country_id = self.env.ref("base.ro")
        self.mainpartner.ro_vat_change()
        self.assertEqual(self.mainpartner.name, "CUMPANA 1993 SRL")
        self.assertEqual(self.mainpartner.street, "Str. Alexander Von Humboldt Nr. 10")
        self.assertEqual(self.mainpartner.street2, "")
        self.assertEqual(self.mainpartner.state_id, self.env.ref("base.RO_B"))
        self.assertEqual(self.mainpartner.city, "Sector 3")
        self.assertEqual(self.mainpartner.country_id, self.env.ref("base.ro"))
        self.assertEqual(self.mainpartner.vat, "RO4264242")
        self.mainpartner.onchange_l10n_ro_vat_subjected()
        self.assertEqual(self.mainpartner.vat, "RO4264242")
        self.assertEqual(self.mainpartner.l10n_ro_vat_subjected, True)
        # Check address from vat without country code - no vat subjected
        self.mainpartner.l10n_ro_vat_subjected = False
        self.mainpartner.vat = "RO42078234"
        self.mainpartner.ro_vat_change()
        self.mainpartner.onchange_l10n_ro_vat_subjected()
        self.assertEqual(
            self.mainpartner.name,
            "COJOCARU AURELIAN-MARCEL SOFTWARE PERSOANĂ FIZICĂ AUTORIZATĂ",
        )
        self.assertEqual(self.mainpartner.street, "Str. Holdelor Nr. 11")
        self.assertEqual(self.mainpartner.state_id, self.env.ref("base.RO_TM"))
        self.assertEqual(self.mainpartner.city, "Timișoara")
        self.assertEqual(self.mainpartner.country_id, self.env.ref("base.ro"))
        self.assertEqual(self.mainpartner.vat, "42078234")
        self.assertEqual(self.mainpartner.l10n_ro_vat_subjected, False)
        # Check split vat with no country code in vat
        vat_country, vat_number = self.mainpartner._split_vat(self.mainpartner.vat)
        self.assertEqual(vat_country, "ro")
        self.assertEqual(vat_number, "42078234")
        # Check vat subjected onchange
        self.mainpartner.l10n_ro_vat_subjected = True
        self.mainpartner.onchange_l10n_ro_vat_subjected()
        self.mainpartner.ro_vat_change()
        self.assertEqual(self.mainpartner.l10n_ro_vat_subjected, False)

    def test_anaf_no_data(self):
        """if a invalid vat will return a empty dictionary."""
        error, res = self.mainpartner._get_Anaf("30834857111")
        self.assertEqual(res, {})
        self.assertTrue(len(error) > 2)

    def test_anaf_exception(self):
        """Check anaf exception."""
        original_anaf_url = res_partner.ANAF_URL
        res_partner.ANAF_URL = (
            "https://webservicesp.anaf.ro/PlatitorTvaRest/api/v6/ws/tvaERROR"
        )
        error, res = self.mainpartner._get_Anaf("30834857")
        self.assertEqual(res, {})
        self.assertTrue(len(error) > 3)
        self.mainpartner.vat = "RO30834857"
        res = self.mainpartner.ro_vat_change()
        self.assertTrue(res.get("warning"))
        res_partner.ANAF_URL = original_anaf_url
