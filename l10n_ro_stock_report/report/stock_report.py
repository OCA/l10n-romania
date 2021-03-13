# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

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

    product_ids = fields.Many2many(
        "product.product",
        "stock_daily_select_products",
        "product_id",
        "report_id",
        string="Only for products",
        domain=[("type", "=", "product")],
        help="will show report only for this products.\
         If nothing selected will show only products that have moves in period",
    )

    products_with_move = fields.Boolean(default=True)

    # found_product_ids = fields.Many2many(
    #     "product.product",
    #     "stock_daily_found_products",
    #     "product_id",
    #     "report_id",
    #     help="this are products that have moves in period, used not to show products that do not have moves ",
    # )

    date_range_id = fields.Many2one("date.range", string="Date range")
    date_from = fields.Date("Start Date", required=True, default=fields.Date.today)
    date_to = fields.Date("End Date", required=True, default=fields.Date.today)
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )
    # mode = fields.Selection(
    #     [("product", "Product")], default="product", string="Detail mode", required=1
    # )

    one_product = fields.Boolean("One product per page")
    line_product_ids = fields.Many2many(comodel_name="stock.daily.stock.report.line")

    def _get_report_base_filename(self):
        self.ensure_one()
        return "Stock Sheet %s" % (self.location_id.name)

    @api.model
    def default_get(self, fields_list):
        res = super(DailyStockReport, self).default_get(fields_list)

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

    def get_products_with_move(self):
        query = """
                    SELECT product_id
                    FROM stock_move as sm
                    WHERE sm.company_id = %(company)s AND
                          (sm.location_id = %(location)s OR sm.location_dest_id = %(location)s) AND
                          date_trunc('day',sm.date) >= %(date_from)s  AND
                          date_trunc('day',sm.date) <= %(date_to)s
                    GROUP BY  product_id
                    """
        params = {
            "date_from": fields.Date.to_string(self.date_from),
            "date_to": fields.Date.to_string(self.date_to),
            "location": self.location_id.id,
            "company": self.company_id.id,
        }
        self.env.cr.execute(query, params=params)
        product_list = [r["product_id"] for r in self.env.cr.dictfetchall()]
        return product_list

    def do_compute_product(self):
        if self.product_ids:
            product_list = self.product_ids.ids
            all_products = False
        else:
            if self.products_with_move:
                product_list = self.get_products_with_move()
                all_products = False
                if not product_list:
                    raise UserError(
                        _("There are no stock movements in the selected period")
                    )
            else:
                product_list = [-1]  # dummy list
                all_products = True

        self.env["account.move.line"].check_access_rights("read")

        lines = self.env["stock.daily.stock.report.line"].search(
            [("report_id", "=", self.id)]
        )
        lines.unlink()
        stock_init = []

        query = """
    SELECT product_id,amount_initial,quantity_initial,
            amount_in,quantity_in,amount_out,
            quantity_out,amount_final,quantity_final,
            date,reference,partner_id
    FROM
        (SELECT sm.product_id as product_id,
            COALESCE(sum(svl.value),
                    sum(svl2.value),
                    sum(svl3.value), 0) as amount_initial,
            COALESCE(sum(svl.quantity),
                    sum(svl2.quantity),
                    sum(svl3.quantity),
                    0) as quantity_initial,
            0 as amount_in,
            0 as quantity_in,
            0 as amount_out,
            0 as quantity_out,
            COALESCE(sum(svl.value),
                    sum(svl2.value),
                    sum(svl3.value), 0) as amount_final,
            COALESCE(sum(svl.quantity),
                    sum(svl2.quantity),
                    sum(svl3.quantity), 0) as quantity_final,
            date_trunc('day',sm.date) as date,
            sm.reference as reference,
            sm.partner_id
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
        where sm.state = 'done' AND
            sm.company_id = %(company)s AND
            ( %(all_products)s  or sm.product_id in %(product)s ) AND
            date_trunc('day',sm.date) <  %(date_from)s AND
            (sm.location_id = %(location)s OR sm.location_dest_id = %(location)s)
        GROUP BY sm.product_id, date_trunc('day',sm.date), sm.reference, sm.partner_id
        order by sm.product_id, date_trunc('day',sm.date)) initial
    union
        (SELECT sm.product_id as product_id, 0 as amount_initial, 0 as quantity_initial,
            COALESCE(sum(svl.value),
                    sum(svl3.value), 0) as amount_in,
            COALESCE(sum(svl.quantity),
                    sum(svl3.quantity) ,0) as quantity_in,
            COALESCE(sum(svl1.value),
                    sum(svl2.value), 0) as amount_out,
            COALESCE(sum(svl1.quantity),
                    sum(svl2.quantity), 0) as quantity_out,
            COALESCE(sum(svl.value),
                    sum(svl1.value),
                    sum(svl2.value),
                    sum(svl3.value), 0) as amount_final,
            COALESCE(sum(svl.quantity),
                    sum(svl1.quantity),
                    sum(svl2.quantity),
                    sum(svl3.quantity), 0) as quantity_final,
            date_trunc('day',sm.date) as date,
            sm.reference as reference,
            sp.partner_id
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
            left join stock_picking as sp on sm.picking_id = sp.id
        where
            sm.state = 'done' AND
            sm.company_id = %(company)s AND
            ( %(all_products)s  or sm.product_id in %(product)s ) AND
            date_trunc('day',sm.date) >= %(date_from)s  AND
            date_trunc('day',sm.date) <= %(date_to)s  AND
            (sm.location_id = %(location)s OR sm.location_dest_id = %(location)s)
        GROUP BY sm.product_id, date_trunc('day',sm.date),  sm.reference, sp.partner_id
        order by sm.product_id, date_trunc('day',sm.date))
    ORDER BY product_id, date
                """

        params = {
            "location": self.location_id.id,
            "product": tuple(product_list),
            "all_products": all_products,
            "company": self.company_id.id,
            "date_from": fields.Date.to_string(self.date_from),
            "date_to": fields.Date.to_string(self.date_to),
        }

        self.env.cr.execute(query, params=params)
        res = self.env.cr.fetchall()

        for row in res:
            values = {
                "product_id": row[0],
                "report_id": self.id,
                "amount_initial": row[1],
                "quantity_initial": row[2],
                "amount_in": row[3],
                "quantity_in": row[4],
                "amount_out": row[5],
                "quantity_out": row[6],
                "amount_final": row[7],
                "quantity_final": row[8],
                "date": row[9],
                "reference": row[10],
                "partner_id": row[11],
            }
            stock_init += [values]
        # The records from stock_init are converted for in stock sheet. That are, a record  with the stock
        # and the initial value, and other with the stock and the final value.
        # The rest of the records are those with stock movements from the selected period.

        products = {prod["product_id"] for prod in stock_init}
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
            stoc_init_total[line["product_id"]] += line["quantity_initial"]
            val_init_total[line["product_id"]] += line["amount_initial"]
            stoc_final_total[line["product_id"]] += line["quantity_final"]
            val_final_total[line["product_id"]] += line["amount_final"]

        sold_stock_init = []
        for product in products:
            sold_stock_init.append(
                {
                    "product_id": product,
                    "report_id": self.id,
                    "date": self.date_from,
                    "quantity_initial": stoc_init_total[product],
                    "amount_initial": val_init_total[product],
                    "quantity_final": None,
                    "amount_final": None,
                    "reference": "INITIALA",
                }
            )
            for line in stock_init:
                if line["product_id"] == product:
                    if line["date"].date() >= self.date_from:
                        line["amount_out"] = -line["amount_out"]
                        line["quantity_out"] = -line["quantity_out"]
                        line["amount_final"] = 0
                        line["quantity_final"] = 0
                        sold_stock_init.append(line)
            sold_stock_init.append(
                {
                    "product_id": product,
                    "report_id": self.id,
                    "date": self.date_to,
                    "quantity_initial": None,
                    "amount_initial": None,
                    "quantity_final": stoc_final_total[product],
                    "amount_final": val_final_total[product],
                    "reference": "FINALA",
                }
            )

        line_model = "stock.daily.stock.report.line"

        lines_report = self.env[line_model].create(sold_stock_init)

        self.line_product_ids = lines_report.ids

        if self.location_id.property_stock_valuation_account_id:
            self.line_product_ids.write(
                {"account_id": self.location_id.property_stock_valuation_account_id.id}
            )
        else:
            for line in self.line_product_ids:
                line.write(
                    {
                        "account_id": line.product_id.categ_id.property_stock_valuation_account_id.id
                    }
                )

    def get_found_products(self):
        found_products = self.product_ids
        product_list = self.get_products_with_move()
        found_products |= self.env["product.product"].browse(product_list)

        return found_products

    def button_show_sheet(self):
        self.do_compute_product()
        action = self.env.ref(
            "l10n_ro_stock_report.action_sheet_stock_report_line"
        ).read()[0]
        action["name"] = "{} {} ({}-{})".format(
            action["name"],
            self.location_id.name,
            self.date_from,
            self.date_to,
        )
        action["domain"] = [("report_id", "=", self.id)]
        action["context"] = {
            "active_id": self.id,
            "general_buttons": self.env[
                "stock.daily.stock.report.line"
            ].get_general_buttons(),
        }
        action["target"] = "main"
        return action

    def button_show_sheet_pdf(self):
        self.do_compute_product()
        return self.print_pdf()

    def print_pdf(self):
        if self.one_product:
            action_report_stock_sheet = self.env.ref(
                "l10n_ro_stock_report.action_report_stock_sheet"
            )
        else:
            action_report_stock_sheet = self.env.ref(
                "l10n_ro_stock_report.action_report_stock_sheet_all"
            )
        return action_report_stock_sheet.report_action(self, config=False)


class DailyStockReportLine(models.TransientModel):
    _name = "stock.daily.stock.report.line"
    _description = "DailyStockReportLine"
    _order = "report_id, product_id, date"
    _rec_name = "product_id"

    report_id = fields.Many2one("stock.daily.stock.report")
    product_id = fields.Many2one("product.product", string="Product")
    amount_initial = fields.Monetary(
        currency_field="currency_id", string="Initial Amount"
    )
    quantity_initial = fields.Float(
        digits="Product Unit of Measure", string="Initial Quantity"
    )
    amount_in = fields.Monetary(currency_field="currency_id", string="Input Amount")
    quantity_in = fields.Float(
        digits="Product Unit of Measure", string="Input Quantity"
    )
    amount_out = fields.Monetary(currency_field="currency_id", string="Output Amount")
    quantity_out = fields.Float(
        digits="Product Unit of Measure", string="Output Quantity"
    )
    amount_final = fields.Monetary(currency_field="currency_id", string="Final Amount")
    quantity_final = fields.Float(
        digits="Product Unit of Measure", string="Final Quantity"
    )
    date = fields.Date(string="Date")
    reference = fields.Char()
    partner_id = fields.Many2one("res.partner")
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
    categ_id = fields.Many2one("product.category", related="product_id.categ_id")
    account_id = fields.Many2one("account.account")

    def get_general_buttons(self):
        return [
            {
                "action": "print_pdf",
                "name": "Print Preview",
                "model": "stock.daily.stock.report",
            }
        ]
