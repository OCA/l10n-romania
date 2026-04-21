Acest modul facilitează gestionarea mesajelor din Spațiul Privat Virtual (SPV) ANAF, asigurând descărcarea și procesarea automată a facturilor electronice (e-Factura):

  - Funcționalități:

    - Descărcare automată mesaje SPV: sincronizare periodică (via cron) a listei de mesaje din SPV pentru facturi primite, trimise sau erori.
    - Procesare fișiere ZIP: descărcarea automată a arhivelor ZIP de la ANAF și extragerea fișierelor XML semnate.
    - Creare automată facturi de furnizor: generează schițe de factură (draft) direct din fișierele XML descărcate, mapând automat furnizorul pe baza codului fiscal (CIF).
    - Gestionare PDF-uri e-Factura:
      - Generare PDF ANAF: posibilitatea de a genera și descărca vizualizarea PDF oficială a XML-ului folosind serviciile ANAF.
      - Extragere PDF încorporat: extrage PDF-urile atașate direct în fișierul XML (dacă există).
    - Monitorizare stări: urmărirea stării fiecărui mesaj (Draft, Downloaded, Invoice, Error, Done) și a încercărilor de descărcare.
    - Integrare cu fluxul de facturare: legarea automată a mesajelor de facturile existente în sistem pe baza ID-ului de tranzacție sau a referinței.
    - Sincronizarea datelor produselor: permite salvarea automată a codurilor de furnizor pentru produse la validarea facturilor primite.
