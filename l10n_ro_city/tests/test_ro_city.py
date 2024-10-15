# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo.tests.common import Form, TransactionCase


class TestRoCity(TransactionCase):
    def setUp(self):
        super(TestRoCity, self).setUp()
        self.city_1 = self.env.ref("base.RO_22585")
        self.city_2 = self.env.ref("base.RO_21588")
        self.city_3 = self.env.ref("base.RO_6734")
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
