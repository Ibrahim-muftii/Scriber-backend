"""
Test with the actual payload (user ID) from frontend
"""

import hmac
import hashlib

SECRET = "QUxMQV9JU19XQVRDSElOR19VU19GUk9NX0FCT1ZF"
timestamp = "1768167595711"
payload = "67fba7f6f9d436d229e87626"  # User ID from frontend
expected_signature = "b0aab65c535d5354611d49aed9934e1fa0f0239bfd8f23d36c8fc4dba4f984f8"

# Generate signature
data = f"{timestamp}:{payload}"
generated_signature = hmac.new(SECRET.encode(), data.encode(), hashlib.sha256).hexdigest()

print("=== HMAC Verification Test ===")
print(f"Secret: {SECRET}")
print(f"Timestamp: {timestamp}")
print(f"Payload (User ID): '{payload}'")
print(f"Data to sign: '{data}'")
print()
print(f"Generated signature: {generated_signature}")
print(f"Expected signature:  {expected_signature}")
print()
print(f"✓ MATCH: {generated_signature == expected_signature}")
