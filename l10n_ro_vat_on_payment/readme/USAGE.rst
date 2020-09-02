On the partner accounting page you will have a new field called
"VAT on Payment" and a new button, called "Update VAT on Payment",
available only on companies (is_company field set to True).
Pushing the button will search in the ANAF datas for records assigned
to the partner's VAT number and linked them to it.

For invoices, you will need to create manually the VAT on payment taxes,
a new fiscal position called "Regim TVA la Incasare" and map the normal
taxes with the VAT on Payment one's.

On invoices partner select it will check for Vat on payment on company / supplier
and change the fiscal position with the "Regim TVA la Incasare" one.

Two daily cron jobs are set up, one for downloading the ANAF datas,
one for checking the Romanian partners for VAT on Payment.
