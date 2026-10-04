# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_ro_retail_non_vat = fields.Boolean(
        string="Not VAT (Retail)",
        help="Tick this on a sale tax that is not VAT - a packaging deposit "
        "(SGR), an eco fee, a WEEE contribution. In a retail warehouse the "
        "shelf price is split into cost, markup (378) and the VAT that "
        "becomes exigible on sale (4428); a charge collected on behalf of "
        "somebody else is none of those, so it is kept out of the split and "
        "out of the value carried on 371.\n"
        "Tick it on every variant of the charge a fiscal position can map to, "
        "the VAT included one included.",
    )

    def _l10n_ro_is_retail_vat(self):
        """Whether this sale tax is VAT as far as the retail split goes.

        The shelf price is split in three: the cost, the markup and the VAT
        that will become exigible when the goods are sold. Only VAT belongs on
        4428. A packaging deposit, an eco fee or a WEEE contribution riding on
        the same taxes is neither markup nor deferred VAT, and it is not part
        of the value the shop carries on 371 either - it is collected on
        behalf of somebody else and settled on its own account.

        Nothing on ``account.tax`` says whether a tax is VAT: the group, the
        amount type and the subtotal label are set or left empty as the chart
        happens to be written, on VAT and non VAT alike. So the answer is
        asked rather than guessed, and the default is VAT - a product whose
        sale taxes are only VAT, which is nearly all of them, needs no
        configuration at all.
        """
        self.ensure_one()
        return not self.l10n_ro_retail_non_vat
