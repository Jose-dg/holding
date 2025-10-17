from __future__ import annotations

import contextlib
from typing import Iterable

import frappe
from frappe import _


def _copy_items(doc):
    return [
        {
            "item_code": it.item_code,
            "qty": it.qty,
            "rate": it.rate,
            "uom": it.uom,
            "conversion_factor": it.conversion_factor,
        }
        for it in doc.items
    ]


def _atomic(fn):
    def wrapper(*args, **kwargs):
        savepoint = "wf_ic_sp"
        frappe.db.savepoint(savepoint)
        try:
            res = fn(*args, **kwargs)
            return res
        except Exception:
            frappe.db.rollback(savepoint=savepoint)
            raise
    return wrapper


@_atomic
def on_submit_sales_invoice(doc, _method=None):
    """
    Si la factura es de B/C/D → crea SI en A y PI en B/C/D de forma atómica.
    Guarda referencias cruzadas (linked_invoice).
    """
    selling_company = doc.company
    if selling_company not in {"Money for gamers", "Laboratorio Clinica del Play"}:
        return

    central_company = "Diem"
    items = _copy_items(doc)

    # Validación simple de stock (puedes endurecerla con reservas/seriales)
    for it in items:
        with contextlib.suppress(Exception):
            bal = frappe.db.get_value("Bin", {"item_code": it["item_code"], "warehouse": f"{central_company} - WH"}, "actual_qty")
            if bal is not None and float(bal) < float(it["qty"]):
                frappe.throw(_("Insufficient stock for item {0}").format(it["item_code"]))

    # Crea Sales Invoice en A (venta intercompañía a B/C/D)
    si_a = frappe.get_doc(
        {
            "doctype": "Sales Invoice",
            "company": central_company,
            "customer": selling_company,
            "items": items,
            "remarks": f"Intercompany sale for {selling_company} - source {doc.name}",
            "flags": {"ignore_permissions": True},
        }
    )
    si_a.insert(ignore_permissions=True)
    si_a.submit()

    # Crea Purchase Invoice en B/C/D (compra a A)
    pi_retail = frappe.get_doc(
        {
            "doctype": "Purchase Invoice",
            "company": selling_company,
            "supplier": central_company,
            "items": [
                {
                    "item_code": it["item_code"],
                    "qty": it["qty"],
                    "rate": it["rate"],
                }
                for it in items
            ],
            "remarks": f"Intercompany purchase from {central_company} - source {doc.name}",
            "flags": {"ignore_permissions": True},
        }
    )
    pi_retail.insert(ignore_permissions=True)
    pi_retail.submit()

    # Referencias cruzadas
    doc.db_set("linked_invoice", si_a.name, update_modified=False)
    si_a.db_set("remarks", (si_a.remarks or "") + f"\nLinked Retail SI: {doc.name}", update_modified=False)
