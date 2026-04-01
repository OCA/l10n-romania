Pentru a utiliza acest modul, urmați pașii de mai jos:

1. Configurare Taxe
--------------------
*   Navigați la **Accounting > Configuration > Taxes**.
*   În fila **Definition**, pe liniile de repartizare a taxelor (Repartition Lines), bifați opțiunea **Romania - Nondeductible** pentru liniile care reprezintă componenta nedeductibilă a taxei.
*   Puteți bifa și opțiunea **Romania - Exclude From Stock** dacă doriți ca această taxă să nu fie adăugată la valoarea de inventar în operațiunile de stoc.

Definirea corectă a unei taxe ND50% (Deductibilitate limitată 50%)
-------------------------------------------------------------------
Pentru a configura o taxă de tip ND50 (de exemplu, TVA 19% cu deductibilitate 50%), urmați acești pași în fila **Definition**:
1.  **Linia de bază (Base):** 100%.
2.  **Liniile de taxă (Tax):**
    *   **Linia 1 (Deductibilă):** Factor 100%, Cont 4426 (TVA deductibil).
    *   **Linia 2 (Nedeductibilă):** Factor 50%, Cont 635 (sau contul de cheltuială dorit), bifați **Romania - Nondeductible**.
    *   **Linia 3 (Corecție):** Factor -50%, Cont 4426 (TVA deductibil).
    *   **Liniile de bază pentru raportare (opțional):** Factor 500% cu bifa de nedeductibil și -500% pentru ajustarea bazei în jurnale, dacă este necesar pentru declarații specifice.
*   Asigurați-vă că opțiunea **Allow negative tax** este bifată pe formularul taxei dacă folosiți factori negativi în liniile de repartizare.

2. Configurare Conturi
-----------------------
*   Puteți seta un cont de cheltuială implicit pentru TVA-ul nedeductibil la nivel de companie (în setările de contabilitate specifice României).
*   Alternativ, în **Accounting > Chart of Accounts**, pe un anumit cont de cheltuială, puteți defini un **Romania - Nondeductible Account** specific. Dacă acesta este setat, sumele nedeductibile de pe liniile care utilizează acest cont vor fi redirecționate către contul specificat.

3. Utilizare pe Facturi de Furnizor
------------------------------------
*   Când introduceți o factură de furnizor, selectați taxa care are definită o componentă nedeductibilă.
*   Sistemul va crea automat liniile contabile, redirecționând partea nedeductibilă către contul de cheltuială configurat.

4. Utilizare în Operațiuni de Stoc
-------------------------------------
*   În operațiunile de tip **Consum (Internal Transfer către locații de consum)** sau **Ajustări de Inventar (Minus)**, puteți selecta o taxă în câmpul **Romania - Non Deductible Tax** pe liniile de mișcare de stoc.
*   Dacă taxa este selectată, la validarea operațiunii, sistemul va genera liniile de evaluare a stocului incluzând taxa (dacă nu este bifată opțiunea de excludere) și va asigura reflectarea corectă în contabilitate.
