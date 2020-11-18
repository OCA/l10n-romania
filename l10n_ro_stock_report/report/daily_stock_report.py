# ©  2008-2018 Fekete Mihai <mihai.fekete@forbiom.eu>
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models


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
        [("product", "Product"), ("ref", "Reference")],
        default="ref",
        string="Detail mode",
    )

    line_product_ids = fields.One2many("stock.daily.stock.report.line", "report_id")
    line_ref_ids = fields.One2many("stock.daily.stock.report.ref", "report_id")

    @api.model
    def default_get(self, fields_list):
        res = super(DailyStockReport, self).default_get(fields_list)
        mode = res.get("mode", "ref")
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
        stock_in = []
        stock_out = []
        if self.mode == "ref":
            query = """

    SELECT 'initial',  sum(value), sum(svl.quantity), array_agg(svl.id)
        from stock_move as sm
        left join  stock_valuation_layer as svl on svl.stock_move_id = sm.id
        where sm.state = 'done' AND
              sm.company_id = %(company)s AND
              sm.date <  %(date)s AND
            ( sm.location_id = %(location)s OR
              sm.location_dest_id = %(location)s )

            """
        else:
            query = """
    SELECT svl.product_id,  sum(value), sum(svl.quantity), array_agg(svl.id)
        from stock_move as sm
        left join  stock_valuation_layer as svl on svl.stock_move_id = sm.id
        where sm.state = 'done' AND
              sm.company_id = %(company)s AND
              sm.date <  %(date)s AND
            ( sm.location_id = %(location)s OR
            sm.location_dest_id = %(location)s)
            GROUP BY svl.product_id
            """
        params = {
            "location": self.location_id.id,
            "company": self.company_id.id,
            "date": fields.Date.to_string(self.date_from),
        }

        self.env.cr.execute(query, params=params)

        if self.mode == "ref":
            key = "ref"
        else:
            key = "product_id"

        res = self.env.cr.fetchall()

        for row in res:

            values = {
                key: row[0],
                "report_id": self.id,
                "amount": row[1] or 0.0,
                "quantity": row[2] or 0.0,
                "type": "balance",
                "valuation_ids": [(6, 0, list(row[3] or ()))],
            }
            stock_init += [values]

        if self.mode == "ref":
            query = """
    SELECT sm.origin, sum(value), sum(svl.quantity), array_agg(svl.id)

        from stock_move as sm
        left join  stock_valuation_layer as svl on svl.stock_move_id = sm.id
        where
              svl.value >=0 and
              sm.state = 'done' AND

              sm.company_id = %(company)s AND
              date_trunc('day',date) >= %(date_from)s AND
              date_trunc('day',date) <= %(date_to)s AND
            ( sm.location_id = %(location)s OR
            sm.location_dest_id = %(location)s)
            GROUP BY sm.picking_id, sm.origin
            """
        else:
            query = """
    SELECT svl.product_id,  sum(value), sum(svl.quantity) , array_agg(svl.id)

        from stock_move as sm
        left join  stock_valuation_layer as svl on svl.stock_move_id = sm.id
        where
              svl.value >=0 and
              sm.state = 'done' AND

              sm.company_id = %(company)s AND
              date_trunc('day',date) >= %(date_from)s AND
              date_trunc('day',date) <= %(date_to)s AND
            ( sm.location_id = %(location)s OR
            sm.location_dest_id = %(location)s)
            GROUP BY svl.product_id
            """

        params = {
            "location": self.location_id.id,
            "company": self.company_id.id,
            "date_from": fields.Date.to_string(self.date_from),
            "date_to": fields.Date.to_string(self.date_to),
        }

        self.env.cr.execute(query, params=params)

        res = self.env.cr.fetchall()
        for row in res:

            values = {
                key: row[0],
                "report_id": self.id,
                "amount": row[1],
                "quantity": row[2],
                "type": "in",
                "valuation_ids": [(6, 0, list(row[3]))],
            }
            stock_in += [values]

        if self.mode == "ref":
            query = """
    SELECT sm.origin,  sum(value), sum(svl.quantity) , array_agg(svl.id)

        from stock_move as sm
        left join  stock_valuation_layer as svl on svl.stock_move_id = sm.id
        where
              svl.value < 0 and
              sm.state = 'done' AND

              sm.company_id = %(company)s AND
             date_trunc('day',date) >= %(date_from)s AND
             date_trunc('day',date)  <= %(date_to)s AND
            ( sm.location_id = %(location)s OR
             sm.location_dest_id = %(location)s)
            GROUP BY sm.origin
            """
        else:
            query = """
    SELECT svl.product_id,  sum(value), sum(svl.quantity) , array_agg(svl.id)

        from stock_move as sm
        left join  stock_valuation_layer as svl on svl.stock_move_id = sm.id
        where
              svl.value < 0 and
              sm.state = 'done' AND

              sm.company_id = %(company)s AND
             date_trunc('day',date) >= %(date_from)s AND
              date_trunc('day',date)  <= %(date_to)s AND
            ( sm.location_id = %(location)s OR
            sm.location_dest_id = %(location)s)
            GROUP BY svl.product_id
            """

        params = {
            "location": self.location_id.id,
            "company": self.company_id.id,
            "date_from": fields.Date.to_string(self.date_from),
            "date_to": fields.Date.to_string(self.date_to),
        }

        self.env.cr.execute(query, params=params)

        res = self.env.cr.fetchall()
        for row in res:
            values = {
                key: row[0],
                "report_id": self.id,
                "amount": row[1],
                "quantity": row[2],
                "type": "out",
                "valuation_ids": [(6, 0, list(row[3]))],
            }
            stock_out += [values]

        if self.mode == "ref":
            line_model = "stock.daily.stock.report.ref"
        else:
            line_model = "stock.daily.stock.report.line"

        self.env[line_model].create(stock_init)
        self.env[line_model].create(stock_in)
        self.env[line_model].create(stock_out)

    def button_show(self):
        self.do_compute()
        if self.mode == "ref":
            action = self.env.ref(
                "l10n_ro_stock_report.action_daily_stock_report_ref"
            ).read()[0]
        else:
            action = self.env.ref(
                "l10n_ro_stock_report.action_daily_stock_report_line"
            ).read()[0]
        action["domain"] = [("report_id", "=", self.id)]
        action["context"] = {"active_id": self.id}
        action["target"] = "main"
        return action

    def button_print(self):
        self.do_compute()
        records = self
        report_name = "l10n_ro_stock_report.action_report_daily_stock_report"
        report = self.env.ref(report_name).report_action(records)

        report["close_on_report_download"] = True
        return report


class DailyStockReportRef(models.TransientModel):
    _name = "stock.daily.stock.report.ref"
    _description = "DailyStockReportRef"

    report_id = fields.Many2one("stock.daily.stock.report")
    picking_id = fields.Many2one("stock.picking")
    ref = fields.Char(string="Reference")
    quantity = fields.Float()
    amount = fields.Float()
    type = fields.Selection(
        [("balance", "Balance"), ("in", "Input"), ("out", "Output")]
    )
    valuation_ids = fields.Many2many("stock.valuation.layer")

    def action_valuation_at_date_details(self):
        self.ensure_one()

        action = {
            "name": _("Valuation"),
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "tree,form",
            "context": self.env.context,
            "res_model": "stock.valuation.layer",
            "domain": [("id", "in", self.valuation_ids.ids)],
        }

        return action


class DailyStockReportLine(models.TransientModel):
    _name = "stock.daily.stock.report.line"
    _description = "DailyStockReportLine"

    report_id = fields.Many2one("stock.daily.stock.report")
    product_id = fields.Many2one("product.product")
    quantity = fields.Float()
    amount = fields.Float()
    type = fields.Selection(
        [("balance", "Balance"), ("in", "Input"), ("out", "Output")]
    )
    valuation_ids = fields.Many2many("stock.valuation.layer")

    def action_valuation_at_date_details(self):
        self.ensure_one()

        action = {
            "name": _("Valuation"),
            "type": "ir.actions.act_window",
            "view_mode": "tree,form",
            "context": self.env.context,
            "res_model": "stock.valuation.layer",
            "domain": [("id", "in", self.valuation_ids.ids)],
        }

        return action
