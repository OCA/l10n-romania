from odoo import models


class MergePartnerAutomatic(models.TransientModel):
    _inherit = "base.partner.merge.automatic.wizard"

    def _merge(self, partner_ids, dst_partner=None, extra_checks=True):
        # Propagate partner_merge=True so the VAT/NRC uniqueness constraint is
        # skipped both on the source/auto-picked partners (via self.env) and on
        # an explicitly passed destination partner (browsed in the caller's
        # context, which our with_context on self would not reach).
        self = self.with_context(partner_merge=True)
        if dst_partner:
            dst_partner = dst_partner.with_context(partner_merge=True)
        return super()._merge(
            partner_ids, dst_partner=dst_partner, extra_checks=extra_checks
        )
