This module allows you to create the partners (companies) based on their
VAT number. It will complete the name, address of the partner from ANAF
webservice.

ANAF <https://webservicesp.anaf.ro/PlatitorTvaRest/api/v8/ws/tva>




---

## 1. CUI (Codul Unic de Înregistrare)
**CUI-ul** este "CNP-ul" unei firme. Este numărul atribuit de Registrul Comerțului (sau de Ministerul Finanțelor, după caz) în momentul în care o entitate juridică este înființată.

* **Format:** Este alcătuit dintr-un șir de cifre (între 2 și 10 cifre).
* **Cine îl are:** Toate entitățile juridice (SRL, PFA, ONG, etc.).
* **Rol:** Identifică în mod unic firma în fața autorităților și a partenerilor de afaceri.

## 2. CIF (Codul de Identificare Fiscală)
**CIF-ul** este, în esență, denumirea generică pentru codul de identificare al unui plătitor de taxe.

* **Confuzia frecventă:** Pentru o firmă (SRL), **CUI și CIF sunt de cele mai multe ori același număr**. Termenul "CIF" este folosit mai des de ANAF, în timp ce "CUI" este folosit de Registrul Comerțului.
* **Cazuri speciale:** Alte entități care nu sunt firme (de exemplu, asociațiile de proprietari sau instituțiile publice) primesc un CIF pentru a putea plăti taxe și impozite.

## 3. VAT ID (Codul de TVA)
**VAT ID** (sau codul de înregistrare în scopuri de TVA) reprezintă CUI-ul/CIF-ul firmei tale, dar cu prefixul de țară (pentru România, acesta este **RO**) atașat în față.

* **Exemplu:** Dacă CUI-ul firmei tale este `12345678`, VAT ID-ul va fi `RO12345678`.
* **Importanță:** Nu toate firmele au un VAT ID automat. O firmă are un cod de TVA doar dacă:
    1. A depășit plafonul de scutire de TVA (300.000 lei cifră de afaceri).
    2. A ales să devină plătitoare de TVA prin opțiune.
    3. S-a înregistrat pentru operațiuni intracomunitare (achiziții/vânzări de servicii sau bunuri în UE).

---

### Rezumat comparativ

| Termen | Ce înseamnă | Exemplu |
| :--- | :--- | :--- |
| **CUI** | Identificatorul oficial al firmei. | `12345678` |
| **CIF** | Termenul fiscal pentru CUI. | `12345678` |
| **VAT ID** | CUI-ul cu prefixul de țară (doar pentru firmele plătitoare de TVA). | `RO12345678` |

> **Notă:** Dacă o firmă **nu** este plătitoare de TVA, pe facturile emise de ea va apărea doar numărul simplu (CUI), fără prefixul "RO".
