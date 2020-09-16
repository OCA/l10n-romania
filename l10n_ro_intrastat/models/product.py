# ©  2008-2020 Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    intrastat_id = fields.Many2one("account.intrastat.code", string="Commodity Code")


class Product(models.Model):
    _inherit = "product.product"

    def search_intrastat_code(self):
        self.ensure_one()
        return self.intrastat_id or self.categ_id.search_intrastat_code()


class ProductCategory(models.Model):
    _inherit = "product.category"

    intrastat_id = fields.Many2one("account.intrastat.code", string="Commodity Code")

    def search_intrastat_code(self):
        self.ensure_one()
        return self.intrastat_id or (
            self.parent_id and self.parent_id.search_intrastat_code()
        )
