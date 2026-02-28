# Real Estate Tracker - Karaburma

Sistem za automatsko praćenje oglasa za stanove na Karaburmi sa sajta **nekretnine.rs**. Program detektuje nove oglase i promene cena, šalje email obaveštenja i čuva podatke u Excel tabeli.

---

## Opis Fajlova

- **`main.py`**: Glavni program. Upravlja logikom, učitava konfiguraciju, pokreće scraper, upoređuje rezultate i poziva notifikacije.
- **`scraper.py`**: Sadrži `NekretnineScraper` klasu koja koristi `BeautifulSoup` za izvlačenje podataka sa sajta.
- **`notifier.py`**: Modul zadužen za slanje emailova i generisanje Excel fajla (`stanovi_karaburma.xlsx`).
- **`config.json`**: Centralni konfiguracioni fajl. Ovde unosite email adrese pošiljaoca i primalaca, kao i listu URL-ova koje želite da pratite.
- **`apartments.json`**: Lokalna "baza" u kojoj se čuvaju podaci o stanovima radi poređenja cena i novih oglasa.
- **`log.txt`**: Fajl u koji se upisuje izveštaj o poslednjem izvršavanju skripte.
- **`pokreni_stanovi.bat`**: Batch skripta za lako pokretanje programa na Windowsu (idealno za Task Scheduler).

---

## Instalacija

1. Instalirajte Python (verzija 3.9 ili novija).
2. Instalirajte potrebne Python biblioteke komandom:
   ```bash
   pip install requests beautifulsoup4 pandas openpyxl lxml
   ```

---

## Konfiguracija (`config.json`)

Otvorite `config.json` i podesite sledeće:
- **`sender`**: Vaša Gmail adresa.
- **`password`**: Google App Password (generiše se u podešavanjima Google naloga).
- **`recipients`**: Lista email adresa koje treba da dobiju obaveštenje (npr. `["me@gmail.com", "friend@gmail.com"]`).
- **`urls`**: Lista URL-ova sa nekretnine.rs koje program treba da pretražuje.

---

## Automatizacija na Windows 11 (Task Scheduler)

Da bi skripta radila automatski u pozadini bez iskakanja prozora:

1. Kliknite na **Start**, ukucajte **Task Scheduler** i otvorite ga.
2. Sa desne strane kliknite na **Create Basic Task...**.
3. Unesite ime: `Pretraga Stanova Karaburma`.
4. Izaberite učestalost (npr. **Daily**), a zatim podesite vreme početka.
5. Za akciju izaberite **Start a program**.
6. U polju **Program/script** kliknite `Browse` i izaberite fajl **`pokreni_stanovi.bat`**.
7. U polju **Start in (optional)** upišite punu putanju do foldera gde su fajlovi (npr. `D:\Docket lab\gemini\stanovi`).
8. Kliknite **Finish**.

### Da radi potpuno nevidljivo:
1. U listi zadataka nađite vaš zadatak, desni klik -> **Properties**.
2. U tabu **General** izaberite: **Run whether user is logged on or not**.
3. Štiklirajte **Hidden**.
4. Potvrdite sa **OK** (biće vam tražena lozinka vašeg Windows naloga).

---

## Napomene
- Ako želite da **resetujete bazu**, jednostavno obrišite fajl `apartments.json`.
- Sve greške ili potvrde o radu možete uvek videti u fajlu `log.txt`.
