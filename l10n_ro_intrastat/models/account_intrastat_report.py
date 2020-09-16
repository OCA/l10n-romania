# ©  2008-2020 Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from odoo import fields, models, tools


class ReportIntrastat(models.Model):
    _name = "report.intrastat"
    _description = "Intrastat report"
    _auto = False

    name = fields.Char(string="Year", readonly=True)
    month = fields.Selection(
        [
            ("01", "January"),
            ("02", "February"),
            ("03", "March"),
            ("04", "April"),
            ("05", "May"),
            ("06", "June"),
            ("07", "July"),
            ("08", "August"),
            ("09", "September"),
            ("10", "October"),
            ("11", "November"),
            ("12", "December"),
        ],
        readonly=True,
    )
    supply_units = fields.Float(string="Supply Units", readonly=True)
    ref = fields.Char(string="Source document", readonly=True)
    code = fields.Char(string="Country code", readonly=True)
    intrastat_name = fields.Char(string="Intrastat code")
    weight = fields.Float(string="Weight", readonly=True)
    value = fields.Float(string="Value", readonly=True, digits=0)
    type = fields.Selection([("import", "Import"), ("export", "Export")], string="Type")
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
create or replace view report_intrastat as (
    select
        to_char(coalesce(inv.date, inv.invoice_date), 'YYYY') as name,
        to_char(coalesce(inv.date, inv.invoice_date), 'MM') as month,
        min(inv_line.id) as id,
        intrastat.name as intrastat_name,
        upper(inv_country.code) as code,




        sum  (inv_line.price_subtotal) as value,

        sum(pt.weight * inv_line.quantity * (
        CASE WHEN inv_line_uom.category_id IS NULL
        OR inv_line_uom.category_id = prod_uom.category_id
        THEN 1 ELSE inv_line_uom.factor END
        )) AS weight,

        sum(inv_line.quantity * (
            CASE WHEN inv_line_uom.category_id IS NULL
            OR inv_line_uom.category_id = prod_uom.category_id
            THEN 1 ELSE inv_line_uom.factor END
        )) AS supply_units,

        inv.currency_id as currency_id,
        inv.name as ref,
        case when inv.type in ('out_invoice','in_refund')
            then 'export'
            else 'import'
            end as type,
        inv.company_id as company_id
    from
        account_move inv
        left join account_move_line inv_line on inv_line.move_id=inv.id
        left join (product_template pt
            left join product_product pp on (pp.product_tmpl_id = pt.id))
        on (inv_line.product_id = pp.id)
        left join uom_uom inv_line_uom on inv_line_uom.id=inv_line.product_uom_id
        left join uom_uom prod_uom on prod_uom.id = pt.uom_id
        left join account_intrastat_code intrastat on pt.intrastat_id = intrastat.id
        left join (res_partner inv_address
        left join res_country inv_country on (inv_country.id = inv_address.country_id))
        on (inv_address.id = coalesce(inv.partner_shipping_id, inv.partner_id))
    where
        inv.state = 'posted'
        and inv_line.product_id is not null
        and inv_country.intrastat=true
    group by to_char(coalesce(inv.date, inv.invoice_date), 'YYYY'),
    to_char(coalesce(inv.date, inv.invoice_date), 'MM'),
    intrastat.id,inv.type,pt.intrastat_id,
    inv_country.code,inv.name,  inv.currency_id, inv.company_id
            )"""
        )
