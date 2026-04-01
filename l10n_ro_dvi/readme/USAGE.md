Pentru a gestiona o Declarație Vamală de Import (DVI), urmați acești pași:

1. Crearea Declarației Vamale
----------------------------
1.  Navigați la **Accounting** -> **Actions** -> **DVI**.
2.  Apăsați butonul **Create**.
3.  Introduceți **Data** declarației și selectați **Jurnalul** corespunzător (de regulă un jurnal de tip Operations Divers).

2. Configurarea Taxelor și Serviciilor Vamale
--------------------------------------------
1.  Selectați **Taxa de TVA** (de regulă TVA 19% Deductibil Import).
2.  Alegeți produsul corespunzător pentru **Taxe Vamale** (trebuie să fie de tip serviciu și să aibă bifată opțiunea "Custom Duty").
3.  Introduceți valoarea taxelor vamale în câmpul **Customs Duty Value**.
4.  Alegeți produsul pentru **Comision Vamal** și introduceți valoarea acestuia.

3. Asocierea Facturilor de Furnizor
------------------------------------
1.  În tab-ul principal, adăugați facturile de furnizor (Vendor Bills) care fac obiectul importului.
2.  Sistemul va prelua automat liniile de produse din aceste facturi în secțiunea **DVI Lines**.
3.  Verificați și ajustați cantitățile declarate în vamă pentru fiecare linie, dacă este necesar.

4. Gestionarea Diferențelor de TVA (Opțional)
-----------------------------------------------
Dacă există o diferență între TVA-ul calculat de Odoo (la cursul BNR al facturii) și TVA-ul înscris în DVI (la cursul vamal lunar):
1.  Introduceți valoarea diferenței în câmpul **VAT Price Difference**.
2.  Selectați un produs pentru repartizarea acestei diferențe.

5. Validarea și Generarea Costurilor de Stoc (Landed Costs)
-----------------------------------------------------------
1.  Apăsați butonul **Post** pentru a valida declarația.
2.  La validare, sistemul va:
    *   Genera automat un document de tip **Landed Cost** pentru repartizarea taxelor vamale și a comisionului pe produsele din stoc.
    *   Genera notele contabile de TVA aferente importului, incluzând etichetele fiscale necesare pentru Declarația 300.
3.  Accesați documentul de Landed Cost creat (via butonul smart din DVI) și validați-l pentru a finaliza capitalizarea costurilor în stoc.

6. Anularea unei Declarații
-----------------------------
Dacă este necesar, puteți folosi butonul **Reverse**. Această acțiune va:
*   Crea noi straturi de evaluare a stocului (valuation layers) cu valori negative pentru a anula impactul costurilor.
*   Anula notele contabile generate inițial.
