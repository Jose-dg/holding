from __future__ import annotations

from typing import List

import frappe
from frappe import _
from frappe.utils import now


def _reserve_serials_fifo(item_code: str, qty: float) -> List[str]:
    """Devuelve lista de seriales FIFO disponibles (simplificado)."""
    serials = frappe.get_all(
        "Serial No",
        filters={"item_code": item_code, "status": "Active"},
        fields=["name", "creation"],
        order_by="creation asc",
        limit=int(qty),
    )
    return [s["name"] for s in serials]

def _send_email(company: str, recipient: str, subject: str, content: str):
    frappe.sendmail(
        recipients=[recipient],
        subject=subject,
        message=content,
    )

def process_invoice(invoice: str):
    """
    Asigna seriales FIFO y envía email por plantilla por compañía.
    Si no hay stock: marca Awaiting Stock y crea Sales Order en A.
    """
    inv = frappe.get_doc("Sales Invoice", invoice)
    if inv.docstatus != 1:
      return

    missing = []
    allocated = {}

    for it in inv.items:
        needed = int(it.qty)
        got = _reserve_serials_fifo(it.item_code, needed)
        if len(got) < needed:
            missing.append((it.item_code, needed - len(got)))
        else:
            allocated[it.item_code] = got

    if missing:
        inv.db_set("status", "Awaiting Stock", update_modified=False)
        # Crea SO en A para reponer
        so = frappe.get_doc(
            {
                "doctype": "Sales Order",
                "company": "Diem",
                "customer": inv.company,
                "delivery_date": now(),
                "items": [{"item_code": ic, "qty": q} for ic, q in missing],
                "flags": {"ignore_permissions": True},
            }
        )
        so.insert(ignore_permissions=True)
        return

    # Renderiza contenido simple (puedes reemplazar por plantilla por compañía)
    email = inv.contact_email or inv.contact_person or ""
    if email:
        lines = []
        for item_code, serials in allocated.items():
            lines.append(f"<p><b>{item_code}</b>: {', '.join(serials)}</p>")
        content = "<h3>Tus pines</h3>" + "".join(lines)
        _send_email(inv.company, email, f"Entrega de pines - {inv.name}", content)


def try_pending(doc, _method=None):
    """Reintenta pendientes cuando hay movimiento de stock/serial."""
    # Reintento simple: procesa todas las SI con status Awaiting Stock por orden antiguo
    names = frappe.get_all(
        "Sales Invoice",
        filters={"status": "Awaiting Stock", "docstatus": 1},
        fields=["name"],
        order_by="creation asc",
        limit=50,
    )
    for row in names:
        frappe.enqueue(
            "workflows.workflows.events.fulfillment.process_invoice",
            queue="short",
            is_async=True,
            kwargs={"invoice": row["name"]},
        )
