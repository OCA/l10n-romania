# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

"""Language forcing and the valued-columns hook of the delivery slip."""

from odoo.tests import tagged

from .common import TestStockPickingValued


@tagged("post_install", "-at_install")
class TestValuedReportLang(TestStockPickingValued):
    def _make_internal_picking(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        return self.env["stock.picking"].create(
            {
                "picking_type_id": warehouse.int_type_id.id,
                "location_id": self.location.id,
                "location_dest_id": self.location_sub_1.id,
            }
        )

    def test_valued_columns_shown_by_default(self):
        """Without a more specific layout the valued columns print."""
        picking = self._make_internal_picking()
        self.assertTrue(picking._l10n_ro_show_valued_columns())

    def test_delivery_slip_is_forced_to_romanian(self):
        """A RO company prints the delivery slip in Romanian.

        Exercised through the report override, not by forcing the language in
        the call: the override flags the render and the picking reports
        ``ro_RO`` whatever the partner (here none) speaks. Other reports and
        non-RO companies keep the partner's language."""
        self.assertEqual(self.env.company.country_id.code, "RO")
        # The forced language must be installed, or rendering with it raises
        # "Invalid language code" - which is also why the override guards on it.
        self.env["res.lang"]._activate_lang("ro_RO")
        picking = self._make_internal_picking()
        Report = self.env["ir.actions.report"]
        slip_env = Report._l10n_ro_picking_report_env("stock.action_report_delivery")
        self.assertTrue(slip_env.env.context.get("l10n_ro_force_picking_report_lang"))
        self.assertEqual(picking.with_env(slip_env.env)._get_report_lang(), "ro_RO")
        # A report that is not the delivery slip is left alone.
        other_env = Report._l10n_ro_picking_report_env("stock.report_return_slip")
        self.assertFalse(other_env.env.context.get("l10n_ro_force_picking_report_lang"))
        # And without the flag the picking keeps the standard language.
        self.assertNotEqual(picking._get_report_lang(), "ro_RO")
