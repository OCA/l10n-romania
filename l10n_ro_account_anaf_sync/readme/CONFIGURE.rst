1. Go to https://pfinternet.anaf.ro/my.policy put put your username and password and code that came on email (or create a new user if you do not have)

2. Go to "Editare profil Oauth"

3. At profile Oauth

   - put some text at "Denumire Aplicatie"
   - at callback URL 1 put your Odoo instance url: /l10n_ro_account_anaf_sync/anaf_oauth
   - (if you odoo site is https://odoo.zzz.ro you must put https://odoo.zzz.ro/l10n_ro_account_anaf_sync/anaf_oauth url shown also in odoo company e-invoice tab)
   - at Serviciu check e-factura and/or e-transport
   - press Generare Client ID

4. Copy the Client ID and Client Secret.

5. Go to Odoo instance and from Settings -> Romania -> Configure ANAF sync create a new record for each company that you have access on ANAF website.

6. From a computer that can connect to anaf.ro and login with digital signature.

    With the usb Token inserted press in Odoo the button Get Token from Anaf.
    It will ask you for usb token pin.
    You will get a error or a token and a new valability date
    If the ANAF website is not asking for a pin you must open and close your browser to ask you again the signature token pin

7. If you do not have errors press the test button and all should be ok.

8. The access token can be used also to test in other ways like

.. code-block:: shell

    > curl "https://api.anaf.ro/TestOauth/jaxrs/hello?name=bbb" -H "Authorization: Bearer a010f5e7dd3e44d114d73729419bd1b9968b92fe2015f0512dcZZZZZZZZ" -i Future

Info:

  https://www.anaf.ro/anaf/internet/ANAF/servicii_online/servicii_web_anaf/!ut/p/a1/hY9NC4JAEIZ_SwevzqRp1k2h3CQojUj3Eiv4FbYrq-nfT8NDRNncZnge3nmBQgiUs7bIWFMIzsphp-aVzIlJNEvzMNAt9A1nu3FWJ3QPyx6IegB_jI0fPvFx8HeB4R4R3cXoTwB_8i9AJyPQHIGJFz2gWSniV93I5rFuZUBlkiYykepD9ue8aap6raCCXdepjLNUlULBb3wu6gbCNwyq-znEm1G2e3v2BHB2faQ!/dl5/d5/L2dBISEvZ0FBIS9nQSEh/

  https://mfinante.gov.ro/web/efactura/informatii-tehnice

  https://docs.peppol.eu/poacc/billing/3.0/syntax/ubl-invoice/
