# Sentinel's Security Journal 🛡️

## 2025-05-14 - CORS Origin Regex Subdomain Suffixing Bypass
**Vulnerability:** The `CORSMiddleware` in `backend/app/main.py` used an unanchored regex (`r"https://(?:tracenet|nettrace)(?:-git-[^.]+)?\.vercel\.app"`) for origin validation. This allowed an attacker to bypass CORS by using a domain like `tracenet.vercel.app.attacker.com`, as `re.match` (used by Starlette) would match the prefix.
**Learning:** Starlette's `CORSMiddleware` uses `re.match`, which only checks from the beginning of the string. Without a `$` anchor, any origin starting with a valid domain would be accepted.
**Prevention:** Always anchor security-critical regexes with `$` when using `re.match` or `CORSMiddleware` origin validation.

## 2025-05-14 - Missing Upload File Size Validation (DoS)
**Vulnerability:** The `/analyze-pkt` and `/analyze-pkt-report` endpoints lacked file size limits, allowing potential Denial-of-Service attacks by uploading extremely large files that would be read into memory.
**Learning:** FastAPI's `UploadFile` provides a `.size` attribute that can be used for quick validation before consuming the file stream.
**Prevention:** Implement explicit file size limits on all file upload endpoints using `file.size`.
