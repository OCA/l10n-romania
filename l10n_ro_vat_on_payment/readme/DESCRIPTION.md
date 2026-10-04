Acest modul implementează suportul pentru **TVA la Încasare** (regim special de TVA conform legislației române), permițând verificarea automată a partenerilor înregistrați în sistemul ANAF ca plătitori de TVA la Încasare.

Funcționalități principale:

- **Verificare ANAF**: Descarcă și procesează fișierul de istoric ANAF (`istoric.txt`) cu toți contribuabilii înregistrați în regimul TVA la Încasare, stocând istoricul perioadelor de aplicare.
- **Câmp TVA la Încasare pe partener**: Adaugă câmpul `Romania - VAT on Payment` pe fișa contabilă a partenerului, indicând dacă partenerul aplică în prezent regimul TVA la Încasare.
- **Verificare automată**: La crearea sau modificarea unui partener român (cu TVA românesc), statusul TVA la Încasare este verificat și actualizat automat din datele ANAF.
- **Setare automată poziție fiscală pe facturi**: La selectarea partenerului pe o factură, modulul verifică dacă firma proprie sau furnizorul aplică TVA la Încasare și setează automat poziția fiscală „Regim TVA la Încasare" (`l10n_ro_property_vat_on_payment_position_id`).
- **Joburi cron zilnice**: Două joburi automate — unul pentru descărcarea datelor ANAF, altul pentru actualizarea statusului TVA la Încasare al partenerilor români — asigură că informațiile sunt mereu la zi.
- **Istoric ANAF**: Pe fișa partenerului este disponibil istoricul complet al perioadelor în care acesta a fost înregistrat în regimul TVA la Încasare.

---

### De ce este nevoie de acest modul față de comportamentul standard Odoo?

Odoo standard poate seta o poziție fiscală pe o factură pe baza regulilor de mapare configurate manual (țară, grup de taxe etc.) sau dacă pe partener este setată explicit o poziție fiscală. **Însă Odoo standard nu știe dacă un furnizor este înregistrat în regimul TVA la Încasare** — nu există nicio integrare cu ANAF și nicio verificare automată.

Fără acest modul, ar fi necesară verificarea manuală a fiecărui furnizor pe site-ul ANAF și setarea manuală a poziției fiscale pe fiecare partener — un proces imposibil de menținut în practică pentru un număr mare de furnizori.

Modulul aduce trei avantaje esențiale față de configurarea manuală:

1. **Sursa oficială de adevăr — datele ANAF**: Statusul TVA la Încasare provine direct din fișierul oficial ANAF (`istoric.txt`), nu dintr-o configurare manuală care poate fi uitată sau greșită. Toți contribuabilii înregistrați în regim sunt acoperiți automat.

2. **Verificare temporală bazată pe data facturii**: Modulul verifică dacă furnizorul era în regim TVA la Încasare **la data facturii**, nu doar în prezent. Aceasta este o cerință legală importantă: un furnizor poate fi intrat sau ieșit din regim între timp, iar factura trebuie tratată conform statusului din ziua emiterii.

3. **Verificare pe firma proprie (emitent)**: Pe lângă verificarea furnizorului, modulul verifică și dacă **firma ta** aplică TVA la Încasare. Dacă da, toate facturile de vânzare emise de firma ta trebuie să folosească automat poziția fiscală corespunzătoare — indiferent de clientul selectat.
