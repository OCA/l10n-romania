==========================
Romania - DVI -
==========================
.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3


DVI - declaraţie vamala de import

Se face legatura dintre factura de achizitie si DVI (landed cost)

Se genereaza automat un DVI cu doua linii si cu TVA.


Contul 447 trebuie sa fie un cont de reconciliere pentru a se putea inchide prin banca


Installation
============

To install this module, you need to:

* clone the branch 14.0 of the repository https://github.com/OCA/l10n-romania
* add the path to this repository in your configuration (addons-path)
* update the module list
* search for "Romania - DVI" in your addons
* install the module




Usage
=====

DVI = Declaraţie Vamala de Import

DVI-ul a fost implementat ca Landed Cost.

At install is creating with check in product puchase tab under is_landed_cost:
 - a product (Romanian Custom Commision) with expense account 446.., and a vat tax of type purchase that contains "deductibil 19%"
 - a product Romanian Customs commision
This products and tax will be used in created journal entry.

a. Pe factura exista buton Create DVI, view DVI.

b. Buttonul de Landed costs vede toate landed cost inclusiv dvi, butonul de view dvi vede doar landed cost tip dvi

c. Pentru anulare/modfificare dvi se instaleaza l10n_ro_landed_cost_dvi_revert

d. In fereastra de creere dvi si cea de landed cost apare si Custom Duty tax. If is set, the value will apear in d394 at tva base

# the vat tva fields are not taken into consideration with their value; dvi will be put in this reports
# from vat_id we take only the account
    24.1 - BAZA - Achiziţii de bunuri şi servicii taxabile cu cota de 19%, altele decat cele de la rd.27
and
     24.1 - TVA - Achiziţii de bunuri şi servicii taxabile cu cota de 19%, altele decat cele de la rd.27
    # I think that this must be taken from selected vat, but in future version if is required by someone
    tag_custom = self.env['account.account.tag'].search([('name','=','+24_1 - TVA')])
    tag_custom_base = self.env['account.account.tag'].search([('name','=','+24_1 - BAZA')])




Known issues / Roadmap
======================


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

* NextERP Romania SRL
* Dorin Hongu <dhongu@gmail.com>

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
