This module will make posible to send  e-invoice to Romanian goverment anaf.ro.

To use this module you must have ( or have someone else that has) a digital signature usb token from romania connected with a anaf account.

1. Go to https://pfinternet.anaf.ro/my.policy
put put your username and password and code that came on email
2. Go to Editare profil Oauth
3. At profil Oauth
 - put some text at Denumire Aplicatie.
 - at callback URL 1 put your odoo instance url  /anaf_oauth  
 - ( if you odoo site is   odoo.zzz.ro    you must put https://odoo.zzz.ro url shown also in odoo company e-invoice tab)
 - at Serviciu check e-factura and/or e-transport
 - press Generare Client ID
4. copy the Client ID and Client Secret and put them into odoo instance 
  in meniu Settings/User & Companies/ Company in anaf_oauth tab.
5. From a computer that can connect to anaf.ro and loggin with digital signature,
    press the button Get/renew anaf_token. You will get the error or a token and a new valability date
    If on anaf website is not asking for pin you must open and close your broser to ask you again the signature token pin
6. If you do not have errors press the test button and all should be ok.
7. In companies you have a check if is_romanian_goverment ( to send only invoices to this partners)

https://mfinante.gov.ro/web/efactura/informatii-tehnice

https://www.anaf.ro/anaf/internet/ANAF/servicii_online/servicii_web_anaf/!ut/p/a1/hY9NC4JAEIZ_SwevzqRp1k2h3CQojUj3Eiv4FbYrq-nfT8NDRNncZnge3nmBQgiUs7bIWFMIzsphp-aVzIlJNEvzMNAt9A1nu3FWJ3QPyx6IegB_jI0fPvFx8HeB4R4R3cXoTwB_8i9AJyPQHIGJFz2gWSniV93I5rFuZUBlkiYykepD9ue8aap6raCCXdepjLNUlULBb3wu6gbCNwyq-znEm1G2e3v2BHB2faQ!/dl5/d5/L2dBISEvZ0FBIS9nQSEh/
   https://docs.peppol.eu/poacc/billing/3.0/syntax/ubl-invoice/