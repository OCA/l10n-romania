# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def _load_pos_data_fields(self, config):
        # The POS needs it to know that a refund always goes out as a credit
        # note, so the customer has to be picked before validating.
        return super()._load_pos_data_fields(config) + ["l10n_ro_accounting"]
