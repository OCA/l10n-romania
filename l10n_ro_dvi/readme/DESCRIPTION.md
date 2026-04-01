DVI - Declarația Vamală de Import
----------------------------------

Acest modul permite gestionarea detaliată a Declarațiilor Vamale de Import (DVI) în Odoo, asigurând conformitatea cu legislația din România (OMFP 1802/2014 și Codul Fiscal).

Caracteristici principale:
-------------------------

*   **Model de date dedicat**: Introduce entitatea `l10n.ro.account.dvi` pentru evidența separată a documentelor vamale.
*   **Grupare facturi**: Permite asocierea mai multor facturi de furnizor (Vendor Bills) într-o singură declarație vamală.
*   **Calcul analitic**: Calculează automat taxele vamale, comisionul vamal și TVA-ul la nivel de linie de produs, bazat pe cantitățile declarate.
*   **Integrare cu Landed Costs**: Generează automat documente de tip `stock.landed.cost` pentru repartizarea taxelor în costul stocului.
*   **Trasabilitate fiscală**: Asigură popularea corectă a etichetelor fiscale (`tax_tag_ids`) pentru jurnalele de cumpărări și Declarația 300.
*   **Ajustări de curs**: Include posibilitatea de a gestiona diferențele de calcul pentru TVA (`vat_price_difference`) rezultate din discrepanța dintre cursul BNR al facturii și cursul vamal lunar.

Baza legală:
------------

Prezentul capitol sintetizează cadrul legal aplicabil operațiunilor de import (achiziție marfă externă + Declarație Vamală de Import – DVI), cu accent pe următoarele aspecte:

*   Factura comercială externă se înregistrează în contabilitate la cursul BNR din data emiterii facturii;
*   Cursul valutar din vamă (cursul vamal lunar) se utilizează exclusiv pentru calculul valorii în vamă, al taxelor vamale (A00) și al TVA-ului la import (B00) din DVI;
*   Toate înregistrările contabile (factură, taxe vamale, stocuri) se efectuează și se prezintă doar în moneda națională (RON).

1. Legea contabilității nr. 82/1991 (republicată)
------------------------------------------------------

*   **Art. 3 alin. (1):** „Contabilitatea se ține în limba română și în moneda națională.”
*   **Art. 3 alin. (2):** „Contabilitatea operațiunilor efectuate în valută se ține atât în moneda națională, cât și în valută, potrivit reglementărilor elaborate în acest sens.”

Toate operațiunile de import (inclusiv factura furnizor și DVI) se înregistrează și se prezintă în situațiile financiare exclusiv în RON.

2. OMFP nr. 1802/2014
-----------------------

*   **Pct. 319:** „O tranzacție în valută trebuie înregistrată inițial la cursul de schimb valutar, comunicat de Banca Națională a României, de la data efectuării operațiunii.” -> Factura comercială externă (Vendor Bill) se înregistrează la cursul BNR din data emiterii facturii.
*   **Pct. 6 (definiția costului de achiziție):** „Costul de achiziție al bunurilor cuprinde prețul de cumpărare, taxele de import și alte taxe (cu excepția acelora pe care persoana juridică le poate recupera de la autoritățile fiscale)…”
*   **Pct. 75 alin. (1) lit. a):** Bunurile se evaluează și se înregistrează la data intrării în entitate la cost de achiziție (care include taxele vamale plătite conform DVI).
*   **Pct. 94 lit. a):** Elementele monetare exprimate în valută se evaluează la cursul BNR la data bilanțului; diferențele de curs se înregistrează pe conturile 665 sau 765.

Taxele vamale (A00) se capitalizează în costul stocurilor, iar toate valorile finale rămân exclusiv în RON.

3. Legea nr. 227/2015 – Codul Fiscal
------------------------------------------

*   **Art. 289 (Baza de impozitare a importului de bunuri):** „Dacă elementele folosite la stabilirea bazei de impozitare a unui import de bunuri se exprimă în valută, cursul de schimb valutar se stabilește conform prevederilor europene care reglementează calculul valorii în vamă.”
*   **Art. 299 alin. (1) lit. c):** Dreptul de deducere a TVA aferente importului de bunuri se exercită pe baza Declarației vamale de import (DVI) sau a actului constatator emis de organele vamale (TVA B00 calculat la cursul vamal).

Cursul din DVI se folosește doar pentru determinarea valorii în vamă, calculul taxei vamale (A00) și al TVA-ului la import (B00). Nu afectează înregistrarea facturii comerciale în contabilitate.

4. Regulamentul de punere în aplicare (UE) 2015/2447 al Comisiei
----------------------------------------------------------------------

*   **Art. 146 (Conversia monetară în scopul determinării valorii în vamă):** „În situația în care valoarea în vamă a mărfurilor este exprimată într-o altă monedă decât cea națională, cursul de schimb folosit la determinarea acestei valori este cursul de schimb stabilit și comunicat de Banca Națională a României în penultima zi de miercuri a lunii anterioare lunii în care se utilizează.”

Cursul vamal este un curs lunar fix, aplicabil exclusiv în cadrul procedurii vamale pentru calculul valorii statistice, taxelor vamale și TVA la import. Nu se utilizează pentru înregistrarea facturii furnizor în contabilitate.

Concluzie
---------

Cadrul legal este clar și unitar:
*   **Factura furnizor** -> curs BNR (data facturii) + înregistrare în RON.
*   **DVI** -> curs vamal lunar (Reg. UE 2015/2447 art. 146 + Cod Fiscal art. 289) doar pentru taxe vamale și TVA la import.
*   **Toate înregistrările contabile** (inclusiv costul stocurilor) -> exclusiv în RON.
