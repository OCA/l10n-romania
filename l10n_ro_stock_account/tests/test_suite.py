# Copyright (C) 2026 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from .common import TestROStockCommon
from .test_ro_stock_avg import StockAvgCases
from .test_ro_stock_fifo import StockFifoCases
from .test_ro_stock_fifo_correction import FifoCorrectionCases
from .test_ro_stock_fifo_partial_delivery import FifoPartialDeliveryCases
from .test_ro_stock_fifo_zero_qty import FifoZeroQtyCases
from .test_stock_fifo_internal_transfer import FifoInternalTransferCases
from .test_stock_location import StockLocationCases


@tagged("post_install", "-at_install")
class TestROStockAccount(
    StockAvgCases,
    StockFifoCases,
    FifoCorrectionCases,
    FifoPartialDeliveryCases,
    FifoZeroQtyCases,
    FifoInternalTransferCases,
    StockLocationCases,
    TestROStockCommon,
):
    """Every scenario that runs on the plain ``TestROStockCommon`` setup.

    Odoo builds a new company and reloads the whole Romanian chart of accounts
    for each ``post_install`` test class, see
    ``AccountTestInvoicingCommon.setup_independent_company``, which costs about
    ten seconds every time.  The scenarios that need nothing beyond the common
    setup therefore share one class; each file keeps its own mixin, and only
    the ones that need a different company keep a class of their own.
    """

    # The scenarios are inherited from the mixins above, and Odoo's test loader
    # only collects methods declared on the class itself without this.
    allow_inherited_tests_method = True
