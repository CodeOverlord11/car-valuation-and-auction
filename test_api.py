import urllib.request
import urllib.error
import json

def test_evaluate():
    url = "http://localhost:8000/api/evaluate"
    data = {
        "brand": "Tesla",
        "model": "Model Y",
        "year": 2024,
        "mileage": 8000,
        "condition": "excellent",
        "fuel_type": "Electric",
        "transmission": "Automatic"
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode("utf-8"))
            print("=== VALUATION API SUCCESS ===")
            print(f"Estimated Value: ${res['estimated_value']:,}")
            print(f"Base Value: ${res['base_value']:,}")
            print("Contributions:")
            for c in res['contributions']:
                print(f"  - {c['display_name']}: ${c['contribution']:,} ({c['explanation']})")
            print(f"Justification: {res['justification']}")
    except urllib.error.HTTPError as e:
        print(f"Valuation API failed: {e.code} - {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"Valuation API error: {e}")

def test_pdf():
    url = "http://localhost:8000/api/evaluate/pdf"
    data = {
        "brand": "Tesla",
        "model": "Model Y",
        "year": 2024,
        "mileage": 8000,
        "condition": "excellent",
        "fuel_type": "Electric",
        "transmission": "Automatic"
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as response:
            pdf_content = response.read()
            if pdf_content.startswith(b"%PDF"):
                print("=== PDF API SUCCESS ===")
                print(f"PDF Size: {len(pdf_content)} bytes")
            else:
                print("PDF API failed: Output does not start with %PDF header")
    except urllib.error.HTTPError as e:
        print(f"PDF API failed: {e.code} - {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"PDF API error: {e}")

if __name__ == "__main__":
    test_evaluate()
    print()
    test_pdf()
