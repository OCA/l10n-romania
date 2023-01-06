# Copyright 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models, tools

from odoo.addons.base.models.ir_ui_menu import IrUiMenu as BaseIrUiMenu

# remove the ormcache decorator
BaseIrUiMenu.load_menus = BaseIrUiMenu.load_menus.__wrapped__
BaseIrUiMenu._visible_menu_ids = BaseIrUiMenu._visible_menu_ids.__wrapped__


class L10nRoIrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    _menus_country_code = "RO"
    is_l10n_ro_record = fields.Boolean()

    @api.model
    @tools.ormcache_context(
        "frozenset(self.env.user.groups_id.ids)",
        "debug",
        keys=("menus_current_company",),
    )
    def _visible_menu_ids(self, debug=False):
        visible_ids = super()._visible_menu_ids(debug=debug)
        if not self._context.get("menus_current_company"):
            return visible_ids

        visible = self.browse()
        for menu in self.sudo().browse(visible_ids):
            is_country_visibile = self._get_country_specific_menu_visibility(menu)
            if is_country_visibile:
                visible |= menu
        return visible.ids

    @api.model
    def _get_country_specific_menu_visibility(self, menu):
        """
        Inherited methods MUST always call super() at the beginning of their implementation
        If super() return False, then the inherited method MUST return FALSE
        Otherwise the inherited method can process weather to return True or False

        example:

        class L10nABCIrUiMenu(models.Model):
            _inherit = "ir.ui.menu"

            @api.model
            def _get_country_specific_menu_visibility(self, menu):
                is_visible = super()._get_country_specific_menu_visibility(menu)
                if is_visible == False:
                    return False

                ....

                return True or False whatever your criteria are

        """
        if not menu.is_l10n_ro_record:
            return True

        current_company = (
            self.sudo()
            .env["res.company"]
            .browse(self._context["menus_current_company"])
        )

        if L10nRoIrUiMenu._menus_country_code != current_company.country_id.code:
            return False

        return True

    @api.model
    @tools.ormcache_context(
        "self._uid", "debug", keys=("lang", "menus_current_company")
    )
    def load_menus(self, debug):
        return super().load_menus(debug)
