# ©  2008-2018 Fekete Mihai <mihai.fekete@forbiom.eu>
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models


class StorageSheetReport(models.TransientModel):
    _name = "stock.storage.sheet.report"
    _description = "Storage sheet"

    # Filters fields, used for data computation

    location_id = fields.Many2one(
        "stock.location",
        domain="[('usage','=','internal'),('company_id','=',company_id)]",
        required=True,
    )

    date_range_id = fields.Many2one("date.range", string="Date range")
    date_from = fields.Date("Start Date", required=True, default=fields.Date.today)
    date_to = fields.Date("End Date", required=True, default=fields.Date.today)

    product_id = fields.Many2one(
        "product.product",
        string="Product",
        required=True,
        domain=[("type", "=", "product")],
    )

    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.user.company_id
    )

    line_product_ids = fields.One2many("stock.storage.sheet.report.line", "report_id")

    @api.model
    def default_get(self, fields_list):
        defaults = super(StorageSheetReport, self).default_get(fields_list)

        active_model = self.env.context.get("active_model", False)
        active_ids = self.env.context.get("active_ids", False)
        active_id = self.env.context.get("active_id", False)
        if active_model == "product.template":
            product = self.env["product.product"].search(
                [("product_tmpl_id", "in", active_ids)], limit=1
            )
            defaults["product_id"] = product.id
        elif active_model == "product.product":
            defaults["product_id"] = active_id

        today = fields.Date.context_today(self)

        from_date = today + relativedelta(day=1, months=0, days=0)
        to_date = today + relativedelta(day=1, months=1, days=-1)

        defaults["date_from"] = from_date
        defaults["date_to"] = to_date
        return defaults

    @api.onchange("date_range_id")
    def onchange_date_range_id(self):
        """Handle date range change."""
        if self.date_range_id:
            self.date_from = self.date_range_id.date_start
            self.date_to = self.date_range_id.date_end

    def do_compute(self):
        self.env["stock.move"].check_access_rights("read")

        lines = self.env["stock.storage.sheet.report.line"].search(
            [("report_id", "=", self.id)]
        )
        lines.unlink()

        to_date = self.date_from

        query = """
    SELECT svl.product_id,  sum(value), sum(svl.quantity), array_agg(svl.id)

        from stock_move as sm
        left join  stock_valuation_layer as svl on svl.stock_move_id = sm.id
        where sm.state = 'done' AND
                sm.product_id = %(product)s AND
              sm.company_id = %(company)s AND
              sm.date <  %(date)s AND
            ( sm.location_id = %(location)s OR
             sm.location_dest_id = %(location)s)
            GROUP BY svl.product_id
        """

        params = {
            "location": self.location_id.id,
            "product": self.product_id.id,
            "company": self.company_id.id,
            "date": to_date,
        }

        self.env.cr.execute(query, params=params)

        res = self.env.cr.fetchall()
        for row in res:
            values = {
                "report_id": self.id,
                "product_id": row[0],
                "amount": row[1],
                "quantity": row[2],
                "type": "balance",
                "valuation_ids": [(6, 0, list(row[3]))],
            }
            self.env["stock.storage.sheet.report.line"].create(values)
        if not res:
            values = {
                "report_id": self.id,
                "product_id": self.product_id.id,
                "date": self.date_from,
                "type": "balance",
            }
            self.env["stock.storage.sheet.report.line"].create(values)

        query = """
    SELECT svl.product_id,  sum(value), sum(svl.quantity),
    date_trunc('day',date), array_agg(svl.id), sm.name

        from stock_move as sm
        left join  stock_valuation_layer as svl on svl.stock_move_id = sm.id
        where
              svl.value >=0 and
              sm.state = 'done' AND
              sm.product_id = %(product)s AND
              sm.company_id = %(company)s AND
              date_trunc('day',date) >= %(date_from)s AND
              date_trunc('day',date) <= %(date_to)s AND
            ( sm.location_id = %(location)s OR
             sm.location_dest_id = %(location)s)
            GROUP BY svl.product_id,  date_trunc('day',date), sm.name
        """

        params = {
            "location": self.location_id.id,
            "product": self.product_id.id,
            "company": self.company_id.id,
            "date_from": self.date_from,
            "date_to": self.date_to,
        }

        self.env.cr.execute(query, params=params)

        res = self.env.cr.fetchall()
        for row in res:
            values = {
                "report_id": self.id,
                "product_id": row[0],
                "amount": row[1],
                "quantity": row[2],
                "date": row[3],
                "type": "in",
                "valuation_ids": [(6, 0, list(row[4]))],
                "ref": row[5],
            }
            self.env["stock.storage.sheet.report.line"].create(values)
        if not res:
            values = {
                "report_id": self.id,
                "product_id": self.product_id.id,
                "date": self.date_from,
                "type": "in",
            }
            self.env["stock.storage.sheet.report.line"].create(values)

        query = """
    SELECT svl.product_id,  sum(value), sum(svl.quantity),
    date_trunc('day',date), array_agg(svl.id), sm.name

        from stock_move as sm
        left join  stock_valuation_layer as svl on svl.stock_move_id = sm.id
        where
              svl.value < 0 and
              sm.state = 'done' AND
              sm.product_id = %(product)s AND
              sm.company_id = %(company)s AND
             date_trunc('day',date) >= %(date_from)s AND
              date_trunc('day',date)  <= %(date_to)s AND
            ( sm.location_id = %(location)s OR
            sm.location_dest_id = %(location)s)
            GROUP BY svl.product_id,  date_trunc('day',date), sm.name
        """
        params = {
            "location": self.location_id.id,
            "product": self.product_id.id,
            "company": self.company_id.id,
            "date_from": self.date_from,
            "date_to": self.date_to,
        }

        self.env.cr.execute(query, params=params)

        res = self.env.cr.fetchall()
        for row in res:
            values = {
                "report_id": self.id,
                "product_id": row[0],
                "amount": row[1],
                "quantity": row[2],
                "date": row[3],
                "type": "out",
                "valuation_ids": [(6, 0, list(row[4]))],
                "ref": row[5],
            }
            self.env["stock.storage.sheet.report.line"].create(values)
        if not res:
            values = {
                "report_id": self.id,
                "product_id": self.product_id.id,
                "date": self.date_to,
                "type": "out",
            }
            self.env["stock.storage.sheet.report.line"].create(values)

    def button_show(self):
        self.do_compute()
        action = self.env.ref(
            "l10n_ro_stock_report.action_storage_sheet_report_line"
        ).read()[0]
        action["domain"] = [("report_id", "=", self.id)]
        action["context"] = {"active_id": self.id}
        action["target"] = "main"
        return action

    def button_print(self):
        self.do_compute()
        records = self
        report_name = "l10n_ro_stock_report.action_report_storage_sheet_report"
        report = self.env.ref(report_name).report_action(records)
        report["close_on_report_download"] = True
        return report


class DailyStockReportLine(models.TransientModel):
    _name = "stock.storage.sheet.report.line"
    _description = "stock.storage.sheet.report.line"

    report_id = fields.Many2one("stock.storage.sheet.report")
    product_id = fields.Many2one("product.product")
    quantity = fields.Float()
    amount = fields.Float()
    ref = fields.Char(string="Reference")
    date = fields.Date()
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
