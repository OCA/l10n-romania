# Copyright (C) 2018 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase


class TestStreetFields(TransactionCase):
    def setUp(self):
        super(TestStreetFields, self).setUp()
        self.env.company.l10n_ro_accounting = True
        self.Partner = self.env["res.partner"]
        self.env.ref("base.be").write(
            {
                "street_format": "%(street_name)s, %(street_number)s/"
                "%(l10n_ro_street_staircase)s/%(street_number2)s"
            }
        )
        self.env.ref("base.us").write(
            {
                "street_format": "%(street_number)s/%(l10n_ro_street_staircase)s/"
                "%(street_number2)s %(street_name)s"
            }
        )
        self.env.ref("base.ch").write(
            {
                "street_format": "header %(street_name)s, %(street_number)s "
                "- %(l10n_ro_street_staircase)s - %(street_number2)s "
                "trailer"
            }
        )

    def create_and_assert(
        self,
        partner_name,
        country_id,
        street,
        street_name,
        street_number,
        l10n_ro_street_staircase,
        street_number2,
    ):
        partner = self.Partner.create(
            {"name": partner_name + "-1", "street": street, "country_id": country_id}
        )
        self.assertEqual(
            partner.street_name or "",
            street_name,
            "wrong street name for {}: {}".format(partner_name, partner.street_name),
        )
        self.assertEqual(
            partner.street_number or "",
            street_number,
            "wrong house number for {}: {}".format(partner_name, partner.street_number),
        )
        self.assertEqual(
            partner.l10n_ro_street_staircase or "",
            l10n_ro_street_staircase,
            "wrong house staircase for {}: {}".format(
                partner_name, partner.l10n_ro_street_staircase
            ),
        )
        self.assertEqual(
            partner.street_number2 or "",
            street_number2,
            "wrong door number for {}: {}".format(partner_name, partner.street_number2),
        )
        partner = self.Partner.create(
            {
                "name": partner_name + "-2",
                "street_name": street_name,
                "street_number": street_number,
                "l10n_ro_street_staircase": l10n_ro_street_staircase,
                "street_number2": street_number2,
                "country_id": country_id,
            }
        )
        self.assertEqual(
            partner.street or "",
            street,
            "wrong street for {}: {}".format(partner_name, partner.street),
        )
        return partner

    def write_and_assert(
        self,
        partner,
        vals,
        street,
        street_name,
        street_number,
        l10n_ro_street_staircase,
        street_number2,
    ):
        partner.write(vals)
        self.assertEqual(
            partner.street_name or "",
            street_name,
            "wrong street name: %s" % partner.street_name,
        )
        self.assertEqual(
            partner.street_number or "",
            street_number,
            "wrong house number: %s" % partner.street_number,
        )
        self.assertEqual(
            partner.l10n_ro_street_staircase or "",
            l10n_ro_street_staircase,
            "wrong house staircase: %s" % partner.l10n_ro_street_staircase,
        )
        self.assertEqual(
            partner.street_number2 or "",
            street_number2,
            "wrong door number: %s" % partner.street_number2,
        )
        self.assertEqual(
            partner.street or "", street, "wrong street: %s" % partner.street
        )

    def test_00_res_partner_name_create(self):
        self.create_and_assert(
            "Test00",
            self.env.ref("base.us").id,
            "40/A1/2b Chaussee de Namur",
            "Chaussee de Namur",
            "40",
            "A1",
            "2b",
        )
        self.create_and_assert(
            "Test01",
            self.env.ref("base.us").id,
            "40 Chaussee de Namur",
            "Chaussee de Namur",
            "40",
            "",
            "",
        )
        self.create_and_assert(
            "Test02",
            self.env.ref("base.us").id,
            "Chaussee de Namur",
            "de Namur",
            "Chaussee",
            "",
            "",
        )

    def test_01_header_trailer(self):
        self.create_and_assert(
            "Test10",
            self.env.ref("base.ch").id,
            "header Chaussee de Namur, 40 - A1 - 2b trailer",
            "Chaussee de Namur",
            "40",
            "A1",
            "2b",
        )
        self.create_and_assert(
            "Test11",
            self.env.ref("base.ch").id,
            "header Chaussee de Namur, 40 trailer",
            "Chaussee de Namur",
            "40",
            "",
            "",
        )
        self.create_and_assert(
            "Test12",
            self.env.ref("base.ch").id,
            "header Chaussee de Namur trailer",
            "Chaussee de Namur",
            "",
            "",
            "",
        )

    def test_02_res_partner_write(self):
        p1 = self.create_and_assert(
            "Test20",
            self.env.ref("base.be").id,
            "Chaussee de Namur, 40/A1/2b",
            "Chaussee de Namur",
            "40",
            "A1",
            "2b",
        )
        self.write_and_assert(
            p1,
            {"street": "Chaussee de Namur, 43/A1"},
            "Chaussee de Namur, 43/A1",
            "Chaussee de Namur",
            "43",
            "A1",
            "",
        )
        self.write_and_assert(
            p1,
            {"street": "Chaussee de Namur, 43/ /2b"},
            "Chaussee de Namur, 43/ /2b",
            "Chaussee de Namur",
            "43",
            " ",
            "2b",
        )
        self.write_and_assert(
            p1,
            {"street": "Chaussee de Namur"},
            "Chaussee de Namur",
            "Chaussee de Namur",
            "",
            "",
            "",
        )
        self.write_and_assert(
            p1,
            {"street_name": "Chee de Namur", "street_number": "40"},
            "Chee de Namur, 40",
            "Chee de Namur",
            "40",
            "",
            "",
        )
        self.write_and_assert(
            p1,
            {"l10n_ro_street_staircase": "A1", "street_number2": "4"},
            "Chee de Namur, 40/A1/4",
            "Chee de Namur",
            "40",
            "A1",
            "4",
        )
        self.write_and_assert(
            p1,
            {"country_id": self.env.ref("base.us").id},
            "40/A1/4 Chee de Namur",
            "Chee de Namur",
            "40",
            "A1",
            "4",
        )
