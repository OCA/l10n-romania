Without this module you need to set the account in invoice for landed_cost_product ( because romania accounting has is_anglo_saxon check and will try to give the input stock_account)


With this module, only for companies that have romanian accounting ("l10n_ro_config",  if company_id.l10n_ro_accounting):
1. will use in invoice line the expense account of landed_cost_product & the same account in stock_landed_cost
Aditional
2. if you have a invoice that has landed cost and recived products will put in created landed cost also the coresponding pickings

future if is not goig to be in another module 3. you can not create landed cost if the inoice is not posted ( did not create the accounting entries)


Test:
storable products with automated inventory valuation & conting fifo or average: p1 marfuri 371,p2 auxiliare 3021 ,p3   materii prime 301
transport_landed_cost  - service expense 624 & Control Policy    On ordered quantities
crane_landed_cost - service expense  628

Romanian company recieve 10 p1 at 100   & 20 p2 at 200 & 30 pr at 300   and a transport of 8
and another invoice with tax of 50 for the p1 and p2


Romania Landed Cost = celeleate cheltuieli ce au fost facute pentru marfa intrata in stock

Conform Regulilor generale de evaluare prezentate de OMFP 3055/2009:

"51 - (1) Costul de achizitie al bunurilor cuprinde pretul de cumparare, taxele de import si alte taxe (cu exceptia acelora pe care persoana juridica le poate recupera de la autoritatile fiscale), cheltuielile de transport, manipulare si alte cheltuieli care pot fi atribuibile direct achizitiei bunurilor respective.
In costul de achizitie se includ, de asemenea, comisioanele, taxele notariale, cheltuielile cu obtinerea de autorizatii si alte cheltuieli nerecuperabile, atribuibile direct bunurilor respective.

(2) Cheltuielile de transport sunt incluse in costul de achizitie si atunci cand functia de aprovizionare este externalizata. "
Nota contabila prin care transportul este inclus in costul stocului de marfa este pur si simplu inregistrarea facturii de transport ca 371 = 401, in loc de 624 = 401.
