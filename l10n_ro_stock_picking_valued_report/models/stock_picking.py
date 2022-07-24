# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"


    currency_id = fields.Many2one(
        # related="sale_id.currency_id",
        "res.currency",
        compute="_compute_amount_all",
        string="Currency",
        compute_sudo=True,  # See explanation for sudo in compute method,
    )
    amount_untaxed = fields.Monetary(
        compute="_compute_amount_all",
        string="Untaxed Amount",
        compute_sudo=True,  # See explanation for sudo in compute method,
        currency_field="currency_id",
    )
    amount_tax = fields.Monetary(
        compute="_compute_amount_all",
        string="Taxes",
        compute_sudo=True,
        currency_field="currency_id",
    )
    amount_total = fields.Monetary(
        compute="_compute_amount_all",
        string="Total",
        compute_sudo=True,
        currency_field="currency_id",
    )
    is_internal_consumption = fields.Boolean(compute="_compute_is_internal_consumption")
    total_internal_consumption = fields.Float(
        compute="_compute_total_internal_consumption"
    )

    def _compute_total_internal_consumption(self):
        for pick in self:
            pick.total_internal_consumption = sum(
                [mvl.subtotal_internal_consumption for mvl in pick.move_line_ids]
            )

    def _compute_is_internal_consumption(self):
        for pick in self:
            pick.is_internal_consumption = pick.move_lines and (
                pick.move_lines[0]._is_internal_transfer()
                or pick.move_lines[0]._is_consumption()
                or pick.move_lines[0]._is_consumption_return()
                or pick.move_lines[0]._is_usage_giving()
                or pick.move_lines[0]._is_usage_giving_return()
            )

    @api.onchange("delegate_id")
    def on_change_delegate_id(self):
        if self.delegate_id:
            self.mean_transp = self.delegate_id.mean_transp

    def write(self, vals):
        "if modified the mean_transp will write into delegate"
        mean_transp = vals.get("mean_transp", False)
        delegate_id = vals.get("delegate_id", False)
        if mean_transp and delegate_id:
            if (
                mean_transp
                != self.env["res.partner"].sudo().browse(delegate_id).mean_transp
            ):
                self.env["res.partner"].sudo().browse(delegate_id).write(
                    {"mean_transp": mean_transp}
                )
        return super().write(vals)

    def _compute_amount_all(self):
        """overwrite of function from stock_picking to take into account also the purchase
        This is computed with sudo for avoiding problems if you don't have
        access to sales orders (stricter warehouse users, inter-company
        records...).
        """
        for pick in self:
            installed = (
                self.env["ir.module.module"]
                .sudo()
                .search(
                    [
                        ("name", "=", "stock_picking_report_valued"),
                        ("state", "=", "installed"),
                    ]
                )
            )
            if installed and "sale_id" in self._fields and pick.sale_id:
                super(StockPicking, pick)._compute_amount_all()
            elif pick.purchase_id:
                currency = (
                    pick.purchase_id.currency_id
                    if pick.purchase_id
                    else pick.company_id.currency_id
                )
                amount_tax = 0.0
                for tax_group in pick.get_taxes_values_purchase().values():
                    amount_tax += currency.round(tax_group["amount"])
                amount_untaxed = sum(
                    [
                        move_line.purchase_price_subtotal
                        for move_line in pick.move_line_ids
                    ]
                )
                pick.update(
                    {
                        "currency_id": currency.id,
                        "amount_untaxed": amount_untaxed,
                        "amount_tax": amount_tax,
                        "amount_total": amount_untaxed + amount_tax,
                    }
                )
            else:
                currency = pick.company_id.currency_id
                pick.update(
                    {
                        "currency_id": currency.id,
                        "amount_untaxed": 0.0,
                        "amount_tax": 0.0,
                        "amount_total": 0.0,
                    }
                )


    def get_taxes_values_purchase(self):
        tax_grouped = {}
        for line in self.move_line_ids:
            for tax in line.purchase_line.taxes_id:
                tax_id = tax.id
                if tax_id not in tax_grouped:
                    tax_grouped[tax_id] = {
                        "base": line.purchase_price_subtotal,
                        "tax": tax,
                    }
                else:
                    tax_grouped[tax_id]["base"] += line.purchase_price_subtotal
        for tax_id, tax_group in tax_grouped.items():
            tax_grouped[tax_id]["amount"] = 0.00
            tax_compute = tax_group["tax"].compute_all(
                tax_group["base"], self.purchase_id.currency_id
            )["taxes"]
            tax_grouped[tax_id]["amount"] = sum(tax["amount"] for tax in tax_compute)
        return tax_grouped

    # this function if from base_comment_template original made by
    # nexterp but was removed, and also position is now selection
    def get_comment_template(
        self, position="before_lines", company_id=False, partner_id=False
    ):
        """Method that is called from report xml and is returning the
        position template as a html if exists
        """
        self.ensure_one()
        if not company_id:
            company_id = self.env.company.id
        present_model_id = self.env["ir.model"].search([("model", "=", self._name)])
        default_dom = [
            ("model_ids", "in", present_model_id.id),
            ("position", "=", position),
        ]
        lang = False
        if self.picking_type_code != "outgoing":
            lang = self.env.user.lang
        elif partner_id and "partner_id" in self._fields:
            default_dom += [
                "|",
                ("partner_ids", "=", False),
                ("partner_ids", "in", partner_id),
            ]
            lang = self.env["res.partner"].browse(partner_id).lang
        if company_id and "company_id" in self._fields:
            if partner_id and "partner_id" in self._fields:
                default_dom.insert(-3, "&")
            default_dom += [
                "|",
                ("company_id", "=", company_id),
                ("company_id", "=", False),
            ]
        templates = self.env["base.comment.template"].search(
            default_dom,
        )
        if lang:
            templates = templates.with_context({"lang": lang})
        template = False
        if templates:
            for templ in templates:
                if self.filtered_domain(safe_eval(templ.domain or "[]")):
                    template = templ
                    break
        if not template:
            return ""
        ret = self.env["mail.template"]._render_template(
            template.text, self._name, [self.id], post_process=True
        )
        if ret[self.id] == "" and template.text:
            _logger.error(
                f"some error in rendering jinja template_id={template.id} "
                f"rendered object={self}. View template syntax and "
                f"if exist those parameters"
            )
        return ret[self.id]
