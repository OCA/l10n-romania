# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from psycopg2 import sql

from odoo import api, fields, models


class StockRetailReport(models.Model):
    """What each shop carries on 371, 378 and 4428, and how it got there.

    One row per (warehouse, product). Every figure comes from the markup
    ledger, where each event writes what it put on, or took off, account 371
    split three ways - cost, markup, deferred VAT. Their sum is the balance of
    371 for that stock, and the markup and VAT columns are the balances of 378
    and 4428 for it, so the report reconciles against the trial balance line by
    line.

    Because the ledger is dated, the report answers for a moment or for a
    stretch of time. Pass ``l10n_ro_retail_date_from`` and
    ``l10n_ro_retail_date_to`` in the context - the wizard does - and the
    columns split into opening balance, movements in and out, corrections and
    closing balance. With no dates it is simply today's position.
    """

    _name = "l10n.ro.stock.retail.report"
    _description = "Retail Stock Report"
    _auto = False
    _order = "warehouse_id, product_id"
    # Tells the ORM this view reads another table, so rows written earlier in
    # the same transaction are flushed before the query runs. Without it the
    # report silently comes back short for anything that posts and then
    # reports in one go.
    _depends = {
        "l10n.ro.retail.markup.line": [
            "company_id",
            "warehouse_id",
            "product_id",
            "date",
            "quantity",
            "cost",
            "markup",
            "vat",
            "origin_type",
        ],
        "stock.quant": ["company_id", "location_id", "product_id", "quantity"],
    }

    warehouse_id = fields.Many2one("stock.warehouse", string="Warehouse", readonly=True)
    product_id = fields.Many2one("product.product", string="Product", readonly=True)
    product_tmpl_id = fields.Many2one(
        "product.template", string="Product Template", readonly=True
    )
    categ_id = fields.Many2one("product.category", string="Category", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", readonly=True
    )

    # --- opening balance, before the period ---------------------------------
    quantity_initial = fields.Float(string="Opening Quantity", readonly=True)
    cost_initial = fields.Monetary(
        string="Opening Cost", readonly=True, currency_field="currency_id"
    )
    markup_initial = fields.Monetary(
        string="Opening Markup (378)", readonly=True, currency_field="currency_id"
    )
    vat_initial = fields.Monetary(
        string="Opening Deferred VAT (4428)",
        readonly=True,
        currency_field="currency_id",
    )
    retail_initial = fields.Monetary(
        string="Opening Retail Value (371)",
        compute="_compute_values",
        currency_field="currency_id",
    )

    # --- movements inside the period ----------------------------------------
    quantity_in = fields.Float(readonly=True)
    cost_in = fields.Monetary(readonly=True, currency_field="currency_id")
    markup_in = fields.Monetary(
        string="Markup In (378)", readonly=True, currency_field="currency_id"
    )
    vat_in = fields.Monetary(
        string="Deferred VAT In (4428)", readonly=True, currency_field="currency_id"
    )
    quantity_out = fields.Float(readonly=True)
    cost_out = fields.Monetary(readonly=True, currency_field="currency_id")
    markup_out = fields.Monetary(
        string="Markup Out (378)", readonly=True, currency_field="currency_id"
    )
    vat_out = fields.Monetary(
        string="Deferred VAT Out (4428)", readonly=True, currency_field="currency_id"
    )
    cost_adjustment = fields.Monetary(
        string="Cost Corrections",
        readonly=True,
        currency_field="currency_id",
        help="Cost added by landed costs and purchase price differences, which "
        "move no goods.",
    )
    markup_adjustment = fields.Monetary(
        string="Markup Corrections (378)",
        readonly=True,
        currency_field="currency_id",
        help="Markup moved by price changes, landed costs and purchase price "
        "differences, which move no goods.",
    )
    vat_adjustment = fields.Monetary(
        string="Deferred VAT Corrections (4428)",
        readonly=True,
        currency_field="currency_id",
    )

    # --- closing balance ----------------------------------------------------
    quantity = fields.Float(string="Recorded Quantity", readonly=True)
    quantity_on_hand = fields.Float(
        readonly=True,
        help="What the shop actually holds, from the quants. Only filled "
        "when the report answers for today: the quants keep no history, so a "
        "report asked for a past position leaves this empty.",
    )
    quantity_unrecorded = fields.Float(
        readonly=True,
        help="Stock on the shelf that the markup ledger has no record of, "
        "normally goods that were already there when this module was "
        "installed. Their shelf value is not on 371 yet: run the retail "
        "markup opening balance to settle them. Only filled when the report "
        "answers for today.",
    )
    cost_total = fields.Monetary(
        string="Stock Value (cost)", readonly=True, currency_field="currency_id"
    )
    markup_total = fields.Monetary(
        string="Markup Carried (378)", readonly=True, currency_field="currency_id"
    )
    vat_total = fields.Monetary(
        string="Deferred VAT Carried (4428)",
        readonly=True,
        currency_field="currency_id",
    )
    retail_value = fields.Monetary(
        string="Retail Value (371)",
        compute="_compute_values",
        currency_field="currency_id",
        help="Cost plus the markup and deferred VAT carried - what account 371 "
        "holds for this stock.",
    )

    # --- unit figures and the gap against today's shelf price ---------------
    cost_unit = fields.Monetary(
        string="Cost / Unit", compute="_compute_values", currency_field="currency_id"
    )
    retail_price_unit = fields.Monetary(
        string="Carried PVA / Unit",
        compute="_compute_values",
        currency_field="currency_id",
        help="Retail value per unit, VAT included, as loaded.",
    )
    current_price_unit = fields.Monetary(
        string="Current Shelf Price / Unit",
        compute="_compute_values",
        currency_field="currency_id",
        help="Shelf price the warehouse pricelist gives today, VAT included. "
        "Always today's price, whatever period the rest of the row covers.",
    )
    price_gap_total = fields.Monetary(
        string="To Revalue",
        compute="_compute_values",
        currency_field="currency_id",
        help="Difference between the current shelf price and what the stock "
        "carries. Anything other than zero means a price change document is "
        "due for this product.",
    )

    # ------------------------------------------------------------------
    @api.model
    def _l10n_ro_period(self):
        """The period asked for, as ``(date_from, date_to)`` SQL literals.

        Either bound may be absent: with no start the opening balance is
        empty, with no end everything up to now is reported.
        """
        context = self.env.context

        def as_literal(key):
            raw = context.get(key)
            if not raw:
                return None
            return sql.Literal(
                fields.Datetime.to_string(fields.Datetime.to_datetime(raw))
            )

        return as_literal("l10n_ro_retail_date_from"), as_literal(
            "l10n_ro_retail_date_to"
        )

    @property
    def _table_query(self):
        date_from, date_to = self._l10n_ro_period()

        before = (
            sql.SQL("ml.date < {}").format(date_from) if date_from else sql.SQL("FALSE")
        )
        upto = sql.SQL("ml.date <= {}").format(date_to) if date_to else sql.SQL("TRUE")
        in_period = sql.SQL("({} AND NOT ({}))").format(upto, before)

        # With no period asked for, a line is worth printing when the shop
        # holds the goods - whether or not the ledger knows about them. With a
        # period, a product that came in and left again inside it is exactly
        # what the reader is checking, so it keeps its row too.
        # The quants have no history: they say what is on the shelf now and
        # nothing about what was there in March. They belong in the report only
        # when it is answering for today - asked for a past position it must
        # speak from the ledger alone, or a product bought last week would show
        # up in a report about last month.
        quants_apply = (
            sql.SQL("TRUE") if not (date_from or date_to) else sql.SQL("FALSE")
        )
        having = (
            sql.SQL(
                "COALESCE(l.quantity, 0) > 0 OR COALESCE(h.quantity_on_hand, 0) > 0"
            )
            if not (date_from or date_to)
            else sql.SQL(
                "COALESCE(l.rows_upto, 0) > 0 OR COALESCE(h.quantity_on_hand, 0) > 0"
            )
        )

        def bucket(column, condition):
            return sql.SQL("SUM(CASE WHEN {cond} THEN ml.{col} ELSE 0 END)").format(
                cond=condition, col=sql.Identifier(column)
            )

        moved_in = sql.SQL(
            "({} AND ml.origin_type = 'move' AND ml.quantity > 0)"
        ).format(in_period)
        moved_out = sql.SQL(
            "({} AND ml.origin_type = 'move' AND ml.quantity < 0)"
        ).format(in_period)
        adjusted = sql.SQL("({} AND ml.origin_type != 'move')").format(in_period)

        query = sql.SQL(
            """
            WITH ledger AS (
                SELECT
                    ml.company_id,
                    ml.warehouse_id,
                    ml.product_id,
                    MIN(ml.id) AS first_id,
                    {qty_initial}::numeric AS quantity_initial,
                    {cost_initial}::numeric AS cost_initial,
                    {markup_initial}::numeric AS markup_initial,
                    {vat_initial}::numeric AS vat_initial,
                    {qty_in}::numeric AS quantity_in,
                    {cost_in}::numeric AS cost_in,
                    {markup_in}::numeric AS markup_in,
                    {vat_in}::numeric AS vat_in,
                    {qty_out}::numeric AS quantity_out,
                    {cost_out}::numeric AS cost_out,
                    {markup_out}::numeric AS markup_out,
                    {vat_out}::numeric AS vat_out,
                    {cost_adj}::numeric AS cost_adjustment,
                    {markup_adj}::numeric AS markup_adjustment,
                    {vat_adj}::numeric AS vat_adjustment,
                    {qty_final}::numeric AS quantity,
                    {cost_final}::numeric AS cost_total,
                    {markup_final}::numeric AS markup_total,
                    {vat_final}::numeric AS vat_total,
                    COUNT(*) FILTER (WHERE {upto}) AS rows_upto
                FROM l10n_ro_retail_markup_line ml
                WHERE ml.warehouse_id IS NOT NULL
                GROUP BY ml.company_id, ml.warehouse_id, ml.product_id
            ),
            -- What the shop really holds. A shop that was trading before this
            -- module arrived has stock here and nothing in the ledger; leaving
            -- the quants out of the report is what made that population
            -- invisible in the one place someone would look for it.
            on_hand AS (
                SELECT
                    sq.company_id,
                    sl.warehouse_id,
                    sq.product_id,
                    SUM(sq.quantity)::numeric AS quantity_on_hand
                FROM stock_quant sq
                JOIN stock_location sl ON sl.id = sq.location_id
                WHERE sl.l10n_ro_retail AND sl.warehouse_id IS NOT NULL
                  AND {quants_apply}
                GROUP BY sq.company_id, sl.warehouse_id, sq.product_id
            )
            SELECT
                -- Arithmetic on the two ids overflows a 4 byte integer as
                -- soon as a warehouse id passes 21, so the row number is the
                -- key. It is computed over the whole view, before any domain
                -- is applied, so it stays put between reads.
                (ROW_NUMBER() OVER (
                    ORDER BY COALESCE(l.warehouse_id, h.warehouse_id),
                             COALESCE(l.product_id, h.product_id)
                ))::integer AS id,
                COALESCE(l.company_id, h.company_id) AS company_id,
                COALESCE(l.warehouse_id, h.warehouse_id) AS warehouse_id,
                COALESCE(l.product_id, h.product_id) AS product_id,
                pp.product_tmpl_id AS product_tmpl_id,
                pt.categ_id AS categ_id,
                COALESCE(l.quantity_initial, 0) AS quantity_initial,
                COALESCE(l.cost_initial, 0) AS cost_initial,
                COALESCE(l.markup_initial, 0) AS markup_initial,
                COALESCE(l.vat_initial, 0) AS vat_initial,
                COALESCE(l.quantity_in, 0) AS quantity_in,
                COALESCE(l.cost_in, 0) AS cost_in,
                COALESCE(l.markup_in, 0) AS markup_in,
                COALESCE(l.vat_in, 0) AS vat_in,
                COALESCE(l.quantity_out, 0) AS quantity_out,
                COALESCE(l.cost_out, 0) AS cost_out,
                COALESCE(l.markup_out, 0) AS markup_out,
                COALESCE(l.vat_out, 0) AS vat_out,
                COALESCE(l.cost_adjustment, 0) AS cost_adjustment,
                COALESCE(l.markup_adjustment, 0) AS markup_adjustment,
                COALESCE(l.vat_adjustment, 0) AS vat_adjustment,
                COALESCE(l.quantity, 0) AS quantity,
                COALESCE(l.cost_total, 0) AS cost_total,
                COALESCE(l.markup_total, 0) AS markup_total,
                COALESCE(l.vat_total, 0) AS vat_total,
                COALESCE(h.quantity_on_hand, 0) AS quantity_on_hand,
                (COALESCE(h.quantity_on_hand, 0)
                    - COALESCE(l.quantity, 0)) AS quantity_unrecorded
            FROM ledger l
            FULL OUTER JOIN on_hand h
                ON h.company_id = l.company_id
               AND h.warehouse_id = l.warehouse_id
               AND h.product_id = l.product_id
            JOIN product_product pp
                ON pp.id = COALESCE(l.product_id, h.product_id)
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            WHERE {having}
            """
        ).format(
            qty_initial=bucket("quantity", before),
            cost_initial=bucket("cost", before),
            markup_initial=bucket("markup", before),
            vat_initial=bucket("vat", before),
            qty_in=bucket("quantity", moved_in),
            cost_in=bucket("cost", moved_in),
            markup_in=bucket("markup", moved_in),
            vat_in=bucket("vat", moved_in),
            qty_out=bucket("quantity", moved_out),
            cost_out=bucket("cost", moved_out),
            markup_out=bucket("markup", moved_out),
            vat_out=bucket("vat", moved_out),
            cost_adj=bucket("cost", adjusted),
            markup_adj=bucket("markup", adjusted),
            vat_adj=bucket("vat", adjusted),
            qty_final=bucket("quantity", upto),
            cost_final=bucket("cost", upto),
            markup_final=bucket("markup", upto),
            vat_final=bucket("vat", upto),
            upto=upto,
            quants_apply=quants_apply,
            having=having,
        )
        return query.as_string(self.env.cr._cnx)

    @api.depends(
        "product_id",
        "warehouse_id",
        "quantity",
        "cost_total",
        "markup_total",
        "vat_total",
    )
    def _compute_values(self):
        for rec in self:
            company = rec.company_id or self.env.company
            currency = company.currency_id
            qty = rec.quantity or 0.0
            retail_value = rec.cost_total + rec.markup_total + rec.vat_total
            rec.retail_initial = currency.round(
                rec.cost_initial + rec.markup_initial + rec.vat_initial
            )
            rec.retail_value = currency.round(retail_value)
            rec.cost_unit = currency.round(rec.cost_total / qty) if qty else 0.0
            rec.retail_price_unit = currency.round(retail_value / qty) if qty else 0.0
            current_unit = (
                rec.product_id._l10n_ro_get_retail_price(
                    warehouse=rec.warehouse_id, company=company
                )
                if rec.product_id and rec.warehouse_id
                else 0.0
            )
            rec.current_price_unit = currency.round(current_unit)
            rec.price_gap_total = currency.round(current_unit * qty - retail_value)
