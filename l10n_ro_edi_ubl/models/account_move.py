# ©  2008-2022 Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


import re

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_cirus_ro_name(self):
        self.ensure_one()
        vat = self.company_id.partner_id.commercial_partner_id.vat
        return "ubl_b2g_{}{}{}".format(
            vat or "", "_" if vat else "", re.sub(r"[\W_]", "", self.name)
        )
