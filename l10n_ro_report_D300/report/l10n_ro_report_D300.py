# Copyright  2018 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class RomaniaReportD300(models.TransientModel):
    _name = "l10n_ro_report_d300"
    """ Here, we just define class fields.
    For methods, go more bottom at this file.

    The class hierarchy is :
    * RomaniaReportD300
    ** RomaniaReportD300TaxTags
    *** RomaniaReportD300Tax
    """

    # Filters fields, used for data computation
    company_id = fields.Many2one(comodel_name='res.company')
    date_from = fields.Date()
    date_to = fields.Date()
    tax_detail = fields.Boolean('Tax Detail')

    # Data fields, used to browse report data
    taxtags_ids = fields.One2many(
        comodel_name='l10n_ro_report_d300_taxtag',
        inverse_name='report_id'
    )


class RomaniaReportD300TaxTag(models.TransientModel):
    _name = 'l10n_ro_report_d300_taxtag'
    _order = 'code ASC'

    @api.multi
    def _compute_move_lines(self):
        ml_object = self.env['account.move.line']
        for tag in self:
            lines = []
            report = tag.report_id
            if report:
                taxes = tag.tax_ids.mapped('tax_id').ids
                domain = [
                    ('tax_line_id', 'in', taxes),
                    ('tax_exigible', '=', True),
                    ('date', '<=', report.date_to),
                    ('date', '>=', report.date_from)
                ]
                lines = ml_object.search(domain)
            tag.move_line_ids = lines if lines else []

    report_id = fields.Many2one(
        comodel_name='l10n_ro_report_d300',
        ondelete='cascade',
        index=True
    )

    # Data fields, used to keep link with real object
    taxtag_id = fields.Many2one(
        'account.account.tag',
        index=True
    )

    # Data fields, used for report display
    code = fields.Integer()
    name = fields.Char()
    net = fields.Float(digits=(16, 2))
    tax = fields.Float(digits=(16, 2))

    # Data fields, used to browse report data
    tax_ids = fields.One2many(
        comodel_name='l10n_ro_report_d300_tax',
        inverse_name='report_tax_id'
    )

    move_line_ids = fields.One2many(
        comodel_name='account.move.line',
        compute='_compute_move_lines'
    )


class RomaniaReportD300Tax(models.TransientModel):
    _name = 'l10n_ro_report_d300_tax'
    _order = 'name ASC'

    report_tax_id = fields.Many2one(
        comodel_name='l10n_ro_report_d300_taxtag',
        ondelete='cascade',
        index=True
    )

    # Data fields, used to keep link with real object
    tax_id = fields.Many2one(
        'account.tax',
        index=True
    )

    # Data fields, used for report display
    code = fields.Char()
    name = fields.Char()
    net = fields.Float(digits=(16, 2))
    tax = fields.Float(digits=(16, 2))

    @api.multi
    def _compute_move_lines(self):
        ml_object = self.env['account.move.line']
        for tax in self:
            lines = []
            report = tax.report_tax_id.report_id
            if report:
                domain = [
                    ('tax_line_id', '=', tax.tax_id.id),
                    ('tax_exigible', '=', True),
                    ('date', '<=', report.date_to),
                    ('date', '>=', report.date_from)
                ]
                lines = ml_object.search(domain)
            tax.move_line_ids = lines if lines else []

    move_line_ids = fields.One2many(
        comodel_name='account.move.line',
        inverse_name='tax_line_id',
        compute='_compute_move_lines'
    )


class RomaniaReportD300Compute(models.TransientModel):
    """ Here, we just define methods.
    For class fields, go more top at this file.
    """

    _inherit = 'l10n_ro_report_d300'

    @api.multi
    def print_report(self, report_type='qweb'):
        self.ensure_one()
        if report_type == 'xlsx':
            report_name = 'l10n_ro_report_d300_xlsx'
        else:
            report_name = 'l10n_ro_report_D300.l10n_ro_report_d300_qweb'
        context = dict(self.env.context)
        action = self.env['ir.actions.report'].search(
            [('report_name', '=', report_name),
             ('report_type', '=', report_type)], limit=1)
        return action.with_context(context).report_action(self)

    def _get_html(self):
        result = {}
        rcontext = {}
        context = dict(self.env.context)
        report = self.browse(context.get('active_id'))
        if report:
            rcontext['o'] = report
            result['html'] = self.env.ref(
                'l10n_ro_report_D300.l10n_ro_report_d300').render(
                    rcontext)
        return result

    @api.model
    def get_html(self, given_context=None):
        return self.with_context(given_context)._get_html()

    @api.multi
    def compute_data_for_report(self):
        self.ensure_one()
        # Compute report data
        self._inject_taxtags_values()
        self._inject_tax_values()
        # Refresh cache because all data are computed with SQL requests
        self.refresh()

    def _inject_taxtags_values(self):
        """Inject report values for report_open_items_account."""
        query_inject_taxtags = """
WITH
    taxtags AS
        (SELECT coalesce(regexp_replace(replace(tag.name, 'D300', ''),
                '[^0-9\\.]+', '', 'g')::numeric * 10, 0)::integer AS code,
                tag.name, tag.id,
                abs(coalesce(sum(movetax.tax_base_amount), 0.00)) AS net,
                abs(coalesce(sum(movetax.balance), 0.00)) AS tax
            FROM
                account_account_tag AS tag
                INNER JOIN account_tax_account_tag AS taxtag
                    ON tag.id = taxtag.account_account_tag_id
                INNER JOIN account_tax AS tax
                    ON tax.id = taxtag.account_tax_id
                INNER JOIN account_move_line AS movetax
                    ON movetax.tax_line_id = tax.id
                INNER JOIN account_move AS move
                    ON move.id = movetax.move_id
            WHERE tag.id is not null AND movetax.tax_exigible
                AND move.company_id = %s AND move.date >= %s
                    AND move.date <= %s AND move.state = 'posted'
            GROUP BY tag.id
            ORDER BY code, tag.name
        )
INSERT INTO
    l10n_ro_report_d300_taxtag
    (
    report_id,
    create_uid,
    create_date,
    taxtag_id,
    code,
    name,
    net, tax
    )
SELECT
    %s AS report_id,
    %s AS create_uid,
    NOW() AS create_date,
    tag.id,
    tag.code,
    tag.name,
    tag.net,
    tag.tax
FROM
    taxtags tag
        """
        query_inject_taxtags_params = (self.company_id.id, self.date_from,
                                       self.date_to, self.id, self.env.uid)
        self.env.cr.execute(query_inject_taxtags, query_inject_taxtags_params)

    def _inject_tax_values(self):
        """ Inject report values for report_open_items_partner. """
        # pylint: disable=sql-injection
        query_inject_tax = """
WITH
    taxtags_tax AS
        (
            SELECT
                tag.id AS report_tax_id, '' AS code,
                tax.name, tax.id,
                abs(coalesce(sum(movetax.tax_base_amount), 0.00)) AS net,
                abs(coalesce(sum(movetax.balance), 0.00)) AS tax
            FROM
                l10n_ro_report_d300_taxtag AS tag
                INNER JOIN account_tax_account_tag AS taxtag
                    ON tag.taxtag_id = taxtag.account_account_tag_id
                INNER JOIN account_tax AS tax
                    ON tax.id = taxtag.account_tax_id
                INNER JOIN account_move_line AS movetax
                    ON movetax.tax_line_id = tax.id
                INNER JOIN account_move AS move
                    ON move.id = movetax.move_id
            WHERE tag.id is not null AND movetax.tax_exigible
                AND tag.report_id = %s AND move.company_id = %s
                AND move.date >= %s AND move.date <= %s
                AND move.state = 'posted'
            GROUP BY tag.id, tax.id
            ORDER BY tax.name
        )
INSERT INTO
    l10n_ro_report_d300_tax
    (
    report_tax_id,
    create_uid,
    create_date,
    tax_id,
    name,
    net,
    tax
    )
SELECT
    tt.report_tax_id,
    %s AS create_uid,
    NOW() AS create_date,
    tt.id,
    tt.name,
    tt.net,
    tt.tax
FROM
    taxtags_tax tt
        """
        query_inject_tax_params = (self.id, self.company_id.id, self.date_from,
                                   self.date_to, self.env.uid)
        self.env.cr.execute(query_inject_tax, query_inject_tax_params)
