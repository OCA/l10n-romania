# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from collections import defaultdict

from odoo import Command, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero


class RetailPriceChange(models.Model):
    _name = "l10n.ro.retail.price.change"
    _description = "Retail Price Change (Proces Verbal de Schimbare Pret)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(
        default="/",
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        readonly=True,
    )
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        required=True,
        domain="[('l10n_ro_retail', '=', True), ('company_id', '=', company_id)]",
        tracking=True,
    )
    pricelist_id = fields.Many2one(
        "product.pricelist",
        compute="_compute_pricelist_id",
        store=True,
        readonly=False,
    )
    date = fields.Date(
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    journal_id = fields.Many2one(
        "account.journal",
        compute="_compute_journal_id",
        store=True,
        readonly=False,
        domain="[('company_id', '=', company_id)]",
    )
    account_move_id = fields.Many2one(
        "account.move",
        readonly=True,
        copy=False,
    )
    line_ids = fields.One2many(
        "l10n.ro.retail.price.change.line",
        "document_id",
        string="Lines",
        copy=True,
    )
    markup_line_ids = fields.One2many(
        "l10n.ro.retail.markup.line",
        "price_change_id",
        string="Markup Ledger",
        readonly=True,
    )
    auto_created = fields.Boolean(
        readonly=True,
        copy=False,
        help="True when this document was generated automatically from a "
        "pricelist change.",
    )
    notes = fields.Html()

    @api.depends("warehouse_id")
    def _compute_pricelist_id(self):
        for doc in self:
            doc.pricelist_id = doc.warehouse_id.l10n_ro_retail_pricelist_id

    @api.depends("company_id")
    def _compute_journal_id(self):
        for doc in self:
            doc.journal_id = doc.company_id.account_stock_journal_id

    @api.model_create_multi
    def create(self, vals_list):
        """Number each document out of the sequence of its own company.

        ``next_by_code`` reads ``self.env.company``, which is not necessarily
        the company of the document being created: the pricelist hook raises
        one document per retail warehouse, in sudo, and a warehouse can belong
        to another company of the group. With a sequence per company that
        would hand a document the series of a different firm.
        """
        Sequence = self.env["ir.sequence"]
        Company = self.env["res.company"]
        for vals in vals_list:
            if vals.get("name", "/") != "/":
                continue
            company = Company.browse(vals.get("company_id")) or self.env.company
            vals["name"] = (
                Sequence.with_company(company).next_by_code(
                    "l10n.ro.retail.price.change"
                )
                or "/"
            )
        return super().create(vals_list)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_done(self):
        """A posted document is not deletable.

        It wrote the prices on the pricelist, posted an entry and left rows in
        the markup ledger. Deleting it cascades its lines - the price history
        of those products - and leaves the ledger rows pointing at nothing,
        with the entry they explain still on the books. A price decision that
        turned out wrong is revoked by posting another Proces Verbal, which is
        also what the paper trail requires.
        """
        for doc in self:
            if doc.state == "done":
                raise UserError(
                    self.env._(
                        "%s has been posted and cannot be deleted. Post a new "
                        "price change document to revoke it.",
                        doc.name,
                    )
                )

    def action_load_products(self):
        self.ensure_one()
        if self.state != "draft":
            raise UserError(self.env._("Only draft documents can be loaded."))
        if not self.warehouse_id:
            raise UserError(self.env._("Select a retail warehouse first."))
        Quant = self.env["stock.quant"]
        quants = Quant.search(
            [
                ("company_id", "=", self.company_id.id),
                ("location_id.l10n_ro_retail", "=", True),
                ("location_id.warehouse_id", "=", self.warehouse_id.id),
                ("quantity", ">", 0),
            ]
        )
        existing_keys = {(ln.product_id.id, ln.location_id.id) for ln in self.line_ids}
        new_lines = []
        for (product, location), qs in self._group_quants(quants):
            key = (product.id, location.id)
            if key in existing_keys:
                continue
            qty = sum(qs.mapped("quantity"))
            if float_is_zero(qty, precision_rounding=product.uom_id.rounding):
                continue
            prices = product._l10n_ro_get_retail_prices(
                warehouse=self.warehouse_id, company=self.company_id
            )
            new_lines.append(
                Command.create(
                    {
                        "product_id": product.id,
                        "location_id": location.id,
                        "quantity": qty,
                        # The old side is read from the ledger. Loading with
                        # today's shelf price on both sides made the document
                        # unable to say anything: a shop whose 371 had drifted
                        # away from its own price list posted nothing and had
                        # no way to put itself right.
                        "new_price_with_vat": prices["price_with_vat"],
                    }
                )
            )
        if new_lines:
            self.line_ids = new_lines

    @staticmethod
    def _group_quants(quants):
        seen = {}
        for q in quants:
            seen[(q.product_id, q.location_id)] = (
                seen.get((q.product_id, q.location_id), q.browse([])) | q
            )
        return seen.items()

    def action_post(self):
        for doc in self:
            doc._post_one()
        return True

    def _post_one(self):
        self.ensure_one()
        if self.state != "draft":
            raise UserError(self.env._("Document %s is not in draft.", self.name))
        if not self.line_ids:
            raise UserError(self.env._("No lines to post on %s.", self.name))
        if not self.journal_id:
            raise UserError(self.env._("No journal defined."))
        self._refresh_from_stock()
        self._check_ledger_covers_stock()
        self._update_pricelist()
        move = self._create_account_move()
        self._create_markup_ledger(move)
        self.write(
            {
                "state": "done",
                "account_move_id": move.id if move else False,
            }
        )

    def _refresh_from_stock(self):
        """Re-read the quantity and what the stock carries, at posting time.

        The old side of a document is a statement of fact, and the fact it
        states is the one that holds when the entry is made - not the one that
        held when somebody loaded the lines. The two part company routinely: a
        pricelist change raises a draft to be reviewed later, and in between
        the shop sells, receives, or another Proces Verbal is posted on the
        same goods. Read once at load, the document then measured its delta
        against a markup that was no longer carried and a quantity that was no
        longer on the shelf - two documents posted one after the other applied
        their deltas to the same starting point and doubled the revaluation
        between them, with nothing in either entry to show it.
        """
        self.ensure_one()
        on_hand = self.line_ids._l10n_ro_on_hand()
        for line in self.line_ids:
            line.quantity = on_hand.get((line.product_id.id, line.location_id.id), 0.0)
        # The quantity may well be unchanged, and the carried markup can have
        # moved anyway - the ledger is not a dependency of the compute, and
        # cannot be, so the refresh is asked for explicitly.
        for field_name in ("cost_unit", "old_markup_unit", "old_vat_unit"):
            self.env.add_to_compute(self.line_ids._fields[field_name], self.line_ids)
        self.line_ids.flush_recordset()

    def _check_ledger_covers_stock(self):
        """Refuse to post a rate derived from one quantity onto another.

        The old markup per unit is the ledger balance divided by the quantity
        the ledger knows about, and it is then applied to the quantity on the
        lines. The two have to be the same quantity, or the document moves
        378 by an amount the rate was never meant to produce, and leaves the
        release rate of the remaining stock wrong for good.

        They differ in two cases. Stock that was on the shelf before this
        module was installed is in the quants and not in the ledger - that is
        what the opening balance wizard is for. And a document that covers
        only part of what the shop holds of a product applies a whole-shop
        rate to a slice of it.
        """
        self.ensure_one()
        Ledger = self.env["l10n.ro.retail.markup.line"].sudo()
        per_product = defaultdict(float)
        for line in self.line_ids:
            per_product[line.product_id] += line.quantity
        problems = []
        for product, qty in per_product.items():
            recorded, _cost, _markup, _vat = Ledger._l10n_ro_balance(
                self.warehouse_id, product, self.company_id
            )
            if (
                float_compare(recorded, qty, precision_rounding=product.uom_id.rounding)
                != 0
            ):
                problems.append((product, recorded, qty))
        if not problems:
            return
        details = "\n".join(
            self.env._(
                " - %(product)s: ledger %(recorded).3f, document %(qty).3f",
                product=product.display_name,
                recorded=recorded,
                qty=qty,
            )
            for product, recorded, qty in problems
        )
        raise UserError(
            self.env._(
                "The markup ledger of %(warehouse)s does not account for the "
                "same quantity this document revalues:\n\n%(details)s\n\n"
                "Load every location that holds these products, and settle "
                "stock the ledger never saw with the retail opening balance "
                "wizard, before posting.",
                warehouse=self.warehouse_id.display_name,
                details=details,
            )
        )

    def _update_pricelist(self):
        """Write the new shelf prices on the warehouse retail pricelist.

        A retail pricelist holds the price VAT included - the figure on the
        shelf label. The old code converted the new PVA to a net price before
        writing it, so the pricelist ended up holding a different number from
        the one on the document, and reading it back produced a third one.
        """
        self.ensure_one()
        if not self.pricelist_id:
            return
        Item = self.env["product.pricelist.item"]
        for line in self.line_ids:
            if not line.new_price_with_vat:
                continue
            item = Item.search(
                [
                    ("pricelist_id", "=", self.pricelist_id.id),
                    ("applied_on", "=", "0_product_variant"),
                    ("product_id", "=", line.product_id.id),
                    ("compute_price", "=", "fixed"),
                ],
                limit=1,
            )
            vals = {
                "fixed_price": line.new_price_with_vat,
                "compute_price": "fixed",
            }
            if item:
                item.with_context(skip_retail_price_change=True).write(vals)
            else:
                Item.with_context(skip_retail_price_change=True).create(
                    dict(
                        vals,
                        pricelist_id=self.pricelist_id.id,
                        applied_on="0_product_variant",
                        product_id=line.product_id.id,
                    )
                )

    def _create_account_move(self):
        self.ensure_one()
        currency = self.company_id.currency_id
        aml_vals = []
        for line in self.line_ids:
            stock_account = line.location_id._l10n_ro_get_stock_account(
                product=line.product_id
            )
            if not stock_account:
                raise UserError(
                    self.env._(
                        "Missing stock valuation account for product %s.",
                        line.product_id.display_name,
                    )
                )
            markup_account = line.location_id._l10n_ro_get_markup_account(
                product=line.product_id
            )
            deferred_vat_account = line.location_id._l10n_ro_get_deferred_vat_account(
                product=line.product_id
            )
            if not markup_account or not deferred_vat_account:
                raise UserError(
                    self.env._(
                        "Missing markup (378) or deferred VAT (4428) account "
                        "for product %(p)s at location %(loc)s.",
                        p=line.product_id.display_name,
                        loc=line.location_id.display_name,
                    )
                )
            markup_delta = currency.round(line.markup_diff_total)
            vat_delta = currency.round(line.vat_diff_total)
            ref = self.env._("Price change %s", line.product_id.display_name)
            if not float_is_zero(markup_delta, precision_rounding=currency.rounding):
                aml_vals += line._aml_pair(
                    stock_account, markup_account, markup_delta, ref
                )
            if not float_is_zero(vat_delta, precision_rounding=currency.rounding):
                aml_vals += line._aml_pair(
                    stock_account, deferred_vat_account, vat_delta, ref
                )
        if not aml_vals:
            return self.env["account.move"]
        move = self.env["account.move"].create(
            {
                "journal_id": self.journal_id.id,
                "date": self.date,
                "ref": self.env._(
                    "Retail price change %s",
                    self.name,
                ),
                "line_ids": aml_vals,
            }
        )
        move._post()
        return move

    def _create_markup_ledger(self, move):
        """Record the revaluation in the markup ledger.

        Without this the shop would release, on the next sale, the markup that
        was loaded at reception - not the one this document just put on 378 -
        and the difference would sit on the account for good.
        """
        self.ensure_one()
        currency = self.company_id.currency_id
        vals_list = []
        for line in self.line_ids:
            markup_delta = currency.round(line.markup_diff_total)
            vat_delta = currency.round(line.vat_diff_total)
            if float_is_zero(
                markup_delta, precision_rounding=currency.rounding
            ) and float_is_zero(vat_delta, precision_rounding=currency.rounding):
                continue
            vals_list.append(
                {
                    "company_id": self.company_id.id,
                    "date": self.date,
                    "product_id": line.product_id.id,
                    "location_id": line.location_id.id,
                    "warehouse_id": self.warehouse_id.id,
                    # A revaluation moves no goods: it changes what the stock
                    # on hand carries, so the quantity that carries it is
                    # unchanged and this row must not shift the rate.
                    "quantity": 0.0,
                    # A revaluation moves no cost. Written explicitly so the
                    # column holds zero rather than NULL, which would drop the
                    # row out of any arithmetic done across the three.
                    "cost": 0.0,
                    "markup": markup_delta,
                    "vat": vat_delta,
                    "origin_type": "price_change",
                    "price_change_id": self.id,
                    "account_move_id": move.id if move else False,
                    "reference": self.name,
                }
            )
        if vals_list:
            self.env["l10n.ro.retail.markup.line"].sudo().create(vals_list)

    def action_cancel(self):
        """Drop a document that was never posted.

        Only from draft, and there is no way back from done. A posted Proces
        Verbal wrote the shelf prices, posted an entry and moved what the
        stock carries; undoing it in place would leave the three out of step
        with each other and the printed document out of step with the books.
        A price decision that turned out wrong is revoked the way it was made,
        by posting another one.
        """
        for doc in self:
            if doc.state != "draft":
                raise UserError(
                    self.env._(
                        "%s is no longer a draft. Post a new price change "
                        "document to revoke it.",
                        doc.name,
                    )
                )
            doc.state = "cancel"

    def action_view_move(self):
        self.ensure_one()
        if not self.account_move_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.account_move_id.id,
            "view_mode": "form",
        }


class RetailPriceChangeLine(models.Model):
    _name = "l10n.ro.retail.price.change.line"
    _description = "Retail Price Change Line"

    document_id = fields.Many2one(
        "l10n.ro.retail.price.change",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(related="document_id.company_id", store=True)
    document_date = fields.Date(
        related="document_id.date", store=True, string="Date", index=True
    )
    warehouse_id = fields.Many2one(
        related="document_id.warehouse_id", store=True, string="Warehouse"
    )
    state = fields.Selection(related="document_id.state", store=False)
    currency_id = fields.Many2one(related="company_id.currency_id", readonly=True)
    product_id = fields.Many2one("product.product", required=True)
    location_id = fields.Many2one("stock.location", required=True)
    quantity = fields.Float(digits="Product Unit of Measure", readonly=True)
    cost_unit = fields.Monetary(
        string="Cost / Unit",
        compute="_compute_carried",
        store=True,
        help="Cost the stock on hand carries, from the markup ledger.",
    )
    old_price_with_vat = fields.Monetary(
        string="Old PVA",
        compute="_compute_old_price",
        store=True,
        help="What the stock on the shelf carries per unit, VAT included - the "
        "cost plus the markup and deferred VAT recorded against it. This is "
        "what 371 holds, which is not always what the pricelist says.",
    )
    new_price_with_vat = fields.Monetary(
        string="New PVA",
        help="New retail price including VAT.",
    )
    old_markup_unit = fields.Monetary(
        compute="_compute_carried",
        string="Old Markup / Unit",
        store=True,
        help="Markup the stock carries on 378 per unit, as recorded.",
    )
    old_vat_unit = fields.Monetary(
        compute="_compute_carried",
        string="Old VAT / Unit",
        store=True,
        help="Deferred VAT the stock carries on 4428 per unit, as recorded.",
    )
    new_markup_unit = fields.Monetary(
        compute="_compute_splits", string="New Markup / Unit", store=True
    )
    new_vat_unit = fields.Monetary(
        compute="_compute_splits", string="New VAT / Unit", store=True
    )
    markup_diff_total = fields.Monetary(
        compute="_compute_splits", string="Markup Delta", store=True
    )
    vat_diff_total = fields.Monetary(
        compute="_compute_splits", string="VAT Delta", store=True
    )

    def _l10n_ro_on_hand(self):
        """Quantity on hand per ``(product, location)`` for the lines in self."""
        if not self:
            return {}
        groups = (
            self.env["stock.quant"]
            .sudo()
            ._read_group(
                [
                    ("product_id", "in", self.product_id.ids),
                    ("location_id", "in", self.location_id.ids),
                ],
                groupby=["product_id", "location_id"],
                aggregates=["quantity:sum"],
            )
        )
        return {
            (product.id, location.id): qty or 0.0 for product, location, qty in groups
        }

    @api.depends("product_id", "location_id", "quantity", "document_id.warehouse_id")
    def _compute_carried(self):
        """What the stock on the shelf carries per unit, from the ledger.

        The old side of the document is a statement of fact - what 371, 378 and
        4428 hold for these goods right now - so it is read from the ledger
        rather than recomputed from the pricelist. Deriving it from the price
        assumed the two agree, which is exactly the assumption that fails: a
        shop whose ledger has drifted then loads a document where old equals
        new, posts nothing, and has no way to put itself right.

        The ledger is read for the whole batch, and so is the cost that stands
        in for it when it holds nothing yet. That cost is the value of the
        quants, the same figure the retail opening balance wizard settles
        against; ``standard_price`` was a different number on any product that
        is not valued at standard, and the difference went straight into the
        markup - two ways of recognising the same stock, disagreeing.
        """
        for line in self:
            line.cost_unit = 0.0
            line.old_markup_unit = 0.0
            line.old_vat_unit = 0.0
        lines = self.filtered(lambda ln: ln.product_id and ln.document_id.warehouse_id)
        if not lines:
            return
        carried = lines._l10n_ro_carried_balances()
        fallback = None
        for line in lines:
            product = line.product_id
            company = line.document_id.company_id or line.env.company
            key = (company.id, line.document_id.warehouse_id.id, product.id)
            qty, cost, markup, vat = carried.get(key, (0.0, 0.0, 0.0, 0.0))
            if not float_is_zero(qty, precision_rounding=product.uom_id.rounding):
                line.cost_unit = cost / qty
                line.old_markup_unit = markup / qty
                line.old_vat_unit = vat / qty
                continue
            # Nothing carried yet: the whole shelf price is markup and VAT
            # over what the goods actually cost.
            if fallback is None:
                fallback = lines._l10n_ro_quant_cost()
            on_hand_qty, on_hand_value = fallback.get(key, (0.0, 0.0))
            line.cost_unit = (
                on_hand_value / on_hand_qty
                if not float_is_zero(
                    on_hand_qty, precision_rounding=product.uom_id.rounding
                )
                else product.with_company(company).standard_price
            )

    def _l10n_ro_keys(self):
        """``(company, warehouse, product)`` triples covered by these lines."""
        keys = set()
        for line in self:
            company = line.document_id.company_id or line.env.company
            keys.add((company.id, line.document_id.warehouse_id.id, line.product_id.id))
        return keys

    def _l10n_ro_carried_balances(self):
        """Ledger balance per ``(company, warehouse, product)``, in one read."""
        keys = self._l10n_ro_keys()
        if not keys:
            return {}
        groups = (
            self.env["l10n.ro.retail.markup.line"]
            .sudo()
            ._read_group(
                [
                    ("company_id", "in", [k[0] for k in keys]),
                    ("warehouse_id", "in", [k[1] for k in keys]),
                    ("product_id", "in", [k[2] for k in keys]),
                ],
                groupby=["company_id", "warehouse_id", "product_id"],
                aggregates=[
                    "quantity:sum",
                    "cost:sum",
                    "markup:sum",
                    "vat:sum",
                ],
            )
        )
        return {
            (company.id, warehouse.id, product.id): (
                qty or 0.0,
                cost or 0.0,
                markup or 0.0,
                vat or 0.0,
            )
            for company, warehouse, product, qty, cost, markup, vat in groups
        }

    def _l10n_ro_quant_cost(self):
        """Quantity and value on hand per ``(company, warehouse, product)``."""
        keys = self._l10n_ro_keys()
        if not keys:
            return {}
        groups = (
            self.env["stock.quant"]
            .sudo()
            ._read_group(
                [
                    ("company_id", "in", [k[0] for k in keys]),
                    ("location_id.warehouse_id", "in", [k[1] for k in keys]),
                    ("location_id.l10n_ro_retail", "=", True),
                    ("product_id", "in", [k[2] for k in keys]),
                ],
                groupby=["company_id", "product_id", "location_id"],
                aggregates=["quantity:sum", "value:sum"],
            )
        )
        result = defaultdict(lambda: (0.0, 0.0))
        for company, product, location, qty, value in groups:
            key = (company.id, location.warehouse_id.id, product.id)
            had_qty, had_value = result[key]
            result[key] = (had_qty + (qty or 0.0), had_value + (value or 0.0))
        return result

    @api.depends("cost_unit", "old_markup_unit", "old_vat_unit")
    def _compute_old_price(self):
        for line in self:
            line.old_price_with_vat = (
                line.cost_unit + line.old_markup_unit + line.old_vat_unit
            )

    @api.depends(
        "new_price_with_vat",
        "cost_unit",
        "old_markup_unit",
        "old_vat_unit",
        "quantity",
        "product_id",
        "document_id.company_id",
    )
    def _compute_splits(self):
        """The new side is what the shelf price implies; the delta closes the
        gap between what is carried and what it should be."""
        for line in self:
            company = line.document_id.company_id or line.env.company
            line.new_markup_unit, line.new_vat_unit = line._split(
                line.new_price_with_vat, company
            )
            line.markup_diff_total = (
                line.new_markup_unit - line.old_markup_unit
            ) * line.quantity
            line.vat_diff_total = (
                line.new_vat_unit - line.old_vat_unit
            ) * line.quantity

    def _split(self, price_with_vat, company):
        """Return ``(markup_per_unit, vat_per_unit)`` for a VAT-inclusive PVA."""
        self.ensure_one()
        if not price_with_vat or not self.product_id:
            return 0.0, 0.0
        prices = self.product_id._l10n_ro_split_retail_price(
            price_with_vat,
            company=company,
            warehouse=self.document_id.warehouse_id,
        )
        return prices["price_without_vat"] - self.cost_unit, prices["vat"]

    def _aml_pair(self, stock_account, other_account, signed_amount, ref):
        """Debit/credit AML pair, swapping sides on negatives."""
        self.ensure_one()
        currency = self.document_id.company_id.currency_id
        abs_value = abs(signed_amount)
        debit_account = stock_account if signed_amount > 0 else other_account
        credit_account = other_account if signed_amount > 0 else stock_account
        base = {
            "name": ref,
            "product_id": self.product_id.id,
            "quantity": self.quantity,
        }
        return [
            Command.create(
                dict(
                    base,
                    account_id=debit_account.id,
                    debit=currency.round(abs_value),
                    credit=0.0,
                )
            ),
            Command.create(
                dict(
                    base,
                    account_id=credit_account.id,
                    debit=0.0,
                    credit=currency.round(abs_value),
                )
            ),
        ]
