# Copyright (C) 2022 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class Account(models.Model):
    _name = "account.account"
    _inherit = ["account.account", "l10n.ro.mixin"]

    @api.model
    def _search(
        self,
        args,
        offset=0,
        limit=None,
        order=None,
        count=False,
        access_rights_uid=None,
    ):
        res = super()._search(
            args,
            offset=offset,
            limit=limit,
            order=order,
            count=count,
            access_rights_uid=access_rights_uid,
        )
        if not res:
            if self.env.company.parent_id:
                new_args = []
                for arg in args:
                    if arg[0] == "company_id":
                        new_args.append(
                            ("company_id", arg[1], self.env.company.parent_id.id)
                        )
                    else:
                        new_args.append(arg)
                self = self.with_company(self.env.company.parent_id.id)
                res = super()._search(
                    new_args,
                    offset=offset,
                    limit=limit,
                    order=order,
                    count=count,
                    access_rights_uid=access_rights_uid,
                )
        return res

    def name_get(self):
        res = super().name_get()
        if not res:
            if self.env.company.parent_id:
                self = self.with_company(self.env.company.parent_id.id)
                res = super().name_get()
        return res
