.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

Romania - VAT on Payment
========================

This module allows you to check partners (companies) that applies
VAT on Payment. It extends standard cash basis behaviour to allow 
configure ax base account for cash basis (taken from Odoo v12.0).

Installation
============

To install this module, you need to:

* clone the branch 11.0 of the repository https://github.com/OCA/l10n-romania
* add the path to this repository in your configuration (addons-path)
* update the module list
* search for "Romania - VAT on Payment" in your addons
* install the module

Usage
=====

On the partner accounting page you will have a new field called 
"VAT on Payment" and a new button, called "Update VAT on Payment", 
available only on companies (is_company field set to True).
Pushing the button will search in the ANAF datas for records assigned 
to the partner's VAT number and linked them to it.

On invoices it will check for Vat on payment on company / supplier 
and change the fiscal position with the "VAT on Payment" one, declared 
in l10n_ro module.

Two daily crons are set up, one for downloading the ANAF datas, 
one for checking the Romanian partners for VAT on Payment.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/177/11.0

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/l10n-romania/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smash it by providing detailed and welcomed feedback.

Credits
=======

Images
------

* Odoo Community Association: `Icon <https://odoo-community.org/logo.png>`_.

Contributors
------------

* Fekete Mihai <feketemihai@gmail.com>
* Dorin Hongu <dhongu@gmail.com>
* Adrian Vasile <adrian.vasile@gmail.com>

Do not contact contributors directly about support or help with technical issues.

Maintainer
----------

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit https://odoo-community.org.
