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

        ro_comps = env["res.company"].search(
            [
                ("l10n_ro_accounting", "=", True),
                ("l10n_ro_stock_acc_price_diff", "=", True),
            ]
        )
        if ro_comps:
            price_diff_module = IrModule.search(
                [("name", "=", "l10n_ro_stock_price_difference")]
            )
            price_diff_module.button_install()
            if hasattr(
                env["account.move.line"],
                "_l10n_ro_get_or_create_price_difference_product",
            ):
                env[
                    "account.move.line"
                ].l10n_ro_get_or_create_price_difference_product()
