# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from unittest.mock import Mock, patch

import requests

from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

from .anaf_data import ANAF_TEST_DATA


@tagged("post_install", "-at_install")
class TestCreatePartnerBase(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country("ro")
    def setUpClass(cls):
        cls._super_send = requests.Session.send
        super().setUpClass()
        cls.env.company.l10n_ro_accounting = True
        cls.mainpartner = cls.env["res.partner"].create({"name": "Test partner"})
        cls.anaf_data = ANAF_TEST_DATA
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
        cod = "30834857"
        with patch(
            "odoo.addons.l10n_ro_partner_create_by_vat.models.res_partner.ResPartner._get_Anaf",  # NOQA
            new=Mock(return_value=("", ANAF_TEST_DATA.get(cod, {}))),
        ):
            error, result = self.mainpartner._get_Anaf(cod)
            if not error and result:
                res = self.mainpartner._Anaf_to_Odoo(result)
                self.assertEqual(res["name"], "FOREST AND BIOMASS ROMÂNIA S.A.")
                self.assertEqual(res["l10n_ro_vat_subjected"], True)
                self.assertEqual(res["company_type"], "company")
                self.assertEqual(res["nrc"], "J2012002622359")
                self.assertEqual(res["street"], "Ferma 5-6")
                self.assertEqual(res["street2"], "")
                self.assertEqual(res["state_id"], self.env.ref("base.RO_TM"))
                self.assertEqual(res["city"], "Sat Giulvăz Com Giulvăz")
                self.assertEqual(res["zip"], "307225")
                self.assertEqual(res["phone"], "0356179038")

    def test_write_anaf_history(self):
        """Test write method in l10n.ro.res.partner.anaf.scptva
        and l10n.ro.res.partner.anaf.status"""
        cod = "30834857"
        partner = self.env["res.partner"].create(
            {
                "name": "Test Partner ANAF",
                "vat": "RO" + cod,
            }
        )
        # Force recompute or manually set l10n_ro_vat_number if needed,
        # but normally it should be computed if l10n_ro_config is installed.
        partner.flush_recordset()
        self.assertEqual(partner.l10n_ro_vat_number, cod)

        # Test l10n.ro.res.partner.anaf.scptva
        scptva = self.env["l10n.ro.res.partner.anaf.scptva"].create(
            {
                "vat_number": "123456",  # different VAT
            }
        )
        self.assertFalse(scptva.partner_id)
        scptva.write({"vat_number": cod})
        self.assertEqual(scptva.partner_id, partner)

        # Test l10n.ro.res.partner.anaf.status
        status = self.env["l10n.ro.res.partner.anaf.status"].create(
            {
                "vat_number": "123456",  # different VAT
            }
        )
        self.assertFalse(status.partner_id)
        status.write({"vat_number": cod})
        self.assertEqual(status.partner_id, partner)

    def test_vat_anaf_error(self):
        """Check methods vat from ANAF."""
        # Test retrieve information from ANAF
        cod = "3083485711"
        with patch(
            "odoo.addons.l10n_ro_partner_create_by_vat.models.res_partner.ResPartner._get_Anaf",  # NOQA
            new=Mock(return_value=("Nu exista date pentru CUI-ul introdus", {})),
        ):
            error, result = self.mainpartner._get_Anaf(cod)
            self.assertTrue(len(error) > 3)
            self.assertEqual(result, {})

    def test_onchange_vat_anaf(self):
        """Check onchange vat from ANAF."""
        # Test onchange from ANAF
        mainpartner = self.mainpartner
        mainpartner.country_id = self.env.ref("base.ro")
        cod = "30834857"
        with patch(
            "odoo.addons.l10n_ro_partner_create_by_vat.models.res_partner.ResPartner._get_Anaf",  # NOQA
            new=Mock(return_value=("", ANAF_TEST_DATA.get(cod, {}))),
        ):
            mainpartner.vat = cod
            mainpartner.ro_vat_change()
            self.assertEqual(mainpartner.name, "FOREST AND BIOMASS ROMÂNIA S.A.")
            self.assertEqual(mainpartner.street, "Ferma 5-6")
            self.assertEqual(mainpartner.street2, "")
            self.assertEqual(mainpartner.state_id, self.env.ref("base.RO_TM"))
            self.assertEqual(mainpartner.city, "Sat Giulvăz Com Giulvăz")
            self.assertEqual(mainpartner.country_id, self.env.ref("base.ro"))

        # Check inactive vatnumber
        cod = "27193515"
        with patch(
            "odoo.addons.l10n_ro_partner_create_by_vat.models.res_partner.ResPartner._get_Anaf",  # NOQA
            new=Mock(return_value=("", ANAF_TEST_DATA.get(cod, {}))),
        ):
            mainpartner.vat = cod
            mainpartner.ro_vat_change()
            self.assertEqual(
                mainpartner.name, "FOREST AND BIOMASS SERVICES ROMANIA S.A."
            )
            self.assertEqual(mainpartner.street, "Cal. Buziașului Nr. 11 A")
            self.assertEqual(mainpartner.street2, "Corp B, Zona Nr.1, Etaj 3")
            self.assertEqual(mainpartner.state_id, self.env.ref("base.RO_TM"))
            self.assertEqual(mainpartner.city, "Timișoara")
            self.assertEqual(mainpartner.country_id, self.env.ref("base.ro"))

        # Check address from commune
        cod = "8235738"
        with patch(
            "odoo.addons.l10n_ro_partner_create_by_vat.models.res_partner.ResPartner._get_Anaf",  # NOQA
            new=Mock(return_value=("", ANAF_TEST_DATA.get(cod, {}))),
        ):
            mainpartner.vat = cod
            mainpartner.ro_vat_change()
            self.assertEqual(mainpartner.name, "HOLZINDUSTRIE ROMANESTI S.R.L.")
            self.assertEqual(mainpartner.street, "Românești Nr. 69/A")
            self.assertEqual(mainpartner.state_id, self.env.ref("base.RO_TM"))
            self.assertTrue(mainpartner.city in "Sat Românești Com Tomești")
            self.assertEqual(mainpartner.country_id, self.env.ref("base.ro"))

        # Check address from vat without country code - vat subjected
        cod = "4264242"
        with patch(
            "odoo.addons.l10n_ro_partner_create_by_vat.models.res_partner.ResPartner._get_Anaf",  # NOQA
            new=Mock(return_value=("", ANAF_TEST_DATA.get(cod, {}))),
        ):
            mainpartner.vat = cod
            mainpartner.ro_vat_change()
            self.assertEqual(mainpartner.name, "CUMPANA 1993 SRL")
            self.assertEqual(mainpartner.street, "Str. Alexander Von Humboldt Nr. 10")
            self.assertEqual(mainpartner.street2, "Parter")
            self.assertEqual(mainpartner.state_id, self.env.ref("base.RO_B"))
            self.assertEqual(mainpartner.city.replace(" ", ""), "Sector3")
            self.assertEqual(mainpartner.country_id, self.env.ref("base.ro"))
            self.assertEqual(mainpartner.vat, "RO4264242")
            self.assertEqual(mainpartner.l10n_ro_vat_subjected, True)

        # Check address from vat without country code - no vat subjected
        cod = "42078234"
        with patch(
            "odoo.addons.l10n_ro_partner_create_by_vat.models.res_partner.ResPartner._get_Anaf",  # NOQA
            new=Mock(return_value=("", ANAF_TEST_DATA.get(cod, {}))),
        ):
            mainpartner.vat = cod
            mainpartner.ro_vat_change()
            self.assertEqual(
                mainpartner.name,
                "COJOCARU AURELIAN-MARCEL SOFTWARE PERSOANĂ FIZICĂ AUTORIZATĂ",
            )
            self.assertEqual(mainpartner.street, "Str. Holdelor Nr. 11")
            self.assertEqual(mainpartner.state_id, self.env.ref("base.RO_TM"))
            self.assertEqual(mainpartner.city, "Timișoara")
            self.assertEqual(mainpartner.country_id, self.env.ref("base.ro"))
            self.assertEqual(mainpartner.vat, "RO42078234")
            self.assertEqual(mainpartner.l10n_ro_vat_subjected, True)
            # Check split vat with no country code in vat
            vat_country, vat_number = self.mainpartner._split_vat(mainpartner.vat)
            self.assertEqual(vat_country, "RO")
            self.assertEqual(vat_number, "42078234")
            # Check vat subjected onchange
            mainpartner.l10n_ro_vat_subjected = True
            self.assertEqual(mainpartner.l10n_ro_vat_subjected, True)

    def test_anaf_exception(self):
        """Check anaf exception."""
        set_param = self.env["ir.config_parameter"].sudo().set_param
        anaf_url = "https://webservicesp.anaf.ro/PlatitorTvaRest/api/v7/ws/tvaERROR"
        set_param("l10n_ro_partner_create_by_vat.anaf_url", anaf_url)
        cod = "20603502"
        mainpartner = self.mainpartner
        mainpartner.country_id = self.env.ref("base.ro")
        with patch(
            "odoo.addons.l10n_ro_partner_create_by_vat.models.res_partner.ResPartner._get_Anaf",  # NOQA
            new=Mock(
                return_value=("Anaf request error", {"message": "Anaf request error"})
            ),
        ):  # NOQA
            error, res = mainpartner._get_Anaf(cod)
            self.assertEqual(error, "Anaf request error")
            self.assertEqual(res, {"message": "Anaf request error"})
            mainpartner.vat = cod
            res = mainpartner.ro_vat_change()
            self.assertTrue(res.get("warning"))

    def test_vat_vies(self):
        with patch(
            "odoo.addons.base_vat.models.res_partner.check_vies",
            return_value={"valid": True},
        ):
            self.env.company.vat_check_vies = True
            partner_odoo = Form(self.env["res.partner"])
            partner_odoo.name = "Test partner"
            partner_odoo.country_id = self.env.ref("base.be")
            partner_odoo.vat = "BE0477472701"
            partner = partner_odoo.save()
            self.assertEqual(partner.vat, "BE0477472701")
