# Copyright 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    is_l10n_ro_record = fields.Boolean()

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        ro_code = self.env.ref("base.ro").code

        def _check_country_menu_action_context(menu):
            if not menu.is_l10n_ro_record:
                return True

            if ro_code not in self.env.user.company_ids.mapped("country_id.code"):
                return False

            return True

        menus = super(IrUiMenu, self).search(
            args, offset=offset, limit=limit, order=order, count=count
        )
        if not count and menus:
            menus = menus.filtered(
                lambda menu: _check_country_menu_action_context(menu)
            )
        return menus
