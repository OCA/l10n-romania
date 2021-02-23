# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class DailyStockReport(models.TransientModel):
    _name = "stock.daily.stock.report"
    _description = "DailyStockReport"

    # Filters fields, used for data computation

    location_id = fields.Many2one(
        "stock.location",
        domain="[('usage','=','internal'),('company_id','=',company_id)]",
        required=True,
    )
    product_id = fields.Many2one("product.product")

    product_ids = fields.Many2many(
        comodel_name="product.product"
    )

    date_range_id = fields.Many2one("date.range", string="Date range")
    date_from = fields.Date("Start Date", required=True, default=fields.Date.today)
    date_to = fields.Date("End Date", required=True, default=fields.Date.today)
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )
    mode = fields.Selection(
        [("product", "Product")], default="product", string="Detail mode", required=1
    )

    line_product_ids = fields.Many2many(comodel_name="stock.daily.stock.report.line")

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

    def do_compute_product(self):
        if self.product_id:
            product_list = [self.product_id.id]
        else:
            product_list = self.env["product.product"].search([]).mapped("id")
            _logger.warning(product_list)
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
                    sum(svl3.value), 0) as valoare_initiala,
            COALESCE(sum(svl.quantity),
                    sum(svl2.quantity),
                    sum(svl3.quantity), 0) as cantitate_initiala,
            0 as valoare_intrata,
            0 as cantitate_intrata,
            0 as valoare_iesita,
            0 as cantitate_iesita,
            COALESCE(sum(svl.value),
                    sum(svl2.value),
                    sum(svl3.value), 0) as valoare_finala,
            COALESCE(sum(svl.quantity),
                    sum(svl2.quantity),
                    sum(svl3.quantity), 0) as cantitate_finala,
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
            sm.product_id in %(product)s AND
            date_trunc('day',sm.date) <  %(date_from)s AND
            (sm.location_id = %(location)s OR sm.location_dest_id = %(location)s)
        GROUP BY sm.product_id, date_trunc('day',sm.date), sm.reference, rp.name
        order by sm.product_id, date_trunc('day',sm.date)) initial
    union
        (SELECT sm.product_id as product_id, 0 as valoare_initiala, 0 as cantitate_initiala,
            COALESCE(sum(svl.value),
                    sum(svl3.value), 0) as valoare_intrata,
            COALESCE(sum(svl.quantity),
                    sum(svl3.quantity) ,0) as cantitate_intrata,
            COALESCE(sum(svl1.value),
                    sum(svl2.value), 0) as valoare_iesita,
            COALESCE(sum(svl1.quantity),
                    sum(svl2.quantity), 0) as cantitate_iesita,
            COALESCE(sum(svl.value),
                    sum(svl1.value),
                    sum(svl2.value),
                    sum(svl3.value), 0) as valoare_finala,
            COALESCE(sum(svl.quantity),
                    sum(svl1.quantity),
                    sum(svl2.quantity),
                    sum(svl3.quantity), 0) as cantitate_finala,
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
            sm.product_id in %(product)s AND
            date_trunc('day',sm.date) >= %(date_from)s  AND
            date_trunc('day',sm.date) <= %(date_to)s  AND
            (sm.location_id = %(location)s OR sm.location_dest_id = %(location)s)
        GROUP BY sm.product_id, date_trunc('day',sm.date),  sm.reference, rp.name
        order by sm.product_id, date_trunc('day',sm.date))
    ORDER BY product_id, data
                """

        params = {
            "location": self.location_id.id,
            "product": tuple(product_list),
            "company": self.company_id.id,
            "date_from": fields.Date.to_string(self.date_from),
            "date_to": fields.Date.to_string(self.date_to),
        }

        self.env.cr.execute(query, params=params)

        if self.mode == "product":
            key = "product_id"

        res = self.env.cr.fetchall()
#
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
        #The records from stock_init are converted for in  stock card. That are, a record  with the stock
        # and the initial value, and other with the stock and the final value.
        # The rest of the records are those with stock movements from the selected period.

        products = {prod[key] for prod in stock_init}
        stoc_init_total = {}
        val_init_total = {}
        stoc_final_total = {}
        val_final_total = {}

        for product in products:
            stoc_init_total[product] = 0
            val_init_total[product] = 0
            stoc_final_total[product] = 0
            val_final_total[product] = 0

        for line in stock_init:
            stoc_init_total[line[key]] += line["cantitate_initiala"]
            val_init_total[line[key]] += line["valoare_initiala"]
            stoc_final_total[line[key]] += line["cantitate_finala"]
            val_final_total[line[key]] += line["valoare_finala"]

        sold_stock_init = []
        for product in products:
            sold_stock_init.append(
                {
                    key: product,
                    "report_id": self.id,
                    "cantitate_initiala": stoc_init_total[product],
                    "valoare_initiala": val_init_total[product],
                    "cantitate_finala": None,
                    "valoare_finala": None,
                    "referinta": "INITIALA",
                }
            )
            for line in stock_init:
                if line[key] == product:
                    if line["data"].date() >= self.date_from:
                        line["valoare_iesita"] = -line["valoare_iesita"]
                        line["cantitate_iesita"] = -line["cantitate_iesita"]
                        line["valoare_finala"] = 0
                        line["cantitate_finala"] = 0
                        sold_stock_init.append(line)
            sold_stock_init.append(
                {
                    key: product,
                    "report_id": self.id,
                    "cantitate_initiala": None,
                    "valoare_initiala": None,
                    "cantitate_finala": stoc_final_total[product],
                    "valoare_finala": val_final_total[product],
                    "referinta": "FINALA",
                }
            )
        if self.mode == "product":
            line_model = "stock.daily.stock.report.line"

        lines_report=self.env[line_model].create(sold_stock_init)

        for line_report in lines_report:
            if line_report.data :
                if line_report.product_id  not in self.product_ids:
                    self.write({'product_ids': [(4, line_report.product_id.id)]})
        self.line_product_ids = lines_report.mapped("id")

    def button_show(self):
        self.do_compute_product()
        if self.mode == "product":
            action = self.env.ref(
                "l10n_ro_stock_report.action_daily_stock_report_line"
            ).read()[0]
        action["domain"] = [("report_id", "=", self.id)]
        action["context"] = {"active_id": self.id}
        action["target"] = "main"
        return action

    def button_show_card(self):
        self.do_compute_product()
        if self.mode == "product":
            action = self.env.ref(
                "l10n_ro_stock_report.action_card_stock_report_line"
            ).read()[0]
        action["domain"] = [("report_id", "=", self.id)]
        action["context"] = {"active_id": self.id}
        action["target"] = "main"
        return action

    def button_show_card_pdf(self):
        self.do_compute_product()

        return self.env.ref('l10n_ro_stock_report.action_report_stock_card').report_action(self, config=False)


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
    data = fields.Datetime()
    referinta = fields.Char()
    partener = fields.Char()
