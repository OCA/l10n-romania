# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _name = "product.product"
    _inherit = ["product.product", "l10n.ro.mixin"]

    def _get_fifo_candidates_domain(self, company):
        domain = super()._get_fifo_candidates_domain(company=company)
        l10n_ro_account_ids = self.env.context.get("l10n_ro_account_ids")
        if l10n_ro_account_ids:
            domain.append(("l10n_ro_account_id", "in", l10n_ro_account_ids))
        return domain
