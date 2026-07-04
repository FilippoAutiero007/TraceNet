# Sentinel Journal

## 2025-07-04 - CORS Regex Subdomain Suffixing
**Vulnerability:** Unanchored regex in CORS configuration allowed origins like `https://tracenet.vercel.app.attacker.com` to match `r"https://(?:tracenet|nettrace)(?:-git-[^.]+)?\.vercel\.app"`.
**Learning:** Starlette's `CORSMiddleware` uses `re.match` for regex validation. `re.match` only anchors to the start of the string, not the end. Without a trailing `$`, any string starting with a valid origin will pass.
**Prevention:** Always anchor security-critical regexes with `$` to ensure the entire string matches the expected pattern.

## 2025-07-04 - Memory-Exhaustion DoS in File Uploads
**Vulnerability:** Endpoints receiving `UploadFile` were reading the entire file into memory using `await file.read()` without size validation.
**Learning:** FastAPI/Starlette `UploadFile` objects have a `.size` attribute that can be used for pre-read validation.
**Prevention:** Enforce strict file size limits on all upload endpoints before performing any memory-intensive operations.
