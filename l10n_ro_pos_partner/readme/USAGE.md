In the *Choose customer* dialog of the Point of Sale, type the customer's
CUI, with or without the `RO` prefix.

If a customer is already on file under that code, they show up in the list as
usual. If none does, the dialog offers **Create from ANAF**: it fetches the
company from ANAF, creates it with its registered name and address, and puts
it on the current order.

A CUI that ANAF does not know is refused with that reason, and no customer is
created -- the receipt should not go out to a company named after a number.
