from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ro_usage_location_id = fields.Many2one(
        "stock.location",
        string="Usage Location",
        readonly=True,
        copy=False,
        domain=[("usage", "=", "usage_giving")],
    )
    l10n_ro_consume_location_id = fields.Many2one(
        "stock.location",
        string="Consume Location",
        readonly=True,
        copy=False,
        domain=[("usage", "=", "consume")],
    )

    @api.model
    def create_missing_usage_location(self):
        company_ids = self.env["res.company"].search(
            [("l10n_ro_accounting", "=", True)]
        )
        companies_having_usage_loc = (
            self.env["stock.location"]
            .search([("usage", "=", "usage_giving")])
            .mapped("company_id")
        )
        company_without_property = company_ids - companies_having_usage_loc
        company_without_property._create_usage_location()

    @api.model
    def create_missing_consume_location(self):
        company_ids = self.env["res.company"].search(
            [("l10n_ro_accounting", "=", True)]
        )
        companies_having_consume_loc = (
            self.env["stock.location"]
            .search([("usage", "=", "consume")])
            .mapped("company_id")
        )
        company_without_property = company_ids - companies_having_consume_loc
        company_without_property._create_consume_location()

    def _create_usage_location(self):
        for company in self:
            location = self.env["stock.location"].create(
                {
                    "name": self.env._("Usage"),
                    "usage": "usage_giving",
                    "company_id": company.id,
                }
            )
            company.write({"l10n_ro_usage_location_id": location.id})

    def _create_consume_location(self):
        for company in self:
            location = self.env["stock.location"].create(
                {
                    "name": self.env._("Consume"),
                    "usage": "consume",
                    "company_id": company.id,
                }
            )
            company.write({"l10n_ro_consume_location_id": location.id})

    def _create_per_company_locations(self):
        res = super()._create_per_company_locations()
        if self._check_is_l10n_ro_record():
            self._create_usage_location()
            self._create_consume_location()
        return res
