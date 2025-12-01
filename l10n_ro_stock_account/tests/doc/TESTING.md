# Documentația Fluxului de Testare - Romanian Stock Accounting

Acest document descrie fluxul de testare pentru modulul `l10n_ro_stock_account` care
implementează contabilitatea stocurilor conform standardelor românești.

## Structura Generală

### Fișiere de Test

1. **`common.py`** - Clasa de bază pentru teste (`TestROStockCommon`)
2. **`cases/xxxx.csv`** - Scenarii generale de test

## Clasa de Bază - TestROStockCommon

### Configurare Inițială

#### Categorii de Produse

- **FIFO Category** (`category_marfa_fifo`)
  - Evaluare în timp real
  - Metodă cost: FIFO
  - Cont evaluare stoc: 371000
  - Permite schimbare conturi pe locații

- **Average Category** (`category_marfa_avg`)
  - Evaluare în timp real
  - Metodă cost: Average
  - Cont evaluare stoc: 371000
  - Permite schimbare conturi pe locații

#### Produse Test

- **`product_fifo`** - Produs cu metodă FIFO
- **`product_avg`** - Produs cu metodă Average
- **`product_fifo_lot`** - Produs FIFO cu trackare pe lot (valuated)
- **`product_avg_lot`** - Produs Average cu trackare pe lot
- **`landed_cost`** - Produs serviciu pentru costuri suplimentare
- **`advance_product`** - Produs pentru avansuri

#### Parteneri

- **`supplier_1`** - Furnizor pentru teste achiziții
- **`customer_1`** - Client pentru teste vânzări

#### Monede

- **RON** - Moneda principală
- **EUR**, **USD** - Monede secundare pentru teste multi-valută

### Configurare Locații și Depozite

#### Depozit Principal (TW1)

- **Locație:** `location` (WH/Stock)
- **Conturi standard:** 371000, 607000, 707000
- **Fără configurare specifică de locație**

#### Depozit Secundar (TW2)

- **Locație:** `location1` (WH2/Stock)
- **Conturi specifice:**
  - Evaluare stoc: 371001
  - Cheltuieli: 607001
- **Configurare pe locație activată**

#### Depozit Terțiar (TW3)

- **Locație:** `location2` (WH3/Stock)
- **Configurare prin poziție fiscală:**
  - Evaluare stoc: 371002
  - Cheltuieli: 607002
  - Cont consum stoc: 371001

#### Locații Speciale

- **`location_production`** - Locație producție
- **`location_sub`** - Sublocatie în depozitul principal
- **`transit_loc`** - Locație tranzit pentru transferuri

## Structura Cazurilor de Test CSV

### Coloane Principale

| Coloană       | Descriere               | Valori                                       |
| ------------- | ----------------------- | -------------------------------------------- |
| `case_no`     | Numărul cazului de test | 1, 2, 3...                                   |
| `type`        | Tipul operațiunii       | purchase, sale, transfer, consume, inventory |
| `currency_id` | Moneda                  | ron, eur, usd                                |
| `partner_id`  | Partenerul              | supplier_1, customer_1                       |
| `location`    | Locația sursă           | location, location1, location2               |
| `location1`   | Locația destinație      | location, location1, location2               |
| `product_id`  | Produsul                | product_fifo, product_avg                    |
| `step`        | Pasul în test           | 1, 2                                         |

### Coloane Cantități și Prețuri

| Coloană      | Descriere                                 |
| ------------ | ----------------------------------------- |
| `qty`        | Cantitatea comandată                      |
| `stock_qty`  | Cantitatea primită/livrată (pasul 1)      |
| `inv_qty`    | Cantitatea facturată (pasul 1)            |
| `stock_qty2` | Cantitatea primită/livrată (pasul 2)      |
| `inv_qty2`   | Cantitatea facturată (pasul 2)            |
| `price`      | Prețul de pe comanda de achizitie/vanzare |
| `inv_price`  | Prețul de pe factură (pasul 1)            |
| `inv_price2` | Prețul de pe factură (pasul 2)            |

### Coloane Opțiuni

| Coloană                 | Descriere                |
| ----------------------- | ------------------------ | -------------------------------------------------------------- |
| `discount`              | Reducerea aplicată       |
| `advance`               | Avansul plătit           |
| `notice`                | Operațiune cu aviz (1/0) |
| `landed_cost`           | Costuri suplimentare     | - nefolosit aici de mutat poate in modulul de landed cost      |
| `reception_in_progress` | Recepție în curs (1/0)   | - nefolosit aici de mutat poate in modulul de receptii in curs |

### Verificări (`checks`)

Format JSON cu verificări așteptate:

```json
{
  "stock": {
    "product_fifo": [ - referinta produsului pe care se verifica
      {"qty": 5, "value": 500}, - verificare stoc produs in companie
      {"location": "location", "qty": 3, "value": 300}, - verificare stoc produs in locatie
      {"lot": "lot_fifo_1", "qty": 3, "value": 300} - verificare stoc produs pe lot in companie
      {"location": "location1", "lot": "lot_fifo_1", "qty": 3, "value": 300} - verificare stoc produs pe lot si locatie
    ]
  },
  "account": {
    "371000": 500, - verificare sold cont
    "607000": 0, - verifica daca sunt note generate pe cont
    "418100": -200
  }
}
```

Pentru a vedea log-urile din check va trebui sa setati

```python
cls.log_checks = True
```

## Tipuri de Operațiuni Test

### 1. Achiziții (`purchase`)

#### Proces:

1. **Creare comandă achiziție** (`create_purchase`)
2. **Recepție mărfuri** (`receive_and_invoice_purchases`)
3. **Facturare** (dacă `inv_qty` > 0)

### 2. Vânzări (`sale`)

#### Proces:

1. **Creare comandă vânzare** (`create_sale_order`)
2. **Livrare mărfuri** (`deliver_and_invoice_sales`)
3. **Facturare** (dacă `inv_qty` > 0)

### 3. Transferuri (`transfer`)

#### Tipuri:

- **Direct** (`transfer_direct`) - Transfer direct între locații
- **Tranzit** (`transfer_transit`) - Transfer prin locație tranzit

#### Proces:

1. **Creare mișcare stoc**
2. **Confirmare și alocare**
3. **Procesare transfer**

### 4. Consum si Dare in folosinta

#### Tipuri:

- **Consum normal** (`consume`)
- **Consum producție** (`consume_production`)
- **Dare în folosință** (`usage_giving`)

#### Proces:

1. **Identificare tip picking**
2. **Creare mișcare consum**
3. **Procesare și validare**

### 5. Inventar (`inventory`)

#### Proces:

1. **Creare ajustare inventar** (`create_stock_inventory`)
2. **Aplicare diferențe** (plus/minus)

## Fluxul de Executare Test

### 1. Citire Cazuri Test

```python
def read_test_cases_from_csv_file(self, filename):
    # Citește CSV-ul
    # Grupează pasii pe case_no
    # Returnează dicționar cu cazuri
```

### 2. Executare Caz Test

```python
def test_case(self, case):
    for step in case.get("steps", []):
        self.run_test_step(step)
```

### 3. Executare Pas Test

```python
def run_test_step(self, step):
    # Determină tipul operațiunii
    # Apelează metoda corespunzătoare
    # Rulează verificările dacă există
```

### 4. Procesare Valori

```python
def get_references_from_values(self, values):
    # Convertește referințele string în obiecte
    # Convertește valorile numerice
    # Convertește valorile boolean
```

## Verificări Automate

### Verificări Stoc

```python
def check_stock_levels(self, checks):
    # Verifică cantitățile în stoc
    # Verifică valorile stocului
    # Verifică distribuția pe locații
    # Verifică loturile (dacă aplicabil)
```

### Verificări Contabile

```python
def check_accounting_entries(self, checks):
    # Verifică soldurile conturilor
    # Compară cu valorile așteptate
    # Raportează diferențele
```

## Exemple de Scenarii Test

### Scenariul 1: Achiziție FIFO Simplă

```csv
3,purchase,ron,supplier_1,,,,product_fifo,1,5,,5,5,,0,0,100,100,0,0,0,0,0,0,
"{'stock': {'product_fifo': [{'qty': 5, 'value': 500}]}, 'account': {'371000': 500}}",
Receptie totala cu factura,"Receptie 5 bucati la 100, factura 5 bucati la 100"
```

**Pași:**

1. Comandă 5 bucăți la 100 RON
2. Recepție 5 bucăți
3. Factură 5 bucăți la 100 RON
4. **Verificare:** Stoc 5 buc/500 RON, Cont 371000 = 500 RON
