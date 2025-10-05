# Generarea Operațiilor Odoo pe Baza Coloanelor CSV

### 1. Procesarea Valorilor din CSV

Sistemul are două nivele de procesare:

#### **Nivel 1: Conversii de Bază**

```python
def get_references_from_values(self, values):
    # Convertește referințele string în obiecte Odoo
    refs = ["partner_id", "product_id", "location", "currency_id", ...]
    float_keys = ["qty", "price", "stock_qty", "inv_qty", ...]
    bool_keys = ["notice", "reception_in_progress"]

    # Procesează automat conversiile
    for ref in refs:
        if ref in values:
            values[ref] = self.env.ref(f"test_object.{values[ref]}")

    for key in float_keys:
        if key in values:
            values[key] = float(values[key])
```

#### **Nivel 2: Funcții Helper pentru Pași**

Implementate ca funcții statice pentru reutilizare și consistență:

```python
def get_stock_quantity(self, values, step):
    if step == 1:
        return values.get("stock_qty", 1)
    elif step == 2:
        return values.get("stock_qty2", 1)
    else:
        return 1

def get_invoice_quantity(self, values, step):
    if step == 1:
        return values.get("inv_qty")  # None dacă nu există
    elif step == 2:
        return values.get("inv_qty2")  # None dacă nu există
    return None

def get_invoice_price(self, values, step):
    if step == 1:
        return values.get("inv_price")  # None dacă nu există
    elif step == 2:
        return values.get("inv_price2")  # None dacă nu există
    return None

def get_stock_lot(self, values, step):
    if step == 1:
        return values.get("lot1")  # None dacă nu există
    elif step == 2:
        return values.get("lot2")  # None dacă nu există
    return None
```

#### **Nivel 2: Contextul de Execuție**

```python
def run_test_step(self, step):
    # Determinează tipul operațiunii
    if step.get("type") == "purchase":
        purchase = self.create_purchase(step)

        # Pentru pasul 2, setează contextul corespunzător
        if step.get("step") == 2:
            self.receive_and_invoice_purchases(
                purchase.with_context(step=2), step
            )

def receive_and_invoice_purchases(self, purchases, values):
    for purchase in purchases:
        # Extrage pasul din context
        step = purchase.env.context.get("step", 1)

        # Folosește funcțiile helper cu pasul corect
        stock_qty = self.get_stock_quantity(values, step)
        invoice_qty = self.get_invoice_quantity(values, step)
        invoice_price = self.get_invoice_price(values, step)
        stock_lot = self.get_stock_lot(values, step)
```

## Coloanele CSV - Explicații Detaliate

### Coloane de Identificare

#### `case_no` - Numărul Cazului

- **Scop:** Identifică unic un caz de test
- **Format:** Numeric (1, 2, 3...)
- **Utilizare:** Grupează pașii secvențiali ai aceluiași test
- **Exemplu:** Cazul 1 poate avea 3 pași pentru achiziție, recepție și facturare

#### `type` - Tipul Operațiunii

- **Scop:** Determină ce metodă se apelează pentru crearea operațiunii
- **Valori posibile:**
  - `purchase` → `create_purchase()`
  - `sale` → `create_sale_order()`
  - `inventory` → `create_stock_inventory()`
  - `transfer` → `create_internal_transfer_direct()`
  - `transfer_transit` → `create_internal_transfer_transit()`
  - `consume` → `create_stock_picking("consume")`
  - `consume_production` → `create_stock_picking("production")`
  - `usage_giving` → `create_stock_picking("usage_giving")`

#### `step` - Pasul în Secvență

- **Scop:** Controlează ordinea execuției în cadrul aceluiași caz
- **Valori:** 1 (primul pas), 2 (al doilea pas)
- **Utilizare:** Pentru operațiuni complexe cu multiple etape
- **Exemplu:**
  - Pas 1: Recepție parțială 2 bucăți
  - Pas 2: Recepție finală 3 bucăți

### Coloane de Referințe

#### `currency_id` - Moneda

- **Scop:** Specifică moneda pentru operațiune
- **Valori:** `ron`, `eur`, `usd`
- **Conversie:** String → obiect `res.currency`
- **Utilizare în cod:**

```python
"currency_id": po_values.get("currency_id", self.env.company.currency_id).id
```

#### `partner_id` - Partenerul

- **Scop:** Identifică furnizorul/clientul
- **Valori:** `supplier_1`, `customer_1`
- **Conversie:** String → obiect `res.partner`
- **Utilizare diferențiată:**
  - Pentru achiziții: furnizor
  - Pentru vânzări: client

#### `fiscal_position_id` - Poziția Fiscală

- **Scop:** Aplică reguli fiscale specifice
- **Utilizare:** Modifică conturile conform mapărilor fiscale
- **Exemplu:** Schimbă contul 371000 → 371002 pentru depozitul 3

#### `product_id` - Produsul

- **Scop:** Identifică produsul pentru operațiune
- **Valori:** `product_fifo`, `product_avg`, `product_fifo_lot`
- **Conversie:** String → obiect `product.product`

#### `location` / `location1` - Locațiile

- **Scop:** Definește locația sursă și destinație
- **Valori:** `location`, `location1`, `location2`
- **Utilizare:**
  - `location`: Locația sursă (pentru transferuri, consum) sau locatie destinatie pentru
    receptii, inventar
  - `location1`: Locația destinație (pentru transferuri)
- **Impact contabil:** Diferite locații = conturi diferite

### Coloane de Cantități

#### `qty` - Cantitatea Comandată

- **Scop:** Cantitatea totală din comandă (achiziție/vânzare)
- **Caracteristici:**
  - Se setează o singură dată la crearea comenzii
  - Nu depinde de pași (step 1 sau 2)
  - Reprezintă cantitatea totală planificată
- **Utilizare:**

```python
# Pentru achiziții
"product_qty": po_values.get("qty", 1)
# Pentru vânzări
"product_uom_qty": so_values.get("qty", 1)
```

- **Exemplu:** `qty=10` înseamnă comandă pentru 10 bucăți total

#### `stock_qty` / `stock_qty2` - Cantități Stoc pe Pași

##### **Conceptul de Pași pentru Stoc:**

Sistemul suportă procesare în 2 pași pentru scenarii complexe:

- **Pas 1:** Prima mișcare de stoc (folosește `stock_qty`)
- **Pas 2:** A doua mișcare de stoc (folosește `stock_qty2`)

##### **`stock_qty` - Cantitatea pentru Pasul 1:**

- **Când se folosește:** Primul pas al oricărei operațiuni
- **Valori pozitive:** Recepții, livrări normale
- **Valori negative:** Retururi în primul pas
- **Lipsește coloana:** Se consideră 1 implicit

##### **`stock_qty2` - Cantitatea pentru Pasul 2:**

- **Când se folosește:** Al doilea pas (doar când `step=2` în CSV)
- **Valori pozitive:** Recepții/livrări suplimentare
- **Valori negative:** Retururi în al doilea pas
- **Lipsește coloana:** Se consideră 1 implicit

##### **Logica de Selectare în Cod:**

```python
def get_stock_quantity(self, values, step):
    if step == 1:
        return values.get("stock_qty", 1)
    elif step == 2:
        return values.get("stock_qty2", 1)
    else:
        return 1

# În metodele de procesare:
stock_qty = get_stock_quantity(values, current_step)
move._set_quantity_done(stock_qty)
```

##### **Scenarii de Utilizare:**

**1. Recepție Completă într-un Pas:**

```csv
case_no,type,step,qty,stock_qty
1,purchase,1,10,10
```

- Comandă 10 bucăți → Recepție 10 bucăți în primul pas

**2. Recepție Parțială în Două Pași:**

```csv
case_no,type,step,qty,stock_qty,stock_qty2
2,purchase,2,10,4,6
```

- Comandă 10 bucăți
- Pas 1: Recepție 4 bucăți
- Pas 2: Recepție 6 bucăți (total = 10)

**3. Recepție cu Retur:**

```csv
case_no,type,step,qty,stock_qty,stock_qty2
3,purchase,2,10,10,-2
```

- Comandă 10 bucăți
- Pas 1: Recepție 10 bucăți
- Pas 2: Retur 2 bucăți (rămân 8 în stoc)

**4. Recepții Excedentare:**

```csv
case_no,type,step,qty,stock_qty,stock_qty2
4,purchase,2,10,12,3
```

- Comandă 10 bucăți
- Pas 1: Recepție 12 bucăți (cu excedent)
- Pas 2: Recepție suplimentară 3 bucăți (total = 15)

#### `inv_qty` / `inv_qty2` - Cantități Factură pe Pași

##### **Conceptul de Facturare pe Pași:**

Similar cu stocul, facturarea poate fi făcută în 2 pași independenți:

- **Pas 1:** Prima factură (folosește `inv_qty`)
- **Pas 2:** A doua factură (folosește `inv_qty2`)

##### **`inv_qty` - Cantitatea Facturată în Pasul 1:**

- **Când se folosește:** Pentru facturarea în primul pas
- **Valoare 0:** Recepție/livrare fără factură
- **Valoare pozitivă:** Cantitatea facturată normal
- **Valoare negativă:** Factură de retur/credit nota
- **Lipsește coloana:** Nu se creează factură

##### **`inv_qty2` - Cantitatea Facturată în Pasul 2:**

- **Când se folosește:** Pentru facturarea în al doilea pas
- **Valori similare cu `inv_qty`**
- **Se procesează doar când `step=2`**

##### **Logica de Selectare în Cod:**

```python
def get_invoice_quantity(self, values, step):
    if step == 1:
        return values.get("inv_qty")  # None dacă nu există
    elif step == 2:
        return values.get("inv_qty2")  # None dacă nu există
    return None

# În metodele de facturare:
inv_qty = get_invoice_quantity(values, current_step)
if inv_qty is not None and inv_qty != 0:
    # Creează și procesează factura
    invoice_line.write({"quantity": inv_qty})
```

##### **Scenarii de Utilizare:**

**1. Facturare Completă într-un Pas:**

```csv
case_no,type,step,qty,stock_qty,inv_qty
5,purchase,1,10,10,10
```

- Recepție 10 + Factură 10 în același pas

**2. Recepție Fără Factură:**

```csv
case_no,type,step,qty,stock_qty,inv_qty
6,purchase,1,10,10,0
```

- Recepție 10 bucăți fără factură (aviz)

**3. Facturare Parțială în Două Pași:**

```csv
case_no,type,step,qty,stock_qty,inv_qty,stock_qty2,inv_qty2
7,purchase,2,10,10,6,0,4
```

- Pas 1: Recepție 10 + Factură 6
- Pas 2: Fără recepție + Factură 4 (completare)

##### **Relația stock_qty vs inv_qty:**

| Scenariul              | stock_qty | inv_qty | Rezultat                            |
| ---------------------- | --------- | ------- | ----------------------------------- |
| **Normal**             | 10        | 10      | Recepție + Factură complete         |
| **Aviz**               | 10        | 0       | Doar recepție (cont 408100)         |
| **Factură Anticipată** | 0         | 10      | Doar factură (fără stoc)            |
| **Parțial**            | 10        | 6       | Recepție completă, factură parțială |
| **Excedent**           | 12        | 10      | Recepție mai mare decât factură     |
| **Retur Stoc**         | -3        | 0       | Doar retur fizic                    |
| **Credit Nota**        | 0         | -3      | Doar retur contabil                 |

### Coloane de Prețuri

#### `price` - Prețul in comanda de achizitie/vanzare

- **Scop:** Prețul unitar in comanda
- **Caracteristici:**
  - Se aplică pentru toate recepțiile/livrările
  - Nu depinde de pași (același preț pentru pas 1 și 2)
- **Utilizare:**

```python
# Pentru mișcări de stoc
move.write({"price_unit": po_values.get("price", 80)})
```

- **Exemplu:** `price=100` → Toate recepțiile se evaluează la 100 RON/bucată

#### `inv_price` / `inv_price2` - Prețurile de Factură pe Pași

##### **Conceptul de Prețuri pe Pași:**

Sistemul permite prețuri diferite pentru fiecare pas de facturare:

- **Pas 1:** Prima factură (folosește `inv_price`)
- **Pas 2:** A doua factură (folosește `inv_price2`)
- **Diferențe de preț:** Generează ajustări automate ale valorii stocului

##### **`inv_price` - Prețul pentru Factura din Pasul 1:**

- **Când se folosește:** Pentru facturarea în primul pas
- **Lipsește coloana:** Se folosește `price` implicit
- **Impact:** Dacă diferit de `price`, creează diferență de preț

##### **`inv_price2` - Prețul pentru Factura din Pasul 2:**

- **Când se folosește:** Pentru facturarea în al doilea pas
- **Lipsește coloana:** Se folosește `price` implicit
- **Impact:** Similar cu `inv_price`, dar pentru pasul 2

##### **Logica de Selectare în Cod:**

```python
def get_invoice_price(self, values, step):
    price = values.get("price", 0)
    if step == 1:
        price = values.get("inv_price")  # None dacă nu există
    elif step == 2:
        price = values.get("inv_price2")  # None dacă nu există
    return price

# În metodele de facturare:
inv_price = get_invoice_price(values, current_step)
invoice_line.write({"price_unit": inv_price})
```

##### **Scenarii de Utilizare Prețuri:**

**1. Preț Fix pentru Toate Operațiunile:**

```csv
case_no,type,step,stock_qty,inv_qty,price
10,purchase,1,10,10,100
```

- Recepție la 100 RON + Factură la 100 RON
- **Rezultat:** Fără diferențe de preț

**2. Diferență de Preț în Primul Pas:**

```csv
case_no,type,step,stock_qty,inv_qty,price,inv_price
11,purchase,1,10,10,100,110
```

- Recepție la 100 RON + Factură la 110 RON
- **Rezultat:** Diferență +10 RON/bucată = +100 RON total
- **Impact contabil:** Ajustare pozitivă a stocului

**3. Diferențe de Preț în Ambii Pași:**

```csv
case_no,type,step,stock_qty,inv_qty,price,inv_price,stock_qty2,inv_qty2,inv_price2
12,purchase,2,5,5,100,110,5,5,105
```

- Pas 1: Recepție 5 la 100 + Factură 5 la 110 → Diferență +50 RON
- Pas 2: Recepție 5 la 100 + Factură 5 la 105 → Diferență +25 RON
- **Total:** Diferență +75 RON pentru 10 bucăți

**4. Preț Mai Mic în Al Doilea Pas:**

```csv
case_no,type,step,stock_qty,inv_qty,price,inv_price,stock_qty2,inv_qty2,inv_price2
13,purchase,2,10,10,100,110,0,5,95
```

- Pas 1: Recepție 10 la 100 + Factură 10 la 110 → +100 RON
- Pas 2: Factură suplimentară 5 la 95 → -25 RON (pentru 5 bucăți)
- **Net:** +75 RON diferență

**5. Facturare Fără Recepție cu Preț Diferit:**

```csv
case_no,type,step,stock_qty,inv_qty,price,inv_price,stock_qty2,inv_qty2,inv_price2
14,purchase,2,10,0,100,,0,10,120
```

- Pas 1: Recepție 10 la 100 (fără factură)
- Pas 2: Factură 10 la 120 (fără recepție)
- **Rezultat:** Diferență +20 RON/bucată = +200 RON total

### Coloane Opțiuni Speciale

#### `notice` - Operațiune cu Aviz

- **Scop:** Indică operațiune cu aviz de însoțire
- **Valori:** 0 (fără aviz), 1 (cu aviz)
- **Impact contabil:** Utilizează contul 418100 pentru furnizori nefacturați
- **Utilizare:**

```python
if values.get("notice"):
    picking.l10n_ro_notice = values.get("notice")
```

- **Scenarii românești:**
  - Recepție cu aviz (fără factură încă)
  - Livrare cu aviz (fără factură încă)

#### `reception_in_progress` - Recepție în Progres

- **Scop:** Activează funcționalitatea de recepție în progres
- **Valori:** 0 (dezactivat), 1 (activat)
- **Impact:** Creează automat factură pentru marfa recepționată
- **Utilizare:**

```python
if values.get("reception_in_progress"):
    purchase.action_create_reception_in_progress_invoice()
```

#### `discount` - Reducerea

- **Scop:** Aplicarea unei reduceri procentuale
- **Utilizare:** Doar pentru vânzări

```python
"discount": so_values.get("discount", 0)
```

#### `advance` - Avansul

- **Scop:** Crearea unei facturi de avans
- **Utilizare:** Pentru vânzări cu avans

```python
if so_values.get("advance") != 0:
    # Creează factură de avans
```

#### `landed_cost` - Costuri Suplimentare

- **Scop:** Adaugă costuri de transport/handling
- **Utilizare:** După recepție, pentru ajustarea valorii stocului

### Coloane de Loturi

#### `lot1` / `lot2` - Loturile

- **Scop:** Specifică lotul pentru produse cu tracking
- **Utilizare:** Pentru produse cu `tracking = 'lot'`
- **Diferențiere:** `lot1` pentru pasul 1, `lot2` pentru pasul 2

## Generarea Operațiilor pe Tipuri

### 1. Achiziții (`purchase`)

#### Procesul de generare:

```python
def create_purchase(self, values):
    # 1. Creează order_line cu qty și price
    order_line = [(0, 0, {
        "product_id": po_values["product_id"].id,
        "product_qty": po_values.get("qty", 1),
        "price_unit": po_values.get("price", 80),
    })]

    # 2. Setează locația dacă specificată
    if po_values.get("location", False):
        # Găsește picking_type pentru locația specificată

    # 3. Creează comanda și confirmă
    purchase = self.env["purchase.order"].create(vals)
    purchase.button_confirm()

    # 4. Procesează recepția în progres
    if values.get("reception_in_progress"):
        purchase.action_create_reception_in_progress_invoice()

    # 5. Procesează recepția și facturarea
    self.receive_and_invoice_purchases(purchase, po_values)
```

#### Recepția și facturarea:

```python
def receive_and_invoice_purchases(self, purchases, values):
    # 1. Pentru returnări (stock_qty2 < 0)
    if step == 2 and values.get("stock_qty2") < 0:
        # Creează return picking

    # 2. Pentru recepții normale
    else:
        # Procesează picking-urile
        for picking in pickings:
            # Setează cantitatea done
            stock_qty = values.get("stock_qty", 1)
            picking.move_ids._set_quantity_done(stock_qty)
            picking._action_done()

    # 3. Creează factura dacă inv_qty > 0
    if values.get("inv_qty", 0) > 0:
        invoice = purchase._create_invoices()[0]
        # Ajustează cantitatea și prețul
        invoice_line.write({
            "quantity": inv_qty,
            "price_unit": inv_price
        })
        invoice.action_post()
```

### 2. Vânzări (`sale`)

#### Procesul similar cu achiziții:

```python
def create_sale_order(self, values):
    # 1. Creează order_line
    # 2. Setează warehouse-ul dacă location specificată
    # 3. Confirmă comanda
    # 4. Procesează avansul dacă există
    # 5. Procesează livrarea și facturarea
```

### 3. Transferuri (`transfer`)

#### Transfer direct:

```python
def create_internal_transfer_direct(self, values):
    # 1. Creează stock.move direct între locații
    move_vals = {
        "location_id": transfer_values.get("location").id,
        "location_dest_id": transfer_values.get("location1").id,
        "product_id": transfer_values.get("product_id").id,
        "product_uom_qty": transfer_values.get("qty", 1),
    }
    # 2. Confirmă și procesează
```

#### Transfer prin tranzit:

```python
def create_internal_transfer_transit(self, values):
    # 1. Creează move către locația tranzit
    # 2. Activează regula push pentru destinația finală
    # 3. Procesează ambele mișcări
```

### 4. Consum si Dare in folosinta

```python
def create_stock_picking(self, oper_type, values):
    # 1. Găsește picking_type pentru tipul de operațiune
    domain = [
        ("default_location_src_id", "=", location.id),
        ("default_location_dest_id.usage", "=", oper_type),
    ]

    # 2. Creează picking și move
    # 3. Procesează cantitatea
```

### 5. Inventar (`inventory`)

```python
def create_stock_inventory(self, values):
    # 1. Creează stock.quant cu inventory_mode
    inventory_vals = {
        "product_id": inventory_values["product_id"].id,
        "location_id": inventory_values["location"].id,
        "inventory_quantity": inventory_values.get("stock_qty", 0),
    }
    # 2. Aplică ajustarea
    self.env["stock.quant"].with_context(inventory_mode=True)
        .create(inventory_vals).action_apply_inventory()
```
