import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo14-addons-oca-l10n-romania",
    description="Meta package for oca-l10n-romania Odoo addons",
    version=version,
    install_requires=[
        'odoo14-addon-currency_rate_update_RO_BNR',
        'odoo14-addon-l10n_ro_account_edit_currency_rate',
        'odoo14-addon-l10n_ro_account_period_close',
        'odoo14-addon-l10n_ro_account_report_invoice',
        'odoo14-addon-l10n_ro_address_extended',
        'odoo14-addon-l10n_ro_city',
        'odoo14-addon-l10n_ro_config',
        'odoo14-addon-l10n_ro_fiscal_validation',
        'odoo14-addon-l10n_ro_nondeductible_vat',
        'odoo14-addon-l10n_ro_partner_create_by_vat',
        'odoo14-addon-l10n_ro_partner_unique',
        'odoo14-addon-l10n_ro_payment_receipt_report',
        'odoo14-addon-l10n_ro_payment_to_statement',
        'odoo14-addon-l10n_ro_siruta',
        'odoo14-addon-l10n_ro_stock',
        'odoo14-addon-l10n_ro_stock_account',
        'odoo14-addon-l10n_ro_stock_account_date',
        'odoo14-addon-l10n_ro_stock_account_date_wizard',
        'odoo14-addon-l10n_ro_stock_account_notice',
        'odoo14-addon-l10n_ro_stock_picking_comment_template',
        'odoo14-addon-l10n_ro_stock_price_difference',
        'odoo14-addon-l10n_ro_stock_report',
        'odoo14-addon-l10n_ro_vat_on_payment',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 14.0',
    ]
)
