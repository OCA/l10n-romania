# Copyright (C) 2026 Terrabit Solutions
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestPartnerVatForeignPrefix(AccountTestInvoicingCommon):
    """A foreign tax ID must keep the exact form it was entered with.

    ``_split_vat`` used to look up a partner having the same ``vat`` and borrow
    its country code. During create/write the record is already in the database
    when ``_check_vat`` runs, so it matched itself and ``_run_vat_checks``
    re-attached the country prefix - the user could never store the local form
    of the number.
    """

    @classmethod
    @AccountTestInvoicingCommon.setup_country("ro")
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.l10n_ro_accounting = True
        cls.env.companies.vat_check_vies = False
        cls.country_hu = cls.env.ref("base.hu")
        # Hungarian adoszam: 8 digits + VAT code + county code. The EU form used
        # by VIES is the prefix plus the first 8 digits only.
        cls.local_vat = "26173247-2-08"
        cls.eu_vat = "HU26173247"

    def _create_hu_partner(self, vat):
        return self.env["res.partner"].create(
            {
                "name": "Hungarian Partner",
                "is_company": True,
                "country_id": self.country_hu.id,
                "vat": vat,
            }
        )

    def test_local_vat_kept_without_prefix(self):
        partner = self._create_hu_partner(self.local_vat)
        self.assertEqual(partner.vat, self.local_vat)

    def test_local_vat_without_separators_kept(self):
        partner = self._create_hu_partner("26173247208")
        self.assertFalse(partner.vat.startswith("HU"))

    def test_eu_vat_kept_with_prefix(self):
        partner = self._create_hu_partner(self.eu_vat)
        self.assertEqual(partner.vat, self.eu_vat)

    def test_prefix_removal_survives_write(self):
        partner = self._create_hu_partner(self.eu_vat)
        partner.write({"vat": self.local_vat})
        self.assertEqual(partner.vat, self.local_vat)

    def test_split_vat_does_not_borrow_country_from_database(self):
        """A second partner must not inherit the first one's country code."""
        self._create_hu_partner(self.local_vat)
        other = self.env["res.partner"].create(
            {"name": "No Country Partner", "is_company": True}
        )
        self.assertEqual(other._split_vat(self.local_vat), ("", self.local_vat))

    def test_ro_cui_without_prefix_still_resolves_to_ro(self):
        """The Romanian shortcut must keep working: bare digits mean RO."""
        partner = self.env["res.partner"].create(
            {
                "name": "Romanian Partner",
                "is_company": True,
                "country_id": self.env.ref("base.ro").id,
                "vat": "4264242",
            }
        )
        self.assertEqual(partner._split_vat("4264242"), ("RO", "4264242"))
