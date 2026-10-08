# Copyright (C) 2020 Terrabit
# Copyright (C) 2025 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo.tests import tagged
from odoo.tools import float_compare

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_ro_stock_account.scenario import StockScenario

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestROStockCommon(StockScenario, AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country("ro")
    def setUpClass(cls):
        super().setUpClass()
        cls.log_checks = False
        cls.env.user.group_ids += cls.env.ref("sales_team.group_sale_salesman")
        # Enable FIFO per location on the test company. The module default
        # is True, but we set it explicitly so the tests are self-contained
        # and do not depend on future changes to the default.
        cls.env.company.fifo_per_location = True
        cls.stock_journal = cls.env["account.journal"].create(
            {
                "name": "Stock Journal",
                "code": "StockJurnal",
                "type": "general",
                "company_id": cls.env.company.id,
            }
        )
        cls.env.company.account_stock_journal_id = cls.stock_journal
        cls.env.company._create_usage_location()
        cls.env.company._create_consume_location()
        stock_val_account = cls.env.company.account_stock_valuation_id
        cls.category_marfa_fifo = cls.env["product.category"].create(
            {
                "name": "Test category",
                "property_valuation": "real_time",
                "property_cost_method": "fifo",
                "property_stock_valuation_account_id": stock_val_account.id,
                "l10n_ro_stock_account_change": True,
            }
        )
        cls.category_marfa_avg = cls.env["product.category"].create(
            {
                "name": "Test category",
                "property_valuation": "real_time",
                "property_cost_method": "average",
                "property_stock_valuation_account_id": stock_val_account.id,
                "l10n_ro_stock_account_change": True,
            }
        )
        cls.product_fifo = cls.env["product.product"].create(
            {
                "name": "Product FIFO",
                "is_storable": True,
                "categ_id": cls.category_marfa_fifo.id,
                "invoice_policy": "delivery",
                "purchase_method": "receive",
            }
        )
        cls.product_avg = cls.env["product.product"].create(
            {
                "name": "Product Average",
                "is_storable": True,
                "purchase_method": "receive",
                "categ_id": cls.category_marfa_avg.id,
                "invoice_policy": "delivery",
            }
        )
        cls.product_fifo_lot = cls.env["product.product"].create(
            {
                "name": "Product FIFO Lot Valuated",
                "is_storable": True,
                "purchase_method": "receive",
                "categ_id": cls.category_marfa_avg.id,
                "invoice_policy": "delivery",
                "tracking": "lot",
                "lot_valuated": True,
            }
        )
        cls.lot_fifo_1 = cls.env["stock.lot"].create(
            {
                "name": "FIFO-LOT-1",
                "product_id": cls.product_fifo_lot.id,
            }
        )
        cls.lot_fifo_2 = cls.env["stock.lot"].create(
            {
                "name": "FIFO-LOT-2",
                "product_id": cls.product_fifo_lot.id,
            }
        )
        cls.product_avg_lot = cls.env["product.product"].create(
            {
                "name": "Product Average Lot Valuated",
                "is_storable": True,
                "purchase_method": "receive",
                "categ_id": cls.category_marfa_avg.id,
                "invoice_policy": "delivery",
                "tracking": "lot",
            }
        )
        cls.lot_avg_1 = cls.env["stock.lot"].create(
            {
                "name": "AVG-LOT-1",
                "product_id": cls.product_avg_lot.id,
            }
        )
        cls.lot_avg_2 = cls.env["stock.lot"].create(
            {
                "name": "AVG-LOT-2",
                "product_id": cls.product_avg_lot.id,
            }
        )

        cls.landed_cost = cls.env["product.product"].create(
            {
                "name": "Landed Cost",
                "type": "service",
                "is_storable": False,
                "purchase_method": "purchase",
                "invoice_policy": "order",
            }
        )
        cls.advance_product = cls.env["product.product"].create(
            {
                "name": "Advance Product",
                "type": "service",
                "is_storable": False,
                "purchase_method": "purchase",
                "invoice_policy": "order",
            }
        )
        cls.supplier_1 = cls.env["res.partner"].create({"name": "Supplier 1"})
        cls.customer_1 = cls.env["res.partner"].create({"name": "Customer 1"})
        cls.ron = cls.env.ref("base.RON")
        cls.eur = cls.env.ref("base.EUR")
        cls.eur.active = True
        cls.usd = cls.env.ref("base.USD")
        cls.usd.active = True

        cls.account_income = cls.env.company.income_account_id
        cls.account_expense = cls.env.company.expense_account_id
        cls.account_valuation = cls.env.company.account_stock_valuation_id

        # On the first warehouse the consume and usage giving operations
        # are not configured by default
        comp_warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)]
        )
        comp_warehouse.write({"name": "Test Warehouse 1", "code": "TW1"})
        cls.location = comp_warehouse.lot_stock_id
        cls.location_production = cls.env["stock.location"].create(
            {
                "name": "Production",
                "usage": "production",
            }
        )
        cls.production_type = cls.env["stock.picking.type"].create(
            {
                "name": "Production",
                "code": "outgoing",
                "sequence_code": "PROD1",
                "default_location_src_id": cls.location.id,
                "default_location_dest_id": cls.location_production.id,
                "warehouse_id": comp_warehouse.id,
            }
        )
        cls.location_sub_1 = cls.env["stock.location"].create(
            {
                "name": "Stock Sub Location 1",
                "usage": "internal",
                "location_id": cls.location.id,
            }
        )
        cls.location_sub_2 = cls.env["stock.location"].create(
            {
                "name": "Stock Sub Location 2",
                "usage": "internal",
                "location_id": cls.location.id,
            }
        )

        # Create a second warehouse with different stock accounts
        # configured by location
        warehouse1 = cls.env["stock.warehouse"].create(
            {
                "name": "Test Warehouse 2",
                "code": "TW2",
                "company_id": cls.env.company.id,
            }
        )
        cls.location1 = warehouse1.lot_stock_id

        new_stock_val_account = cls.env.company.account_stock_valuation_id.copy(
            {"code": "371001"}
        )
        new_expense_acc = cls.env.company.expense_account_id.copy({"code": "607001"})
        cls.location1.write(
            {
                "l10n_ro_property_account_expense_location_id": new_expense_acc.id,
                "l10n_ro_property_stock_valuation_account_id": new_stock_val_account.id,
            }
        )

        cls.transit_loc = comp_warehouse.company_id.internal_transit_location_id
        cls.transit_transfer = cls.env["stock.picking.type"].create(
            {
                "name": "Transfer Warehouse to Transit",
                "code": "outgoing",
                "sequence_code": "INTW1",
                "default_location_src_id": cls.location.id,
                "default_location_dest_id": cls.transit_loc.id,
                "warehouse_id": comp_warehouse.id,
            }
        )
        cls.transit_route = cls.env["stock.route"].create(
            {
                "name": "Push",
                "company_id": False,
                "rule_ids": [
                    (
                        0,
                        False,
                        {
                            "name": "Transit to Warehouse 1 Stock",
                            "location_src_id": cls.transit_loc.id,
                            "location_dest_id": cls.location1.id,
                            "action": "push",
                            "auto": "manual",
                            "picking_type_id": warehouse1.int_type_id.id,
                        },
                    )
                ],
            }
        )

        # Create a third warehouse with different stock accounts
        # configured by fiscal position
        new_stock_val_account1 = cls.env.company.account_stock_valuation_id.copy(
            {
                "code": "371002",
                "l10n_ro_stock_consume_account_id": new_stock_val_account.id,
            }
        )
        new_expense_acc1 = cls.env.company.expense_account_id.copy(
            {"code": "607002", "l10n_ro_stock_consume_account_id": new_expense_acc.id}
        )
        fiscal_position = cls.env["account.fiscal.position"].create(
            {
                "name": "Fiscal Position Warehouse 2",
                "account_ids": [
                    (
                        0,
                        0,
                        {
                            "account_src_id": cls.account_valuation.id,
                            "account_dest_id": new_stock_val_account1.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_src_id": cls.account_expense.id,
                            "account_dest_id": new_expense_acc1.id,
                        },
                    ),
                ],
            }
        )
        warehouse2 = cls.env["stock.warehouse"].create(
            {
                "name": "Test Warehouse 3",
                "code": "TW3",
                "company_id": cls.env.company.id,
                "l10n_ro_fiscal_position_id": fiscal_position.id,
            }
        )
        cls.location2 = warehouse2.lot_stock_id

        # ``account.account.code`` is computed and company dependent, so
        # ``search([("code", "=", ...)])`` goes through ``_search_code`` and
        # orders by ``placeholder_code``, which costs ~250ms per call.  The
        # test cases look accounts up by code on every check, so resolve them
        # once here and keep them in a map.
        cls.accounts_by_code = {}
        accounts = (
            cls.env["account.account"]
            .with_company(cls.env.company)
            .search([("company_ids", "in", cls.env.company.id)])
        )
        for account in accounts:
            cls.accounts_by_code.setdefault(account.code, account)

    def get_account_by_code(self, account_code):
        """Return the company account having ``account_code``.

        Uses the map built in :meth:`setUpClass` instead of searching, see the
        comment there.  Falls back to a search for accounts created by a test.
        """
        account = self.accounts_by_code.get(account_code)
        if account is None:
            account = self.env["account.account"].search(
                [
                    ("code", "=", account_code),
                    ("company_ids", "in", self.env.company.id),
                ],
                limit=1,
            )
            self.accounts_by_code[account_code] = account
        return account

    def _receive(self, qty, price, index):
        """Receive ``qty`` of ``product_fifo`` at ``price``, one FIFO layer.

        Returns the incoming ``stock.move`` that carries the layer.
        """
        self.create_purchase(
            {
                "currency_id": self.ron,
                "partner_id": self.supplier_1,
                "product_id": self.product_fifo,
                "qty": qty,
                "stock_qty": qty,
                "inv_qty": qty,
                "price": price,
                "inv_price": price,
                "index": index,
            }
        )
        return self.env["stock.move"].search(
            [
                ("product_id", "=", self.product_fifo.id),
                ("is_in", "=", True),
                ("state", "=", "done"),
                ("location_dest_id", "=", self.location.id),
            ],
            order="id desc",
            limit=1,
        )

    def run_checks(self, checks):
        # Run accounting checks
        if "account" in checks:
            self.check_accounting_entries(checks["account"])
        # Run stock checks
        if "stock" in checks:
            self.check_stock_levels(checks["stock"])

    def check_stock_levels(self, checks):
        for product_ref, check_list in checks.items():
            product = getattr(self, product_ref)
            for vals in check_list:
                if vals.get("location"):
                    location = getattr(self, vals.get("location"))
                    quant_domain = [
                        ("product_id", "=", product.id),
                        ("location_id", "=", location.id),
                    ]
                    move_domain = [
                        ("product_id", "=", product.id),
                        ("location_dest_id", "=", location.id),
                    ]
                else:
                    locations = self.env["stock.location"].search(
                        [
                            ("usage", "in", ("internal", "transit")),
                            ("company_id", "=", self.env.company.id),
                        ]
                    )
                    quant_domain = [
                        ("product_id", "=", product.id),
                        ("location_id", "in", locations.ids),
                    ]
                    move_domain = [
                        ("product_id", "=", product.id),
                        ("location_dest_id", "in", locations.ids),
                    ]
                if vals.get("lot"):
                    lot = getattr(self, vals.get("lot"))
                    quant_domain.append(("lot_id", "=", lot.id))
                    move_domain.append(("lot_ids", "in", lot.id))
                quants = self.env["stock.quant"].search(quant_domain)
                quants._compute_value()
                stock_moves = self.env["stock.move"].search(move_domain)
                product_moves = self.env["stock.move"].search(
                    [
                        ("product_id", "=", product.id),
                    ]
                )
                if self.log_checks:
                    product_moves._invalidate_cache(
                        ["remaining_qty", "remaining_value"]
                    )
                    _logger.info("Stock quants for product %s", product.name)
                    for quant in quants:
                        _logger.info(
                            "%s | %s | Quantity: %.2f | Value: %.2f",
                            quant.location_id.display_name,
                            quant.product_id.display_name,
                            quant.quantity,
                            quant.value,
                        )
                    _logger.info("Stock moves for product %s", product.name)
                    # Antetul tabelului
                    _logger.info(
                        "%-5s | %-20s | %-10s | %-10s | %-5s | %-10s | %-10s | %-10s | %s",  # noqa
                        "ID",
                        "Name",
                        "From",
                        "To",
                        "Qty",
                        "Value",
                        "Remain Qty",
                        "Price Unit",
                        "Remain Value",  # noqa
                    )
                    _logger.info("-" * 120)
                    for move in product_moves:
                        _logger.info(
                            "%-5s | %-20s | %-10s | %-10s | %5.2f | %10.2f | %10.2f | %10.2f | %10.2f",  # noqa
                            move.id,
                            move.display_name,
                            move.location_id.display_name,
                            move.location_dest_id.display_name,
                            move.quantity,
                            move.value,
                            move.remaining_qty,
                            move.price_unit,
                            move.remaining_value,
                        )
                total_qty = sum(quants.mapped("quantity"))
                total_value = sum(quants.mapped("value"))
                self.assertEqual(
                    float_compare(
                        total_qty,
                        float(vals.get("qty", 0)),
                        precision_rounding=product.uom_id.rounding,
                    ),
                    0,
                    f"Stock quant quantity for {product.name} expected {vals.get('qty', 0)}, got {total_qty}",  # noqa
                )
                if product != self.product_avg:
                    self.assertEqual(
                        float_compare(
                            sum(stock_moves.mapped("remaining_qty")),
                            float(vals.get("qty", 0)),
                            precision_rounding=product.uom_id.rounding,
                        ),
                        0,
                        f"Stock Move Remaining quantity for {product.name} expected {vals.get('qty', 0)}, got {sum(stock_moves.mapped('remaining_qty'))}",  # noqa
                    )
                self.assertEqual(
                    float_compare(
                        total_value,
                        float(vals.get("value", 0)),
                        precision_rounding=0.01,
                    ),
                    0,
                    f"Stock quant value for {product.name} expected {vals.get('value', 0)}, got {total_value}",  # noqa
                )
                if product != self.product_avg:
                    self.assertEqual(
                        float_compare(
                            sum(stock_moves.mapped("remaining_value")),
                            float(vals.get("value", 0)),
                            precision_rounding=0.01,
                        ),
                        0,
                        f"Stock Remaining value for {product.name} expected {vals.get('value', 0)}, got {sum(stock_moves.mapped('remaining_value'))}",  # noqa
                    )

    def check_accounting_entries(self, checks):
        if self.log_checks:
            acc_moves = self.env["account.move"].search(
                [
                    ("company_id", "=", self.env.company.id),
                    ("state", "=", "posted"),
                ],
                order="id",
            )
            for move in acc_moves:
                # Opțional, puteți adăuga un separator pentru fiecare "move"
                _logger.info("-" * 80)

                # Antetul tabelului
                _logger.info(
                    "%-20s | %-10s | %-10s | %-10s | %s",
                    "Document",
                    "Cont",
                    "Debit",
                    "Credit",
                    "Sold",
                )
                _logger.info("-" * 80)

                for line in move.line_ids:
                    _logger.info(
                        "%-20s | %-10s | %10.2f | %10.2f | %10.2f",
                        line.move_id.name,
                        line.account_id.code,
                        line.debit,
                        line.credit,
                        line.balance,
                    )
        for account_code, expected_balance in checks.items():
            account = self.get_account_by_code(account_code)

            if not account:
                raise AssertionError(f"Account with code {account_code} not found")
            acc_move_lines = self.env["account.move.line"].search(
                [
                    ("account_id", "=", account.id),
                    ("company_id", "=", self.env.company.id),
                    ("parent_state", "=", "posted"),
                ]
            )

            if self.log_checks:
                _logger.info("-" * 80)

                for line in acc_move_lines:
                    _logger.info(
                        "%-20s | %-10s | %10.2f | %10.2f | %10.2f",
                        line.move_id.name,
                        line.account_id.code,
                        line.debit,
                        line.credit,
                        line.balance,
                    )

            if not acc_move_lines and float(expected_balance) != 0.0:
                raise AssertionError(
                    f"No posted entries found for account {account_code}"
                )
            balance = sum(acc_move_lines.mapped("balance"))
            self.assertEqual(
                float_compare(
                    balance, float(expected_balance), precision_rounding=0.01
                ),
                0,
                f"Account {account_code} balance expected {expected_balance}, got {balance}",  # noqa
            )  # noqa
