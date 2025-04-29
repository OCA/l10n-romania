# Copyright (C) 2023 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    try:
        openupgrade.logged_query(
            cr,
            """
            UPDATE stock_valuation_layer svl set
                l10n_ro_invoice_id = lsvl.l10n_ro_invoice_id,
                l10n_ro_invoice_line_id = lsvl.l10n_ro_invoice_line_id
            FROM stock_valuation_layer lsvl
            WHERE
                svl.stock_valuation_layer_id = lsvl.id and
                svl.description like '%Price Difference%'
            """,
        )
    except Exception as e:
        _logger.error("Failed to update stock_valuation_layer: %s", str(e))
