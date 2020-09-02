# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo.tests.common import TransactionCase


class TestRoCity(TransactionCase):
    def setUp(self):
        super(TestRoCity, self).setUp()
        self.city_1 = self.env.ref("base.RO_22585")
        self.city_2 = self.env.ref("base.RO_21588")
        self.state_bc = self.env.ref("base.RO_BC")

    def test_city(self):
        self.assertEqual(self.city_1.name, "Filipești")

        name = self.city_1.name_get()
        self.assertEqual(name[0][1], "Filipești (BC)")

        name = self.city_2.name_get()
        self.assertEqual(name[0][1], "Filipești (Bogdănești) (BC)")

    def test_partner_on_change_city(self):
        partner_1 = self.env["res.partner"].create(
            {"name": "Partener Test City", "state_id": self.state_bc.id}
        )
        res = partner_1.onchange_state()
        self.assertEqual(
            res["domain"]["city_id"], [("state_id", "=", self.state_bc.id)]
        )
