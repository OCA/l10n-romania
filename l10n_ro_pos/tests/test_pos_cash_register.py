# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
"""Coverage for the shared cash journal.

A Romanian shop keeps one registru de casa per place, not per register, so
the registers standing in that place have to book their cash into the same
journal -- which core refuses.
"""

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.common import CommonPosTest


@tagged("post_install", "-at_install")
class TestL10nRoPosCashRegister(CommonPosTest):
    @classmethod
    @CommonPosTest.setup_country("ro")
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.l10n_ro_accounting = True
        cls.config = cls.pos_config_usd
        cls.cash_journal = cls.cash_payment_method.journal_id

    def _second_register_method(self, name="Cash register 2"):
        """The cash method of another register in the same shop."""
        return self.env["pos.payment.method"].create(
            {
                "name": name,
                "journal_id": self.cash_journal.id,
                "company_id": self.env.company.id,
            }
        )

    def test_two_registers_share_the_shops_cash_journal(self):
        second = self._second_register_method()
        self.config.payment_method_ids = [(4, second.id)]
        self.config.flush_recordset()
        self.assertIn(second, self.config.payment_method_ids)
        self.assertEqual(second.journal_id, self.cash_payment_method.journal_id)

    def test_a_non_romanian_company_keeps_the_core_rule(self):
        self.env.company.l10n_ro_accounting = False
        # `is_l10n_ro_record` is computed from the chart of accounts, which
        # never flips under a live company; only a test moves it, so the
        # cached value has to be dropped by hand.
        self.env.invalidate_all()
        second = self._second_register_method("Cash register 2 abroad")
        with self.assertRaises(ValidationError):
            self.config.payment_method_ids = [(4, second.id)]
            self.config.flush_recordset()

    def test_one_payment_method_still_cannot_serve_two_registers(self):
        # Each register closes its own drawer; sharing the method would mix
        # them, and that half of the core check has to survive.
        other = self.config.copy({"name": "Second register"})
        with self.assertRaises(ValidationError):
            other.payment_method_ids = [(6, 0, self.cash_payment_method.ids)]
            other.flush_recordset()

    def test_the_journal_selector_offers_a_cash_journal_already_in_use(self):
        field = self.env["pos.payment.method"]._fields["journal_id"]
        domain = field._internal_description_domain_raw(self.env)
        self.assertNotIn(("pos_payment_method_ids", "=", False), domain)
        journals = self.env["account.journal"].search(domain)
        self.assertIn(self.cash_journal, journals)

    def test_the_journal_selector_abroad_keeps_the_core_restriction(self):
        self.env.company.l10n_ro_accounting = False
        field = self.env["pos.payment.method"]._fields["journal_id"]
        domain = field._internal_description_domain_raw(self.env)
        self.assertIn(("pos_payment_method_ids", "=", False), domain)
