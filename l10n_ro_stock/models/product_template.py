# Copyright 2020 NextERP Romania SRL
# License OPL-1.0 or later
# (https://www.odoo.com/documentation/user/15.0/legal/licenses/licenses.html#).

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ["product.template", "l10n.ro.mixin"]

    l10n_ro_net_weight = fields.Float(
        "Net Weight",
        compute="_compute_l10n_ro_net_weight",
        inverse="_inverse_l10n_ro_net_weight",
        digits="Stock Weight",
        store=True,
    )
    l10n_ro_net_weight_uom_name = fields.Char(
        string="Net Weight unit of measure label",
        compute="_compute_l10n_ro_net_weight_uom_name",
    )

    def _compute_l10n_ro_net_weight_uom_name(self):
        self.l10n_ro_net_weight_uom_name = (
            self._get_weight_uom_name_from_ir_config_parameter()
        )

    @api.depends("product_variant_ids.l10n_ro_net_weight")
    def _compute_l10n_ro_net_weight(self):
        self._compute_template_field_from_variant_field("l10n_ro_net_weight")

    def _inverse_l10n_ro_net_weight(self):
        self._set_product_variant_field("l10n_ro_net_weight")


class ProductProduct(models.Model):
    _name = "product.product"
    _inherit = ["product.product", "l10n.ro.mixin"]

    l10n_ro_net_weight = fields.Float("Net Weight", digits="Stock Weight")
