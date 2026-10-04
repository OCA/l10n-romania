# Copyright (C) 2026 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from .common import TestStockPickingValued
from .test_ro_stock_avg import PickingValuedAvgCases
from .test_ro_stock_fifo import PickingValuedFifoCases


@tagged("post_install", "-at_install")
class TestStockPickingValuedReport(
    PickingValuedAvgCases,
    PickingValuedFifoCases,
    TestStockPickingValued,
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
