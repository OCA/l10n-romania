# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models
from odoo.exceptions import UserError


class AccountTax(models.Model):
    _inherit = "account.tax"

    def _l10n_ro_get_base_from_tax_amount(self, tax_amount, currency=None):
        """Deduce the tax base underlying a known VAT amount.

        Used when only the VAT amount is known (e.g. a VAT price
        difference) and the corresponding base still has to be
        reported on a tax grid. The rate is derived through
        ``compute_all`` rather than reading ``self.amount`` directly,
        so 'percent', 'division' and 'group' taxes are all handled
        correctly.
        """
        self.ensure_one()
        if self.amount_type == "fixed":
            raise UserError(
                self.env._(
                    "Tax %s is a fixed amount tax; the VAT base cannot be"
                    " deduced from a VAT amount.",
                    self.display_name,
                )
            )
        rate_values = self.compute_all(100.0)
        tax_rate = rate_values["total_included"] - rate_values["total_excluded"]
        if not tax_rate:
            raise UserError(
                self.env._(
                    "Tax %s has no rate; the VAT base cannot be deduced.",
                    self.display_name,
                )
            )
        base_value = tax_amount * 100 / tax_rate
        return currency.round(base_value) if currency else base_value
