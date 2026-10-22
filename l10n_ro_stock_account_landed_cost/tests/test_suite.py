# Copyright (C) 2026 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestROStockCommon

from .test_ro_stock_avg import LandedCostAvgCases
from .test_ro_stock_fifo import LandedCostFifoCases
from .test_stock_fifo_internal_transfer import LandedCostInternalTransferCases


@tagged("post_install", "-at_install")
class TestROStockAccountLandedCost(
    LandedCostAvgCases,
    LandedCostFifoCases,
    LandedCostInternalTransferCases,
    TestROStockCommon,
):
    """Every scenario that runs on the module's common setup.

    Odoo builds a new company and reloads the whole Romanian chart of accounts
    for each ``post_install`` test class, see
    ``AccountTestInvoicingCommon.setup_independent_company``, which costs about
    ten seconds every time.  The scenarios therefore share one class; each file
    keeps its own mixin.
    """

    # The scenarios are inherited from the mixins above, and Odoo's test loader
    # only collects methods declared on the class itself without this.
    allow_inherited_tests_method = True
