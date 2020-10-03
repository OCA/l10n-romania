# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models


class AccountAccount(models.Model):
    _inherit = "account.account"

    def init(self, *a):
        """init called at every install to change the user_type_id
            for accounts 408, 418.This is required to be able to create
            a invoice with a line with this accounts and a invoice with
            right base from sale and purchase
        """
        account_408 = self.search([("code", "=", "408000")])
        for account in account_408:
            account.user_type_id = self.env.ref(
                "account.data_account_type_current_liabilities"
            )

        account_418 = self.search([("code", "=", "418000")])
        for account in account_418:
            account.user_type_id = self.env.ref(
                "account.data_account_type_current_assets"
            )
