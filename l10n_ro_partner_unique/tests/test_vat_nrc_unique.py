# Copyright (C) 2017 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestVatUnique(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country("ro")
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.l10n_ro_accounting = True
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test partner",
                "vat": "RO30834857",
                "nrc": "J35/2622/2012",
                "is_company": True,
            }
        )

    def test_duplicated_vat_nrc_creation(self):
        """
        Test if it is possible to create two partners with the same vat
        """
        set_para = self.env["ir.config_parameter"].sudo().set_param
        set_para("l10n_ro_partner_unique.vat_nrc_unique", "vat_nrc")
        with self.assertRaises(ValidationError):
            self.env["res.partner"].create(
                {
                    "name": "Second partner",
                    "vat": "RO30834857",
                    "nrc": "J35/2622/2012",
                    "is_company": True,
                }
            )

        self.env["res.partner"].create(
            {
                "name": "Second partner",
                "vat": "RO30834857",
                "nrc": "J2012002622359",
                "is_company": True,
            }
        )

    def test_duplicated_vat_creation(self):
        """
        Test if it is possible to create two partners with the same vat
        """
        set_para = self.env["ir.config_parameter"].sudo().set_param
        set_para("l10n_ro_partner_unique.vat_nrc_unique", "vat")
        with self.assertRaises(ValidationError):
            self.env["res.partner"].create(
                {
                    "name": "Second partner",
                    "vat": "RO30834857",
                    "nrc": "J35/2622/2012",
                    "is_company": True,
                }
            )
        with self.assertRaises(ValidationError):
            self.env["res.partner"].create(
                {
                    "name": "Second partner",
                    "vat": "RO30834857",
                    "nrc": "J2012002622359",
                    "is_company": True,
                }
            )

    def test_duplicated_vat_creation_without_prefix(self):
        """
        Test if it is possible to create two partners with the same
         vat without prefix
        """
        with self.assertRaises(ValidationError):
            self.env["res.partner"].create(
                {
                    "name": "Second partner",
                    "vat": "30834857",
                    "nrc": "J35/2622/2012",
                    "is_company": True,
                }
            )

    def test_contact_vat_creation(self):
        """
        Test if it is possible to create a contact with the same vat
        as the parent company
        """
        self.env["res.partner"].create(
            {
                "name": "Test partner 1 - child",
                "parent_id": self.partner.id,
                "is_company": False,
                "vat": "RO30834857",
                "nrc": "J35/2622/2012",
            }
        )
        self.env["res.partner"].create(
            {
                "name": "Test partner 2 - child",
                "parent_id": self.partner.id,
                "is_company": True,
                "vat": "RO30834857",
                "nrc": "J35/2622/2012",
            }
        )

    def test_partial_vat_creation(self):
        """
        Test if it is possible to create a contact with a partial
        vat of an existing one
        """

        partner = self.env["res.partner"].create(
            {
                "name": "Test partner 1",
                "is_company": True,
                "vat": "RO308",
                "nrc": "J35/2622/2012",
            }
        )
        with self.assertRaises(ValidationError):
            partner.vat = "RO30834857"  # try to fix vat

        partner = self.env["res.partner"].create(
            {
                "name": "Test partner 1",
                "is_company": True,
                "vat": "RO3083485789",
                "nrc": "J35/2622/2012",
            }
        )
        with self.assertRaises(ValidationError):
            partner.vat = "RO30834857"  # try to fix vat

    def test_duplicated_vat_creation_individual(self):
        """
        Test if is possible to create an individual with the same
        vat as a company
        """
        partner = self.env["res.partner"].create(
            {
                "name": "Second partner",
                "vat": "RO30834857",
                "nrc": "J35/2622/2012",
                "is_company": False,
            }
        )

        with self.assertRaises(ValidationError):
            partner.is_company = True
