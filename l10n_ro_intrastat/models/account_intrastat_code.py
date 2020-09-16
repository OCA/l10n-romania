# ©  2008-2020 Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from odoo import api, fields, models


class AccountIntrastatCode(models.Model):
    """
    Codes used for the intrastat reporting.

    The list of commodity codes is available on:
          http://www.intrastat.ro/doc/CN_2020.xml
    """

    _name = "account.intrastat.code"
    _description = "Intrastat Code"
    _translate = False
    _order = "nckey"

    name = fields.Char(string="Name")
    nckey = fields.Char(string="NC Key")
    code = fields.Char(string="NC Code", required=True)

    description = fields.Char(string="Description")
    suppl_unit_code = fields.Char("SupplUnitCode")

    def name_get(self):
        result = []
        for r in self:
            text = r.name or r.description
            result.append((r.id, text and "{} {}".format(r.code, text) or r.code))
        return result

    @api.model
    def _name_search(self, name="", args=None, operator="ilike", limit=100):
        if args is None:
            args = []
        domain = args + [
            "|",
            "|",
            ("code", operator, name),
            ("name", operator, name),
            ("description", operator, name),
        ]
        return super(AccountIntrastatCode, self).search(domain, limit=limit).name_get()

    _sql_constraints = [
        (
            "intrastat_region_nckey_unique",
            "UNIQUE (nckey)",
            "The NC key must be unique.",
        ),
    ]
