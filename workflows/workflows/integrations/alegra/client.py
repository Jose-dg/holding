from __future__ import annotations

import requests
from typing import Any, Dict

import frappe


class AlegraClient:
    def __init__(self, company: str, timeout: int = 15):
        name = frappe.db.get_value("Alegra Settings", {"company": company}, "name")
        if not name:
            frappe.throw(f"Alegra Settings not configured for company {company}")
        doc = frappe.get_doc("Alegra Settings", name)
        self.base_url = "https://api.alegra.com/api/v1"
        self.auth = (doc.alegra_user, doc.get_password("alegra_token"))
        self.timeout = timeout

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        resp = requests.request(method, url, auth=self.auth, timeout=self.timeout, **kwargs)
        if resp.status_code >= 400:
            raise frappe.ValidationError(f"Alegra error {resp.status_code}: {resp.text}")
        return resp.json()

    # Ejemplos
    def create_invoice(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/invoices", json=payload)

    def get_contact(self, contact_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/contacts/{contact_id}")
