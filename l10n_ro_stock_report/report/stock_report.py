# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging

import pytz
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_ro_stock_account.models.stock_valuation_layer import VALUED_TYPE

_logger = logging.getLogger(__name__)


class StorageSheet(models.TransientModel):
    _name = "l10n.ro.stock.storage.sheet"
    _description = "StorageSheet"

    # Filters fields, used for data computation

    location_id = fields.Many2one(
        "stock.location",
        domain="[('usage','=','internal')]",
    )

    product_ids = fields.Many2many(
        "product.product",
        string="Only for products",
        domain=[("type", "=", "product")],
        help="will show report only for this products.\
         If nothing selected will show only products that have moves in period",
    )

    products_with_move = fields.Boolean(default=False)

    date_from = fields.Date("Start Date", required=True, default=fields.Date.today)
    date_to = fields.Date("End Date", required=True, default=fields.Date.today)
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )

    one_product = fields.Boolean("One product per page")
    line_product_ids = fields.One2many(
        comodel_name="l10n.ro.stock.storage.sheet.line", inverse_name="report_id"
    )
    sublocation = fields.Boolean("Include Sublocations", default=True)
    detailed_locations = fields.Boolean("Detailed by locations", default=False)
    show_locations = fields.Boolean("Show location", default=False)
    location_ids = fields.Many2many(
        "stock.location", string="Only for locations", compute="_compute_location_ids"
    )

    @api.depends("sublocation", "location_id", "show_locations")
    def _compute_location_ids(self):
        if not self.location_id:
            self.location_ids = self.env["stock.location"].search(
                [("usage", "=", "internal")]
            )
        else:
            if self.sublocation:
                children_location = (
                    self.env["stock.location"]
                    .with_context(active_test=False)
                    .search([("id", "child_of", self.location_id.ids)])
                )
                self.location_ids = self.location_id + children_location
            else:
                self.location_ids = self.location_id

    def _get_report_base_filename(self):
        self.ensure_one()
        return "Stock Sheet %s" % (self.location_id.name or "")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        today = fields.Date.context_today(self)
        today = fields.Date.from_string(today)

        from_date = today + relativedelta(day=1, months=0, days=0)
        to_date = today + relativedelta(day=1, months=1, days=-1)

        res["date_from"] = fields.Date.to_string(from_date)
        res["date_to"] = fields.Date.to_string(to_date)
        return res

    def get_products_with_move_sql(self, product_list=False):
        locations = self.location_ids

        if product_list:
            query = """
                SELECT product_id
                FROM stock_move as sm
                WHERE
                        sm.product_id in %(product_list)s and
                        sm.state = 'done' AND
                        sm.company_id = %(company)s AND
                      (sm.location_id in %(locations)s OR
                      sm.location_dest_id in %(locations)s) AND
                      date_trunc('day',sm.date) >= %(date_from)s  AND
                      date_trunc('day',sm.date) <= %(date_to)s
                GROUP BY  product_id
                        """
        else:
            query = """
                SELECT product_id
                FROM stock_move as sm
                WHERE
                        sm.state = 'done' AND
                        sm.company_id = %(company)s AND
                      (sm.location_id in %(locations)s OR
                      sm.location_dest_id in %(locations)s) AND
                      date_trunc('day',sm.date) >= %(date_from)s  AND
                      date_trunc('day',sm.date) <= %(date_to)s
                GROUP BY  product_id
                        """
        params = {
            "date_from": fields.Date.to_string(self.date_from),
            "date_to": fields.Date.to_string(self.date_to),
            "locations": tuple(locations.ids),
            "product_list": tuple(product_list or []),
            "company": self.company_id.id,
        }
        self.env.cr.execute(query, params=params)
        product_list = [r["product_id"] for r in self.env.cr.dictfetchall()]
        return product_list

    def get_products_with_move(self, product_list=False):
        if not product_list:
            product_list = []
        if product_list:
            products_with_moves = (
                self.env["stock.move"]
                .with_context(active_test=False)
                .search(
                    [
                        ("state", "=", "done"),
                        ("date", "<=", self.date_to),
                        ("product_id", "in", product_list),
                        "|",
                        ("company_id", "=", self.company_id.id),
                        ("company_id", "=", False),
                        "|",
                        ("location_id", "in", self.location_ids.ids),
                        ("location_dest_id", "in", self.location_ids.ids),
                    ]
                )
                .mapped("product_id")
                .filtered(lambda p: p.type == "product")
            )
            product_list = products_with_moves.ids
        return product_list

    def do_compute_product(self):
        if self.product_ids:
            product_list = self.product_ids.ids
            all_products = False
        else:
            if self.products_with_move:
                product_list = self.get_products_with_move_sql()
                all_products = False
                if not product_list:
                    raise UserError(
                        _("There are no stock movements in the selected period")
                    )
            else:
                product_list = [-1]  # dummy list
                all_products = True

        self.env["account.move.line"].check_access_rights("read")

        lines = self.env["l10n.ro.stock.storage.sheet.line"].search(
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

        if self.detailed_locations:
            all_locations = self.with_context(active_test=False).location_ids
        else:
            all_locations = self.location_id or self.location_ids[0]
            locations = self.location_ids

        for location in all_locations:
            if self.detailed_locations:
                locations = location
            params = {
                "report": self.id,
                "location": location.id,
                "locations": tuple(locations.ids),
                "product": tuple(product_list),
                "all_products": all_products,
                "company": self.company_id.id,
                "date_from": fields.Date.to_string(self.date_from),
                "date_to": fields.Date.to_string(self.date_to),
                "datetime_from": fields.Datetime.to_string(datetime_from),
                "datetime_to": fields.Datetime.to_string(datetime_to),
                "tz": self._context.get("tz") or self.env.user.tz or "UTC",
            }
            _logger.info("start query_select_sold_init %s", location.name)
            # defalcare sold initial pe preturi
            query_select_sold_init = self._get_sql_select_sold_init()

            params.update({"reference": "INITIAL"})
            self.env.cr.execute(query_select_sold_init, params=params)
            # res = self.env.cr.dictfetchall()
            # self.env["l10n.ro.stock.storage.sheet.line"].create(res)
            _logger.info("start query_select_sold_final %s", location.name)
            query_select_sold_final = self._get_sql_select_sold_final()

            params.update({"reference": "FINAL"})
            self.env.cr.execute(query_select_sold_final, params=params)
            # res = self.env.cr.dictfetchall()
            # self.env["l10n.ro.stock.storage.sheet.line"].create(res)
            _logger.info("start query_in %s", location.name)
            query_in = self._get_sql_select_in()
            self.env.cr.execute(query_in, params=params)
            # res = self.env.cr.dictfetchall()
            # self.env["l10n.ro.stock.storage.sheet.line"].create(res)
            _logger.info("start query_out %s", location.name)
            query_out = self._get_sql_select_out()
            self.env.cr.execute(query_out, params=params)
            # res = self.env.cr.dictfetchall()
            # self.line_product_ids.create(res)
        _logger.info("end select ")

    def _get_lot_fields(self):
        if "lot_id" in self.env["stock.valuation.layer"]:
            field = ", serial_number"
            select = ",sml.lot_id as serial_number"
            join = (
                "left join stock_move_line sml on sml.id=svl.l10n_ro_stock_move_line_id"
            )
            group = "ml.lot_id"
        else:
            field = ""
            select = ""
            join = ""
            group = ""
        return field, select, join, group

    def _get_sql_select_sold_init(self):
        field, select, join, group = self._get_lot_fields()

        sql = f"""
         insert into l10n_ro_stock_storage_sheet_line
          (report_id, product_id, amount_initial, quantity_initial,
           account_id, date_time, date, reference, document,
           location_id, categ_id {field})

        select * from(
            SELECT %(report)s as report_id, prod.id as product_id,
                COALESCE(sum(svl.value), 0)  as amount_initial,
                COALESCE(sum(svl.quantity), 0)  as quantity_initial,
                COALESCE(svl.l10n_ro_account_id, Null) as account_id,
                %(datetime_from)s::timestamp without time zone  as date_time,
                %(date_from)s::date as date,
                %(reference)s as reference,
                %(reference)s as document,
                %(location)s as location_id,
                pt.categ_id as categ_id
                {select}
            from product_product as prod
            join stock_move as sm ON sm.product_id = prod.id AND sm.state = 'done' AND
                sm.company_id = %(company)s AND
                 sm.date <  %(datetime_from)s AND
                (sm.location_id in %(locations)s OR
                sm.location_dest_id in %(locations)s)
            left join product_template pt on pt.id = prod.product_tmpl_id
            left join stock_valuation_layer as svl on svl.stock_move_id = sm.id and
                    ((l10n_ro_valued_type !='internal_transfer' or
                        l10n_ro_valued_type is Null
                     ) or
                     (l10n_ro_valued_type ='internal_transfer' and svl.quantity<0 and
                      sm.location_id in %(locations)s) or
                     (l10n_ro_valued_type ='internal_transfer' and svl.quantity>0 and
                      sm.location_dest_id in %(locations)s))
            {join}
            where
                ( %(all_products)s  or sm.product_id in %(product)s )
            GROUP BY prod.id, svl.l10n_ro_account_id, pt.categ_id {group})
        a --where a.amount_initial!=0 and a.quantity_initial!=0
            """
        return sql

    def _get_sql_select_sold_final(self):
        field, select, join, group = self._get_lot_fields()

        sql = f"""
        insert into l10n_ro_stock_storage_sheet_line
          (report_id, product_id, amount_final, quantity_final,
           account_id, date_time, date, reference, document,
           location_id, categ_id {field})
        select * from(
            SELECT %(report)s as report_id, sm.product_id as product_id,
                COALESCE(sum(svl.value),0)  as amount_final,
                COALESCE(sum(svl.quantity),0)  as quantity_final,

                COALESCE(svl.l10n_ro_account_id, Null) as account_id,
                %(datetime_to)s::timestamp without time zone as date_time,
                %(date_to)s::date as date,
                %(reference)s as reference,
                %(reference)s as document,
                %(location)s as location_id,
                pt.categ_id as categ_id
                {select}
            from stock_move as sm
            left join product_product prod on prod.id = sm.product_id
            left join product_template pt on pt.id = prod.product_tmpl_id
            inner join  stock_valuation_layer as svl on svl.stock_move_id = sm.id and
                    ((l10n_ro_valued_type !='internal_transfer' or
                      l10n_ro_valued_type is Null
                     ) or
                     (l10n_ro_valued_type ='internal_transfer' and svl.quantity<0 and
                      sm.location_id in %(locations)s) or
                     (l10n_ro_valued_type ='internal_transfer' and svl.quantity>0 and
                      sm.location_dest_id in %(locations)s))
            {join}
            where
                sm.state = 'done' AND
                sm.company_id = %(company)s AND
                ( %(all_products)s  or sm.product_id in %(product)s ) AND
                sm.date <=  %(datetime_to)s AND
                (sm.location_id in %(locations)s OR
                 sm.location_dest_id in %(locations)s)
            GROUP BY sm.product_id, svl.l10n_ro_account_id, pt.categ_id {group})
        a
            """
        return sql

    def _get_sql_select_in(self):
        field, select, join, group = self._get_lot_fields()

        sql = f"""
        insert into l10n_ro_stock_storage_sheet_line
          (report_id, product_id, amount_in, quantity_in, unit_price_in,
           account_id, invoice_id, date_time, date, reference,  location_id,
           partner_id, document, valued_type, categ_id {field} )
        select * from(


        SELECT  %(report)s as report_id, sm.product_id as product_id,
            COALESCE(sum(svl_in.value),0)   as amount_in,
            COALESCE(ROUND(sum(svl_in.quantity), 5), 0)   as quantity_in,
            CASE
                WHEN ROUND(COALESCE(sum(svl_in.quantity), 0), 5) != 0
                    THEN COALESCE(sum(svl_in.value),0) / sum(svl_in.quantity)
                ELSE 0
            END as unit_price_in,
             svl_in.l10n_ro_account_id as account_id,
             svl_in.l10n_ro_invoice_id as invoice_id,
            sm.date as date_time,
            date_trunc('day', sm.date at time zone 'utc' at time zone %(tz)s) as date,
            sm.reference as reference,
            %(location)s as location_id,
            sp.partner_id,
            COALESCE(am.name, sm.reference) as document,
            COALESCE(svl_in.l10n_ro_valued_type, 'indefinite') as valued_type,
            pt.categ_id as categ_id
                {select}
            from stock_move as sm
                inner join stock_valuation_layer as svl_in
                    on svl_in.stock_move_id = sm.id and
                    (
                     (sm.location_dest_id in %(locations)s and svl_in.quantity>=0 and
                      l10n_ro_valued_type not like '%%_return')
                    or
                     (sm.location_id in %(locations)s and (svl_in.quantity<=0 and
                     l10n_ro_valued_type='reception_return'))
                    )
                left join product_product prod on prod.id = sm.product_id
                left join product_template pt on pt.id = prod.product_tmpl_id
                left join stock_picking as sp on sm.picking_id = sp.id
                left join account_move am on svl_in.l10n_ro_invoice_id = am.id
            {join}
            where
                sm.state = 'done' AND
                sm.company_id = %(company)s AND
                ( %(all_products)s  or sm.product_id in %(product)s ) AND
                sm.date >= %(datetime_from)s  AND  sm.date <= %(datetime_to)s  AND
                (sm.location_dest_id in %(locations)s or
                 sm.location_id in %(locations)s)
            GROUP BY sm.product_id, sm.date,
             sm.reference, sp.partner_id, l10n_ro_account_id,
             svl_in.l10n_ro_invoice_id, am.name, svl_in.l10n_ro_valued_type,
             pt.categ_id {group})
        a --where a.amount_in!=0 and a.quantity_in!=0
                """
        return sql

    def _get_sql_select_out(self):
        field, select, join, group = self._get_lot_fields()

        sql = f"""
        insert into l10n_ro_stock_storage_sheet_line
          (report_id, product_id, amount_out, quantity_out, unit_price_out,
           account_id, invoice_id, date_time, date, reference,  location_id,
           partner_id, document, valued_type, categ_id {field})

        select * from(

        SELECT  %(report)s as report_id, sm.product_id as product_id,
            -1*COALESCE(sum(svl_out.value),0)   as amount_out,
            -1*COALESCE(ROUND(sum(svl_out.quantity), 5),0) as quantity_out,
            CASE
                WHEN ROUND(COALESCE(sum(svl_out.quantity), 0), 5) != 0
                    THEN COALESCE(sum(svl_out.value),0) / sum(svl_out.quantity)
                ELSE 0
            END as unit_price_out,
            svl_out.l10n_ro_account_id as account_id,
            svl_out.l10n_ro_invoice_id as invoice_id,
            sm.date as date_time,
            date_trunc('day', sm.date at time zone 'utc' at time zone %(tz)s) as date,
            sm.reference as reference,
            %(location)s as location_id,
            sp.partner_id,
            COALESCE(am.name, sm.reference) as document,
            COALESCE(svl_out.l10n_ro_valued_type, 'indefinite') as valued_type,
            pt.categ_id as categ_id
            {select}
            from stock_move as sm

                inner join stock_valuation_layer as svl_out
                on svl_out.stock_move_id = sm.id and
                 (
                  (sm.location_id in %(locations)s and svl_out.quantity<=0 and
                    l10n_ro_valued_type != 'reception_return')
                 or
                  (sm.location_dest_id in  %(locations)s and (svl_out.quantity>=0 and
                   l10n_ro_valued_type like '%%_return'))
                 )
                left join product_product prod on prod.id = sm.product_id
                left join product_template pt on pt.id = prod.product_tmpl_id
                left join stock_picking as sp on sm.picking_id = sp.id
                left join account_move am on svl_out.l10n_ro_invoice_id = am.id
                {join}
            where
                sm.state = 'done' AND
                sm.company_id = %(company)s AND
                ( %(all_products)s  or sm.product_id in %(product)s ) AND
                sm.date >= %(datetime_from)s  AND  sm.date <= %(datetime_to)s  AND
                (sm.location_id in %(locations)s or
                 sm.location_dest_id in %(locations)s)
            GROUP BY sm.product_id, sm.date,
                     sm.reference, sp.partner_id, account_id,
                     svl_out.l10n_ro_invoice_id, am.name, svl_out.l10n_ro_valued_type,
                     pt.categ_id {group})
        a --where a.amount_out!=0 and a.quantity_out!=0
                """
        return sql

    def get_report_products(self):
        self.ensure_one()
        if self.product_ids:
            product_list = self.product_ids.ids
            all_products = False
        else:
            product_list = (
                self.env["product.product"]
                .with_context(active_test=False)
                .search(
                    [
                        ("type", "=", "product"),
                        "|",
                        ("company_id", "=", self.company_id.id),
                        ("company_id", "=", False),
                    ]
                )
                .ids
            )
            all_products = True
        if self.products_with_move:
            product_list = self.get_products_with_move_sql(product_list)
            all_products = False
            if not product_list:
                raise UserError(
                    _("There are no stock movements in the selected period")
                )
        return product_list, all_products

    def get_found_products(self):
        self.ensure_one()
        product_list, _all_products = self.get_report_products()
        return (
            self.env["product.product"]
            .with_context(active_test=False)
            .browse(product_list)
        )

    def button_show_sheet(self):
        self.do_compute_product()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "l10n_ro_stock_report.action_sheet_stock_report_line"
        )

        action["display_name"] = "{} {} ({}-{})".format(
            action["name"],
            self.location_id.name or _("All Locations"),
            self.date_from,
            self.date_to,
        )
        action["domain"] = [("report_id", "=", self.id)]
        action["context"] = {"active_id": self.id}

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
    _name = "l10n.ro.stock.storage.sheet.line"
    _description = "StorageSheetLine"
    _order = "report_id, product_id, date_time"
    _rec_name = "product_id"

    report_id = fields.Many2one(
        "l10n.ro.stock.storage.sheet", index=True, ondelete="cascade"
    )
    product_id = fields.Many2one("product.product", string="Product", index=True)
    amount_initial = fields.Monetary(
        currency_field="currency_id", string="Initial Amount", default=0.0
    )
    quantity_initial = fields.Float(
        digits="Product Unit of Measure", string="Initial Quantity", default=0.0
    )
    amount_in = fields.Monetary(
        currency_field="currency_id", string="Input Amount", default=0.0
    )
    quantity_in = fields.Float(
        digits="Product Unit of Measure", string="Input Quantity", default=0.0
    )
    unit_price_in = fields.Monetary(
        currency_field="currency_id",
        string="Price Unit In",
        default=0.0,
        group_operator="avg",
    )
    amount_out = fields.Monetary(
        currency_field="currency_id", default=0.0, string="Output Amount"
    )
    quantity_out = fields.Float(
        digits="Product Unit of Measure", string="Output Quantity", default=0.0
    )
    unit_price_out = fields.Monetary(
        currency_field="currency_id",
        string="Price Unit Out",
        default=0.0,
        group_operator="avg",
    )
    amount_final = fields.Monetary(
        currency_field="currency_id", default=0.0, string="Final Amount"
    )
    quantity_final = fields.Float(
        digits="Product Unit of Measure", string="Final Quantity", default=0.0
    )
    date_time = fields.Datetime(string="Datetime")
    date = fields.Date()
    reference = fields.Char()
    partner_id = fields.Many2one("res.partner", index=True)
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        index=True,
    )
    categ_id = fields.Many2one("product.category", index=True)
    serial_number = fields.Many2one("stock.lot", index=True)
    account_id = fields.Many2one("account.account", index=True)
    location_id = fields.Many2one("stock.location", index=True)
    invoice_id = fields.Many2one("account.move", index=True)
    valued_type = fields.Selection(VALUED_TYPE)
    document = fields.Char()
