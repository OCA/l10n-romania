# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero


class RetailPriceChange(models.Model):
    _name = "l10n.ro.retail.price.change"
    _description = "Proces Verbal de Schimbare Pret (Retail Price Change)"
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
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "l10n.ro.retail.price.change"
                ) or "/"
        return super().create(vals_list)

    def action_load_products(self):
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Only draft documents can be loaded."))
        if not self.warehouse_id:
            raise UserError(_("Select a retail warehouse first."))
        Quant = self.env["stock.quant"]
        quants = Quant.search(
            [
                ("company_id", "=", self.company_id.id),
                ("location_id.l10n_ro_retail", "=", True),
                ("location_id.warehouse_id", "=", self.warehouse_id.id),
                ("quantity", ">", 0),
            ]
        )
        existing_keys = {
            (l.product_id.id, l.location_id.id) for l in self.line_ids
        }
        new_lines = []
        for (product, location), qs in self._group_quants(quants):
            key = (product.id, location.id)
            if key in existing_keys:
                continue
            qty = sum(qs.mapped("quantity"))
            if float_is_zero(qty, precision_rounding=product.uom_id.rounding):
                continue
            prices = product.product_tmpl_id._l10n_ro_get_retail_prices(
                warehouse=self.warehouse_id, company=self.company_id
            )
            cost_unit = product.with_company(self.company_id).standard_price
            new_lines.append(
                Command.create(
                    {
                        "product_id": product.id,
                        "location_id": location.id,
                        "quantity": qty,
                        "cost_unit": cost_unit,
                        "old_price_with_vat": prices["price_with_vat"],
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
            seen.setdefault((q.product_id, q.location_id), q.browse([])).__iadd__
            seen[(q.product_id, q.location_id)] = seen.get(
                (q.product_id, q.location_id), q.browse([])
            ) | q
        return seen.items()

    def action_post(self):
        for doc in self:
            doc._post_one()
        return True

    def _post_one(self):
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Document %s is not in draft.", self.name))
        if not self.line_ids:
            raise UserError(_("No lines to post on %s.", self.name))
        if not self.journal_id:
            raise UserError(_("No journal defined."))
        self._update_pricelist()
        move = self._create_account_move()
        self.write(
            {
                "state": "done",
                "account_move_id": move.id if move else False,
            }
        )

    def _update_pricelist(self):
        """Write the new prices on the warehouse retail pricelist."""
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
            new_price_excl = line._compute_new_price_excl()
            vals = {
                "fixed_price": new_price_excl,
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
            stock_account = line._get_stock_account()
            if not stock_account:
                raise UserError(
                    _(
                        "Missing stock valuation account for product %s.",
                        line.product_id.display_name,
                    )
                )
            markup_account = line.location_id._l10n_ro_get_markup_account(
                product=line.product_id
            )
            deferred_vat_account = (
                line.location_id._l10n_ro_get_deferred_vat_account(
                    product=line.product_id
                )
            )
            if not markup_account or not deferred_vat_account:
                raise UserError(
                    _(
                        "Missing markup (378) or deferred VAT (4428) account "
                        "for product %(p)s at location %(l)s.",
                        p=line.product_id.display_name,
                        l=line.location_id.display_name,
                    )
                )
            markup_delta = currency.round(line.markup_diff_total)
            vat_delta = currency.round(line.vat_diff_total)
            ref = _("Price change %s", line.product_id.display_name)
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
                "ref": _(
                    "Proces verbal schimbare pret %s",
                    self.name,
                ),
                "line_ids": aml_vals,
            }
        )
        move._post()
        return move

    def action_cancel(self):
        for doc in self:
            if doc.state == "done" and doc.account_move_id:
                raise UserError(
                    _(
                        "Cancel the related journal entry %s first.",
                        doc.account_move_id.display_name,
                    )
                )
            doc.state = "cancel"

    def action_draft(self):
        for doc in self:
            if doc.account_move_id and doc.account_move_id.state == "posted":
                raise UserError(
                    _(
                        "Reverse the related journal entry %s first.",
                        doc.account_move_id.display_name,
                    )
                )
            doc.state = "draft"

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
    state = fields.Selection(related="document_id.state", store=False)
    product_id = fields.Many2one("product.product", required=True)
    location_id = fields.Many2one("stock.location", required=True)
    quantity = fields.Float(readonly=True)
    cost_unit = fields.Float(string="Cost / Unit", readonly=True)
    old_price_with_vat = fields.Float(
        string="Old PVA",
        readonly=True,
        help="Retail price including VAT at document creation.",
    )
    new_price_with_vat = fields.Float(
        string="New PVA",
        help="New retail price including VAT.",
    )
    old_markup_unit = fields.Float(
        compute="_compute_splits", string="Old Markup / Unit", store=True
    )
    old_vat_unit = fields.Float(
        compute="_compute_splits", string="Old VAT / Unit", store=True
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

    @api.depends(
        "old_price_with_vat",
        "new_price_with_vat",
        "cost_unit",
        "quantity",
        "product_id",
        "document_id.company_id",
    )
    def _compute_splits(self):
        for line in self:
            company = line.document_id.company_id or line.env.company
            taxes = line.product_id.taxes_id.filtered(
                lambda t: t.company_id == company
            )
            line.old_markup_unit, line.old_vat_unit = line._split(
                line.old_price_with_vat, taxes, company
            )
            line.new_markup_unit, line.new_vat_unit = line._split(
                line.new_price_with_vat, taxes, company
            )
            line.markup_diff_total = (
                line.new_markup_unit - line.old_markup_unit
            ) * line.quantity
            line.vat_diff_total = (
                line.new_vat_unit - line.old_vat_unit
            ) * line.quantity

    def _split(self, price_with_vat, taxes, company):
        """Return (markup_per_unit, vat_per_unit) given a PVA with VAT."""
        if not price_with_vat:
            return 0.0, 0.0
        if not taxes:
            return price_with_vat - self.cost_unit, 0.0
        tax_res = taxes.with_context(force_price_include=True).compute_all(
            price_with_vat,
            currency=company.currency_id,
            quantity=1.0,
            product=self.product_id,
        )
        price_without_vat = tax_res["total_excluded"]
        return (
            price_without_vat - self.cost_unit,
            price_with_vat - price_without_vat,
        )

    def _compute_new_price_excl(self):
        """Return the new price without VAT, to be written on the pricelist
        item ``fixed_price`` field."""
        self.ensure_one()
        company = self.document_id.company_id or self.env.company
        taxes = self.product_id.taxes_id.filtered(lambda t: t.company_id == company)
        if not taxes:
            return self.new_price_with_vat
        tax_res = taxes.with_context(force_price_include=True).compute_all(
            self.new_price_with_vat,
            currency=company.currency_id,
            quantity=1.0,
            product=self.product_id,
        )
        return tax_res["total_excluded"]

    def _get_stock_account(self):
        self.ensure_one()
        company = self.document_id.company_id or self.env.company
        loc_account = self.location_id.l10n_ro_property_stock_valuation_account_id
        if loc_account:
            return loc_account
        return (
            self.product_id.with_company(company)
            .l10n_ro_property_stock_valuation_account_id
            or self.product_id.categ_id.property_stock_valuation_account_id
        )

    def _aml_pair(self, stock_account, other_account, signed_amount, ref):
        """Debit/credit AML pair, picking storno on negatives."""
        self.ensure_one()
        currency = self.document_id.company_id.currency_id
        is_storno = signed_amount < 0
        abs_value = abs(signed_amount)
        debit_account = stock_account if signed_amount > 0 else other_account
        credit_account = other_account if signed_amount > 0 else stock_account
        base = {
            "name": ref,
            "product_id": self.product_id.id,
            "quantity": self.quantity,
            "is_storno": is_storno,
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
