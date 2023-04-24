# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import api, fields, models


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ["product.template", "l10n.ro.mixin"]

    l10n_ro_nc_code = fields.Char(
        "Romania - NC Code",
        compute="_compute_l10n_ro_nc_code",
        inverse="_inverse_l10n_ro_nc_code",
        store=True,
    )

    @api.depends("product_variant_ids", "product_variant_ids.l10n_ro_nc_code")
    def _compute_l10n_ro_nc_code(self):
        unique_variants = self.filtered(
            lambda template: len(template.product_variant_ids) == 1
        )
        for template in unique_variants:
            template.l10n_ro_nc_code = template.product_variant_ids.l10n_ro_nc_code
        for template in self - unique_variants:
            template.l10n_ro_nc_code = False

    def _inverse_l10n_ro_nc_code(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.l10n_ro_nc_code = template.l10n_ro_nc_code


class ProductProduct(models.Model):
    _inherit = "product.product"

    l10n_ro_nc_code = fields.Char(
        "Romania - NC Code",
        compute="_compute_l10n_ro_nc_code",
        store=True,
        index=True,
        readonly=False,
    )

    @api.depends(lambda self: self._check_l10n_ro_intrastat_fields())
    def _compute_l10n_ro_nc_code(self):
        for product in self:
            l10n_ro_nc_code = product.l10n_ro_nc_code
            has_hs_code_id = "hs_code_id" in self.env[self._name]._fields
            if has_hs_code_id:
                rec_l10n_ro_nc_code = product.get_hs_code_recursively()
                if rec_l10n_ro_nc_code:
                    l10n_ro_nc_code = rec_l10n_ro_nc_code
            has_intrastat_id = "intrastat_id" in self.env[self._name]._fields
            if has_intrastat_id and product.intrastat_id:
                l10n_ro_nc_code = product.intrastat_id.code
            product.l10n_ro_nc_code = l10n_ro_nc_code

    def _check_l10n_ro_intrastat_fields(self):
        # Add compatibility with intrastat modules from OCA or Enterprise
        has_hs_code_id = "hs_code_id" in self.env[self._name]._fields
        if has_hs_code_id:
            return ["hs_code_id"]
        has_intrastat_id = "intrastat_id" in self.env[self._name]._fields
        if has_intrastat_id:
            return ["intrastat_id"]
        return []
