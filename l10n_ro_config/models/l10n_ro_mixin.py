# Copyright 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from lxml import etree

from odoo import api, fields, models


class L10nRoMixin(models.AbstractModel):
    _name = "l10n.ro.mixin"
    _description = "Mixin model for applying to any object that use Romanian Accounting"

    is_l10n_ro_record = fields.Boolean(
        string="Is Romanian Record",
        compute="_compute_is_l10n_ro_record",
        readonly=False,
    )

    @api.depends(lambda self: self._check_company_id_in_fields())
    @api.depends_context("company")
    def _compute_is_l10n_ro_record(self):
        for obj in self:
            has_company = obj._check_company_id_in_fields()
            has_company = has_company and obj.company_id
            company = obj.company_id if has_company else obj.env.company
            obj.is_l10n_ro_record = company._check_is_l10n_ro_record()

    def _check_company_id_in_fields(self):
        has_company = "company_id" in self.env[self._name]._fields
        if has_company:
            return ["company_id"]
        return []

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)
        if self.env.company._check_is_l10n_ro_record():
            return result
        if view_type == "tree":
            doc = etree.fromstring(result["arch"])
            for field in doc.xpath('//field[contains(@name,"l10n_ro")]'):
                field.set("column_invisible", "True")
            result["arch"] = etree.tostring(doc)

        if view_type == "form":
            doc = etree.fromstring(result["arch"])
            for field in doc.xpath('//field[contains(@name,"l10n_ro")]'):
                field.set("invisible", "True")
                parent = field.getparent()
                if parent is not None and "tree" in parent.tag:
                    field.set("column_invisible", "True")
                else:
                    field.set("invisible", "True")

            for field in doc.xpath('//group[contains(@id,"l10n_ro")]'):
                field.set("invisible", "True")

            result["arch"] = etree.tostring(doc)

        if view_type == "search":
            doc = etree.fromstring(result["arch"])
            # Hide filters
            for field in doc.xpath('//filter[contains(@domain,"l10n_ro")]'):
                field.set("invisible", "True")
            # Hide groups by
            for field in doc.xpath('//filter[contains(@context,"l10n_ro")]'):
                field.set("invisible", "True")
            result["arch"] = etree.tostring(doc)
        return result
