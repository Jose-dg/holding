# Frappe/ERPNext Workflows Project

This project implements a custom Frappe/ERPNext application named `workflows` to automate sales and fulfillment of digital pins. It includes multi-company logic, Shopify integration, FIFO serial assignment, and stock-based triggers, with a foundation for Alegra integration.

## Requirements

*   Docker and Docker Compose
*   Git

## Installation

1.  **Clone the repository:**

    ```bash
    git clone <your-repo-url>
    cd <your-repo-name>
    ```

2.  **Create `.env` file:**

    Copy `.env.example` to `.env` and fill in the required environment variables.

    ```bash
    cp .env.example .env
    # Edit .env with your specific values
    ```

3.  **Initialize the project:**

    This will start the database and redis services.

    ```bash
    make init
    ```

4.  **Build the Docker image:**

    ```bash
    make build-image
    ```

5.  **Run initial setup:**

    This will create the Frappe site, install ERPNext and the `workflows` app, run migrations, build assets, and clear cache.

    ```bash
    make setup
    ```

6.  **Start all services:**

    ```bash
    make up
    ```

## Accessing the Application

The ERPNext frontend should be accessible at `http://localhost:8081`.

*   **Username:** Administrator
*   **Password:** (as set in your `.env` file, default `admin`)

## How to Test the Shopify Webhook

To test the Shopify webhook, you'll need to simulate a signed webhook request. This involves calculating the HMAC-SHA256 signature of the payload using your `SHOPIFY_WEBHOOK_SECRET` (configured in `Shopify Settings` DocType within ERPNext).

1.  **Get your `SHOPIFY_WEBHOOK_SECRET`:** Once ERPNext is running, navigate to `Shopify Settings` (you'll need to create an instance of this DocType) and retrieve the secret.

2.  **Prepare a sample Shopify order payload:** This is a JSON object representing a Shopify order.

3.  **Calculate the HMAC:** Use a tool or script to calculate the `HMAC-SHA256` of your payload using the secret.

4.  **Send the `curl` request:**

    ```bash
    PAYLOAD='{"id": 12345, "email": "test@example.com", ...}' # Your Shopify order JSON
    HMAC_SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "YOUR_SHOPIFY_WEBHOOK_SECRET" -binary | base64)

    curl -X POST \
         -H "Content-Type: application/json" \
         -H "X-Shopify-Hmac-Sha256: $HMAC_SIGNATURE" \
         -d "$PAYLOAD" \
         http://localhost:8081/api/method/workflows.api.shopify.handle_shopify_order
    ```

    *Replace `YOUR_SHOPIFY_WEBHOOK_SECRET` and `PAYLOAD` with your actual values.*

## Troubleshooting

*   **`ModuleNotFoundError` or `bench` commands failing:** Ensure your Docker image is built correctly and the `workflows` app is properly installed and migrated. Check `make setup` logs.
*   **Workers not processing queues:** Verify that `queue-short`, `queue-long`, and `scheduler` services are running (`make logs`).
*   **Invalid HMAC:** Double-check your `SHOPIFY_WEBHOOK_SECRET` in ERPNext and ensure the HMAC calculation in your test script is correct.

## Development Checklist

*   [ ] `docker compose run --rm setup` creates the site and installs `workflows` without errors.
*   [ ] `docker compose up -d` brings up all services and `http://localhost:8081` responds.
*   [ ] `bench --site $(SITE_NAME) list-apps` shows `workflows`.
*   [ ] `curl` to the Shopify webhook endpoint with a valid HMAC returns 200/202 and creates a Sales Invoice.
*   [ ] Workers process `short` and `long` queues.
*   [ ] Pytest tests run (even if stubs) and CI executes them.
