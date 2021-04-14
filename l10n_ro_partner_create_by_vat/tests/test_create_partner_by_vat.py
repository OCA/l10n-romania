# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import common


class TestCreatePartnerBase(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestCreatePartnerBase, cls).setUpClass()
        cls.mainpartner = cls.env["res.partner"].create({"name": "Test partner"})


class TestCreatePartner(TestCreatePartnerBase):
    def test_vat_anaf(self):
        """ Check methods vat from ANAF."""
        # Test retrieve information from ANAF
        result = self.mainpartner._get_Anaf("30834857")
        if result:
            res = self.mainpartner._Anaf_to_Odoo(result)
            self.assertEqual(res["name"], "FOREST AND BIOMASS ROMÂNIA S.A.")
            self.assertEqual(res["vat_subjected"], True)
            self.assertEqual(res["company_type"], "company")
            self.assertEqual(res["nrc"], "J35/2622/2012")
            self.assertEqual(res["street"], "Ciprian Porumbescu Nr.12 Zona Nr.3 Etaj 1")
            self.assertEqual(res["state_id"], self.env.ref("base.RO_TM"))
            self.assertEqual(res["city"], "Timișoara")
            self.assertEqual(res["zip"], "307225")
            self.assertEqual(res["phone"], "0356179038")

    def test_onchange_vat_anaf(self):
        """ Check onchange vat from ANAF."""
        # Test onchange from ANAF
        self.mainpartner.vat = "RO30834857"
        self.mainpartner.ro_vat_change()
        self.assertEqual(self.mainpartner.name, "FOREST AND BIOMASS ROMÂNIA S.A.")
        self.assertEqual(
            self.mainpartner.street, "Ciprian Porumbescu Nr.12 Zona Nr.3 Etaj 1"
        )
        self.assertEqual(self.mainpartner.state_id, self.env.ref("base.RO_TM"))
        self.assertEqual(self.mainpartner.city, "Timișoara")
        self.assertEqual(self.mainpartner.country_id, self.env.ref("base.ro"))
        # Check inactive vatnumber
        self.mainpartner.vat = "RO27193515"
        self.mainpartner.ro_vat_change()
        self.assertEqual(
            self.mainpartner.name, "FOREST AND BIOMASS SERVICES ROMANIA S.A."
        )
        self.assertEqual(
            self.mainpartner.street, "Cal. Buziașului Nr.11 A Corp B Zona Nr.1 Etaj 3"
        )
        self.assertEqual(self.mainpartner.state_id, self.env.ref("base.RO_TM"))
        self.assertEqual(self.mainpartner.city, "Timișoara")
        self.assertEqual(self.mainpartner.country_id, self.env.ref("base.ro"))
        # Check address from commune
        self.mainpartner.vat = "RO8235738"
        self.mainpartner.ro_vat_change()
        self.assertEqual(self.mainpartner.name, "HOLZINDUSTRIE ROMANESTI S.R.L.")
        self.assertEqual(self.mainpartner.street, "Românești Nr.69/A")
        self.assertEqual(self.mainpartner.state_id, self.env.ref("base.RO_TM"))
        self.assertEqual(self.mainpartner.city, "Sat Românești Com. Tomești")
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
        self.assertEqual(
            self.mainpartner.street, "Alexander Von Humboldt Nr.10 Et.Parter"
        )
        self.assertEqual(self.mainpartner.state_id, self.env.ref("base.RO_B"))
        self.assertEqual(self.mainpartner.city, "Sector 3")
        self.assertEqual(self.mainpartner.country_id, self.env.ref("base.ro"))
        self.assertEqual(self.mainpartner.vat, "4264242")
        self.mainpartner.onchange_vat_subjected()
        self.assertEqual(self.mainpartner.vat, "RO4264242")
        self.assertEqual(self.mainpartner.vat_subjected, True)
        # Check address from vat without country code - no vat subjected
        self.mainpartner.vat_subjected = False
        self.mainpartner.vat = "36525532"
        self.mainpartner.ro_vat_change()
        self.mainpartner.onchange_vat_subjected()
        self.assertEqual(self.mainpartner.name, "COLOR 4 YOU S.R.L.")
        self.assertEqual(self.mainpartner.street, "Voinicilor Bl.1C Ap.18")
        self.assertEqual(self.mainpartner.state_id, self.env.ref("base.RO_AR"))
        self.assertEqual(self.mainpartner.city, "Arad")
        self.assertEqual(self.mainpartner.country_id, self.env.ref("base.ro"))
        self.assertEqual(self.mainpartner.vat_subjected, False)
        # Check split vat with no country code in vat
        vat_country, vat_number = self.mainpartner._split_vat(self.mainpartner.vat)
        self.assertEqual(vat_country, "ro")
        self.assertEqual(vat_number, "36525532")
        # Check vat subjected onchange
        self.mainpartner.vat_subjected = True
        self.mainpartner.onchange_vat_subjected()
        self.mainpartner.ro_vat_change()
        self.assertEqual(self.mainpartner.vat_subjected, False)
