# 2022 Nexterp Romania SRL
# ©  2008-2020 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    l10n_ro_custom_duty = fields.Boolean(
        help="This product can be used as custom duty in DVI",
    )
    l10n_ro_custom_commision = fields.Boolean(
        help="This product can be used as custom commision in DVI",
    )

    @api.constrains("l10n_ro_custom_duty", "type", "l10n_ro_custom_commision")
    def _check_l10n_ro_custom_duty(self):
        for rec in self:
            if (
                rec.l10n_ro_custom_duty or rec.l10n_ro_custom_commision
            ) and rec.type != "service":
                raise ValidationError(
                    _("Custom duty/commision product must have type=service")
                )
