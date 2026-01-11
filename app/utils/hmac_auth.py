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
    return hmac.compare_digest(expected, signature)
