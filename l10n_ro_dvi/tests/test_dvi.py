# Copyright (C) 2020 Terrabit
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged

from odoo.addons.l10n_ro_stock_account.tests.common2 import TestStockCommon2


@tagged("post_install", "-at_install")
class TestDVI(TestStockCommon2):
    @classmethod
    def setUpClass(cls):
        super(TestDVI, cls).setUpClass()
        cls.env.company._l10n_ro_get_or_create_custom_duty_product()
        cls.env.company._l10n_ro_get_or_create_customs_commission_product()
        cls.tax_id = cls.product_1.supplier_taxes_id
        cls.journal_id = cls.env["account.journal"].search(
            [("type", "=", "general"), ("company_id", "=", cls.env.company.id)], limit=1
        )

    def test_dvi(self):
        self.create_po()
        self.create_invoice()
        dvi = Form(self.env["l10n.ro.account.dvi"])
        dvi.name = "DVI test"
        dvi.tax_id = self.tax_id
        dvi.journal_id = self.journal_id
        dvi.customs_duty_value = 100
        dvi.customs_commission_value = 50
        dvi = dvi.save()
        dvi.invoice_ids = [(6, 0, self.invoice.ids)]
        for dvi_line in dvi.line_ids:
            dvi_line.line_qty = dvi_line.qty
        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)
        self.check_account_valuation(self.val_p1_i, self.val_p2_i)
        for line in dvi.line_ids:
            self.assertEqual(line.price_subtotal, line.base_amount)
            self.assertAlmostEqual(line.vat_amount, round(line.base_amount * 0.19, 2))
        inv_subtotal = -1 * dvi.invoice_ids.amount_untaxed_signed
        self.assertEqual(dvi.invoice_base_value, inv_subtotal)
        self.assertEqual(dvi.invoice_tax_value, round(inv_subtotal * 0.19, 2))
        self.assertEqual(
            dvi.total_base_tax_value, inv_subtotal + dvi.customs_duty_value
        )
        self.assertEqual(
            dvi.total_tax_value,
            round((inv_subtotal + dvi.customs_duty_value) * 0.19, 2),
        )
        dvi.button_post()
        lc = dvi.landed_cost_ids
        self.assertEqual(lc.l10n_ro_cost_type, "dvi")
        self.assertEqual(lc.l10n_ro_tax_id, dvi.tax_id)
        self.assertEqual(lc.l10n_ro_base_tax_value, dvi.total_base_tax_value)
        self.assertEqual(lc.l10n_ro_tax_value, dvi.total_tax_value)
        self.assertEqual(lc.l10n_ro_account_dvi_id, dvi)
        self.assertEqual(lc.l10n_ro_dvi_bill_ids, dvi.invoice_ids)
        lc.button_validate()
        # Because of landed costs rounding issues, which is using ROUND=UP,
        # we will have more with 0.02 in stock
        # Example for product_1 split:
        # 500 / 1100 * 50 = 22,727272727 -> ROUNDED TO 22.73
        # 500 / 1100 * 25 = 11,363636364 -> ROUNDED TO 11.37
        # 600 / 1100 * 50 = 27,272727273 -> ROUNDED TO 27.28
        # 600 / 1100 * 25 = 13,636363636 -> ROUNDED TO 13.64
        # TOTAL TO BE SPLITTED 75 -> ROUNDED 75.02
        # For product_2 the 0.02 will be deducted
        self.check_stock_valuation(self.val_p1_i + 75.02, self.val_p2_i + 74.98)
        self.check_account_valuation(self.val_p1_i + 75.02, self.val_p2_i + 74.98)
        vat_paid_aml_name = "VAT paid at customs"
        vat_paid_line = lc.account_move_id.line_ids.filtered(
            lambda l: l.name == vat_paid_aml_name
        )
        tax_repartition_line = dvi.tax_id.invoice_repartition_line_ids.filtered(
            lambda r: r.repartition_type == "tax"
        )
        self.assertEqual(vat_paid_line.tax_line_id, dvi.tax_id)
        self.assertEqual(vat_paid_line.tax_repartition_line_id, tax_repartition_line)
        self.assertEqual(vat_paid_line.tax_tag_ids, tax_repartition_line.tag_ids)
        self.assertEqual(vat_paid_line.tax_base_amount, lc.l10n_ro_base_tax_value)

        # Revert DVI
        dvi.button_reverse()
        revert_lc = dvi.landed_cost_ids - lc
        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)
        self.check_account_valuation(self.val_p1_i, self.val_p2_i)
        inv_subtotal = -1 * dvi.invoice_ids.amount_untaxed_signed
        self.assertEqual(dvi.invoice_base_value, inv_subtotal)
        self.assertEqual(dvi.invoice_tax_value, round(inv_subtotal * 0.19, 2))
        self.assertEqual(
            dvi.total_base_tax_value, inv_subtotal + dvi.customs_duty_value
        )
        self.assertEqual(
            dvi.total_tax_value,
            round((inv_subtotal + dvi.customs_duty_value) * 0.19, 2),
        )
        self.assertEqual(revert_lc.l10n_ro_cost_type, "dvi")
        self.assertEqual(revert_lc.l10n_ro_tax_id, dvi.tax_id)
        self.assertEqual(
            revert_lc.l10n_ro_base_tax_value, -1 * dvi.total_base_tax_value
        )
        self.assertEqual(revert_lc.l10n_ro_tax_value, -1 * dvi.total_tax_value)
        self.assertEqual(revert_lc.l10n_ro_account_dvi_id, dvi)
        self.assertEqual(revert_lc.l10n_ro_dvi_bill_ids, dvi.invoice_ids)
        self.assertEqual(lc.account_move_id.state, "cancel")

    def test_vat_price_difference(self):
        # pentru valoare pozitiva
        self.create_po()
        self.create_invoice()
        self.account_expense = self.env["account.account"].search(
            [("code", "=", "658820")], limit=1
        )
        if not self.account_expense:
            self.account_expense = self.env["account.account"].create(
                {
                    "code": "658820",
                    "name": "Alte cheltuieli de exploatare nedeductibile",
                    "user_type_id": self.env.ref(
                        "account.data_account_type_expenses"
                    ).id,
                }
            )
        self.vat_product_id = self.env["product.product"].create(
            {
                "name": "VAT Price Difference",
                "type": "service",
                "purchase_method": "purchase",
                "invoice_policy": "order",
                "property_account_expense_id": self.account_expense.id,
            }
        )
        dvi = Form(self.env["l10n.ro.account.dvi"])
        dvi.name = "DVI test vat difference"
        dvi.tax_id = self.tax_id
        dvi.journal_id = self.journal_id
        dvi.customs_duty_value = 100
        dvi.customs_commission_value = 50
        dvi.vat_price_difference_product_id = self.vat_product_id
        dvi.vat_price_difference = 10
        dvi = dvi.save()
        dvi.button_post()
        for line in dvi.vat_price_difference_move_id.line_ids:
            if line.account_id.id == self.account_expense.id:
                self.assertEqual(line.debit, 10)
            else:
                self.assertEqual(line.credit, 10)
        # pentru valoare negativa
        self.create_po()
        self.create_invoice()
        dvi = Form(self.env["l10n.ro.account.dvi"])
        dvi.name = "DVI test vat difference"
        dvi.tax_id = self.tax_id
        dvi.journal_id = self.journal_id
        dvi.customs_duty_value = 100
        dvi.customs_commission_value = 50
        dvi.vat_price_difference_product_id = self.vat_product_id
        dvi.vat_price_difference = -10
        dvi = dvi.save()
        dvi.button_post()
        for line in dvi.vat_price_difference_move_id.line_ids:
            tags = self.tax_id.invoice_repartition_line_ids.filtered(
                lambda m: m.repartition_type == "tax"
            )[0]
            if line.account_id.id == tags.account_id.id:
                self.assertEqual(line.credit, 10)
            else:
                self.assertEqual(line.debit, 10)

        # cand da reverse move-ul trebuie sa fie in cancel
        self.create_po()
        self.create_invoice()
        self.vat_product_id = self.env["product.product"].create(
            {
                "name": "VAT Price Difference",
                "type": "service",
                "purchase_method": "purchase",
                "invoice_policy": "order",
            }
        )
        dvi = Form(self.env["l10n.ro.account.dvi"])
        dvi.name = "DVI test vat difference"
        dvi.tax_id = self.tax_id
        dvi.journal_id = self.journal_id
        dvi.customs_duty_value = 100
        dvi.customs_commission_value = 50
        dvi.vat_price_difference_product_id = self.vat_product_id
        dvi.vat_price_difference = -10
        dvi = dvi.save()
        dvi.invoice_ids = [(6, 0, self.invoice.ids)]
        for dvi_line in dvi.line_ids:
            dvi_line.line_qty = dvi_line.qty
        dvi.button_post()
        lc = dvi.landed_cost_ids
        lc.button_validate()
        dvi.button_reverse()
        self.assertEqual(dvi.vat_price_difference_move_id.state, "cancel")

        # daca nu exista cont pe produsul vat_product_id
        self.create_po()
        self.create_invoice()
        self.vat_product_id = self.env["product.product"].create(
            {
                "name": "VAT Price Difference",
                "type": "service",
                "purchase_method": "purchase",
                "invoice_policy": "order",
            }
        )
        self.vat_product_id.categ_id.property_account_expense_categ_id = False
        dvi = Form(self.env["l10n.ro.account.dvi"])
        dvi.name = "DVI test vat difference"
        dvi.tax_id = self.tax_id
        dvi.journal_id = self.journal_id
        dvi.customs_duty_value = 100
        dvi.customs_commission_value = 50
        dvi.vat_price_difference_product_id = self.vat_product_id
        dvi.vat_price_difference = -10
        dvi = dvi.save()
        with self.assertRaises(
            ValidationError,
            msg="Expense account is not set on product VAT Price Difference",
        ):
            dvi.button_post()

        # daca nu exista cont pe produsul vat_product_id
        self.create_po()
        self.create_invoice()
        self.vat_product_id = self.env["product.product"].create(
            {
                "name": "VAT Price Difference",
                "type": "service",
                "purchase_method": "purchase",
                "invoice_policy": "order",
                "property_account_expense_id": self.account_expense.id,
            }
        )
        dvi = Form(self.env["l10n.ro.account.dvi"])
        dvi.name = "DVI test vat difference"
        dvi.tax_id = self.tax_id
        dvi.journal_id = self.journal_id
        dvi.customs_duty_value = 100
        dvi.customs_commission_value = 50
        dvi.vat_price_difference_product_id = self.vat_product_id
        dvi.vat_price_difference = -10
        dvi.customs_duty_product_id.categ_id.property_account_expense_categ_id = False
        dvi.customs_duty_product_id.property_account_expense_id = False
        dvi = dvi.save()
        with self.assertRaises(
            ValidationError, msg="Expense account is not set on product Custom Duty"
        ):
            dvi.button_post()
