import hmac
import hashlib

SECRET = "QUxMQV9JU19XQVRDSElOR19VU19GUk9NX0FCT1ZF"

def verify(payload, timestamp, signature):
    """
    Verify HMAC signature for request authentication.
    
    Args:
        payload: Request payload as string
        timestamp: Unix timestamp as string
        signature: HMAC signature from client
        
    Returns:
        bool: True if signature is valid, False otherwise
    """
    data = f"{timestamp}:{payload}"
    expected = hmac.new(SECRET.encode(), data.encode(), hashlib.sha256).hexdigest()
    
    # Debug logging
    print(f"HMAC Debug:")
    print(f"  Timestamp: {timestamp}")
    print(f"  Payload: '{payload}'")
    print(f"  Data to sign: '{data}'")
    print(f"  Expected signature: {expected}")
    print(f"  Received signature: {signature}")
    print(f"  Match: {hmac.compare_digest(expected, signature)}")
    
    return hmac.compare_digest(expected, signature)
