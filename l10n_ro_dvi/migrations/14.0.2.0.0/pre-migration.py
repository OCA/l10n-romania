# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
            ALTER TABLE stock_landed_cost
                ADD l10n_ro_landed_type character varying,
                ADD l10n_ro_tax_value duble precision,
                ADD l10n_ro_tax_id integer

        """
    )
    cr.execute(
        """
            UPDATE stock_landed_cost SET
                l10n_ro_landed_type=landed_type,
                l10n_ro_tax_value = tax_value
                l10n_ro_tax_id = tax_id
        """
    )

    env = api.Environment(cr, SUPERUSER_ID, {})
    invoices_with_dvi = env["account.move"].search([("dvi_id", "!=", False)])
    for invoice in invoices_with_dvi:
        invoice.dvi_id.vendor_bill_id = invoice.id
