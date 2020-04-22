# Copyright (C) 2020 NextERP Romania S.R.L.
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

import odoo.tests.common as common
from odoo.exceptions import ValidationError
from odoo.fields import Date


class TestAccountCompensation(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestAccountCompensation, cls).setUpClass()
        res_users_account_manager = cls.env.ref("account.group_account_manager")
        partner_manager = cls.env.ref("base.group_partner_manager")
        cls.env.user.write(
            {"groups_id": [(6, 0, [res_users_account_manager.id, partner_manager.id])]}
        )
        # only adviser can create an account
        cls.account_receivable = cls.env["account.account"].create(
            {
                "code": "cust_acc",
                "name": "customer account",
                "user_type_id": cls.env.ref("account.data_account_type_receivable").id,
                "reconcile": True,
            }
        )
        cls.account_payable = cls.env["account.account"].create(
            {
                "code": "supp_acc",
                "name": "supplier account",
                "user_type_id": cls.env.ref("account.data_account_type_payable").id,
                "reconcile": True,
            }
        )
        cls.account_revenue = cls.env["account.account"].search(
            [
                (
                    "user_type_id",
                    "=",
                    cls.env.ref("account.data_account_type_revenue").id,
                )
            ],
            limit=1,
        )
        cls.account_expense = cls.env["account.account"].search(
            [
                (
                    "user_type_id",
                    "=",
                    cls.env.ref("account.data_account_type_expenses").id,
                )
            ],
            limit=1,
        )
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Supplier/Customer",
                "property_account_receivable_id": cls.account_receivable.id,
                "property_account_payable_id": cls.account_payable.id,
            }
        )
        cls.journal = cls.env["account.journal"].create(
            {"name": "Test sale journal", "type": "sale", "code": "TEST"}
        )
        cls.expenses_journal = cls.env["account.journal"].create(
            {"name": "Test expense journal", "type": "purchase", "code": "EXP"}
        )
        cls.miscellaneous_journal = cls.env["account.journal"].create(
            {"name": "Miscellaneus journal", "type": "general", "code": "OTHER"}
        )
        cls.customer_invoice = cls.env["account.move"].create(
            {
                "journal_id": cls.journal.id,
                "type": "out_invoice",
                "partner_id": cls.partner.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Test",
                            "price_unit": 2000.0,
                            "account_id": cls.account_revenue.id,
                        },
                    )
                ],
            }
        )
        cls.customer_invoice.action_post()
        customer_move = cls.customer_invoice
        cls.move_line_1 = customer_move.line_ids.filtered(
            lambda x: x.account_id == cls.account_receivable
        )
        cls.supplier_invoice = cls.env["account.move"].create(
            {
                "journal_id": cls.expenses_journal.id,
                "type": "in_invoice",
                "partner_id": cls.partner.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Test",
                            "price_unit": 1200.0,
                            "account_id": cls.account_expense.id,
                        },
                    )
                ],
            }
        )
        cls.supplier_invoice.action_post()
        supplier_move = cls.supplier_invoice
        cls.move_line_2 = supplier_move.line_ids.filtered(
            lambda x: x.account_id == cls.account_payable
        )
        cls.supplier_invoice = cls.env["account.move"].create(
            {
                "journal_id": cls.expenses_journal.id,
                "type": "in_invoice",
                "partner_id": cls.partner.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Test",
                            "price_unit": 200.0,
                            "account_id": cls.account_expense.id,
                        },
                    )
                ],
            }
        )
        cls.supplier_invoice.action_post()
        supplier_move = cls.supplier_invoice
        cls.move_line_3 = supplier_move.line_ids.filtered(
            lambda x: x.account_id == cls.account_payable
        )
        cls.supplier_invoice = cls.env["account.move"].create(
            {
                "journal_id": cls.expenses_journal.id,
                "type": "in_refund",
                "partner_id": cls.partner.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Test",
                            "price_unit": 200.0,
                            "account_id": cls.account_expense.id,
                        },
                    )
                ],
            }
        )
        cls.supplier_invoice.action_post()
        supplier_move = cls.supplier_invoice
        cls.move_line_4 = supplier_move.line_ids.filtered(
            lambda x: x.account_id == cls.account_payable
        )
        cls.supplier_invoice = cls.env["account.move"].create(
            {
                "journal_id": cls.expenses_journal.id,
                "type": "in_refund",
                "partner_id": cls.partner.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Test",
                            "price_unit": 200.0,
                            "account_id": cls.account_expense.id,
                        },
                    )
                ],
            }
        )
        cls.supplier_invoice.action_post()
        supplier_move = cls.supplier_invoice
        cls.move_line_5 = supplier_move.line_ids.filtered(
            lambda x: x.account_id == cls.account_payable
        )
        cls.supplier_invoice = cls.env["account.move"].create(
            {
                "journal_id": cls.expenses_journal.id,
                "type": "in_refund",
                "partner_id": cls.partner.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Test",
                            "price_unit": 200.0,
                            "account_id": cls.account_expense.id,
                        },
                    )
                ],
            }
        )
        cls.supplier_invoice.action_post()
        supplier_move = cls.supplier_invoice
        cls.move_line_6 = supplier_move.line_ids.filtered(
            lambda x: x.account_id == cls.account_payable
        )

    def test_compensation_onchange(self):
        # Test partner compensation onchange
        comp = self.env["account.compensation"].create(
            {
                "date": Date.context_today(self.env.user),
                "journal_id": self.miscellaneous_journal.id,
                "partner_id": self.partner.id,
            }
        )
        self.assertFalse(comp.line_ids)
        comp._onchange_for_all()
        self.assertTrue(comp.line_ids)
        self.assertEqual(len(comp.line_ids), 6)
        with self.assertRaises(ValidationError):
            comp.action_done()

    def test_partial_compensation(self):
        comp = self.env["account.compensation"].create(
            {
                "date": Date.context_today(self.env.user),
                "journal_id": self.miscellaneous_journal.id,
                "partner_id": self.partner.id,
            }
        )
        comp._onchange_for_all()
        comp_line_1 = comp_line_3 = self.env["account.compensation.line"]
        for line in comp.line_ids:
            if line.move_line_id == self.move_line_1:
                line.amount = 2500
                comp_line_1 = line
            if line.move_line_id == self.move_line_3:
                line.amount = -300
                comp_line_3 = line
            if line.move_line_id == self.move_line_4:
                line.amount = -200
            if line.move_line_id == self.move_line_5:
                line.amount = -200
            if line.move_line_id == self.move_line_6:
                line.amount = -200
        with self.assertRaises(ValidationError):
            comp_line_1.onchange_amount()
        with self.assertRaises(ValidationError):
            comp_line_3.onchange_amount()
        with self.assertRaises(ValidationError):
            comp.action_done()
        comp_line_1.amount = 800
        comp_line_3.amount = -200
        comp.action_done()

    def test_total_compensation(self):
        comp = self.env["account.compensation"].create(
            {
                "date": Date.context_today(self.env.user),
                "journal_id": self.miscellaneous_journal.id,
                "partner_id": self.partner.id,
            }
        )
        comp._onchange_for_all()
        for line in comp.line_ids:
            if line.move_line_id == self.move_line_1:
                line.amount = 2000
            if line.move_line_id == self.move_line_2:
                line.amount = -1200
            if line.move_line_id == self.move_line_3:
                line.amount = -200
            if line.move_line_id == self.move_line_4:
                line.amount = -200
            if line.move_line_id == self.move_line_5:
                line.amount = -200
            if line.move_line_id == self.move_line_6:
                line.amount = -200
        comp.action_done()
