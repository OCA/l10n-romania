from odoo import models


class MergePartnerAutomatic(models.TransientModel):
    _inherit = "base.partner.merge.automatic.wizard"

    def _merge(self, partner_ids, dst_partner=None, extra_checks=True):
        self = self.with_context(partner_merge=True)
        return super()._merge(
            partner_ids, dst_partner=dst_partner, extra_checks=extra_checks
        )
