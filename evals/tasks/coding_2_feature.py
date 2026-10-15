"""Medium: implement a feature that spans three modules of a small package, keeping existing tests green."""
import subprocess
import textwrap

AREA = "coding"
TITLE = "Multi-module feature: discounts + CSV export in shop package"
KIND = "agent"
TIMEOUT = 1500

PROMPT = """Implement the feature described in FEATURE.md in the `shop` package. The existing tests in
tests/ must keep passing, and add tests for the new behaviour in tests/test_feature.py.
Run the whole suite with `python3 -m unittest discover -s tests -v` and make sure everything passes.
Standard library only."""

FILES = {
    "FEATURE.md": """
        # Feature: discount rules and CSV export

        1. `shop/discounts.py` (new): a `Discount` dataclass with fields `code: str`, `percent: float`
           (0 < percent <= 100) and `min_total: float = 0.0`. Constructing one with an invalid percent
           raises `ValueError`.
        2. `Cart.apply_discount(discount)` in `shop/cart.py`: stores the discount. Only one discount can be
           active; applying a second replaces the first. `Cart.total()` returns the subtotal minus the
           discount, but only when the subtotal is >= `min_total` (otherwise no discount). Totals are
           rounded to 2 decimals (round half up, use `decimal`).
        3. `shop/export.py`: `to_csv(cart) -> str` returns CSV text with header `sku,name,qty,unit_price,line_total`,
           one row per line item in insertion order, then a final row `,,,discount,<amount>` (amount as a
           negative number with 2 decimals, `0.00` if no discount applies) and `,,,total,<total>`.
           Prices are formatted with exactly 2 decimals. Use the `csv` module, `\\n` line endings.
        """,
    "shop/__init__.py": "",
    "shop/catalog.py": """
        from dataclasses import dataclass


        @dataclass(frozen=True)
        class Product:
            sku: str
            name: str
            price: float
        """,
    "shop/cart.py": """
        from .catalog import Product


        class Cart:
            def __init__(self):
                self.items = {}  # sku -> [product, qty]

            def add(self, product: Product, qty: int = 1):
                if qty <= 0:
                    raise ValueError("qty must be positive")
                if product.sku in self.items:
                    self.items[product.sku][1] += qty
                else:
                    self.items[product.sku] = [product, qty]

            def subtotal(self) -> float:
                return round(sum(p.price * q for p, q in self.items.values()), 2)

            def total(self) -> float:
                return self.subtotal()
        """,
    "tests/__init__.py": "",
    "tests/test_cart.py": """
        import unittest
        from shop.catalog import Product
        from shop.cart import Cart


        class CartTest(unittest.TestCase):
            def test_add_and_subtotal(self):
                c = Cart()
                c.add(Product("A1", "Apple", 0.5), 4)
                c.add(Product("B2", "Bread", 2.25))
                self.assertEqual(c.subtotal(), 4.25)

            def test_merge_same_sku(self):
                c = Cart()
                p = Product("A1", "Apple", 0.5)
                c.add(p, 2); c.add(p, 3)
                self.assertEqual(c.items["A1"][1], 5)

            def test_rejects_bad_qty(self):
                with self.assertRaises(ValueError):
                    Cart().add(Product("A1", "Apple", 0.5), 0)
        """,
}

HIDDEN = r'''
import sys, csv, io
sys.path.insert(0, ".")
from shop.catalog import Product
from shop.cart import Cart
from shop.discounts import Discount
from shop.export import to_csv
ok = []
def check(name, cond):
    ok.append((name, bool(cond)))
for bad in (0, -5, 100.5):
    try:
        Discount("X", bad); check(f"invalid percent {bad}", False)
    except ValueError:
        check(f"invalid percent {bad}", True)
c = Cart(); c.add(Product("A1", "Apple", 0.5), 4); c.add(Product("B2", "Bread", 2.25))
check("no discount total", c.total() == 4.25)
c.apply_discount(Discount("TEN", 10))
check("10% total", c.total() == 3.83)
c.apply_discount(Discount("BIG", 50, min_total=100))
check("replaced + min_total not met", c.total() == 4.25)
c2 = Cart(); c2.add(Product("C3", "Cheese", 10.0), 1); c2.apply_discount(Discount("HALF", 50, min_total=10))
check("min_total met exactly", c2.total() == 5.0)
c3 = Cart(); c3.add(Product("D", "D", 0.125), 1); c3.apply_discount(Discount("Z", 10))
check("round half up", c3.total() == 0.11)
text = to_csv(c2)
rows = list(csv.reader(io.StringIO(text)))
check("header", rows[0] == ["sku", "name", "qty", "unit_price", "line_total"])
check("line row", rows[1] == ["C3", "Cheese", "1", "10.00", "10.00"])
check("discount row", rows[-2] == ["", "", "", "discount", "-5.00"])
check("total row", rows[-1] == ["", "", "", "total", "5.00"])
check("no CRLF", "\r\n" not in text)
c4 = Cart(); c4.add(Product("E", "E", 1.0), 2)
rows4 = list(csv.reader(io.StringIO(to_csv(c4))))
check("no-discount row", rows4[-2] == ["", "", "", "discount", "0.00"])
print(sum(v for _, v in ok), len(ok), ";".join(n for n, v in ok if not v))
'''


def setup(ws):
    for rel, body in FILES.items():
        p = ws / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(body).lstrip("\n"))


def grade(ws):
    hidden = subprocess.run(["python3", "-E", "-s", "-c", HIDDEN], cwd=ws, capture_output=True, text=True, timeout=60)
    try:
        parts = hidden.stdout.strip().split(" ", 2)
        ok, total = int(parts[0]), int(parts[1])
        failed = parts[2] if len(parts) > 2 else ""
    except (ValueError, IndexError):
        return {"score": 0.0, "passed": False, "notes": f"hidden tests crashed: {hidden.stderr.strip()[-200:]}"}
    suite = subprocess.run(["python3", "-E", "-s", "-m", "unittest", "discover", "-s", "tests"], cwd=ws,
                           capture_output=True, text=True, timeout=120)
    suite_ok = suite.returncode == 0
    has_new_tests = (ws / "tests/test_feature.py").exists()
    score = 0.75 * ok / total + 0.15 * suite_ok + 0.10 * has_new_tests
    return {"score": round(score, 3), "passed": ok == total and suite_ok and has_new_tests,
            "notes": f"hidden {ok}/{total}" + (f" failed: {failed}" if failed else "") +
                     f"; suite {'pass' if suite_ok else 'FAIL'}; new tests {'yes' if has_new_tests else 'no'}"}
