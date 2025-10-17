from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any, Dict

import frappe
from frappe import _
from frappe.utils import now
from werkzeug.wrappers import Response


def _get_shopify_secret(company: str) -> str:
    # Shopify Settings (custom doctype en fixture)
    settings = frappe.get_all(
        "Shopify Settings",
        filters={"company": company},
        fields=["name", "webhook_secret"],
        limit=1,
    )
    if not settings:
        frappe.throw(_("Shopify Settings not configured for company: {0}").format(company), exc=frappe.ValidationError)
    doc = frappe.get_doc("Shopify Settings", settings[0]["name"])
    return doc.webhook_secret


def _verify_hmac(raw_body: bytes, provided_hmac: str, secret: str) -> bool:
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
    calc = base64.b64encode(digest).decode()
    # Timing-safe compare
    return hmac.compare_digest(calc, provided_hmac)


def _log_integration(request_id: str, status: str, data: Dict[str, Any]):
    # Usa Integration Request como "Integration Log" (estándar ERPNext)
    frappe.get_doc(
        {
            "doctype": "Integration Request",
            "integration_type": "Remote",
            "status": status,
            "reference_doctype": "Sales Invoice",
            "request_id": request_id,
            "data": json.dumps(data, ensure_ascii=False),
            "output": "",
            "error": "",
        }
    ).insert(ignore_permissions=True)


def _enqueue_fulfillment(inv_name: str):
    frappe.enqueue(
        "workflows.workflows.events.fulfillment.process_invoice",
        queue="short",
        timeout=300,
        is_async=True,
        kwargs={"invoice": inv_name},
    )


@frappe.whitelist(allow_guest=True, methods=["POST"])
def handle_shopify_order():
    """
    Webhook firmado (X-Shopify-Hmac-Sha256).
    Payload esperado (mínimo):
      {
        "company": "B",            # B/C/D quien vende al cliente final
        "order_id": "123456789",
        "request_ts": "2025-10-15T15:00:00Z",
        "items": [{"item_code":"PIN-PS-50","qty":1,"rate":250000}],
        "customer": {"name":"Juan Perez","email":"juan@x.com","mobile":"+57..."}
      }
    """
    raw = frappe.request.get_data(as_text=False)  # bytes
    provided_hmac = frappe.get_request_header("X-Shopify-Hmac-Sha256") or ""
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception:  # noqa: BLE001
        return Response(response="Invalid JSON", status=400)

    company = data.get("company")
    order_id = str(data.get("order_id"))
    request_id = f"{company}:{order_id}"

    # Idempotencia: si ya procesamos request_id, no duplicar
    if frappe.db.exists("Integration Request", {"request_id": request_id}):
        return Response(response="OK (idempotent)", status=200)

    try:
        secret = _get_shopify_secret(company)
        if not _verify_hmac(raw, provided_hmac, secret):
            _log_integration(request_id, "Invalid", {"reason": "Invalid HMAC", "ts": now()})
            return Response(response="Invalid HMAC", status=401)

        # Crea Sales Invoice en compañía B/C/D
        inv = frappe.get_doc(
            {
                "doctype": "Sales Invoice",
                "company": company,
                "customer": data.get("customer", {}).get("name") or "Guest",
                "posting_date": now().split(" ")[0],
                "set_posting_time": 1,
                "items": [
                    {
                        "item_code": row["item_code"],
                        "qty": row["qty"],
                        "rate": row["rate"],
                    }
                    for row in data.get("items", [])
                ],
                "remarks": f"Shopify Order {order_id}",
                "flags": {"ignore_permissions": True},
            }
        )
        inv.insert(ignore_permissions=True)
        inv.submit()

        _log_integration(request_id, "Completed", {"invoice": inv.name, "ts": now()})
        _enqueue_fulfillment(inv.name)
        return Response(response="Accepted", status=202)
    except frappe.ValidationError as ve:
        _log_integration(request_id, "Invalid", {"error": str(ve)})
        return Response(response=str(ve), status=422)
    except Exception as e:  # noqa: BLE001
        _log_integration(request_id, "Failed", {"error": str(e)})
        return Response(response="Internal Error", status=500)
