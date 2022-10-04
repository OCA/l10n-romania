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

        stock_landed_costs_module = IrModule.search(
            [("name", "=", "stock_landed_costs")]
        )
        if stock_landed_costs_module.state not in (
            "installed",
            "to install",
            "to upgrade",
        ):
            stock_landed_costs_module.button_install()
