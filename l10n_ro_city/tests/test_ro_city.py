# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo.tests.common import Form, TransactionCase


class TestRoCity(TransactionCase):
    def setUp(self):
        super(TestRoCity, self).setUp()
        self.env.company.anglo_saxon_accounting = True
        self.env.company.l10n_ro_accounting = True
        self.city_1 = self.env.ref("l10n_ro_city.RO_22585")
        self.city_2 = self.env.ref("l10n_ro_city.RO_21588")
        self.city_3 = self.env.ref("l10n_ro_city.RO_6734")
        self.state_bc = self.env.ref("base.RO_BC")

    def test_city(self):
        self.assertEqual(self.city_1.name, "Filipești")

        name = self.city_1.name_get()
        self.assertEqual(name[0][1], "Filipești (BC)")

        name = self.city_2.name_get()
        self.assertEqual(name[0][1], "Filipești (Bogdănești) (BC)")

    def test_partner_on_change_city(self):
        city_obj = self.env["res.city"]
        with Form(self.env["res.partner"]) as partner_form:
            partner_form.name = "Test State Onchange"
            partner_form.city_id = self.city_3

            # Changes state, which triggers onchange
            partner_form.state_id = self.state_bc

        self.assertEqual(partner_form.city_id, city_obj)

    def test_completare_zip(self):
        partner_form = Form(self.env["res.partner"])
        partner_form.country_id = self.env.ref("base.ro")
        # competare cod postal filipesti
        partner_form.zip = "607185"
        self.assertEqual(partner_form.city_id.name, "Filipești")

        partner_form.zip = "030011"
        self.assertEqual(partner_form.city_id.name, "Sector3")
