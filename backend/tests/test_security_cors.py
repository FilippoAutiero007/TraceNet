from app.main import origin_regex
import re

def test_cors_origin_regex_vulnerability():
    """
    Test that the CORS origin regex does NOT match subdomain suffixing bypasses.
    This test will FAIL if the vulnerability is present.
    """
    malicious_origin = "https://tracenet.vercel.app.attacker.com"

    # re.match is what Starlette's CORSMiddleware uses.
    is_match = re.match(origin_regex, malicious_origin) is not None

    assert not is_match, (
        f"SECURITY VULNERABILITY: CORS regex '{origin_regex}' matches malicious origin '{malicious_origin}'. "
        "It should be anchored with '$' at the end."
    )

def test_cors_origin_regex_valid_match():
    """Test that valid origins matching the regex are still accepted."""
    valid_origins = [
        "https://tracenet.vercel.app",
        "https://nettrace.vercel.app",
        "https://tracenet-git-main-user.vercel.app",
        "https://nettrace-git-feat-test.vercel.app",
    ]

    for origin in valid_origins:
        assert re.match(origin_regex, origin) is not None, f"Valid origin {origin} should match"
