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
        cls.country_ro = cls.env.ref("base.ro")
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test partner",
                "vat": "RO30834857",
                "nrc": "J35/2622/2012",
                "is_company": True,
                "country_id": cls.country_ro.id,
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
                    "country_id": self.country_ro.id,
                }
            )

        self.env["res.partner"].create(
            {
                "name": "Second partner",
                "vat": "RO30834857",
                "nrc": "J2012002622359",
                "is_company": True,
                "country_id": self.country_ro.id,
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
                    "country_id": self.country_ro.id,
                }
            )
        with self.assertRaises(ValidationError):
            self.env["res.partner"].create(
                {
                    "name": "Second partner",
                    "vat": "RO30834857",
                    "nrc": "J2012002622359",
                    "is_company": True,
                    "country_id": self.country_ro.id,
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
                    "country_id": self.country_ro.id,
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
                "country_id": self.country_ro.id,
            }
        )
        self.env["res.partner"].create(
            {
                "name": "Test partner 2 - child",
                "parent_id": self.partner.id,
                "is_company": True,
                "vat": "RO30834857",
                "nrc": "J35/2622/2012",
                "country_id": self.country_ro.id,
            }
        )

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
                "country_id": self.country_ro.id,
            }
        )

        with self.assertRaises(ValidationError):
            partner.is_company = True

    def test_merge_two_partners_same_cui_without_country_then_set_ro(self):
        """
        Creează 2 parteneri companie fără țară, cu același CUI
        (VAT numeric, fără prefix RO),
        apoi setează țara România și verifică faptul că pot fi uniți fără eroare.

        Constrângerea de unicat este omisă în contextul de merge (partner_merge=True)
        prin override-ul din wizard-ul local.
        """
        # Setăm regula de unicat pe CUI (VAT)
        self.env["ir.config_parameter"].sudo().set_param(
            "l10n_ro_partner_unique.vat_nrc_unique", "vat"
        )

        # 1) Creăm 2 companii fără țară, cu același CUI numeric (fără prefix RO)
        p1 = self.env["res.partner"].create(
            {
                "name": "P1 Test",
                "vat": "30834857",
                "is_company": True,
                "country_id": False,
            }
        )
        p2 = self.env["res.partner"].create(
            {
                "name": "P2 Test",
                "vat": "30834857",
                "is_company": True,
                "country_id": False,
            }
        )

        ro = self.env.ref("base.ro")
        p1.country_id = ro
        p2.country_id = ro

        wiz = self.env["base.partner.merge.automatic.wizard"].create({})
        wiz._merge([p1.id, p2.id])
