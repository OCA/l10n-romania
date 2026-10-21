# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models
from odoo.exceptions import ValidationError


class PosConfig(models.Model):
    _name = "pos.config"
    _inherit = ["pos.config", "l10n.ro.mixin"]

    @api.constrains("payment_method_ids")
    def _check_payment_method_ids_journal(self):
        """Let the registers of one shop share a single cash journal.

        Core refuses two cash payment methods on the same journal, which
        forces a journal per register. In Romania the *registru de casa* is
        kept per place, not per register: several registers standing in the
        same shop hand their cash to the same till, and it is counted and
        reported once. They need one cash journal between them.

        What stays is the other half of the check -- one cash payment method
        cannot serve two registers -- because each register still closes its
        own drawer.
        """
        romanian = self.filtered("is_l10n_ro_record")
        for config in romanian:
            for cash_method in config.payment_method_ids.filtered(
                lambda method: method.journal_id.type == "cash"
            ):
                if self.env["pos.config"].search_count(
                    [
                        ("id", "!=", config.id),
                        ("payment_method_ids", "in", cash_method.ids),
                    ],
                    limit=1,
                ):
                    raise ValidationError(
                        self.env._(
                            "The cash payment method %(method)s is already used "
                            "by another point of sale. Each register closes its "
                            "own drawer, so it needs a payment method of its "
                            "own -- they may share the cash journal behind it.",
                            method=cash_method.display_name,
                        )
                    )
        return super(PosConfig, self - romanian)._check_payment_method_ids_journal()
