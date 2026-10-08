# Copyright (C) 2026 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
"""Builds the Romanian stock scenarios described by the CSV cases.

The scenarios were written for the tests, where each row of a CSV is a
purchase, a delivery, a transfer or an inventory to run and then check.  They
describe the Romanian stock flows better than any hand written demo data does,
so the part that *builds* the documents lives here, outside the tests, and the
part that *checks* them stays with them.

The host decides what the names in the CSV mean.  A test resolves them against
the objects it built in ``setUpClass``; demo data resolves them against records
loaded from XML.  Everything else - the steps, the partial receptions, the
returns on a negative quantity, the landed cost that follows the last
reception - is the same on both sides, which is the point of keeping it in one
place.

Nothing here imports ``odoo.tests``: the runner has to work while demo data is
loading, where the test framework is not available.
"""

import ast
import codecs
import csv
import logging
import os

_logger = logging.getLogger(__name__)


class StockScenario:
    """Runs the CSV scenarios against ``self.env``.

    Mixed into the test common, or into the small host that demo data uses.
    The host provides ``env`` and, if it wants to, overrides ``_resolve`` and
    ``run_checks``.
    """

    # The host turns this on to trace what the scenario builds.
    log_checks = False
    # Options a host may set to steer the scenarios.
    l10n_ro_approved_price_difference = False
    l10n_ro_cost_type = None
    # Records the scenarios reach for by name; a host that runs the cases
    # needing them provides its own.
    advance_product = None
    landed_cost = None
    transit_loc = None
    transit_route = None

    def _resolve(self, name):
        """Return the record a name in the CSV stands for.

        The default is what the tests have always done: an attribute of the
        host, set up before the scenarios run.  Demo data overrides this to
        look up external identifiers instead.
        """
        return getattr(self, name) if hasattr(self, name) else None

    def run_checks(self, checks):
        """Assert the expected stock and accounting of a step.

        Only the tests check anything; building the documents is the whole job
        on the demo side.
        """
        return

    def create_sale_dropship(self, values):
        """Dropship scenarios live in the module that adds dropshipping."""
        raise NotImplementedError(
            "The 'dropship' step needs a host that knows how to build one."
        )

    def get_account_by_code(self, account_code):
        """Return the company account having ``account_code``."""
        return self.env["account.account"].search(
            [
                ("code", "=", account_code),
                ("company_ids", "in", self.env.company.id),
            ],
            limit=1,
        )

    def read_test_cases_from_csv_file(
        self, filename, module_dir=None, subdir="tests/cases"
    ):
        """Read the cases of one CSV, grouped by ``case_no``.

        ``subdir`` is where the file sits inside the module: the tests keep
        theirs under ``tests/cases``, demo data under ``demo/cases``.
        """
        if not module_dir:
            module_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(module_dir, subdir)
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

    def run_test_case(self, case=False):
        if case:
            for step in case.get("steps", []):
                step["index"] = case.get("steps", []).index(step) + 1
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
        elif step.get("type") == "invoice":
            self.create_invoice(step)
        if step.get("checks"):
            if isinstance(step.get("checks"), dict):
                checks = step.get("checks")
            else:
                checks = ast.literal_eval(step["checks"])
            if checks:
                self.run_checks(checks)

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
                    record = self._resolve(values[key])
                    if record is not None:
                        values[key] = record
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
        sale.write({"currency_id": vals["currency_id"]})
        if self.log_checks:
            _logger.info(
                "Setting sale order variables: sale_order_%s", values.get("index", 0)
            )
        setattr(self, f"sale_order_{values.get('index', 0)}", sale)
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
                if self.log_checks:
                    _logger.info(
                        "Setting advance invoice variables: advance_invoice_%s",
                        values.get("index", 0),
                    )
                setattr(self, f"advance_invoice_{values.get('index', 0)}", invoice)
                invoice.currency_id = sale.currency_id
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
                    # ``product_return_moves`` is a stored compute on ``picking_id``,
                    # so creating the wizard fills the lines without a Form.
                    return_wiz = self.env["stock.return.picking"].create(
                        {"picking_id": picking.ids[0]}
                    )
                    return_wiz.product_return_moves.write(
                        {
                            "quantity": stock_qty,
                            "to_refund": True,
                        }
                    )
                    if stock_lot:
                        lot = self._resolve(stock_lot)
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
                    if self.log_checks:
                        _logger.info(
                            "Setting return picking variables: return_delivery_%s_%s",
                            values.get("index", 0),
                            step,
                        )
                    setattr(
                        self,
                        f"return_delivery_{values.get('index', 0)}_{step}",
                        return_pick,
                    )
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
                        lot = self._resolve(stock_lot)
                        picking.move_ids.write({"lot_id": lot.id})
                    picking.move_ids.picked = True
                    picking.button_validate()
                    if self.log_checks:
                        _logger.info(
                            "Setting picking variables: delivery_%s_%s",
                            values.get("index", 0),
                            step,
                        )
                    setattr(self, f"delivery_{values.get('index', 0)}_{step}", picking)
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
                    invoice.write(
                        {
                            "currency_id": sale.currency_id.id,
                            "date": sale.date_order,
                            "invoice_date": sale.date_order,
                            "invoice_date_due": sale.date_order,
                        }
                    )
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
                    if self.log_checks:
                        _logger.info(
                            "Setting customer invoice variables: "
                            "customer_invoice_%s_%s",
                            values.get("index", 0),
                            step,
                        )
                    setattr(
                        self,
                        f"customer_invoice_{values.get('index', 0)}_{step}",
                        invoice,
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
        if self.log_checks:
            _logger.info(
                "Setting purchase order variables: purchase_order_%s",
                values.get("index", 0),
            )
        setattr(self, f"purchase_order_{values.get('index', 0)}", purchase)
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
            if self.log_checks:
                _logger.info(
                    "Setting reception in progress invoice variables: "
                    "reception_in_progress_invoice_%s",
                    values.get("index", 0),
                )
            setattr(
                self, f"reception_in_progress_invoice_{values.get('index', 0)}", invoice
            )
            invoice.action_post()
            if self.l10n_ro_approved_price_difference:
                purchase = purchase.with_context(l10n_ro_approved_price_difference=True)
        self.receive_and_invoice_purchases(purchase, po_values)
        if values.get("step") == 2:
            self.receive_and_invoice_purchases(purchase.with_context(step=2), po_values)
        return purchase

    def create_invoice(self, values):
        po_values = self.get_references_from_values(values)
        if po_values.get("inv_price"):
            purchase = getattr(self, "purchase_order_1", None)
        if po_values.get("inv_price2"):
            purchase = getattr(self, "purchase_order_2", None)
        if self.l10n_ro_approved_price_difference:
            purchase = purchase.with_context(l10n_ro_approved_price_difference=True)
        self.receive_and_invoice_purchases(purchase, po_values)
        if values.get("step") == 2:
            self.receive_and_invoice_purchases(purchase.with_context(step=2), po_values)

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
                    # ``product_return_moves`` is a stored compute on ``picking_id``,
                    # so creating the wizard fills the lines without a Form.
                    return_wiz = self.env["stock.return.picking"].create(
                        {"picking_id": picking.ids[0]}
                    )
                    return_wiz.product_return_moves.write(
                        {
                            "quantity": stock_qty,
                            "to_refund": True,
                        }
                    )
                    if stock_lot:
                        lot = self._resolve(stock_lot)
                        return_wiz.product_return_moves.write({"lot_id": lot.id})
                    res = return_wiz.action_create_returns()
                    return_pick = self.env["stock.picking"].browse(res["res_id"])
                    return_pick.action_confirm()
                    return_pick.action_assign()
                    return_pick.move_ids._set_quantity_done(stock_qty)
                    return_pick.move_ids.picked = True
                    return_pick._action_done()
                    if self.log_checks:
                        _logger.info(
                            "Setting return picking variables: return_reception_%s_%s",
                            values.get("index", 0),
                            step,
                        )
                    setattr(
                        self,
                        f"return_reception_{values.get('index', 0)}_{step}",
                        return_pick,
                    )
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
                        lot = self._resolve(stock_lot)
                        picking.move_ids.write({"lot_id": lot.id})
                    picking.move_ids.picked = True
                    picking.button_validate()
                    if self.log_checks:
                        _logger.info(
                            "Setting picking variables: reception_%s_%s",
                            values.get("index", 0),
                            step,
                        )
                    setattr(self, f"reception_{values.get('index', 0)}_{step}", picking)
                    if picking.state == "assigned":
                        picking._action_done()
            if invoice_qty:
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
                    if self.log_checks:
                        _logger.info(
                            "Setting supplier invoice variables: "
                            "supplier_invoice_%s_%s",
                            values.get("index", 0),
                            step,
                        )
                    setattr(
                        self,
                        f"supplier_invoice_{values.get('index', 0)}_{step}",
                        invoice,
                    )
                    invoice.with_context(
                        l10n_ro_approved_price_difference=True
                    ).action_post()
            lc_pickings = purchase.picking_ids.filtered(
                lambda x: x.state == "done" and x.picking_type_code == "incoming"
            )
            if lc_pickings:
                lc_pickings = lc_pickings.sorted(
                    key=lambda r: (r.date_done, r.id), reverse=True
                )[:1]
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
            # ``product_return_moves`` is a stored compute on ``picking_id``,
            # so creating the wizard fills the lines without a Form.
            return_wiz = self.env["stock.return.picking"].create(
                {"picking_id": picking.id}
            )
            return_wiz.product_return_moves.write(
                {
                    "quantity": stock_qty,
                    "to_refund": True,
                }
            )
            if stock_lot:
                lot = self._resolve(stock_lot)
                return_wiz.product_return_moves.write({"lot_id": lot.id})
            res = return_wiz.action_create_returns()
            return_pick = self.env["stock.picking"].browse(res["res_id"])
            return_pick.action_confirm()
            return_pick.action_assign()
            return_pick.move_ids._set_quantity_done(stock_qty)
            return_pick.move_ids.picked = True
            return_pick._action_done()
            if self.log_checks:
                _logger.info(
                    "Setting return picking variables: "
                    "return_transit_int_transfer_%s_%s",
                    values.get("index", 0),
                    step,
                )
            setattr(
                self,
                f"return_transit_int_transfer_{values.get('index', 0)}_{step}",
                return_pick,
            )
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
            lot = self._resolve(stock_lot)
            move_vals["lot_ids"] = [(6, 0, [lot.id])]
        move_transit_out = self.env["stock.move"].create(move_vals)
        move_transit_out._action_confirm()
        move_transit_out._action_assign()
        move_transit_out._set_quantity_done(stock_qty)
        move_transit_out.picked = True
        move_transit_out._action_done()
        picking_transit_out = move_transit_out.picking_id
        if self.log_checks:
            _logger.info(
                "Setting picking variables: transit_int_transfer_out_%s_%s",
                values.get("index", 0),
                step,
            )
        setattr(
            self,
            f"transit_int_transfer_out_{values.get('index', 0)}_{step}",
            picking_transit_out,
        )
        move_transit_in = move_transit_out.move_dest_ids
        picking_receipt = move_transit_in.picking_id
        picking_receipt.move_ids.picked = True
        picking_receipt.button_validate()
        if self.log_checks:
            _logger.info(
                "Setting picking variables: transit_int_transfer_in_%s_%s",
                values.get("index", 0),
                step,
            )
        setattr(
            self,
            f"transit_int_transfer_in_{values.get('index', 0)}_{step}",
            picking_receipt,
        )
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
            # ``product_return_moves`` is a stored compute on ``picking_id``,
            # so creating the wizard fills the lines without a Form.
            return_wiz = self.env["stock.return.picking"].create(
                {"picking_id": picking.id}
            )
            return_wiz.product_return_moves.write(
                {
                    "quantity": stock_qty,
                    "to_refund": True,
                }
            )
            if stock_lot:
                lot = self._resolve(stock_lot)
                return_wiz.product_return_moves.write({"lot_id": lot.id})
            res = return_wiz.action_create_returns()
            return_pick = self.env["stock.picking"].browse(res["res_id"])
            return_pick.action_confirm()
            return_pick.action_assign()
            return_pick.move_ids._set_quantity_done(stock_qty)
            return_pick.move_ids.picked = True
            return_pick._action_done()
            if self.log_checks:
                _logger.info(
                    "Setting return picking variables: "
                    "return_direct_int_transfer_%s_%s",
                    values.get("index", 0),
                    step,
                )
            setattr(
                self,
                f"return_direct_int_transfer_{values.get('index', 0)}_{step}",
                return_pick,
            )
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
            lot = self._resolve(stock_lot)
            move_vals["lot_ids"] = [(6, 0, [lot.id])]
        move_transfer = self.env["stock.move"].create(move_vals)
        move_transfer._action_confirm()
        move_transfer._action_assign()
        move_transfer._set_quantity_done(stock_qty)
        move_transfer.picked = True
        move_transfer._action_done()
        picking_receipt = move_transfer.picking_id
        if self.log_checks:
            _logger.info(
                "Setting picking variables: direct_int_transfer_%s_%s",
                values.get("index", 0),
                step,
            )
        setattr(
            self,
            f"direct_int_transfer_{values.get('index', 0)}_{step}",
            picking_receipt,
        )
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
            # ``product_return_moves`` is a stored compute on ``picking_id``,
            # so creating the wizard fills the lines without a Form.
            return_wiz = self.env["stock.return.picking"].create(
                {"picking_id": picking.id}
            )
            return_wiz.product_return_moves.write(
                {
                    "quantity": stock_qty,
                    "to_refund": True,
                }
            )
            if stock_lot:
                lot = self._resolve(stock_lot)
                return_wiz.product_return_moves.write({"lot_id": lot.id})
            res = return_wiz.action_create_returns()
            return_pick = self.env["stock.picking"].browse(res["res_id"])
            return_pick.action_confirm()
            return_pick.action_assign()
            return_pick.move_ids._set_quantity_done(stock_qty)
            return_pick.move_ids.picked = True
            return_pick._action_done()
            if self.log_checks:
                _logger.info(
                    "Setting return picking as variable: picking_return_%s_%s_%s",
                    oper_type,
                    values.get("index", 0),
                    step,
                )
            setattr(
                self,
                f"return_picking_{oper_type}_{values.get('index', 0)}_{step}",
                return_pick,
            )
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
        if self.log_checks:
            _logger.info(
                "Setting picking as variable: picking_%s_%s_%s",
                oper_type,
                values.get("index", 0),
                step,
            )
        setattr(self, f"picking_{oper_type}_{values.get('index', 0)}_{step}", picking)
        move_vals = {
            "location_id": location_src,
            "location_dest_id": location_dest,
            "picking_id": picking.id,
            "product_id": product.id,
            "product_uom": product.uom_id.id,
            "product_uom_qty": picking_values.get("qty", 1),
        }
        if stock_lot:
            lot = self._resolve(stock_lot)
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
        acc = self.get_account_by_code("624000")
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
        if self.l10n_ro_cost_type:
            landed_cost.l10n_ro_cost_type = self.l10n_ro_cost_type
        landed_cost.compute_landed_cost()
        landed_cost.button_validate()
        if self.log_checks:
            _logger.info(
                "Setting landed cost as variable: landed_cost_%s",
                values.get("index", 0),
            )
        setattr(self, f"landed_cost_{values.get('index', 0)}", landed_cost)
        return landed_cost
