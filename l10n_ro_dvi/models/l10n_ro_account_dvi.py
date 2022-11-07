# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountInvoiceDVI(models.Model):
    _name = "l10n.ro.account.dvi"
    _description = "Create DVI for invoices"

    name = fields.Char(required=True)
    date = fields.Date("Date", required=True)

    state = fields.Selection(
        string="Status",
        selection=[("draft", "Draft"), ("posted", "Posted"), ("reversed", "Reversed")],
        copy=False,
        index=True,
        readonly=True,
        tracking=True,
        default="draft",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )

    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        required=True,
        readonly=True,
        domain="[('type', '=', 'general')]",
        states={"draft": [("readonly", False)]},
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id",
        readonly=True,
        store=True,
        help="Utility field to express amount currency",
    )
    tax_id = fields.Many2one(
        "account.tax",
        required=True,
        domain="[('type_tax_use', '=', 'purchase')]",
        help="Is the vat that is paid in custom for products."
        " default is taken from custom duty tax"
        ". will put this vat tag in journal entry to find it in reports",
    )
    line_ids = fields.One2many(
        "l10n.ro.account.dvi.line",
        "dvi_id",
        string="DVI Lines",
        copy=False,
        readonly=False,
        states={"done": [("readonly", True)]},
    )
    total_base_tax_value = fields.Monetary(
        compute="_compute_total_tax_value",
        readonly=1,
        help="Is readonly sum of product tax and custom tax."
        "This must be the tax value that you have on dvi",
    )
    total_tax_value = fields.Monetary(
        compute="_compute_total_tax_value",
        readonly=1,
        help="Is readonly sum of product tax and custom tax."
        "This must be the tax value that you have on dvi",
    )

    customs_duty_product_id = fields.Many2one(
        "product.product",
        required=True,
        help="A product type service with l10n_ro_custom_duty checked"
        " (purchase tab).  Journal entry for duty will be with this product &"
        " default vat for custom duty and invoice - to find it in declaration based on tags",
    )
    customs_duty_value = fields.Monetary(help="This is a value from received dvi")
    customs_duty_tax_value = fields.Monetary(
        readonly=1,
        compute="_compute_total_tax_value",
        help="readonly computed tax from custom_duty_value",
    )

    customs_commision_product_id = fields.Many2one(
        "product.product",
        required=True,
        help="Product type service with l10n_ro_custom_commision checed "
        "(in purchase tab). Journal entry for commision will be with this product",
    )
    customs_commission_value = fields.Monetary(help="taken from dvi if exists")

    invoice_ids = fields.Many2many(
        "account.move",
        string="Invoices",
        required=True,
        domain=[("move_type", "in", ["in_invoice", "in_refund"])],
    )
    invoice_base_value = fields.Monetary(
        compute="_compute_amount", help="Invoices value without taxes"
    )
    invoice_tax_value = fields.Monetary(
        compute="_compute_amount",
        help="default is computed as tax_id from product;"
        " is not recomputed based on selected vat",
    )

    landed_cost_ids = fields.One2many(
        "stock.landed.cost", "l10n_ro_account_dvi_id", readonly=True
    )

    @api.model
    def default_get(self, fields_list):
        defaults = super(AccountInvoiceDVI, self).default_get(fields_list)
        defaults["date"] = fields.Date.today()
        if "company_id" not in defaults:
            defaults["company_id"] = self.env.company
        domain = [
            ("type", "=", "general"),
            ("company_id", "=", self.env.company.id),
        ]
        defaults["journal_id"] = self.env["account.journal"].search(domain, limit=1)
        customs_duty_product = (
            self.env.company._l10n_ro_get_or_create_custom_duty_product()
        )
        customs_commission_product = (
            self.env.company._l10n_ro_get_or_create_customs_commission_product()
        )
        defaults["customs_duty_product_id"] = customs_duty_product.id
        defaults["customs_commision_product_id"] = customs_commission_product.id
        return defaults

    def action_view_landed_costs(self):
        self.ensure_one()
        if not self.landed_cost_ids:
            raise ValidationError(
                _("You do not have created landed costs for this DVI")
            )
        action = self.env.ref("stock_landed_costs.action_stock_landed_cost")
        action = action.sudo().read()[0]
        action["domain"] = [("id", "in", self.landed_cost_ids.ids)]
        return action

    @api.depends(
        "invoice_base_value", "invoice_tax_value", "tax_id", "customs_duty_value"
    )
    def _compute_total_tax_value(self):
        for rec in self:
            if rec.customs_duty_value and rec.tax_id:
                tax_values = rec.tax_id.compute_all(rec.customs_duty_value)
                rec.customs_duty_tax_value = (
                    tax_values["total_included"] - tax_values["total_excluded"]
                )
            else:
                rec.customs_duty_tax_value = 0
            rec.total_base_tax_value = rec.invoice_base_value + rec.customs_duty_value
            rec.total_tax_value = rec.invoice_tax_value + rec.customs_duty_tax_value

    @api.depends("line_ids.base_amount", "line_ids.vat_amount")
    def _compute_amount(self):
        for dvi in self:
            dvi.invoice_base_value = sum(line.base_amount for line in dvi.line_ids)
            dvi.invoice_tax_value = sum(line.vat_amount for line in dvi.line_ids)

    def write(self, vals):
        res = super().write(vals)
        if vals.get("invoice_ids"):
            for dvi in self:
                new_lines = []
                if dvi.line_ids:
                    dvi.line_ids.unlink()
                for invoice in dvi.invoice_ids:
                    invoice_lines = invoice.invoice_line_ids.filtered(
                        lambda line: not line.display_type
                        and (
                            line.product_id.type == "product"
                            or line.is_landed_costs_line is True
                        )
                    )
                    for inv_line in invoice_lines:
                        new_lines.append(
                            (
                                0,
                                0,
                                {
                                    "dvi_id": dvi.id,
                                    "invoice_id": invoice.id,
                                    "invoice_line_id": inv_line.id,
                                },
                            )
                        )
                dvi.line_ids = new_lines
        return res

    @api.model
    def create(self, vals):
        dvi = super().create(vals)
        if vals.get("invoice_ids"):
            new_lines = []
            if dvi.line_ids:
                dvi.line_ids.unlink()
            for invoice in dvi.invoice_ids:
                invoice_lines = invoice.invoice_line_ids.filtered(
                    lambda line: not line.display_type
                    and (
                        line.product_id.type == "product"
                        or line.is_landed_costs_line is True
                    )
                )
                for inv_line in invoice_lines:
                    new_lines.append(
                        (
                            0,
                            0,
                            {
                                "dvi_id": dvi.id,
                                "invoice_id": invoice.id,
                                "invoice_line_id": inv_line.id,
                            },
                        )
                    )
            dvi.line_ids = new_lines
        return dvi

    def button_post(self):
        self.ensure_one()
        if self.state != "draft":
            raise ValidationError(_("You can only post DVI from 'draft' state."))

        values = self.prepare_dvi_landed_cost_values()
        landed_cost = self.env["stock.landed.cost"].create(values)
        action = self.env.ref("stock_landed_costs.action_stock_landed_cost")
        action = action.read()[0]

        action["views"] = [(False, "form")]
        action["res_id"] = landed_cost.id
        self.state = "posted"
        return action

    def button_reverse(self):
        self.ensure_one()
        if self.state != "posted":
            raise UserError(_("Only Posted DVI can be reversed."))
        for lc in self.landed_cost_ids:
            if lc.account_move_id:
                if lc.account_move_id.state == "posted":
                    lc.account_move_id.button_draft()
                if lc.account_move_id.state == "draft":
                    lc.account_move_id.button_cancel()

        values = self.prepare_dvi_landed_cost_values()
        values["l10n_ro_base_tax_value"] = -1 * values["l10n_ro_base_tax_value"]
        values["l10n_ro_tax_value"] = -1 * values["l10n_ro_tax_value"]
        for line in values.get("cost_lines"):
            line_vals = line[2]
            line_vals["price_unit"] = -1 * line_vals["price_unit"]
        landed_cost = self.env["stock.landed.cost"].create(values)
        landed_cost.with_context(dvi_revert=True).button_validate()
        action = self.env.ref("stock_landed_costs.action_stock_landed_cost")
        action = action.read()[0]

        action["views"] = [(False, "form")]
        action["res_id"] = landed_cost.id
        self.state = "reversed"
        return action

    def prepare_dvi_landed_cost_values(self):
        values = self.prepare_dvi_landed_cost_vals()
        if self.customs_duty_value:
            product = self.customs_duty_product_id
            accounts_data = product.product_tmpl_id.get_product_accounts()
            values["cost_lines"] += self.prepare_dvi_landed_cost_lines(
                product, self.customs_duty_value, accounts_data
            )

        if self.customs_commission_value:
            product = self.customs_commision_product_id
            accounts_data = (
                self.customs_commision_product_id.product_tmpl_id.get_product_accounts()
            )
            values["cost_lines"] += self.prepare_dvi_landed_cost_lines(
                product, self.customs_commission_value, accounts_data
            )
        return values

    def prepare_dvi_landed_cost_vals(self):
        pickings = self.env["stock.picking"]

        for line in self.line_ids:
            pickings |= (
                line.invoice_line_id.purchase_line_id.order_id.picking_ids.filtered(
                    lambda p: p.state == "done"
                )
            )
        return {
            "date": self.date,
            "l10n_ro_cost_type": "dvi",
            "picking_ids": [(6, 0, pickings.ids)],
            "cost_lines": [],
            "account_journal_id": self.journal_id.id,
            "l10n_ro_tax_id": self.tax_id.id,
            "l10n_ro_base_tax_value": self.total_base_tax_value,
            "l10n_ro_tax_value": self.total_tax_value,
            "l10n_ro_account_dvi_id": self.id,
            "l10n_ro_dvi_bill_ids": self.invoice_ids,
        }

    def prepare_dvi_landed_cost_lines(self, product, value, accounts_data):
        return [
            (
                0,
                0,
                {
                    "name": product.name,
                    "product_id": product.id,
                    "price_unit": value,
                    "split_method": "by_current_cost_price",
                    "account_id": accounts_data["expense"].id,
                },
            )
        ]


class AccountDVILine(models.Model):
    _name = "l10n.ro.account.dvi.line"
    _description = "DVI Lines"

    dvi_id = fields.Many2one(
        "l10n.ro.account.dvi",
        string="DVI Ref",
        ondelete="cascade",
        required=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company", string="Company", related="dvi_id.company_id", store=True
    )
    currency_id = fields.Many2one("res.currency", related="dvi_id.currency_id")
    tax_id = fields.Many2one("account.tax", related="dvi_id.tax_id")
    invoice_id = fields.Many2one(
        "account.move",
        string="DVI Invoice",
        copy=False,
        readonly=True,
        check_company=True,
        index=True,
    )
    invoice_line_id = fields.Many2one(
        "account.move.line",
        "Invoice Line",
        copy=False,
        readonly=True,
        check_company=True,
    )
    name = fields.Char(related="invoice_line_id.name", readonly=True)
    product_id = fields.Many2one(related="invoice_line_id.product_id", readonly=True)
    product_uom_id = fields.Many2one(
        related="invoice_line_id.product_uom_id", readonly=True
    )
    price_unit = fields.Float(related="invoice_line_id.price_unit", readonly=True)
    qty = fields.Float(related="invoice_line_id.quantity", readonly=True)
    price_subtotal = fields.Monetary(related="invoice_line_id.balance", readonly=True)
    line_qty = fields.Float(
        string="DVI Quantity",
        default=1.0,
        digits="Product Unit of Measure",
        help="The quantity declared in the DVI.",
    )
    base_amount = fields.Float(string="Base Amount", compute="_compute_base_vat_amount")
    vat_amount = fields.Float(string="VAT Amount", compute="_compute_base_vat_amount")

    @api.depends("line_qty")
    def _compute_base_vat_amount(self):
        for line in self:
            base_amount = vat_amount = 0
            if line.qty:
                base_amount = line.line_qty / line.qty * line.price_subtotal
                tax_values = line.dvi_id.tax_id.compute_all(base_amount)
                vat_amount = tax_values["total_included"] - tax_values["total_excluded"]
            line.base_amount = base_amount
            line.vat_amount = vat_amount
