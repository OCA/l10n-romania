.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License: AGPL-3

Romania - VAT on Payment
========================

This module allows you to check partners (companies) that applies
VAT on Payment behaviour. It extends standard VAT on payment module
available in https://github.com/OCA/account-payment repo, adding
the check in supplier invoices of the partner behaviour.

Installation
============

To install this module, you need to:

* clone the branch 8.0 of the repository https://github.com/OCA/l10n-romania
* add the path to this repository in your configuration (addons-path)
* update the module list
* search for "Romania - VAT on Payment" in your addons
* install the module

Usage
=====

On the partner accounting page you will have a new field called "VAT on Payment" and a new button, called "Update VAT on Payment", available only on companies (is_company field set to True).
Pushing the button will search in the ANAF datas for records assigned to the partner's VAT number and linked them to it.

On invoices, you have:

* A new field, "Is a fiscal Receipt", for mark the invoices appropriate.
* A new method, about checking if the partner applies VAT on Payment at the invoice date. The method is available for invoices:

* without Fiscal Position.
* with National Fiscal Position.
* "Is a fiscal Receipt" field not checked.

Two daily crons are set up, one for downloading the ANAF datas, one for checking the Romanian partners for VAT on Payment.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/177/8.0

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/l10n-romania/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed feedback
`here <https://github.com/OCA/l10n-romania/issues/new?body=module:%20l10n_ro_vat_on_payment%0Aversion:%208.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.

Credits
=======

Contributors
------------

* Fekete Mihai <feketemihai@gmail.com>
* Dorin Hongu <dhongu@gmail.com>
* Adrian Vasile <adrian.vasile@gmail.com>

Maintainer
----------

.. image:: http://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: http://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit http://odoo-community.org.
