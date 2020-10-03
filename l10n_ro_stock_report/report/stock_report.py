# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class DailyStockReport(models.TransientModel):
    _name = "stock.daily.stock.report"
    _description = "DailyStockReport"

    # Filters fields, used for data computation

    location_id = fields.Many2one(
        "stock.location",
        domain="[('usage','=','internal'),('company_id','=',company_id)]",
        required=True,
    )

    date_range_id = fields.Many2one("date.range", string="Date range")
    date_from = fields.Date("Start Date", required=True, default=fields.Date.today)
    date_to = fields.Date("End Date", required=True, default=fields.Date.today)
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.user.company_id
    )
    mode = fields.Selection(
        [("product", "Product")], default="product", string="Detail mode",
    )

    line_product_ids = fields.One2many("stock.daily.stock.report.line", "report_id")

    @api.model
    def default_get(self, fields_list):
        res = super(DailyStockReport, self).default_get(fields_list)
        mode = res.get("mode", "product")
        if mode == "product":
            today = fields.Date.context_today(self)
            today = fields.Date.from_string(today)

            from_date = today + relativedelta(day=1, months=0, days=0)
            to_date = today + relativedelta(day=1, months=1, days=-1)

            res["date_from"] = fields.Date.to_string(from_date)
            res["date_to"] = fields.Date.to_string(to_date)
        return res

    @api.onchange("date_range_id")
    def onchange_date_range_id(self):
        """Handle date range change."""
        if self.date_range_id:
            self.date_from = self.date_range_id.date_start
            self.date_to = self.date_range_id.date_end

    def do_compute(self):

        self.env["account.move.line"].check_access_rights("read")

        lines = self.env["stock.daily.stock.report.line"].search(
            [("report_id", "=", self.id)]
        )
        lines.unlink()
        stock_init = []
        if self.mode == "product":
            query = """
SELECT product_id,valoare_initiala,cantitate_initiala,
        valoare_intrata,cantitate_intrata,valoare_iesita,
        cantitate_iesita,valoare_finala,cantitate_finala,
        data,reference,partner
FROM
    (SELECT sm.product_id as product_id,
        COALESCE(sum(svl.value),
                sum(svl2.value),
                sum(svl3.value)) as valoare_initiala,
        COALESCE(sum(svl.quantity),
                sum(svl2.quantity),
                sum(svl3.quantity)) as cantitate_initiala,
        0 as valoare_intrata,
        0 as cantitate_intrata,
        0 as valoare_iesita,
        0 as cantitate_iesita,
        COALESCE(sum(svl.value),
                sum(svl2.value),
                sum(svl3.value)) as valoare_finala,
        COALESCE(sum(svl.quantity),
                sum(svl2.quantity),
                sum(svl3.quantity)) as cantitate_finala,
        date_trunc('day',sm.date) as data,
        sm.reference as reference,
        rp.name as partner
    from stock_move as sm
        left join (select * from stock_valuation_layer
                    where valued_type !='internal_transfer' or valued_type is Null)
                    as svl on svl.stock_move_id = sm.id
        left join (select * from stock_valuation_layer
                    where valued_type ='internal_transfer' and quantity<0) as svl2
                    on svl2.stock_move_id = sm.id and sm.location_id=%(location)s
        left join (select * from stock_valuation_layer
                    where valued_type ='internal_transfer' and quantity>0) as svl3
                    on svl3.stock_move_id = sm.id and sm.location_dest_id=%(location)s
        left join res_partner rp on rp.id=sm.partner_id
    where sm.state = 'done' AND
        sm.company_id = %(company)s AND
        date_trunc('day',sm.date) <  %(date_from)s AND
        (sm.location_id = %(location)s OR sm.location_dest_id = %(location)s)
    GROUP BY sm.product_id, date_trunc('day',sm.date), sm.reference, rp.name
    order by sm.product_id, date_trunc('day',sm.date)) initial
union
    (SELECT sm.product_id as product_id, 0 as valoare_initiala, 0 as cantitate_initiala,
        COALESCE(sum(svl.value),
                sum(svl3.value),0) as valoare_intrata,
        COALESCE(sum(svl.quantity),
                sum(svl3.quantity),0) as cantitate_intrata,
        COALESCE(sum(svl1.value),
                sum(svl2.value),0) as valoare_iesita,
        COALESCE(sum(svl1.quantity),
                sum(svl2.quantity),0) as cantitate_iesita,
        COALESCE(sum(svl.value),
                sum(svl1.value),
                sum(svl2.value),
                sum(svl3.value)) as valoare_finala,
        COALESCE(sum(svl.quantity),
                sum(svl1.quantity),
                sum(svl2.quantity),
                sum(svl3.quantity)) as cantitate_finala,
        date_trunc('day',sm.date) as data,
        sm.reference as reference,
        rp.name as partner
    from stock_move as sm
        left join (select * from stock_valuation_layer
                    where valued_type !='internal_transfer' or valued_type is Null)
                    as svl on svl.stock_move_id = sm.id and
                    sm.location_dest_id=%(location)s
        left join (select * from stock_valuation_layer
                    where valued_type !='internal_transfer' or valued_type is Null)
                    as svl1 on svl1.stock_move_id = sm.id and
                    sm.location_id=%(location)s
        left join (select * from stock_valuation_layer
                    where valued_type ='internal_transfer' and quantity<0) as svl2
                    on svl2.stock_move_id = sm.id and
                    sm.location_id=%(location)s
        left join (select * from stock_valuation_layer
                    where valued_type ='internal_transfer' and quantity>0) as svl3
                    on svl3.stock_move_id = sm.id and
                    sm.location_dest_id=%(location)s
        left join res_partner rp on rp.id=sm.partner_id
    where
        sm.state = 'done' AND
        sm.company_id = %(company)s AND
        date_trunc('day',sm.date) >= %(date_from)s  AND
        date_trunc('day',sm.date) <= %(date_to)s  AND
        (sm.location_id = %(location)s OR sm.location_dest_id = %(location)s)
    GROUP BY sm.product_id, date_trunc('day',sm.date),  sm.reference, rp.name
    order by sm.product_id, date_trunc('day',sm.date))
ORDER BY product_id, data
            """

        params = {
            "location": self.location_id.id,
            "company": self.company_id.id,
            "date_from": fields.Date.to_string(self.date_from),
            "date_to": fields.Date.to_string(self.date_to),
        }

        self.env.cr.execute(query, params=params)

        if self.mode == "product":
            key = "product_id"

        res = self.env.cr.fetchall()

        for row in res:
            values = {
                key: row[0],
                "report_id": self.id,
                "valoare_initiala": row[1],
                "cantitate_initiala": row[2],
                "valoare_intrata": row[3],
                "cantitate_intrata": row[4],
                "valoare_iesita": row[5],
                "cantitate_iesita": row[6],
                "valoare_finala": row[7],
                "cantitate_finala": row[8],
                "data": row[9],
                "referinta": row[10],
                "partener": row[11],
            }
            stock_init += [values]

        if self.mode == "product":
            line_model = "stock.daily.stock.report.line"

        self.env[line_model].create(stock_init)

    def button_show(self):
        self.do_compute()
        if self.mode == "product":
            action = self.env.ref(
                "l10n_ro_stock_report.action_daily_stock_report_line"
            ).read()[0]
        action["domain"] = [("report_id", "=", self.id)]
        action["context"] = {"active_id": self.id}
        action["target"] = "main"
        return action


class DailyStockReportLine(models.TransientModel):
    _name = "stock.daily.stock.report.line"
    _description = "DailyStockReportLine"

    report_id = fields.Many2one("stock.daily.stock.report")
    product_id = fields.Many2one("product.product")
    valoare_initiala = fields.Float()
    cantitate_initiala = fields.Float()
    valoare_intrata = fields.Float()
    cantitate_intrata = fields.Float()
    valoare_iesita = fields.Float()
    cantitate_iesita = fields.Float()
    valoare_finala = fields.Float()
    cantitate_finala = fields.Float()
    data = fields.Date()
    referinta = fields.Char()
    partener = fields.Char()
