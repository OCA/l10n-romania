# Copyright 2022 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models
from odoo.tools.safe_eval import safe_eval


class CommentTemplate(models.AbstractModel):
    _inherit = "comment.template"

    def _compute_comment_template_ids(self):
        super()._compute_comment_template_ids()
        for record in self.filtered(lambda r: not r.comment_template_ids):
            templates = self.env["base.comment.template"].search(
                [
                    ("partner_ids", "=", False),
                    ("model_ids.model", "=", self._name),
                ]
            )
            for template in templates:
                domain = safe_eval(template.domain)
                if not domain or record.filtered_domain(domain):
                    record.comment_template_ids = [(4, template.id)]
