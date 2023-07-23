import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo-addons-oca-l10n-romania",
    description="Meta package for oca-l10n-romania Odoo addons",
    version=version,
    install_requires=[
        'odoo-addon-l10n_ro_account_bank_statement_report>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_account_edit_currency_rate>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_account_report_invoice>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_city>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_config>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_fiscal_validation>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_partner_create_by_vat>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_partner_unique>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_stock>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_stock_account>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_stock_account_date>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_stock_account_date_wizard>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_stock_report>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_vat_on_payment>=16.0dev,<16.1dev',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 16.0',
    ]
)
