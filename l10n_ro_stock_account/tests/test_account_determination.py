# Copyright (C) 2025 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo.tests import tagged

from .common import TestStockCommon


@tagged("post_install", "-at_install")
class TestStockAccountDetermination(TestStockCommon):
    """Verificare determinare conturi contabile analitice pentru fiecare depozit"""

    # se vor defini doua depzoite cu conturi contabile diferite
    # 371 va deveni 371.1 si respectiv 371.2
    # 607 va deveni 607.1 si respectiv 607.2
    # 707 va deveni 707.1 si respectiv 707.2

    @classmethod
    def setUpAccounts(cls):
        res = super().setUpAccounts()

        cls.account_371_1 = cls.account_valuation.copy({"name": "371001"})
        cls.account_371_2 = cls.account_valuation.copy({"name": "371002"})
        cls.account_607_1 = cls.account_expense.copy({"name": "607001"})
        cls.account_607_2 = cls.account_expense.copy({"name": "607002"})
        cls.account_707_1 = cls.account_income.copy({"name": "707001"})
        cls.account_707_2 = cls.account_income.copy({"name": "707002"})

        # definire pozitie fiscale pentru depozitul 1

        cls.fiscal_position_1 = cls.env["account.fiscal.position"].create(
            {
                "name": "Fiscal Position 1",
                "account_ids": [
                    (
                        0,
                        0,
                        {
                            "account_src_id": cls.account_valuation.id,
                            "account_dest_id": cls.account_371_1.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_src_id": cls.account_expense.id,
                            "account_dest_id": cls.account_607_1.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_src_id": cls.account_income.id,
                            "account_dest_id": cls.account_707_1.id,
                        },
                    ),
                ],
            }
        )
        cls.fiscal_position_2 = cls.env["account.fiscal.position"].create(
            {
                "name": "Fiscal Position 2",
                "account_ids": [
                    (
                        0,
                        0,
                        {
                            "account_src_id": cls.account_valuation.id,
                            "account_dest_id": cls.account_371_2.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_src_id": cls.account_expense.id,
                            "account_dest_id": cls.account_607_2.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_src_id": cls.account_income.id,
                            "account_dest_id": cls.account_707_2.id,
                        },
                    ),
                ],
            }
        )
        cls.stock_journal_1 = cls.env["account.journal"].create(
            {
                "name": "Stock Journal 1",
                "type": "general",
                "code": "STK1",
                "l10n_ro_fiscal_position_id": cls.fiscal_position_1.id,
            }
        )
        cls.stock_journal_2 = cls.env["account.journal"].create(
            {
                "name": "Stock Journal 2",
                "type": "general",
                "code": "STK2",
                "l10n_ro_fiscal_position_id": cls.fiscal_position_2.id,
            }
        )

        cls.warehouse_1 = cls.env["stock.warehouse"].create(
            {
                "name": "Warehouse 1",
                "code": "WH_D1",
                "company_id": cls.env.company.id,
                "l10n_ro_property_stock_journal_id": cls.stock_journal_1.id,
            }
        )

        cls.warehouse_2 = cls.env["stock.warehouse"].create(
            {
                "name": "Warehouse 2",
                "code": "WH_D2",
                "company_id": cls.env.company.id,
                "l10n_ro_property_stock_journal_id": cls.stock_journal_2.id,
            }
        )

        return res

    def test_account_determination(self):
        picking_type_in = self.warehouse_1.in_type_id
        self.create_po(picking_type_in=picking_type_in)
        self.check_stock_valuation(self.val_p1_i, self.val_p2_i, self.account_371_1)
