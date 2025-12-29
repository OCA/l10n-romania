# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountTaxRepartitionLineExtend(models.Model):
    _name = "account.tax.repartition.line"
    _inherit = ["account.tax.repartition.line", "l10n.ro.mixin"]

    l10n_ro_exclude_from_stock = fields.Boolean(string="Romania - Exclude From Stock")
