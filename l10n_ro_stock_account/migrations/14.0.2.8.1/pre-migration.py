# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return

    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        IrModule = env["ir.module.module"]
        IrModule.update_list()

        ro_comps = env["res.company"].search([("l10n_ro_accounting", "=", True)])
        if ro_comps:
            stock_account_notice_module = IrModule.search(
                [("name", "=", "l10n_ro_stock_account_notice")]
            )
            stock_account_notice_module.button_install()
        # Delete views
        view_list = [
            "view_picking_add_notice_form",
            "view_picking_add_notice_tree",
            "view_picking_internal_add_notice_search",
            "stock_picking_kanban",
        ]
        for view in view_list:
            if env.ref("l10n_ro_stock_account." + view, raise_if_not_found=False):
                env.cr.execute(
                    "DELETE FROM ir_ui_view WHERE id = %s"
                    % env.ref("l10n_ro_stock_account." + view).id
                )
