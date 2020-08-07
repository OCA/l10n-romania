# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models


class AccountAccount(models.Model):
    _inherit = "account.account"

    def init(self, *a):
        """init called at every install to change the user_type_id for account 408 418
            this is required to be able to create a invoice with a line with this accounts
            and a invoice with right base from sale and purchase

            search with('company_id','=',self.env.company.id) is changing at env company
            search without compnay_id is modify at all the companies from this database
        """
        account_408 = self.search(
            [("code", "=", "408000"), ("name", "=", "Furnizori - facturi nesosite")]
        )
        for account in account_408:
            if account.user_type_id == self.env.ref(
                "account.data_account_type_payable"
            ):
                account.user_type_id = self.env.ref(
                    "account.data_account_type_current_liabilities"
                )

        account_418 = self.search(
            [("code", "=", "418000"), ("name", "=", "Clienţi - facturi de întocmit")]
        )
        for account in account_418:
            if account.user_type_id == self.env.ref(
                "account.data_account_type_receivable"
            ):
                account.user_type_id = self.env.ref(
                    "account.data_account_type_current_assets"
                )
