import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo-addons-oca-l10n-romania",
    description="Meta package for oca-l10n-romania Odoo addons",
    version=version,
    install_requires=[
        'odoo-addon-l10n_ro_account_anaf_sync>=15.0dev,<15.1dev',
        'odoo-addon-l10n_ro_account_bank_statement_import_mt940_base>=15.0dev,<15.1dev',
        'odoo-addon-l10n_ro_account_bank_statement_report>=15.0dev,<15.1dev',
        'odoo-addon-l10n_ro_account_edi_ubl>=15.0dev,<15.1dev',
        'odoo-addon-l10n_ro_account_edit_currency_rate>=15.0dev,<15.1dev',
        'odoo-addon-l10n_ro_account_period_close>=15.0dev,<15.1dev',
        'odoo-addon-l10n_ro_account_report_invoice>=15.0dev,<15.1dev',
        'odoo-addon-l10n_ro_address_extended>=15.0dev,<15.1dev',
        'odoo-addon-l10n_ro_city>=15.0dev,<15.1dev',
        'odoo-addon-l10n_ro_config>=15.0dev,<15.1dev',
        'odoo-addon-l10n_ro_fiscal_validation>=15.0dev,<15.1dev',
        'odoo-addon-l10n_ro_nondeductible_vat>=15.0dev,<15.1dev',
        'odoo-addon-l10n_ro_partner_create_by_vat>=15.0dev,<15.1dev',
        'odoo-addon-l10n_ro_partner_unique>=15.0dev,<15.1dev',
        'odoo-addon-l10n_ro_payment_to_statement>=15.0dev,<15.1dev',
        'odoo-addon-l10n_ro_siruta>=15.0dev,<15.1dev',
        'odoo-addon-l10n_ro_stock>=15.0dev,<15.1dev',
        'odoo-addon-l10n_ro_stock_account>=15.0dev,<15.1dev',
        'odoo-addon-l10n_ro_stock_account_date>=15.0dev,<15.1dev',
        'odoo-addon-l10n_ro_stock_account_date_wizard>=15.0dev,<15.1dev',
        'odoo-addon-l10n_ro_stock_account_notice>=15.0dev,<15.1dev',
        'odoo-addon-l10n_ro_stock_picking_valued_report>=15.0dev,<15.1dev',
        'odoo-addon-l10n_ro_stock_price_difference>=15.0dev,<15.1dev',
        'odoo-addon-l10n_ro_stock_report>=15.0dev,<15.1dev',
        'odoo-addon-l10n_ro_vat_on_payment>=15.0dev,<15.1dev',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 15.0',
    ]
)
