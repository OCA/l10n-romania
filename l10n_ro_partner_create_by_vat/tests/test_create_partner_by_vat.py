# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


import json

import requests

from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged

# from odoo.modules.module import get_module_resource
from odoo.tools import file_path

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestCreatePartnerBase(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref="ro"):
        cls._super_send = requests.Session.send
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.env.company.l10n_ro_accounting = True
        cls.mainpartner = cls.env["res.partner"].create({"name": "Test partner"})
        test_file_path = file_path("l10n_ro_partner_create_by_vat/tests/anaf_data.json")
        cls.anaf_data = json.load(open(test_file_path))
        cls.mainpartner = cls.mainpartner.with_context(anaf_data=cls.anaf_data)

    @classmethod
    def _request_handler(cls, s, r, /, **kw):
        """Don't block external requests."""
        return cls._super_send(s, r, **kw)


@tagged("post_install", "-at_install")
class TestCreatePartner(TestCreatePartnerBase):
    def test_vat_anaf(self):
        """Check methods vat from ANAF."""
        # Test retrieve information from ANAF
        error, result = self.mainpartner._get_Anaf("30834857")
        if not error and result:
            res = self.mainpartner._Anaf_to_Odoo(result)
            self.assertEqual(res["name"], "FOREST AND BIOMASS ROMÂNIA S.A.")
            self.assertEqual(res["l10n_ro_vat_subjected"], True)
            self.assertEqual(res["company_type"], "company")
            self.assertEqual(res["nrc"], "J35/2622/2012")
            self.assertEqual(res["street"], "Str. Ciprian Porumbescu Nr. 12")
            self.assertEqual(res["street2"], "Zona Nr.3, Etaj 1")
            self.assertEqual(res["state_id"], self.env.ref("base.RO_TM"))
            self.assertEqual(res["city"], "Timișoara")
            self.assertEqual(res["zip"], "")
            self.assertEqual(res["phone"], "0356179038")

    def test_vat_anaf_error(self):
        """Check methods vat from ANAF."""
        # Test retrieve information from ANAF
        cod = "3083485711"
        error, result = self.mainpartner._get_Anaf(cod)
        self.assertTrue(len(error) > 3)
        cod = ["30834857", "3083485711"]
        error, result = self.mainpartner._get_Anaf(cod)
        if result:
            self.assertTrue(result.get("cod"))

    def test_onchange_vat_anaf(self):
        """Check onchange vat from ANAF."""
        # Test onchange from ANAF

        mainpartner = Form(self.mainpartner)
        mainpartner.company_type = "company"
        mainpartner.vat = "RO30834857"
        self.assertEqual(mainpartner.name, "FOREST AND BIOMASS ROMÂNIA S.A.")
        self.assertEqual(mainpartner.street, "Str. Ciprian Porumbescu Nr. 12")
        self.assertEqual(mainpartner.street2, "Zona Nr.3, Etaj 1")
        self.assertEqual(mainpartner.state_id, self.env.ref("base.RO_TM"))
        self.assertEqual(mainpartner.city, "Timișoara")
        self.assertEqual(mainpartner.country_id, self.env.ref("base.ro"))
        # Check inactive vatnumber

        mainpartner.vat = "RO27193515"

        self.assertEqual(mainpartner.name, "FOREST AND BIOMASS SERVICES ROMANIA S.A.")
        self.assertEqual(mainpartner.street, "Cal. Buziașului Nr. 11 A")
        self.assertEqual(mainpartner.street2, "Corp B, Zona Nr.1, Etaj 3")
        self.assertEqual(mainpartner.state_id, self.env.ref("base.RO_TM"))
        self.assertEqual(mainpartner.city, "Timișoara")
        self.assertEqual(mainpartner.country_id, self.env.ref("base.ro"))
        # Check address from commune

        mainpartner.vat = "RO8235738"

        self.assertEqual(mainpartner.name, "HOLZINDUSTRIE ROMANESTI S.R.L.")
        self.assertEqual(mainpartner.street, "Românești Nr. 69/A")
        self.assertEqual(mainpartner.state_id, self.env.ref("base.RO_TM"))
        self.assertTrue(mainpartner.city in "Sat Românești Com Tomești")
        self.assertEqual(mainpartner.country_id, self.env.ref("base.ro"))

        # Check address from vat without country code - vat subjected

        mainpartner.vat = "4264242"
        mainpartner.country_id = self.env.ref("base.ro")
        mainpartner.zip = "031472"

        self.assertEqual(mainpartner.name, "CUMPANA 1993 SRL")
        self.assertEqual(mainpartner.street, "Str. Alexander Von Humboldt Nr. 10")
        self.assertEqual(mainpartner.street2, "")

        self.assertEqual(mainpartner.state_id, self.env.ref("base.RO_B"))
        self.assertEqual(mainpartner.city.replace(" ", ""), "Sector3")
        self.assertEqual(mainpartner.country_id, self.env.ref("base.ro"))
        self.assertEqual(mainpartner.vat, "RO4264242")

        self.assertEqual(mainpartner.l10n_ro_vat_subjected, True)
        # Check address from vat without country code - no vat subjected

        mainpartner.l10n_ro_vat_subjected = False
        mainpartner.vat = "RO42078234"

        self.assertEqual(
            mainpartner.name,
            "COJOCARU AURELIAN-MARCEL SOFTWARE PERSOANĂ FIZICĂ AUTORIZATĂ",
        )
        self.assertEqual(mainpartner.street, "Str. Holdelor Nr. 11")
        self.assertEqual(mainpartner.state_id, self.env.ref("base.RO_TM"))
        self.assertEqual(mainpartner.city, "Timișoara")
        self.assertEqual(mainpartner.country_id, self.env.ref("base.ro"))
        self.assertEqual(mainpartner.vat, "42078234")
        self.assertEqual(mainpartner.l10n_ro_vat_subjected, False)
        # Check split vat with no country code in vat

        mainpartner.save()

        vat_country, vat_number = self.mainpartner._split_vat_and_mapped_country(
            mainpartner.vat
        )
        self.assertEqual(vat_country, "ro")
        self.assertEqual(vat_number, "42078234")
        # Check vat subjected onchange
        mainpartner.l10n_ro_vat_subjected = True

        self.assertEqual(mainpartner.l10n_ro_vat_subjected, False)

    def test_anaf_no_data(self):
        """if a invalid vat will return a empty dictionary."""
        error, res = self.mainpartner._get_Anaf("30834857111")
        self.assertEqual(res, {})
        self.assertTrue(len(error) > 2)

    def test_anaf_exception(self):
        """Check anaf exception."""
        get_param = self.env["ir.config_parameter"].sudo().get_param
        set_param = self.env["ir.config_parameter"].sudo().set_param

        get_param("l10n_ro_partner_create_by_vat.anaf_url")
        original_anaf_url = get_param("l10n_ro_partner_create_by_vat.anaf_url")
        anaf_url = "https://webservicesp.anaf.ro/PlatitorTvaRest/api/v7/ws/tvaERROR"

        set_param("l10n_ro_partner_create_by_vat.anaf_url", anaf_url)
        error, res = self.mainpartner._get_Anaf("20603502")
        self.assertEqual(res, {})
        self.assertTrue(len(error) > 3)
        self.mainpartner.company_type = "company"
        self.mainpartner.vat = "RO20603502"
        res = self.mainpartner.ro_vat_change()
        self.assertTrue(res.get("warning"))

        set_param("l10n_ro_partner_create_by_vat.anaf_url", original_anaf_url)

    def test_vat_vies(self):
        self.env.vat_check_vies = True
        partner_odoo = Form(self.env["res.partner"])
        partner_odoo.name = "Test partner"
        partner_odoo.country_id = self.env.ref("base.be")
        partner_odoo.vat = "BE0477472701"
        partner = partner_odoo.save()
        self.assertEqual(partner.vat, "BE0477472701")

        with self.assertRaises(ValidationError):
            partner_odoo.vat = "BE0577472701"
            partner_odoo.save()
