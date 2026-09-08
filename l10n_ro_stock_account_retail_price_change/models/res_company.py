# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models

SEQUENCE_CODE = "l10n.ro.retail.price.change"


class ResCompany(models.Model):
    _inherit = "res.company"

    def _l10n_ro_create_retail_price_change_sequence(self):
        """One Proces Verbal series per company.

        A single sequence shared by the whole database hands PVSP/2026/00001
        to one firm and PVSP/2026/00002 to the next, so neither has a series
        of its own to show. Each company numbers its own documents, and
        ``next_by_code`` picks the right one on its own: it looks for the
        sequences of the current company and the shared ones, and the
        company's own comes first.
        """
        Sequence = self.env["ir.sequence"].sudo()
        for company in self:
            if Sequence.search_count(
                [("code", "=", SEQUENCE_CODE), ("company_id", "=", company.id)],
                limit=1,
            ):
                continue
            Sequence.create(
                {
                    "name": "Retail Price Change",
                    "code": SEQUENCE_CODE,
                    "prefix": "PVSP/%(year)s/",
                    "padding": 5,
                    "company_id": company.id,
                }
            )

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        companies._l10n_ro_create_retail_price_change_sequence()
        return companies
