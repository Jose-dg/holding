import pytest


@pytest.fixture
def sample_payload():
    return {
        "company": "B",
        "order_id": "T-001",
        "items": [{"item_code": "PIN-PS-50", "qty": 1, "rate": 250000}],
        "customer": {"name": "Juan", "email": "juan@example.com"},
    }
