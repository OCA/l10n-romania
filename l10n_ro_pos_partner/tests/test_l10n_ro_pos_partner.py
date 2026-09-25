# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
"""Coverage for the CUI search in the Point of Sale.

A company buying over the counter hands over a CUI, not a name, and it is
rarely on file already. The search has to recognise that code and bring the
company back from ANAF in the shape the POS front end can put on the order.
"""

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.l10n_ro_partner_create_by_vat.tests.anaf_data import ANAF_TEST_DATA
from odoo.addons.point_of_sale.tests.common import CommonPosTest

ANAF_PATH = (
    "odoo.addons.l10n_ro_partner_create_by_vat.models.res_partner.ResPartner._get_Anaf"
)
CUI = "30834857"


@tagged("post_install", "-at_install")
class TestL10nRoPosPartner(CommonPosTest):
    @classmethod
    @CommonPosTest.setup_country("ro")
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.l10n_ro_accounting = True
        cls.config = cls.pos_config_usd
        cls.Partner = cls.env["res.partner"]

    def _anaf(self, cui=CUI):
        """Answer as ANAF would for ``cui``, without leaving the test."""
        return patch(ANAF_PATH, return_value=("", ANAF_TEST_DATA.get(cui, {})))

    def _create(self, vat_number, cui=CUI):
        with self._anaf(cui):
            return self.Partner.l10n_ro_pos_create_partner_from_vat(
                self.config.id, vat_number
            )

    # -- what the cashier typed ------------------------------------------

    def test_the_ro_prefix_and_spaces_are_not_part_of_the_cui(self):
        for typed in (CUI, "RO" + CUI, " ro 30 834 857 "):
            self.assertEqual(self.Partner._l10n_ro_pos_vat_to_cui(typed), CUI)

    def test_a_name_typed_in_the_search_is_not_a_cui(self):
        for typed in ("INVALID", "ROABC123", ""):
            with self.assertRaises(UserError):
                self.Partner._l10n_ro_pos_vat_to_cui(typed)

    # -- the customer already on file ------------------------------------

    def test_a_customer_already_on_file_is_returned_as_is(self):
        existing = self.Partner.create({"name": "On file", "vat": "RO" + CUI})
        # The cashier searched by VAT, so ANAF has nothing to add -- and must
        # not be asked, or every regular gets a round trip at the till.
        with patch(ANAF_PATH, side_effect=AssertionError("ANAF was called")):
            res = self.Partner.l10n_ro_pos_create_partner_from_vat(
                self.config.id, "RO " + CUI
            )
        self.assertEqual(res["res.partner"][0]["id"], existing.id)
        self.assertEqual(res["res.partner"][0]["name"], "On file")

    def test_a_customer_on_file_without_the_ro_prefix_still_matches(self):
        existing = self.Partner.create({"name": "No prefix", "vat": CUI})
        with patch(ANAF_PATH, side_effect=AssertionError("ANAF was called")):
            res = self.Partner.l10n_ro_pos_create_partner_from_vat(
                self.config.id, "RO" + CUI
            )
        self.assertEqual(res["res.partner"][0]["id"], existing.id)

    # -- the customer ANAF knows about -----------------------------------

    def test_the_company_comes_back_from_anaf_with_its_address(self):
        self._create(CUI)
        partner = self.Partner.search([("vat", "=", "RO" + CUI)])
        self.assertEqual(len(partner), 1)
        self.assertEqual(partner.name, "FOREST AND BIOMASS ROMÂNIA S.A.")
        self.assertEqual(partner.company_type, "company")
        self.assertEqual(partner.country_id, self.env.ref("base.ro"))
        self.assertEqual(partner.state_id, self.env.ref("base.RO_TM"))
        self.assertEqual(partner.nrc, "J2012002622359")
        self.assertTrue(partner.l10n_ro_vat_subjected)

    def test_the_anaf_history_is_kept_as_on_the_partner_form(self):
        self._create(CUI)
        partner = self.Partner.search([("vat", "=", "RO" + CUI)])
        self.assertTrue(partner.l10n_ro_vat_subjected_anaf_line_ids)
        self.assertEqual(partner.l10n_ro_vat_subjected_anaf_line_ids[0].vat_number, CUI)

    def test_the_payload_is_what_the_front_end_loads(self):
        # `callRelated` feeds this straight into the POS model store, which
        # relates records by id -- a display name in a many2one would be read
        # as one, and the customer would land on the order half broken.
        res = self._create(CUI)
        self.assertEqual(set(res), {"res.partner", "account.fiscal.position"})
        payload = res["res.partner"][0]
        self.assertEqual(
            set(payload),
            set(self.Partner._load_pos_data_fields(self.config)),
        )
        for field in ("country_id", "state_id"):
            self.assertIsInstance(payload[field], int)

    # -- when ANAF cannot answer ------------------------------------------

    def test_an_anaf_error_reaches_the_cashier(self):
        with patch(ANAF_PATH, return_value=("ANAF is down", None)):
            with self.assertRaises(UserError):
                self.Partner.l10n_ro_pos_create_partner_from_vat(self.config.id, CUI)

    def test_an_unknown_cui_leaves_no_placeholder_customer_behind(self):
        unknown = "3083485711"
        with self.assertRaises(UserError):
            self._create(unknown, cui=unknown)
        self.assertFalse(
            self.Partner.search_count(
                ["|", ("vat", "=ilike", unknown), ("name", "=", unknown)]
            )
        )
