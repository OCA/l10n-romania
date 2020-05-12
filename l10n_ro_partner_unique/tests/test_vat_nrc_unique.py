# Copyright (C) 2017 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import ValidationError
from odoo.tests.common import SavepointCase


class TestVatUnique(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestVatUnique, cls).setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "Test partner", "vat": "RO30834857", "nrc": "J35/2622/2012"}
        )

    def test_duplicated_vat_creation(self):
        """ Test creation of partner."""
        with self.assertRaises(ValidationError):
            self.env["res.partner"].create(
                {"name": "Second partner", "vat": "RO30834857", "nrc": "J35/2622/2012"}
            )

    def test_contact_vat_creation(self):
        """ Test creation of partner contacs."""
        self.env["res.partner"].create(
            {
                "name": "Test partner 1 - child",
                "parent_id": self.partner.id,
                "is_company": False,
                "vat": "RO30834857",
                "nrc": "J35/2622/2012",
            }
        )
