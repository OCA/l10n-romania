#
# ©  2008-2020 Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


from odoo.tests.common import TransactionCase


class TestRoCity(TransactionCase):
    def setUp(self):
        super(TestRoCity, self).setUp()

    def test_city(self):
        city_1 = self.env.ref("base.RO_22585")
        self.assertEqual(city_1.name, "Filipești")
