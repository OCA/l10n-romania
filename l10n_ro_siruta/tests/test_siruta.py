# Copyright (C) 2017 Forest and Biomass Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import Form, common


class TestSirutaBase(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestSirutaBase, cls).setUpClass()
        cls.mainpartner = cls.env["res.partner"].create({"name": "TEST mainpartner"})

        cls.partner1 = cls.env["res.partner"].create(
            {"name": "TEST res_partner_address_1"}
        )
        cls.city1 = cls.env.ref("l10n_ro_siruta.RO_155252")
        cls.city2 = cls.env.ref("l10n_ro_siruta.RO_54984")
        cls.commune1 = cls.env.ref("l10n_ro_siruta.RO_155243")
        cls.commune2 = cls.env.ref("l10n_ro_siruta.RO_54975")
        cls.state1 = cls.env.ref("base.RO_TM")
        cls.state2 = cls.env.ref("base.RO_CJ")
        cls.zone1 = cls.env.ref("l10n_ro_siruta.RO_V")
        cls.zone2 = cls.env.ref("l10n_ro_siruta.RO_NV")


class TestSiruta(TestSirutaBase):
    def test_name_search(self):
        # Ar trebui sa avem si ceva asserturi aici
        self.env["res.country.zone"].name_search("")
        self.env["res.country.zone"].name_search("Centru")
        self.env["res.country.state"].name_search("")
        self.env["res.country.state"].name_search("centru")
        self.env["res.country.state"].name_search("bc")

        self.env["res.country.commune"].name_search("")
        self.env["res.country.commune"].name_search("bc")

        self.env["res.city"].name_search("")
        self.env["res.city"].name_search("bc")

    def test_onchange_city(self):
        """Check onchange city_id on partner and check if all the fields
        from main partner are changed."""

        mainpartner_form = Form(self.mainpartner)
        # User change city of main partner
        mainpartner_form.city_id = self.city1
        mainpartner_form.commune_id = self.commune2
        mainpartner_form.city_id = self.city1

        mainpartner_form.commune_id = self.commune1
        mainpartner_form.city_id = self.city2
        mainpartner_form.state_id = self.state1
        mainpartner_form.city_id = self.city1
        self.mainpartner = mainpartner_form.save()

        # Check main partner changed fields
        self.assertEqual(self.mainpartner.city, self.city1.name)
        self.assertEqual(self.mainpartner.commune_id.id, self.city1.commune_id.id)
        self.assertEqual(self.mainpartner.state_id.id, self.city1.state_id.id)
        self.assertEqual(self.mainpartner.zone_id.id, self.city1.zone_id.id)
        self.assertEqual(self.mainpartner.country_id.id, self.city1.country_id.id)

    def test_write_city(self):
        """Check write city_id on partner and check if all the fields
        from contacts are changed."""
        self.partner1.write({"city_id": self.city1.id})
        self.partner1._onchange_city_id()

        self.mainpartner.write({"city_id": self.city1.id})
        self.mainpartner._onchange_city_id()
        # Check contact changed fields from inheritance
        self.assertEqual(self.partner1.city_id.id, self.mainpartner.city_id.id)
        self.assertEqual(self.partner1.commune_id.id, self.mainpartner.commune_id.id)
        self.assertEqual(self.partner1.state_id.id, self.mainpartner.state_id.id)
        self.assertEqual(self.partner1.zone_id.id, self.mainpartner.zone_id.id)
        self.assertEqual(self.partner1.country_id.id, self.mainpartner.country_id.id)

    def test_onchange_state(self):
        """Check onchange zone_id on states."""
        state1_form = Form(self.state1)
        # User change zone of country state
        state1_form.zone_id = self.zone2
        self.state1 = state1_form.save()
        # self.state1._onchange_zone_id()

        # Check country state changed fields
        self.assertEqual(self.state1.country_id.id, self.zone2.country_id.id)

    def test_onchange_commune(self):
        """Check onchange state and zone on communes."""
        commune1_form = Form(self.commune1)
        # User change zone of country commune
        commune1_form.zone_id = self.zone2

        # self.commune1._onchange_zone_id()

        self.commune1 = commune1_form.save()

        # Check country commune changed fields
        self.assertEqual(self.commune1.country_id.id, self.zone2.country_id.id)
        self.assertFalse(self.commune1.state_id)

        # User change state of country commune
        commune1_form.state_id = self.state2
        self.commune1 = commune1_form.save()

        # Check country commune changed fields
        self.assertEqual(self.commune1.zone_id.id, self.state2.zone_id.id)
        self.assertEqual(self.commune1.country_id.id, self.state2.country_id.id)

    def test_onchange_city_fields(self):
        """Check onchange state and zone on cities."""
        # User change zone of country city
        city1_form = Form(self.city1)
        city1_form.zone_id = self.zone2
        # self.city1._onchange_zone_id()
        self.city1 = city1_form.save()

        # Check country commune changed fields
        self.assertEqual(self.city1.country_id.id, self.zone2.country_id.id)
        self.assertFalse(self.city1.state_id)
        self.assertFalse(self.city1.commune_id)

        # User change state of country city
        self.city1.state_id = self.state2.id
        self.city1._onchange_state_id()

        # Check country commune changed fields
        self.assertEqual(self.city1.zone_id.id, self.state2.zone_id.id)
        self.assertEqual(self.city1.country_id.id, self.state2.country_id.id)
        self.assertFalse(self.city1.commune_id)

        # User change commune of country city
        self.city1.commune_id = self.commune2.id
        self.city1._onchange_commune_id()

        # Check country commune changed fields
        self.assertEqual(self.city1.state_id.id, self.commune2.state_id.id)
        self.assertEqual(self.city1.zone_id.id, self.commune2.zone_id.id)
        self.assertEqual(self.city1.country_id.id, self.commune2.country_id.id)
