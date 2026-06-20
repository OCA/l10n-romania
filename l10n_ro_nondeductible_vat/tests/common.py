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

        # Set up the non-deductible tax grids: the deductible grids
        # (24 - TAX BASE / 24 - VAT) point to their non-deductible
        # counterparts (24_2 - ...). This is what flags a tax as
        # `l10n_ro_is_nondeductible`.
        cls.tag_base = _get_tags_by_name("24 - TAX BASE")
        cls.tag_base_nd = cls.tag_base.copy({"name": "24_2 - TAX BASE"})
        cls.tag_vat = _get_tags_by_name("24 - VAT")
        cls.tag_vat_nd = cls.tag_vat.copy({"name": "24_2 - VAT"})
        cls.tag_base.l10n_ro_nondeductible_tag_id = cls.tag_base_nd.id
        cls.tag_vat.l10n_ro_nondeductible_tag_id = cls.tag_vat_nd.id

        # Build dedicated non-deductible purchase taxes instead of relying
        # on the taxes shipped with the chart of accounts (which are not
        # configured for the Romanian non-deductible flow). The tax line
        # is flagged `l10n_ro_exclude_from_stock` so that, on stock moves,
        # it does not generate a deductible VAT entry (the VAT was already
        # deducted on reception); only the non-deductible reversal is kept.
        cls.tax = cls._l10n_ro_create_nondeductible_tax("21% Not deductible")
        # VAT on payment non-deductible tax: identical configuration but
        # with exigibility on payment (cash basis).
        cls.vatp_tax = cls._l10n_ro_create_nondeductible_tax(
            "21% Not deductible VATP",
            tax_exigibility="on_payment",
            cash_basis_account=cls.vatp_tax_account,
        )
        # A second VAT-on-payment tax sharing the very same grids (24 - TAX
        # BASE / 24 - VAT). It is used on fully deductible lines, to check that
        # a deductible and a non-deductible cash-basis tax can coexist on the
        # same invoice without the split bleeding from one into the other.
        cls.vatp_tax_deductible = cls._l10n_ro_create_nondeductible_tax(
            "21% VATP",
            tax_exigibility="on_payment",
            cash_basis_account=cls.vatp_tax_account,
        )

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

    @classmethod
    def _l10n_ro_create_nondeductible_tax(
        cls, name, tax_exigibility="on_invoice", cash_basis_account=None
    ):
        """Create a 21% purchase tax wired for the Romanian non-deductible
        flow: base grid 24 - TAX BASE, tax grid 24 - VAT (both with a
        non-deductible counterpart), and the tax repartition line flagged
        `l10n_ro_exclude_from_stock`."""

        def rep_lines():
            return [
                Command.create(
                    {
                        "repartition_type": "base",
                        "factor_percent": 100,
                        "tag_ids": [Command.set(cls.tag_base.ids)],
                    }
                ),
                Command.create(
                    {
                        "repartition_type": "tax",
                        "factor_percent": 100,
                        "account_id": cls.tax_account.id,
                        "tag_ids": [Command.set(cls.tag_vat.ids)],
                        "l10n_ro_exclude_from_stock": True,
                    }
                ),
            ]

        vals = {
            "name": name,
            "type_tax_use": "purchase",
            "amount_type": "percent",
            "amount": 21.0,
            "company_id": cls.env.company.id,
            "tax_exigibility": tax_exigibility,
            "invoice_repartition_line_ids": rep_lines(),
            "refund_repartition_line_ids": rep_lines(),
        }
        if cash_basis_account:
            vals["cash_basis_transition_account_id"] = cash_basis_account.id
        return cls.env["account.tax"].create(vals)
