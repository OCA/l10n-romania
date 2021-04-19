# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging

import pytz
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StorageSheet(models.TransientModel):
    _name = "stock.storage.sheet"
    _description = "StorageSheet"

    # Filters fields, used for data computation

    location_id = fields.Many2one(
        "stock.location",
        domain="[('usage','=','internal'),('company_id','=',company_id)]",
        required=True,
    )

    product_ids = fields.Many2many(
        "product.product",
        string="Only for products",
        domain=[("type", "=", "product")],
        help="will show report only for this products.\
         If nothing selected will show only products that have moves in period",
    )

    products_with_move = fields.Boolean(default=False)

    date_range_id = fields.Many2one("date.range", string="Date range")
    date_from = fields.Date("Start Date", required=True, default=fields.Date.today)
    date_to = fields.Date("End Date", required=True, default=fields.Date.today)
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )

    one_product = fields.Boolean("One product per page")
    line_product_ids = fields.Many2many(comodel_name="stock.storage.sheet.line")

    def _get_report_base_filename(self):
        self.ensure_one()
        return "Stock Sheet %s" % (self.location_id.name)

    @api.model
    def default_get(self, fields_list):
        res = super(StorageSheet, self).default_get(fields_list)

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

        lines = self.env["stock.storage.sheet.line"].search(
            [("report_id", "=", self.id)]
        )
        lines.unlink()

        datetime_from = fields.Datetime.to_datetime(self.date_from)
        datetime_from = fields.Datetime.context_timestamp(self, datetime_from)
        datetime_from = datetime_from.replace(hour=0)
        datetime_from = datetime_from.astimezone(pytz.utc)

        datetime_to = fields.Datetime.to_datetime(self.date_to)
        datetime_to = fields.Datetime.context_timestamp(self, datetime_to)
        datetime_to = datetime_to.replace(hour=23, minute=59, second=59)
        datetime_to = datetime_to.astimezone(pytz.utc)

        params = {
            "report": self.id,
            "location": self.location_id.id,
            "product": tuple(product_list),
            "all_products": all_products,
            "company": self.company_id.id,
            "date_from": fields.Date.to_string(self.date_from),
            "date_to": fields.Date.to_string(self.date_to),
            "datetime_from": fields.Datetime.to_string(datetime_from),
            "datetime_to": fields.Datetime.to_string(datetime_to),
            "tz": self._context.get("tz") or self.env.user.tz,
        }

        query_select_sold_init = """
            SELECT %(report)s as report_id, sm.product_id as product_id,
                COALESCE(sum(svl.value),0)  as amount_initial,
                COALESCE(sum(svl.quantity),0)  as quantity_initial,
                svl.account_id,
                %(date_from)s as date,
                %(reference)s as reference
            from stock_move as sm

            inner join  stock_valuation_layer as svl on svl.stock_move_id = sm.id
                    and ((valued_type !='internal_transfer' or valued_type is Null) or
                    (valued_type ='internal_transfer' and quantity<0 and sm.location_id=%(location)s) or
                    (valued_type ='internal_transfer' and quantity>0 and sm.location_dest_id=%(location)s) )

            where sm.state = 'done' AND
                sm.company_id = %(company)s AND
                ( %(all_products)s  or sm.product_id in %(product)s ) AND
                 sm.date <  %(datetime_from)s AND
                (sm.location_id = %(location)s OR sm.location_dest_id = %(location)s)
            GROUP BY sm.product_id, svl.account_id
        """

        params.update({"reference": "INITIALA"})
        self.env.cr.execute(query_select_sold_init, params=params)
        res = self.env.cr.dictfetchall()
        self.line_product_ids.create(res)

        query_select_sold_final = """
            SELECT %(report)s as report_id, sm.product_id as product_id,
                COALESCE(sum(svl.value),0)  as amount_final,
                COALESCE(sum(svl.quantity),0)  as quantity_final,
                svl.account_id,
                %(date_to)s as date,
                %(reference)s as reference
            from stock_move as sm
            inner join  stock_valuation_layer as svl on svl.stock_move_id = sm.id
                    and ((valued_type !='internal_transfer' or valued_type is Null) or
                    (valued_type ='internal_transfer' and quantity<0 and sm.location_id=%(location)s) or
                    (valued_type ='internal_transfer' and quantity>0 and sm.location_dest_id=%(location)s) )
            where sm.state = 'done' AND
                sm.company_id = %(company)s AND
                ( %(all_products)s  or sm.product_id in %(product)s ) AND
                sm.date <=  %(datetime_to)s AND
                (sm.location_id = %(location)s OR sm.location_dest_id = %(location)s)
            GROUP BY sm.product_id, svl.account_id
        """

        params.update({"reference": "FINALA"})
        self.env.cr.execute(query_select_sold_final, params=params)
        res = self.env.cr.dictfetchall()
        self.line_product_ids.create(res)

        query_in = """


        SELECT  %(report)s as report_id, sm.product_id as product_id,
                COALESCE(sum(svl_in.value),0)   as amount_in,
                COALESCE(sum(svl_in.quantity), 0)   as quantity_in,
                date_trunc('day',sm.date at time zone 'utc' at time zone %(tz)s) as date,
                 svl_in.account_id,
                sm.reference as reference,
                sp.partner_id
            from stock_move as sm

                inner join stock_valuation_layer as svl_in on svl_in.stock_move_id = sm.id and
                    (
                    ( ((svl_in.valued_type !='internal_transfer' and svl_in.valued_type not like '%%return' )
                       or svl_in.valued_type is Null)  and  sm.location_dest_id=%(location)s) or
                    ( svl_in.valued_type ='internal_transfer' and
                                      svl_in.quantity>0 and sm.location_dest_id=%(location)s) or
                    ( svl_in.valued_type  like '%%return' and sm.location_id=%(location)s)
                    )
                left join stock_picking as sp on sm.picking_id = sp.id
            where
                sm.state = 'done' AND
                sm.company_id = %(company)s AND
                ( %(all_products)s  or sm.product_id in %(product)s ) AND
                sm.date >= %(datetime_from)s  AND  sm.date <= %(datetime_to)s  AND
                (sm.location_id = %(location)s OR sm.location_dest_id = %(location)s)
            GROUP BY sm.product_id, date_trunc('day',sm.date at time zone 'utc' at time zone %(tz)s),
             sm.reference, sp.partner_id, account_id
            """

        self.env.cr.execute(query_in, params=params)
        res = self.env.cr.dictfetchall()
        self.line_product_ids.create(res)

        query_out = """

        SELECT  %(report)s as report_id, sm.product_id as product_id,

                -1*COALESCE(sum(svl_out.value),0)   as amount_out,
                -1*COALESCE(sum(svl_out.quantity),0)   as quantity_out,
                svl_out.account_id,
                date_trunc('day',sm.date) as date,
                sm.reference as reference,
                sp.partner_id
            from stock_move as sm

                inner join stock_valuation_layer as svl_out on svl_out.stock_move_id = sm.id and
                    (
                    ( ((svl_out.valued_type !='internal_transfer' and svl_out.valued_type not like '%%return' )
                       or svl_out.valued_type is Null)   and  sm.location_id=%(location)s) or
                    ( svl_out.valued_type ='internal_transfer' and svl_out.quantity<0 and sm.location_id=%(location)s) or
                    ( svl_out.valued_type  like '%%return' and sm.location_dest_id=%(location)s)
                    )


                left join stock_picking as sp on sm.picking_id = sp.id
            where
                sm.state = 'done' AND
                sm.company_id = %(company)s AND
                ( %(all_products)s  or sm.product_id in %(product)s ) AND
                sm.date >= %(datetime_from)s  AND  sm.date <= %(datetime_to)s  AND
                (sm.location_id = %(location)s OR sm.location_dest_id = %(location)s)
            GROUP BY sm.product_id, date_trunc('day',sm.date),  sm.reference, sp.partner_id, account_id
            """

        self.env.cr.execute(query_out, params=params)
        res = self.env.cr.dictfetchall()
        self.line_product_ids.create(res)

    def get_found_products(self):
        found_products = self.product_ids
        product_list = self.get_products_with_move()
        found_products |= self.env["product.product"].browse(product_list)

        return found_products

    def button_show_sheet(self):
        self.do_compute_product()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "l10n_ro_stock_report.action_sheet_stock_report_line"
        )

        action["display_name"] = "{} {} ({}-{})".format(
            action["name"],
            self.location_id.name,
            self.date_from,
            self.date_to,
        )
        action["domain"] = [("report_id", "=", self.id)]
        action["context"] = {
            "active_id": self.id,
            "general_buttons": self.env[
                "stock.storage.sheet.line"
            ].get_general_buttons(),
        }
        action["target"] = "main"
        return action

    def button_show_sheet_pdf(self):
        self.do_compute_product()
        return self.print_pdf()

    def print_pdf(self):
        if self.one_product:
            action_report_storage_sheet = self.env.ref(
                "l10n_ro_stock_report.action_report_storage_sheet"
            )
        else:
            action_report_storage_sheet = self.env.ref(
                "l10n_ro_stock_report.action_report_storage_sheet_all"
            )
        return action_report_storage_sheet.report_action(self, config=False)


class StorageSheetLine(models.TransientModel):
    _name = "stock.storage.sheet.line"
    _description = "StorageSheetLine"
    _order = "report_id, product_id, date"
    _rec_name = "product_id"

    report_id = fields.Many2one("stock.storage.sheet")
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
    categ_id = fields.Many2one(
        "product.category", related="product_id.categ_id", index=True, store=True
    )
    account_id = fields.Many2one("account.account")

    def get_general_buttons(self):
        return [
            {
                "action": "print_pdf",
                "name": _("Print Preview"),
                "model": "stock.storage.sheet",
            }
        ]
