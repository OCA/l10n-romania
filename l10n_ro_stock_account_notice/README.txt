The module is for reception/devlivery of products without invoice.
(modul folositor daca vindeti sau cumparati cu aviz si facturati/sunteti facturat mai tarziu)
In picking fields 
        - l10n_ro_notice menas that is stock that does not have invoice and will be done later.
        - l10n_ro_accounting_date if notice  the date of created svl and account_moves.

At reception or delivery we have also a price_unit per product.
This price_unit will create svl and accounting Journal Entries ( for each product)
Created journal entries will have the account 408/418 invoices to make/receive

! Ff you done a mistake at a notice reception ( price, date), you can modify the generated account_moves form svl per picking
! you are doing this by setting to draft and post it again
! by doing this it will not change values from picking, but the changes will be visible in svl

At the receiving of a bill or creating a invoice you can set the notice pickings; 
if this is the case you'll have acocunt_mvoe_lines with account 408/418 and if a price 
difference will create another line with price difference

In case (not probable) of reciving a invoice that have partialy of a notice (aviz), do not use the notice_pickings_ids field and modify the account_move_lines in bill.

At invoice for picking we are going to compare the qty and price. It will raise error if qty diffrence, and will create diffrence line ( if is in another currency will be loss/gain, if not will be discount/diffrence)

 
Pretul de achizitie ce este mentionat pe NIR (nota intrare si receptie marfa)este cel de la data primirii bunurilor, respectiv cel de 250 lei / buc. In privinta facturii finale, dupa cum mentionati, aceasta cuprinde un discount (de 10 lei / buc) acordat pe insasi factura de livrare (240 lei in loc de 250 lei). Pretul de vanzare catre client este, probabil, cel putin egal cu cel de achizitie initial, de 250 lei, urmand ca societatea sa castige din discountul primit pe factura finala de la furnizor.
 
Monografia contabila este urmatoarea:
1) primirea, receptia si inregistrarea bunurilor in gestiune si in contabilitate pe baza deliverz-note-ului si a NIR-ului intocmit de societate:

371 = 408  x buc * 250 lei.
Nu se efectueaza raportari in D 300 si D 390 si nu se inregistreaza taxarea inversa.

2) vanzare bunuri catre client, pe baza de factura:
4111 = 707  x buc * 250 lei pret vanzare (cel putin)
4111 = 4427

si, concomitent, se inregistreaza descarcarea din gestiune a bunurilor vandute:
607 = 371 x buc * 250 lei.

3) primirea facturii centralizatoare, la finalul lunii:
408 = 401   valoarea de la punctul 1)
si inregistrarea discountului primit de la furnizor:
401 = 609  x buc * 10 lei/buc.

709 = “Reduceri comerciale acordate”
609 = “Reduceri comerciale primite“
767 = se foloseste doar atunci cand reducerea e de natura financiara, adica furnizorul accepta, prin contract, sa incaseze mai putin 

 348 “Diferente de pret la produse”  

665 "Cheltuieli cu diferentele de curs valutar"
765 "Venituri din diferente de curs valutar"
 
It will create a landed cost with a "Price Difference" product available in the configuration.
Primirea marfurilor pe baza de aviz de insotire:
371 = 408       300.000 lei

Primirea facturii:
% = 401         357.000 lei
408                   300.000 lei
4426                      57.000 lei
+ line diferente

