# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import Command, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero


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
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("l10n.ro.retail.price.change")
                    or "/"
                )
        return super().create(vals_list)

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
        self._update_pricelist()
        move = self._create_account_move()
        self._create_markup_ledger(move)
        self.write(
            {
                "state": "done",
                "account_move_id": move.id if move else False,
            }
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
                    "date": fields.Datetime.to_datetime(self.date),
                    "product_id": line.product_id.id,
                    "location_id": line.location_id.id,
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
        for doc in self:
            if doc.state == "done" and doc.account_move_id:
                raise UserError(
                    self.env._(
                        "Cancel the related journal entry %s first.",
                        doc.account_move_id.display_name,
                    )
                )
            doc.state = "cancel"

    def action_draft(self):
        """Send the document back to draft.

        Refused while any trace of the posting survives. Checking only for a
        *posted* entry let a document whose entry had been reversed - so left
        in state 'cancel' - go back to draft and be posted a second time: a
        second journal entry, a second set of ledger rows, and the link to the
        first entry silently overwritten.
        """
        for doc in self:
            if doc.account_move_id and doc.account_move_id.state != "cancel":
                raise UserError(
                    doc.env._(
                        "Reverse and cancel the related journal entry "
                        "%(entry)s before resetting %(document)s to draft.",
                        entry=doc.account_move_id.display_name,
                        document=doc.name,
                    )
                )
            if doc.markup_line_ids:
                raise UserError(
                    doc.env._(
                        "%s already moved the markup carried by the stock. "
                        "Post a new price change document to correct it "
                        "instead of resetting this one to draft.",
                        doc.name,
                    )
                )
            doc.write({"state": "draft", "account_move_id": False})

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
    product_id = fields.Many2one("product.product", required=True)
    location_id = fields.Many2one("stock.location", required=True)
    quantity = fields.Float(readonly=True)
    cost_unit = fields.Float(
        string="Cost / Unit",
        compute="_compute_carried",
        store=True,
        help="Cost the stock on hand carries, from the markup ledger.",
    )
    old_price_with_vat = fields.Float(
        string="Old PVA",
        compute="_compute_old_price",
        store=True,
        help="What the stock on the shelf carries per unit, VAT included - the "
        "cost plus the markup and deferred VAT recorded against it. This is "
        "what 371 holds, which is not always what the pricelist says.",
    )
    new_price_with_vat = fields.Float(
        string="New PVA",
        help="New retail price including VAT.",
    )
    old_markup_unit = fields.Float(
        compute="_compute_carried",
        string="Old Markup / Unit",
        store=True,
        help="Markup the stock carries on 378 per unit, as recorded.",
    )
    old_vat_unit = fields.Float(
        compute="_compute_carried",
        string="Old VAT / Unit",
        store=True,
        help="Deferred VAT the stock carries on 4428 per unit, as recorded.",
    )
    new_markup_unit = fields.Float(
        compute="_compute_splits", string="New Markup / Unit", store=True
    )
    new_vat_unit = fields.Float(
        compute="_compute_splits", string="New VAT / Unit", store=True
    )
    markup_diff_total = fields.Float(
        compute="_compute_splits", string="Markup Delta", store=True
    )
    vat_diff_total = fields.Float(
        compute="_compute_splits", string="VAT Delta", store=True
    )

    @api.depends("product_id", "location_id", "quantity", "document_id.warehouse_id")
    def _compute_carried(self):
        """What the stock on the shelf carries per unit, from the ledger.

        The old side of the document is a statement of fact - what 371, 378 and
        4428 hold for these goods right now - so it is read from the ledger
        rather than recomputed from the pricelist. Deriving it from the price
        assumed the two agree, which is exactly the assumption that fails: a
        shop whose ledger has drifted then loads a document where old equals
        new, posts nothing, and has no way to put itself right.
        """
        Ledger = self.env["l10n.ro.retail.markup.line"]
        for line in self:
            company = line.document_id.company_id or line.env.company
            warehouse = line.document_id.warehouse_id
            product = line.product_id
            line.cost_unit = 0.0
            line.old_markup_unit = 0.0
            line.old_vat_unit = 0.0
            if not product or not warehouse:
                continue
            qty, cost, markup, vat = Ledger._l10n_ro_balance(
                warehouse, product, company
            )
            if float_is_zero(qty, precision_rounding=product.uom_id.rounding):
                # Nothing carried yet: fall back to the product cost, and let
                # the whole shelf price be markup and VAT.
                line.cost_unit = product.with_company(company).standard_price
                continue
            line.cost_unit = cost / qty
            line.old_markup_unit = markup / qty
            line.old_vat_unit = vat / qty

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
            price_with_vat, company=company
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
