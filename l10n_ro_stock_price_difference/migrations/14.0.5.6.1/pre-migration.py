# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openupgradelib import openupgrade


def migrate(cr, version):
    if not version:
        return

    openupgrade.logged_query(
        cr,
        """
        UPDATE stock_valuation_layer set remaining_qty = 0
        WHERE description = 'Price Difference'
        """,
    )
