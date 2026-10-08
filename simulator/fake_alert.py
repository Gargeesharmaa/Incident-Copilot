import requests

URL = "http://localhost:8000/webhook/alert"

checkout = {
    "service": "checkout-service",
    "alert": "High 5xx error rate",
    "value": "8%",
    "threshold": "5%",
}
payment = {
    "service": "payment-service",
    "alert": "High latency p95",
    "value": "2300ms",
    "threshold": "800ms",
}


def send_alert(data):
    """Sends a JSON payload and safely prints the response."""
    try:
        r = requests.post(URL, json=data)
        print(f"Status Code: {r.status_code}")

        if not r.text.strip():
            print("Response Body: <Empty>")
            return

        try:
            print("Response JSON:", r.json())
        except requests.exceptions.JSONDecodeError:
            print("Response Raw Text:", repr(r.text))

    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to {URL}. Is your server running?")


if __name__ == "__main__":
    print("--- burst: same alert x5 ---")
    for _ in range(5):
        send_alert(checkout)

    print("\n--- different alert ---")
    send_alert(payment)