# Copyright (C) 2020 Terrabit
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


import logging

from odoo import Command, fields
from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestROStockCommon
from odoo.addons.l10n_ro_vat_on_payment.tests.test_vat_on_payment import (
    TestVATonpayment,
)

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestNondeductibleCommon(TestROStockCommon, TestVATonpayment):
    @classmethod
    @TestROStockCommon.setup_country("ro")
    def setUpClass(cls):
        def get_account(code):
            account = cls.env["account.account"].search([("code", "=", code)], limit=1)
            return account

        def _get_tags_by_name(name):
            return cls.env["account.account.tag"].search([("name", "=", name)], limit=1)

        super().setUpClass()

        cls.env.user.group_ids += cls.env.ref(
            "account.group_partial_purchase_deductibility"
        )
        # Use standard Odoo tax (e.g. VAT 21% G)
        cls.tax = cls.env["account.tax"].search(
            [
                ("type_tax_use", "=", "purchase"),
                ("name", "=", "21% G"),
                ("company_id", "=", cls.env.company.id),
            ],
            limit=1,
        )
        if not cls.tax:
            raise Exception("Standard VAT 21% G tax not found for company!")
        cls.vatp_tax = cls.env["account.tax"].search(
            [
                ("type_tax_use", "=", "purchase"),
                ("name", "=", "21%"),
                ("company_id", "=", cls.env.company.id),
            ],
            limit=1,
        )
        if not cls.vatp_tax:
            raise Exception(
                "Standard VAT on Payment VAT 21% tax not found for company!"
            )
        # Set l10n_ro_exclude_from_stock on tax repartition lines
        for rep_line in cls.tax.repartition_line_ids.filtered(
            lambda line: line.repartition_type == "tax"
        ):
            rep_line.l10n_ro_exclude_from_stock = True

        # Set l10n_ro_nondeductible_tag_id on tax tags for non-deductible logic
        cls.tag_base = _get_tags_by_name("24_1 - TAX BASE")
        cls.tag_base_nd = _get_tags_by_name("24_2 - TAX BASE")
        cls.tag_vat = _get_tags_by_name("24_1 - VAT")
        cls.tag_vat_nd = _get_tags_by_name("24_2 - VAT")
        if cls.tag_base and cls.tag_base_nd:
            cls.tag_base.l10n_ro_nondeductible_tag_id = cls.tag_base_nd.id
        if cls.tag_vat and cls.tag_vat_nd:
            cls.tag_vat.l10n_ro_nondeductible_tag_id = cls.tag_vat_nd.id

        cls.tax_account = get_account("442600")
        cls.payable_account = get_account("401100")
        cls.receivable_account = get_account("411100")
        # Create non deductible account
        cls.account_expense = get_account("607000")
        cls.nd_account = cls.account_expense.copy(
            {"name": "Expenditure on goods Non Deductible", "code": "607100"}
        )
        cls.account_expense.l10n_ro_nondeductible_account_id = cls.nd_account.id

        cls.nd_expense_tax_account = get_account("635200")
        cls.env.company.l10n_ro_nondeductible_account_id = cls.nd_expense_tax_account
        # Set up account_cash_basis_base_account_id on company
        vatp_tax_account_id = get_account("442820")
        cls.vatp_tax_account = vatp_tax_account_id
        vatp_base_account_id = vatp_tax_account_id.copy(
            {
                "name": "Baza TVA neexigibila",
                "code": "442830",
            }
        )
        cls.env.company.account_cash_basis_base_account_id = vatp_base_account_id
        cls.vatp_base_account_id = vatp_base_account_id

        # Create invoices
        cls.nd_invoice = cls.invoice_model.create(
            {
                "partner_id": cls.fbr_partner.id,
                "move_type": "in_invoice",
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Test description #1",
                            "product_id": cls.product_fifo.id,
                            "account_id": cls.account_expense.id,
                            "quantity": 1.0,
                            "price_unit": 100.0,
                            "tax_ids": [(6, 0, cls.tax.ids)],
                        }
                    )
                ],
            }
        )

        cls.vatp_nd_invoice = cls.invoice_model.create(
            {
                "partner_id": cls.lxt_partner.id,
                "move_type": "in_invoice",
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Test description #1",
                            "product_id": cls.product_fifo.id,
                            "account_id": cls.account_expense.id,
                            "quantity": 1.0,
                            "price_unit": 100.0,
                            "tax_ids": [(6, 0, cls.vatp_tax.ids)],
                        }
                    )
                ],
            }
        )

        # Create inventory for product fifo
        cls.product_fifo.standard_price = 100
        inventory_vals = {
            "product_id": cls.product_fifo.id,
            "location_id": cls.location.id,
            "inventory_quantity": 10,
        }
        cls.env["stock.quant"].with_context(inventory_mode=True).create(
            inventory_vals
        ).action_apply_inventory()
