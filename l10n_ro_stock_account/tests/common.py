# Copyright (C) 2020 Terrabit
# Copyright (C) 2025 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import ast
import codecs
import csv
import logging
import os

from odoo.tests import Form, tagged
from odoo.tools import float_compare

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestROStockCommon(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country("ro")
    def setUpClass(cls):
        super().setUpClass()
        cls.log_checks = False
        cls.env.user.group_ids += cls.env.ref("sales_team.group_sale_salesman")
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
        cls.ron = cls.env["res.currency"].search([("name", "=", "RON")])
        cls.eur = cls.env["res.currency"].search([("name", "=", "EUR")])
        cls.usd = cls.env["res.currency"].search([("name", "=", "USD")])

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

    def read_test_cases_from_csv_file(self, filename, module_dir=None):
        if not module_dir:
            module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(module_dir, "tests/cases/")
        f = open(os.path.join(data_dir, filename), "rb")
        reader = csv.DictReader(codecs.iterdecode(f, "utf-8"))
        test_cases = {}
        for row in reader:
            if row.get("case_no") not in test_cases:
                row_case = row.copy()
                test_cases[row["case_no"]] = {
                    "name": row.get("name", "No Name"),
                    "code": row["case_no"],
                    "steps": [row_case],
                }
            else:
                test_cases[row["case_no"]]["steps"].append(row)
        return test_cases

    def test_case(self, case=False):
        if case:
            for step in case.get("steps", []):
                self.run_test_step(step)
        else:
            pass

    def run_test_step(self, step):
        if self.log_checks:
            _logger.info(
                "Running test step: %s - %s - %s",
                step.get("case_no"),
                step.get("name"),
                step.get("type"),
            )
        if step.get("type") == "sale":
            self.create_sale_order(step)
        elif step.get("type") == "purchase":
            self.create_purchase(step)
        elif step.get("type") == "inventory":
            self.create_stock_inventory(step)
        elif step.get("type") == "transfer_transit":
            self.create_internal_transfer_transit(step)
        elif step.get("type") == "transfer_direct":
            self.create_internal_transfer_direct(step)
        elif step.get("type") == "consume":
            self.create_stock_picking("consume", step)
        elif step.get("type") == "consume_production":
            self.create_stock_picking("production", step)
        elif step.get("type") == "usage_giving":
            self.create_stock_picking("usage_giving", step)
        elif step.get("type") == "dropship":
            self.create_sale_dropship(step)
        if step.get("checks"):
            if isinstance(step.get("checks"), dict):
                checks = step.get("checks")
            else:
                checks = ast.literal_eval(step["checks"])
            if checks:
                self.run_checks(checks)

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
                stock_moves = self.env["stock.move"].search(move_domain)
                product_moves = self.env["stock.move"].search(
                    [
                        ("product_id", "=", product.id),
                    ]
                )
                if self.log_checks:
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
            account = self.env["account.account"].search(
                [
                    ("code", "=", account_code),
                    ("company_ids", "in", self.env.company.id),
                ],
                limit=1,
            )

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

    def get_references_from_values(self, values):
        refs = [
            "partner_id",
            "fiscal_position_id",
            "product_id",
            "currency_id",
            "location",
            "location1",
            "lot1",
            "lot2",
        ]
        float_keys = [
            "step",
            "qty",
            "stock_qty",
            "inv_qty",
            "stock_qty2",
            "inv_qty2",
            "price",
            "inv_price",
            "inv_price2",
            "discount",
            "advance",
            "landed_cost",
        ]
        bool_keys = ["notice", "reception_in_progress"]
        try:
            for key in values.keys():
                if key in refs and values.get(key, False):
                    if hasattr(self, values[key]):
                        values[key] = getattr(self, values[key])
                if key in float_keys and values.get(key, False):
                    values[key] = float(values[key])
                if key in bool_keys and values.get(key, False):
                    values[key] = bool(float(values[key]))
        except Exception as e:
            _logger.debug("Error getting references from values: %(error)s", error=e)
            pass
        return dict(values)

    def get_stock_quantity(self, values, step):
        if step == 1:
            return values.get("stock_qty", 1)
        elif step == 2:
            return values.get("stock_qty2", 1)
        else:
            return 1

    def get_stock_lot(self, values, step):
        if step == 1:
            return values.get("lot1")  # None dacă nu există
        elif step == 2:
            return values.get("lot2")  # None dacă nu există
        return None

    def get_invoice_quantity(self, values, step):
        if step == 1:
            return values.get("inv_qty")  # None dacă nu există
        elif step == 2:
            return values.get("inv_qty2")  # None dacă nu există
        return None

    def get_invoice_price(self, values, step):
        price = values.get("price", 0)
        if step == 1:
            price = values.get("inv_price")  # None dacă nu există
        elif step == 2:
            price = values.get("inv_price2")  # None dacă nu există
        return price

    def create_sale_order(self, values):
        so_values = self.get_references_from_values(values)
        order_line = [
            (
                0,
                0,
                {
                    "product_id": so_values["product_id"].id,
                    "product_uom_qty": so_values.get("qty", 1),
                    "price_unit": so_values.get("price", 100),
                    "discount": so_values.get("discount", 0),
                },
            )
        ]
        fpos = False
        if so_values.get("fiscal_position_id", False):
            fpos = so_values["fiscal_position_id"].id
        vals = {
            "partner_id": so_values["partner_id"].id,
            "partner_invoice_id": so_values["partner_id"].id,
            "fiscal_position_id": fpos,
            "partner_shipping_id": so_values["partner_id"].id,
            "currency_id": so_values.get(
                "currency_id", self.env.company.currency_id
            ).id,
            "order_line": order_line,
            "client_order_ref": so_values.get("ref", False),
        }
        if so_values.get("location", False):
            warehouse = so_values["location"].warehouse_id
            if warehouse:
                vals["warehouse_id"] = warehouse.id
        sale = self.env["sale.order"].create(vals)
        sale.action_confirm()
        if so_values.get("advance") != 0:
            product = self.advance_product
            if product:
                adv_wiz = (
                    self.env["sale.advance.payment.inv"]
                    .with_context(active_ids=[sale.id])
                    .create(
                        {
                            "advance_payment_method": "percentage",
                            "amount": 50.0,
                            "product_id": product.id,
                        }
                    )
                )
                act = adv_wiz.with_context(open_invoices=True).create_invoices()
                invoice = self.env["account.move"].browse(act["res_id"])
                invoice.action_post()
        self.deliver_and_invoice_sales(sale, so_values)
        if values.get("step") == 2:
            self.deliver_and_invoice_sales(sale.with_context(step=2), so_values)
        return sale

    def deliver_and_invoice_sales(self, sales, values):
        for sale in sales:
            step = sale.env.context.get("step", 1)
            stock_qty = self.get_stock_quantity(values, step)
            invoice_qty = self.get_invoice_quantity(values, step)
            invoice_price = self.get_invoice_price(values, step)
            stock_lot = self.get_stock_lot(values, step)
            picking = self.env["stock.picking"]
            if step == 2 and stock_qty < 0:
                stock_qty = -stock_qty
                # Create return to initial reception
                picking = sale.picking_ids.filtered(lambda x: x.state == "done")
                if picking:
                    stock_return_picking_form = Form(
                        self.env["stock.return.picking"].with_context(
                            active_ids=picking.ids,
                            active_id=picking.ids[0],
                            active_model="stock.picking",
                        )
                    )
                    return_wiz = stock_return_picking_form.save()
                    return_wiz.product_return_moves.write(
                        {
                            "quantity": stock_qty,
                            "to_refund": True,
                        }
                    )
                    if stock_lot:
                        lot = getattr(self, stock_lot)
                        return_wiz.product_return_moves.write({"lot_id": lot.id})
                    res = return_wiz.action_create_returns()
                    return_pick = self.env["stock.picking"].browse(res["res_id"])
                    if values.get("notice"):
                        return_pick.l10n_ro_notice = values.get("notice")
                    return_pick.action_confirm()
                    return_pick.action_assign()
                    return_pick.move_ids._set_quantity_done(stock_qty)
                    return_pick.move_ids.picked = True
                    return_pick._action_done()
                    picking = return_pick
            else:
                # Create reception
                pickings = sale.picking_ids.filtered(lambda x: x.state != "done")
                if pickings:
                    picking = pickings[0]
                    picking.write(
                        {
                            "l10n_ro_notice": values.get("notice"),
                            "scheduled_date": sale.date_order,
                            "date_done": sale.date_order,
                        }
                    )
                    picking.move_ids._set_quantity_done(stock_qty)
                    if stock_lot:
                        lot = getattr(self, stock_lot)
                        picking.move_ids.write({"lot_id": lot.id})
                    picking.move_ids.picked = True
                    picking.button_validate()
                    if picking.state == "assigned":
                        picking._action_done()
            if picking.state == "done" and invoice_qty:
                invoice = self.env["account.move"]
                try:
                    invoices = sale._create_invoices(final=True)
                    invoice = invoices[0]
                except Exception as e:
                    _logger.info("Error creating invoice: %(error)s", error=e)
                if invoice:
                    invoice_line = invoice.invoice_line_ids[0]
                    if (
                        invoice_qty
                        and invoice_qty < 0
                        and invoice.move_type == "out_refund"
                    ):
                        invoice_qty = -invoice_qty
                    invoice_line.write(
                        {"quantity": invoice_qty, "price_unit": invoice_price}
                    )
                    invoice.write(
                        {
                            "date": sale.date_order,
                            "invoice_date": sale.date_order,
                            "invoice_date_due": sale.date_order,
                        }
                    )
                    invoice.action_post()

    def create_purchase(self, values):
        po_values = self.get_references_from_values(values)
        order_line = [
            (
                0,
                0,
                {
                    "product_id": po_values["product_id"].id,
                    "product_qty": po_values.get("qty", 1),
                    "price_unit": po_values.get("price", 80),
                },
            )
        ]
        fpos = False
        if po_values.get("fiscal_position_id", False):
            fpos = po_values["fiscal_position_id"].id
        vals = {
            "partner_id": po_values["partner_id"].id,
            "currency_id": po_values.get(
                "currency_id", self.env.company.currency_id
            ).id,
            "fiscal_position_id": fpos,
            "order_line": order_line,
            "origin": po_values.get("ref", False),
        }

        if po_values.get("location", False):
            picking_type = self.env["stock.picking.type"].search(
                [
                    ("company_id", "=", self.env.company.id),
                    ("default_location_src_id.usage", "=", "supplier"),
                    ("default_location_dest_id", "=", po_values["location"].id),
                ],
                limit=1,
                order="sequence",
            )
            if picking_type:
                vals["picking_type_id"] = picking_type.id

        purchase = self.env["purchase.order"].create(vals)
        purchase.onchange_partner_id()
        purchase.button_confirm()
        if values.get("reception_in_progress"):
            purchase.action_create_reception_in_progress_invoice()
            invoice = purchase.invoice_ids[0]
            invoice.write(
                {
                    "date": purchase.date_order,
                    "invoice_date": purchase.date_order,
                    "invoice_date_due": purchase.date_order,
                }
            )
            invoice.action_post()
        self.receive_and_invoice_purchases(purchase, po_values)
        if values.get("step") == 2:
            self.receive_and_invoice_purchases(purchase.with_context(step=2), po_values)
        return purchase

    def receive_and_invoice_purchases(self, purchases, values):
        for purchase in purchases:
            step = purchase.env.context.get("step", 1)
            stock_qty = self.get_stock_quantity(values, step)
            invoice_qty = self.get_invoice_quantity(values, step)
            invoice_price = self.get_invoice_price(values, step)
            stock_lot = self.get_stock_lot(values, step)
            picking = self.env["stock.picking"]
            invoice = self.env["account.move"]
            if step == 2 and stock_qty < 0:
                # Create return to initial reception
                stock_qty = -stock_qty
                picking = purchase.picking_ids.filtered(lambda x: x.state == "done")
                if picking:
                    stock_return_picking_form = Form(
                        self.env["stock.return.picking"].with_context(
                            active_ids=picking.ids,
                            active_id=picking.ids[0],
                            active_model="stock.picking",
                        )
                    )
                    return_wiz = stock_return_picking_form.save()
                    return_wiz.product_return_moves.write(
                        {
                            "quantity": stock_qty,
                            "to_refund": True,
                        }
                    )
                    if stock_lot:
                        lot = getattr(self, stock_lot)
                        return_wiz.product_return_moves.write({"lot_id": lot.id})
                    res = return_wiz.action_create_returns()
                    return_pick = self.env["stock.picking"].browse(res["res_id"])
                    return_pick.action_confirm()
                    return_pick.action_assign()
                    return_pick.move_ids._set_quantity_done(stock_qty)
                    return_pick.move_ids.picked = True
                    return_pick._action_done()
                    picking = return_pick
            else:
                # Create reception
                pickings = purchase.picking_ids.filtered(lambda x: x.state != "done")
                if pickings:
                    picking = pickings[0]
                    picking.write(
                        {
                            "l10n_ro_notice": values.get("notice"),
                            "scheduled_date": purchase.date_planned,
                            "date_done": purchase.date_planned,
                        }
                    )
                    picking.move_ids._set_quantity_done(stock_qty)
                    if stock_lot:
                        lot = getattr(self, stock_lot)
                        picking.move_ids.write({"lot_id": lot.id})
                    picking.move_ids.picked = True
                    picking.button_validate()
                    if picking.state == "assigned":
                        picking._action_done()
            if picking.state == "done" and invoice_qty:
                try:
                    action = purchase.action_create_invoice()
                    invoice = self.env["account.move"].browse(action["res_id"])
                except Exception as e:
                    _logger.info("Error creating invoice: %(error)s", error=e)
                if invoice:
                    invoice_line = invoice.invoice_line_ids[0]
                    if (
                        invoice_qty
                        and invoice_qty < 0
                        and invoice.move_type == "in_refund"
                    ):
                        invoice_qty = -invoice_qty
                    invoice_line.write(
                        {"quantity": invoice_qty, "price_unit": invoice_price}
                    )
                    invoice.write(
                        {
                            "date": purchase.date_planned,
                            "invoice_date": purchase.date_planned,
                            "invoice_date_due": purchase.date_planned,
                        }
                    )
                    invoice.with_context(
                        l10n_ro_approved_price_difference=True
                    ).action_post()
            lc_pickings = purchase.picking_ids.filtered(
                lambda x: x.state == "done" and x.picking_type_code == "incoming"
            )
            if lc_pickings:
                if values.get("landed_cost", 0) != 0:
                    self.create_landed_cost(invoice, lc_pickings, values)

    def create_stock_inventory(self, values):
        inventory_values = self.get_references_from_values(values)
        inventory_vals = {
            "product_id": inventory_values["product_id"].id,
            "location_id": inventory_values["location"].id,
            "inventory_quantity": inventory_values.get("stock_qty", 0),
        }
        if inventory_values.get("lot1"):
            lot = inventory_values["lot1"]
            inventory_vals["lot_id"] = lot.id
        self.env["stock.quant"].with_context(inventory_mode=True).create(
            inventory_vals
        ).action_apply_inventory()

    def create_internal_transfer_transit(self, values, picking=None):
        transfer_values = self.get_references_from_values(values)
        step = 1
        if picking:
            step = picking.env.context.get("step", 1)

        stock_qty = self.get_stock_quantity(values, step)
        stock_lot = self.get_stock_lot(values, step)
        if step == 2 and stock_qty < 0:
            # Create return to initial transfer
            stock_qty = -stock_qty
            stock_return_picking_form = Form(
                self.env["stock.return.picking"].with_context(
                    active_ids=[picking.id],
                    active_id=picking.id,
                    active_model="stock.picking",
                )
            )
            return_wiz = stock_return_picking_form.save()
            return_wiz.product_return_moves.write(
                {
                    "quantity": stock_qty,
                    "to_refund": True,
                }
            )
            if stock_lot:
                lot = getattr(self, stock_lot)
                return_wiz.product_return_moves.write({"lot_id": lot.id})
            res = return_wiz.action_create_returns()
            return_pick = self.env["stock.picking"].browse(res["res_id"])
            return_pick.action_confirm()
            return_pick.action_assign()
            return_pick.move_ids._set_quantity_done(stock_qty)
            return_pick.move_ids.picked = True
            return_pick._action_done()
            return return_pick
        step = 1
        if picking:
            step = picking.env.context.get("step", 1)
        move_vals = {
            "company_id": self.env.company.id,
            "location_id": transfer_values.get("location").id,
            "location_dest_id": self.transit_loc.id,
            "product_id": transfer_values.get("product_id").id,
            "product_uom": transfer_values.get("product_id").uom_id.id,
            "product_uom_qty": transfer_values.get("qty", 1),
            "route_ids": [(4, self.transit_route.id)],
        }
        if stock_lot:
            lot = getattr(self, stock_lot)
            move_vals["lot_ids"] = [(6, 0, [lot.id])]
        move_transit_out = self.env["stock.move"].create(move_vals)
        move_transit_out._action_confirm()
        move_transit_out._action_assign()
        move_transit_out._set_quantity_done(stock_qty)
        move_transit_out.picked = True
        move_transit_out._action_done()
        move_transit_in = move_transit_out.move_dest_ids
        self.assertTrue(move_transit_in, "No move created from push rules")
        self.assertEqual(move_transit_in.state, "assigned")
        picking_receipt = move_transit_in.picking_id
        picking_receipt.move_ids.picked = True
        picking_receipt.button_validate()
        if values.get("step") == 2:
            self.create_internal_transfer_transit(
                values, picking_receipt.with_context(step=2)
            )
        return picking_receipt

    def create_internal_transfer_direct(self, values, picking=None):
        transfer_values = self.get_references_from_values(values)
        step = 1
        if picking:
            step = picking.env.context.get("step", 1)
        stock_qty = self.get_stock_quantity(values, step)
        stock_lot = self.get_stock_lot(values, step)
        if step == 2 and stock_qty < 0:
            # Create return to initial transfer
            stock_qty = -stock_qty
            stock_return_picking_form = Form(
                self.env["stock.return.picking"].with_context(
                    active_ids=[picking.id],
                    active_id=picking.id,
                    active_model="stock.picking",
                )
            )
            return_wiz = stock_return_picking_form.save()
            return_wiz.product_return_moves.write(
                {
                    "quantity": stock_qty,
                    "to_refund": True,
                }
            )
            if stock_lot:
                lot = getattr(self, stock_lot)
                return_wiz.product_return_moves.write({"lot_id": lot.id})
            res = return_wiz.action_create_returns()
            return_pick = self.env["stock.picking"].browse(res["res_id"])
            return_pick.action_confirm()
            return_pick.action_assign()
            return_pick.move_ids._set_quantity_done(stock_qty)
            return_pick.move_ids.picked = True
            return_pick._action_done()
            return return_pick
        move_vals = {
            "company_id": self.env.company.id,
            "location_id": transfer_values.get("location").id,
            "location_dest_id": transfer_values.get("location1").id,
            "product_id": transfer_values.get("product_id").id,
            "product_uom": transfer_values.get("product_id").uom_id.id,
            "product_uom_qty": stock_qty,
        }
        if stock_lot:
            lot = getattr(self, stock_lot)
            move_vals["lot_ids"] = [(6, 0, [lot.id])]
        move_transfer = self.env["stock.move"].create(move_vals)
        move_transfer._action_confirm()
        move_transfer._action_assign()
        move_transfer._set_quantity_done(stock_qty)
        move_transfer.picked = True
        move_transfer._action_done()
        picking_receipt = move_transfer.picking_id
        if values.get("step") == 2:
            self.create_internal_transfer_direct(
                values, picking_receipt.with_context(step=2)
            )
        return picking_receipt

    def create_stock_picking(self, oper_type, values, picking=None):
        picking_values = self.get_references_from_values(values)
        step = 1
        if picking:
            step = picking.env.context.get("step", 1)
        stock_qty = self.get_stock_quantity(values, step)
        stock_lot = self.get_stock_lot(values, step)
        if step == 2 and stock_qty < 0:
            # Create return to initial operation
            stock_qty = -stock_qty
            stock_return_picking_form = Form(
                self.env["stock.return.picking"].with_context(
                    active_ids=[picking.id],
                    active_id=picking.id,
                    active_model="stock.picking",
                )
            )
            return_wiz = stock_return_picking_form.save()
            return_wiz.product_return_moves.write(
                {
                    "quantity": stock_qty,
                    "to_refund": True,
                }
            )
            if stock_lot:
                lot = getattr(self, stock_lot)
                return_wiz.product_return_moves.write({"lot_id": lot.id})
            res = return_wiz.action_create_returns()
            return_pick = self.env["stock.picking"].browse(res["res_id"])
            return_pick.action_confirm()
            return_pick.action_assign()
            return_pick.move_ids._set_quantity_done(stock_qty)
            return_pick.move_ids.picked = True
            return_pick._action_done()
            return return_pick
        if not picking_values.get("location"):
            _logger.warning(
                "You need to provide the location source for stock operations"
            )
            pass
        domain = [
            ("company_id", "=", self.env.company.id),
            ("default_location_src_id", "=", picking_values["location"].id),
            ("default_location_dest_id.usage", "=", oper_type),
        ]
        if picking_values.get("location1"):
            domain.append(
                ("default_location_dest_id", "=", picking_values["location1"].id)
            )
        picking_type = self.env["stock.picking.type"].search(domain)
        if not picking_type:
            _logger.warning(
                self.env._(
                    "No picking type found for type %(picking_type)s and locations %(location)s %(location1)s.",  # noqa
                    picking_type=oper_type,
                    location=picking_values.get("location"),
                    location1=picking_values.get("location1"),
                )
            )
        picking_type.use_existing_lots = True
        location_src = picking_type.default_location_src_id.id
        location_dest = picking_type.default_location_dest_id.id
        product = picking_values.get("product_id")
        picking_vals = {
            "location_id": location_src,
            "location_dest_id": location_dest,
            "picking_type_id": picking_type.id,
        }
        if picking_values.get("partner_id"):
            picking_vals["partner_id"] = picking_values["partner_id"].id
        picking = self.env["stock.picking"].create(picking_vals)
        move_vals = {
            "location_id": location_src,
            "location_dest_id": location_dest,
            "picking_id": picking.id,
            "product_id": product.id,
            "product_uom": product.uom_id.id,
            "product_uom_qty": picking_values.get("qty", 1),
        }
        if stock_lot:
            lot = getattr(self, stock_lot)
            move_vals["lot_ids"] = [(6, 0, [lot.id])]
        move = self.env["stock.move"].create(move_vals)
        picking.action_confirm()
        picking.action_assign()
        move._set_quantity_done(stock_qty)

        picking.button_validate()
        if step == 1 and picking_values.get("step") == 2:
            self.create_stock_picking(oper_type, values, picking.with_context(step=2))
        return picking

    def create_landed_cost(self, invoice, pickings, values):
        journal = self.env["account.journal"].search(
            [("company_id", "=", self.env.company.id), ("type", "=", "general")],
            limit=1,
        )
        # For landed cost use 624000 account
        acc = self.env["account.account"].search(
            [
                ("company_ids", "in", self.env.company.id),
                ("code", "=", "624000"),
            ],
            limit=1,
        )
        product = self.landed_cost
        landed_cost = self.env["stock.landed.cost"].create(
            {
                "picking_ids": [(4, picking.id) for picking in pickings],
                "vendor_bill_id": invoice.id if invoice else False,
                "account_journal_id": journal.id,
                "date": invoice.date if invoice else pickings[0].scheduled_date,
                "cost_lines": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "price_unit": values.get("landed_cost"),
                            "split_method": "equal",
                            "account_id": acc.id
                            if acc
                            else product.property_account_expense_id.id,
                        },
                    )
                ],
            }
        )
        if hasattr(self, "l10n_ro_cost_type"):
            landed_cost.l10n_ro_cost_type = self.l10n_ro_cost_type
        landed_cost.compute_landed_cost()
        landed_cost.button_validate()
