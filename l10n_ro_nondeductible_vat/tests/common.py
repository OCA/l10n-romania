# Copyright (C) 2020 Terrabit
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


import logging

from odoo import fields
from odoo.tests import Form, tagged

from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import (
    ValuationReconciliationTestCommon,
)

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestNondeductibleCommon(ValuationReconciliationTestCommon):
    @classmethod
    def setUpTax(cls):
        def get_account(code):
            account = cls.env["account.account"].search([("code", "=", code)], limit=1)
            return account

        def get_account_tag(name):
            account = cls.env["account.account.tag"].search(
                [("name", "=", name)], limit=1
            )
            return account

        cls.account_vat_deductible = get_account("442600")
        cls.account_income = get_account("707000")
        cls.account_valuation = get_account("371000")
        cls.account_difference = get_account("378000")
        cls.account_expense_vat_nondeductible = get_account("635200")
        if not cls.account_expense_vat_nondeductible:
            cls.account_expense_vat_nondeductible = get_account("635100")
        cls.account_expense = get_account("607000")
        cls.account_expense_nondeductible = cls.account_expense.copy(
            {
                "name": "Cheltuieli cu marfurile nedeductibile",
                "code": "607001",
            }
        )

        cls.account_expense.l10n_ro_nondeductible_account_id = (
            cls.account_expense_nondeductible
        )
        cls.tag_base = get_account_tag("+24_1 - BAZA")
        cls.tag_base_nondeductible = get_account_tag("+24_2 - BAZA")
        cls.tag_vat = get_account_tag("+24_1 - TVA")
        cls.tag_vat_nondeductible = get_account_tag("+24_2 - TVA")
        cls.minus_tag_base = get_account_tag("-24_1 - BAZA")
        cls.minus_tag_base_nondeductible = get_account_tag("-24_2 - BAZA")
        cls.minus_tag_vat = get_account_tag("-24_1 - TVA")
        cls.minus_tag_vat_nondeductible = get_account_tag("-24_2 - TVA")

        cls.uneligible_deductible_tax_account_id = get_account("442820")
        cls.account_cash_basis_base_account_id = (
            cls.uneligible_deductible_tax_account_id.copy(
                {
                    "name": "Baza TVA neexigibila",
                    "code": "442830",
                }
            )
        )
        cls.env.company.account_cash_basis_base_account_id = (
            cls.account_cash_basis_base_account_id
        )

        invoice_rep_lines = [
            (
                0,
                0,
                {
                    "factor_percent": 100,
                    "repartition_type": "base",
                    "tag_ids": [(6, 0, [cls.tag_base.id])],
                },
            ),
            (
                0,
                0,
                {
                    "factor_percent": 100,
                    "repartition_type": "tax",
                    "account_id": cls.account_vat_deductible.id,
                    "tag_ids": [(6, 0, [cls.tag_vat.id])],
                    "l10n_ro_exclude_from_stock": True,
                },
            ),
            (
                0,
                0,
                {
                    "factor_percent": 50,
                    "repartition_type": "tax",
                    "account_id": cls.account_expense_vat_nondeductible.id,
                    "tag_ids": [(6, 0, [cls.tag_vat_nondeductible.id])],
                },
            ),
            (
                0,
                0,
                {
                    "factor_percent": -50,
                    "repartition_type": "tax",
                    "account_id": cls.account_vat_deductible.id,
                    "tag_ids": [(6, 0, [cls.tag_vat.id])],
                },
            ),
            (
                0,
                0,
                {
                    "factor_percent": 500,
                    "repartition_type": "tax",
                    "account_id": cls.account_expense_vat_nondeductible.id,
                    "tag_ids": [(6, 0, [cls.tag_base_nondeductible.id])],
                    "l10n_ro_nondeductible": True,
                },
            ),
            (
                0,
                0,
                {
                    "factor_percent": -500,
                    "repartition_type": "tax",
                    "tag_ids": [(6, 0, [cls.tag_base.id])],
                },
            ),
        ]

        refund_rep_lines = [
            (
                0,
                0,
                {
                    "factor_percent": 100,
                    "repartition_type": "base",
                    "tag_ids": [(6, 0, [cls.minus_tag_base.id])],
                },
            ),
            (
                0,
                0,
                {
                    "factor_percent": 100,
                    "repartition_type": "tax",
                    "account_id": cls.account_vat_deductible.id,
                    "tag_ids": [(6, 0, [cls.minus_tag_vat.id])],
                    "l10n_ro_exclude_from_stock": True,
                },
            ),
            (
                0,
                0,
                {
                    "factor_percent": 50,
                    "repartition_type": "tax",
                    "account_id": cls.account_expense_vat_nondeductible.id,
                    "tag_ids": [(6, 0, [cls.minus_tag_vat_nondeductible.id])],
                },
            ),
            (
                0,
                0,
                {
                    "factor_percent": -50,
                    "repartition_type": "tax",
                    "account_id": cls.account_vat_deductible.id,
                    "tag_ids": [(6, 0, [cls.minus_tag_vat.id])],
                },
            ),
            (
                0,
                0,
                {
                    "factor_percent": 500,
                    "repartition_type": "tax",
                    "account_id": cls.account_expense_vat_nondeductible.id,
                    "tag_ids": [(6, 0, [cls.minus_tag_base_nondeductible.id])],
                    "l10n_ro_nondeductible": True,
                },
            ),
            (
                0,
                0,
                {
                    "factor_percent": -500,
                    "repartition_type": "tax",
                    "tag_ids": [(6, 0, [cls.minus_tag_base.id])],
                },
            ),
        ]

        cls.tax_10_nondeductible = cls.env["account.tax"].create(
            {
                "name": "Tax 10% Non Deductible 50%",
                "amount": 10.0,
                "amount_type": "percent",
                "type_tax_use": "purchase",
                "company_id": cls.env.company.id,
                "invoice_repartition_line_ids": invoice_rep_lines,
                "refund_repartition_line_ids": refund_rep_lines,
            }
        )

        # CASH BASIS
        invoice_rep_lines_cash_basis = [
            (
                0,
                0,
                {
                    "factor_percent": 100,
                    "repartition_type": "base",
                    "tag_ids": [(6, 0, [cls.tag_base.id])],
                },
            ),
            (
                0,
                0,
                {
                    "factor_percent": 100,
                    "repartition_type": "tax",
                    "account_id": cls.account_vat_deductible.id,
                    "tag_ids": [(6, 0, [cls.tag_vat.id])],
                    "l10n_ro_exclude_from_stock": True,
                },
            ),
            (
                0,
                0,
                {
                    "factor_percent": 50,
                    "repartition_type": "tax",
                    "account_id": cls.account_expense_vat_nondeductible.id,
                    "tag_ids": [(6, 0, [cls.tag_vat_nondeductible.id])],
                },
            ),
            (
                0,
                0,
                {
                    "factor_percent": -50,
                    "repartition_type": "tax",
                    "account_id": cls.account_vat_deductible.id,
                    "tag_ids": [(6, 0, [cls.tag_vat.id])],
                },
            ),
            (
                0,
                0,
                {
                    "factor_percent": 500,
                    "repartition_type": "tax",
                    "account_id": cls.account_expense_vat_nondeductible.id,
                    "tag_ids": [(6, 0, [cls.tag_base_nondeductible.id])],
                    "l10n_ro_nondeductible": True,
                    "l10n_ro_skip_cash_basis_account_switch": True,
                },
            ),
            (
                0,
                0,
                {
                    "factor_percent": -500,
                    "repartition_type": "tax",
                    "tag_ids": [(6, 0, [cls.tag_base.id])],
                    "l10n_ro_skip_cash_basis_account_switch": True,
                },
            ),
        ]

        refund_rep_lines_cash_basis = [
            (
                0,
                0,
                {
                    "factor_percent": 100,
                    "repartition_type": "base",
                    "tag_ids": [(6, 0, [cls.minus_tag_base.id])],
                },
            ),
            (
                0,
                0,
                {
                    "factor_percent": 100,
                    "repartition_type": "tax",
                    "account_id": cls.account_vat_deductible.id,
                    "tag_ids": [(6, 0, [cls.minus_tag_vat.id])],
                    "l10n_ro_exclude_from_stock": True,
                },
            ),
            (
                0,
                0,
                {
                    "factor_percent": 50,
                    "repartition_type": "tax",
                    "account_id": cls.account_expense_vat_nondeductible.id,
                    "tag_ids": [(6, 0, [cls.minus_tag_vat_nondeductible.id])],
                },
            ),
            (
                0,
                0,
                {
                    "factor_percent": -50,
                    "repartition_type": "tax",
                    "account_id": cls.account_vat_deductible.id,
                    "tag_ids": [(6, 0, [cls.minus_tag_vat.id])],
                },
            ),
            (
                0,
                0,
                {
                    "factor_percent": 500,
                    "repartition_type": "tax",
                    "account_id": cls.account_expense_vat_nondeductible.id,
                    "tag_ids": [(6, 0, [cls.minus_tag_base_nondeductible.id])],
                    "l10n_ro_nondeductible": True,
                    "l10n_ro_skip_cash_basis_account_switch": True,
                },
            ),
            (
                0,
                0,
                {
                    "factor_percent": -500,
                    "repartition_type": "tax",
                    "tag_ids": [(6, 0, [cls.minus_tag_base.id])],
                    "l10n_ro_skip_cash_basis_account_switch": True,
                },
            ),
        ]

        cls.tax_10_nondeductible_cash_basis = cls.env["account.tax"].create(
            {
                "name": "Tax 10% Non Deductible Cash Basis 50% ",
                "amount": 10.0,
                "amount_type": "percent",
                "type_tax_use": "purchase",
                "company_id": cls.env.company.id,
                "invoice_repartition_line_ids": invoice_rep_lines_cash_basis,
                "refund_repartition_line_ids": refund_rep_lines_cash_basis,
                "tax_exigibility": "on_payment",
                "cash_basis_transition_account_id": cls.uneligible_deductible_tax_account_id.id,
            }
        )

        cls.fp_model = cls.env["account.fiscal.position"]
        cls.fptvainc = cls.fp_model.search(
            [
                ("name", "ilike", "Regim TVA la Incasare"),
                ("company_id", "=", cls.env.company.id),
            ]
        )
        cls.fptvainc.write(
            {
                "tax_ids": [
                    (
                        0,
                        0,
                        {
                            "tax_src_id": cls.tax_10_nondeductible.id,
                            "tax_dest_id": cls.tax_10_nondeductible_cash_basis.id,
                        },
                    )
                ]
            }
        )

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        ro_template_ref = "l10n_ro.ro_chart_template"
        super(TestNondeductibleCommon, cls).setUpClass(
            chart_template_ref=ro_template_ref
        )

        cls.env.company.anglo_saxon_accounting = True
        cls.env.company.l10n_ro_accounting = True
        cls.env.company.l10n_ro_stock_acc_price_diff = True

        cls.setUpTax()

        stock_journal = cls.env["account.journal"].search(
            [("code", "=", "STJ"), ("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        if not stock_journal:
            stock_journal = cls.env["account.journal"].create(
                {"name": "Stock Journal", "code": "STJ", "type": "general"}
            )

        acc_diff_id = cls.account_difference.id

        category_value = {
            "name": "TEST Marfa",
            "property_cost_method": "fifo",
            "property_valuation": "real_time",
            "property_account_creditor_price_difference_categ": acc_diff_id,
            "property_account_income_categ_id": cls.account_income.id,
            "property_account_expense_categ_id": cls.account_expense.id,
            "property_stock_account_input_categ_id": cls.account_valuation.id,
            "property_stock_account_output_categ_id": cls.account_valuation.id,
            "property_stock_valuation_account_id": cls.account_valuation.id,
            "property_stock_journal": stock_journal.id,
            "l10n_ro_stock_account_change": True,
        }

        cls.category = cls.env["product.category"].search(
            [("name", "=", "TEST Marfa")], limit=1
        )
        if not cls.category:
            cls.category = cls.env["product.category"].create(category_value)
        else:
            cls.category.write(category_value)

        cls.product_1 = cls.env["product.product"].create(
            {
                "name": "Product A",
                "type": "product",
                "categ_id": cls.category.id,
                "invoice_policy": "delivery",
                "purchase_method": "receive",
                "list_price": 150,
                "standard_price": 100,
            }
        )

        cls.vendor = cls.env["res.partner"].search(
            [("name", "=", "TEST Vendor")], limit=1
        )
        if not cls.vendor:
            cls.vendor = cls.env["res.partner"].create({"name": "TEST Vendor"})

        cls.warehouse = cls.env["stock.warehouse"].create(
            {
                "name": "Warehouse Romania",
                "code": "ROW",
                "company_id": cls.env.company.id,
            }
        )

    def create_po(self, picking_type_in=None):

        if not picking_type_in:
            picking_type_in = self.warehouse.in_type_id

        po = Form(self.env["purchase.order"])
        po.partner_id = self.vendor
        po.picking_type_id = picking_type_in

        with po.order_line.new() as po_line:
            po_line.product_id = self.product_1
            po_line.product_qty = 100
            po_line.price_unit = 1
        po = po.save()
        po.button_confirm()
        self.picking = po.picking_ids[0]
        for move_line in self.picking.move_line_ids:
            if move_line.product_id == self.product_1:
                move_line.write({"qty_done": 100})

        self.picking.button_validate()
        self.picking._action_done()
        _logger.info("Receptie facuta")

        self.po = po
        return po

    def create_invoice_notdeductible(self, fiscal_position=False):
        invoice = Form(
            self.env["account.move"].with_context(
                default_move_type="in_invoice", default_invoice_date=fields.Date.today()
            )
        )
        invoice.partner_id = self.vendor
        invoice.purchase_id = self.po
        if fiscal_position:
            self.vendor.vat = "RO39187746"
            self.env["l10n.ro.res.partner.anaf"].create(
                {
                    "anaf_id": "1",
                    "vat": self.vendor.l10n_ro_vat_number,
                    "start_date": fields.Date.today(),
                    "publish_date": fields.Date.today(),
                    "operation_date": fields.Date.today(),
                    "operation_type": "I",
                }
            )
            invoice.fiscal_position_id = fiscal_position
        with invoice.invoice_line_ids.edit(0) as invoice_line_form:
            invoice_line_form.account_id = self.account_expense
            invoice_line_form.tax_ids.clear()
            invoice_line_form.tax_ids.add(self.tax_10_nondeductible)

        invoice = invoice.save()
        invoice.action_post()
        self.invoice = invoice

        _logger.info("Factura introdusa")

    def create_invoice(self):
        invoice = Form(
            self.env["account.move"].with_context(
                default_move_type="in_invoice", default_invoice_date=fields.Date.today()
            )
        )
        invoice.partner_id = self.vendor
        invoice.purchase_id = self.po
        invoice = invoice.save()
        invoice.action_post()

        _logger.info("Factura introdusa")

    def make_purchase(self):
        self.create_po()
        self.create_invoice()

    def make_purchase_notdeductible(self, fiscal_position=False):
        self.create_po()
        self.create_invoice_notdeductible(fiscal_position=fiscal_position)

    def make_consume(self):
        consume_type = self.warehouse.l10n_ro_consume_type_id
        stock_picking_form = Form(self.env["stock.picking"])
        stock_picking_form.picking_type_id = consume_type
        with stock_picking_form.move_ids_without_package.new() as line:
            line.product_id = self.product_1
            line.product_uom_qty = 10
            line.l10n_ro_nondeductible_tax_id = self.tax_10_nondeductible
        stock_picking = stock_picking_form.save()
        stock_picking.action_confirm()
        stock_picking.action_assign()
        for line in stock_picking.move_ids_without_package:
            line.quantity_done = 10
        stock_picking.button_validate()

    def make_inventory(self):
        stock_quant = self.env["stock.quant"].search(
            [
                ("product_id", "=", self.product_1.id),
                ("location_id", "=", self.warehouse.lot_stock_id.id),
            ]
        )
        stock_quant = stock_quant.with_context(inventory_mode=True)
        stock_quant.write(
            {
                "inventory_quantity": 50,
                "l10n_ro_nondeductible_tax_id": self.tax_10_nondeductible.id,
            }
        )
        stock_quant.action_apply_inventory()

    def check_account_valuation(self, balance, account=None):
        balance = round(balance, 2)
        if not account:
            account = self.account_valuation

        domain = [("account_id", "=", account.id)]
        account_valuations = self.env["account.move.line"].read_group(
            domain, ["debit:sum", "credit:sum"], ["account_id"]
        )
        self.assertNotEqual(account_valuations, [])
        for valuation in account_valuations:
            val = round(valuation["debit"] - valuation["credit"], 2)
            if valuation["account_id"][0] == account.id:
                _logger.info("Check account {} = {}".format(val, balance))
                self.assertAlmostEqual(val, balance)

    def check_no_move_lines(self, account=None):
        if not account:
            account = self.account_valuation

        domain = [("account_id", "=", account.id)]
        account_valuations = self.env["account.move.line"].read_group(
            domain, ["debit:sum", "credit:sum"], ["account_id"]
        )
        self.assertEqual(account_valuations, [])
