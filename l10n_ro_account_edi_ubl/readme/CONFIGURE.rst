* Go to Accounting -> Configuration -> Journals, and set up the "Electronic invoicing" option to "UBL 2.1 (CIUS-RO)"
* Go to Settings -> Romania -> Configure ANAF sync and create a sync config.

** If you don't have any ANAF sync config, you can still generate the XML files, but you will have to send them manually to ANAF.
** If you have a sync config, the XML files will be sent automatically to ANAF after the number of days of resilience set in the settings.
** If you want to send the XMl files before the number of days of resilience, you can do it manually from the Action available in the invoices.

Pentru verificare XMl se poate utiliza:
https://www.anaf.ro/uploadxmi/
