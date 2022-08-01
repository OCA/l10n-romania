# Copyright 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class L10nRoMixin(models.AbstractModel):
    _name = "l10n.ro.mixin"
    _description = (
        "Mixin model for applying to any object that use " "Romanian Accounting"
    )

    is_l10n_ro_record = fields.Boolean(
        string="Is Romanian Record",
        compute="_compute_is_l10n_ro_record",
        readonly=False,
    )

    def _compute_is_l10n_ro_record(self):
        for obj in self:
            has_company = "company_id" in self.env[obj._name]._fields
            has_company = has_company and obj.company_id
            company = obj.company_id if has_company else obj.env.company
            obj.is_l10n_ro_record = company.l10n_ro_accounting
