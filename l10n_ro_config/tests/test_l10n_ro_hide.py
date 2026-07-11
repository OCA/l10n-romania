# Copyright (C) 2024 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from lxml import etree

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestL10nRoHide(AccountTestInvoicingCommon):
    """The Romanian localization hides its own fields, buttons and contextual
    actions when the active company is not a Romanian company (see
    ``l10n.ro.mixin.get_view`` and ``ir.actions.actions.get_bindings``)."""

    @classmethod
    @AccountTestInvoicingCommon.setup_country("ro")
    def setUpClass(cls):
        super().setUpClass()
        cls.ro_company = cls.env.company
        cls.ro_company.l10n_ro_accounting = True
        cls.non_ro_company = cls.env["res.company"].create(
            {"name": "Test Non RO Company"}
        )
        cls.non_ro_company.l10n_ro_accounting = False
        cls.group_ro_menus = cls.env.ref("l10n_ro_config.group_ro_menus")

    # ------------------------------------------------------------------ #
    #  Fields
    # ------------------------------------------------------------------ #
    def _partner_form(self, company):
        view = self.env["res.partner"].with_company(company).get_view(view_type="form")
        return etree.fromstring(view["arch"])

    def test_ro_fields_hidden_on_non_ro_company(self):
        doc = self._partner_form(self.non_ro_company)
        ro_fields = doc.xpath('//field[contains(@name, "l10n_ro")]')
        self.assertTrue(ro_fields, "The partner form must expose l10n_ro fields")
        for node in ro_fields:
            self.assertTrue(
                node.get("invisible") == "True"
                or node.get("column_invisible") == "True",
                "Field {} must be hidden on a non-Romanian company".format(
                    node.get("name")
                ),
            )

    def test_ro_fields_not_forced_hidden_on_ro_company(self):
        doc = self._partner_form(self.ro_company)
        node = doc.xpath('//field[@name="l10n_ro_vat_subjected"]')
        self.assertTrue(node, "l10n_ro_vat_subjected must be in the partner form")
        # On a Romanian company get_view returns early, so the field keeps its
        # original attributes and is not force-hidden.
        self.assertNotEqual(node[0].get("invisible"), "True")

    # ------------------------------------------------------------------ #
    #  Buttons
    # ------------------------------------------------------------------ #
    def test_ro_buttons_hidden_on_non_ro_company(self):
        doc = etree.fromstring(
            """
            <form>
                <button name="action_l10n_ro_something" type="object"
                    string="Romanian button"/>
                <button name="action_regular" type="object"
                    string="Regular button"/>
            </form>
            """
        )
        self.env["res.partner"].with_company(self.non_ro_company)._l10n_ro_hide_buttons(
            doc
        )
        ro_button = doc.xpath('//button[@name="action_l10n_ro_something"]')[0]
        regular_button = doc.xpath('//button[@name="action_regular"]')[0]
        self.assertEqual(ro_button.get("invisible"), "True")
        self.assertIsNone(regular_button.get("invisible"))

    # ------------------------------------------------------------------ #
    #  Contextual actions ("Action" menu)
    # ------------------------------------------------------------------ #
    def _create_ro_binding_action(self):
        partner_model = self.env["ir.model"]._get("res.partner")
        action = self.env["ir.actions.server"].create(
            {
                "name": "RO Test Server Action",
                "model_id": partner_model.id,
                "binding_model_id": partner_model.id,
                "state": "code",
                "code": "records.mapped('id')",
            }
        )
        # Give it an xml id that belongs to an ``l10n_ro*`` module so the
        # override recognises it as a Romanian action.
        self.env["ir.model.data"].create(
            {
                "name": "action_l10n_ro_test_binding",
                "module": "l10n_ro_config",
                "model": "ir.actions.server",
                "res_id": action.id,
            }
        )
        self.env.registry.clear_cache()
        return action

    def _binding_ids(self, company):
        result = (
            self.env["ir.actions.actions"]
            .with_company(company)
            .get_bindings("res.partner")
        )
        return [action["id"] for actions in result.values() for action in actions]

    def test_ro_action_hidden_on_non_ro_company(self):
        action = self._create_ro_binding_action()
        self.assertIn(
            action.id,
            self._binding_ids(self.ro_company),
            "The Romanian action must be available on a Romanian company",
        )
        self.assertNotIn(
            action.id,
            self._binding_ids(self.non_ro_company),
            "The Romanian action must be hidden on a non-Romanian company",
        )
