"""
Mint a pre-signed (read) URL for a file in a UiPath Orchestrator Storage Bucket,
then VERIFY the Content-Type the signed URL actually serves.

WHY the verify step: the PDF reaches WhatsApp but won't open ("no proper app for
viewing this content") when the blob is served as application/octet-stream instead
of application/pdf. A desktop browser sniffs the bytes and opens it anyway, which
hides the problem. This script fetches the minted URL's headers and tells you the
real Content-Type, so you know BEFORE wiring it into Twilio whether the phone will
open it.

SECURITY: never hardcode the bearer token. Set it as an env var:
    PowerShell:  $env:UIPATH_TOKEN="<token>"
    bash:        export UIPATH_TOKEN="<token>"
If you previously pasted a token into a file, rotate/revoke it.
"""
import os
import ssl
import json
import urllib.parse
import urllib.request
import urllib.error

# ---- config (env-overridable; non-secret defaults from your screenshots) ----
ORG_TENANT = os.environ.get(
    "UIPATH_ORG_TENANT",
    "https://staging.uipath.com/0a4588ad-5058-46df-b939-4af72e0be6ed/8b8bd555-2c55-413e-83b5-e63b6043292d",
)
BUCKET_ID  = int(os.environ.get("UIPATH_BUCKET_ID", "217194"))   # foreman-context
FOLDER_ID  = os.environ.get("UIPATH_FOLDER_ID", "3118920")       # Shared/foremen v1
BLOB_PATH  = os.environ.get("UIPATH_BLOB_PATH", "mc4-connector-install-spec.pdf")
EXPIRY_MIN = int(os.environ.get("UIPATH_EXPIRY_MIN", "20"))
TOKEN      = os.environ.get("UIPATH_TOKEN", "eyJhbGciOiJSUzI1NiIsImtpZCI6IkI5M0U5RjU0RENBRkY4OTJCNkMyMjE2NDNGN0FGNzFFMzJCODdDNjEiLCJ4NXQiOiJ1VDZmVk55di1KSzJ3aUZrUDNyM0hqSzRmR0UiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3N0YWdpbmcudWlwYXRoLmNvbS9pZGVudGl0eV8iLCJuYmYiOjE3ODI0MjI2MjYsImlhdCI6MTc4MjQyMjkyNiwiZXhwIjoxNzgyNDI2NTI2LCJhdWQiOlsiUHJvY2Vzc01pbmluZyIsIk9yY2hlc3RyYXRvckFwaVVzZXJBY2Nlc3MiLCJTdHVkaW9XZWJCYWNrZW5kIiwiSWRlbnRpdHlTZXJ2ZXJBcGkiLCJDb25uZWN0aW9uU2VydmljZSIsIkRhdGFTZXJ2aWNlIiwiRGF0YVNlcnZpY2VBcGlVc2VyQWNjZXNzIiwiRG9jdW1lbnRVbmRlcnN0YW5kaW5nIiwiVWlQYXRoLkRvY3VtZW50VW5kZXJzdGFuZGluZyIsIkVudGVycHJpc2VDb250ZXh0U2VydmljZSIsIkphbUphbUFwaSIsIkxMTUdhdGV3YXkiLCJMTE1PcHMiLCJPTVMiLCJSZXNvdXJjZUNhdGFsb2dTZXJ2aWNlQXBpIiwiVGVzdE1hbmFnZXIiLCJBdXRvbWF0aW9uU29sdXRpb25zIiwiQXV0b21hdGlvblRyYWNrZXJBcGkiLCJEb2NzLkdQVC5TZWFyY2guQXBpIl0sInNjb3BlIjpbIlByb2Nlc3NNaW5pbmciLCJPcmNoZXN0cmF0b3JBcGlVc2VyQWNjZXNzIiwiU3R1ZGlvV2ViQmFja2VuZCIsIklkZW50aXR5U2VydmVyQXBpIiwiQ29ubmVjdGlvblNlcnZpY2UiLCJEYXRhU2VydmljZSIsIkRhdGFTZXJ2aWNlQXBpVXNlckFjY2VzcyIsIkRvY3VtZW50VW5kZXJzdGFuZGluZyIsIkR1LkRpZ2l0aXphdGlvbi5BcGkiLCJEdS5DbGFzc2lmaWNhdGlvbi5BcGkiLCJEdS5FeHRyYWN0aW9uLkFwaSIsIkR1LlZhbGlkYXRpb24uQXBpIiwiRW50ZXJwcmlzZUNvbnRleHRTZXJ2aWNlIiwiRGlyZWN0b3J5IiwiSmFtSmFtQXBpIiwiTExNR2F0ZXdheSIsIkxMTU9wcyIsIk9NUyIsIlJDUy5Gb2xkZXJBdXRob3JpemF0aW9uIiwiVE0uUHJvamVjdHMiLCJUTS5UZXN0Q2FzZXMiLCJUTS5SZXF1aXJlbWVudHMiLCJUTS5UZXN0U2V0cyIsIkF1dG9tYXRpb25Tb2x1dGlvbnMiLCJBVC5UcmFja09wZXJhdGlvbnMiLCJEb2NzLkdQVC5TZWFyY2giLCJvZmZsaW5lX2FjY2VzcyJdLCJhbXIiOlsiZXh0ZXJuYWwiXSwic3ViX3R5cGUiOiJ1c2VyIiwiY2xpZW50X2lkIjoiMzZkZWE1YjgtZThiYi00MjNkLThlN2ItYzgwOGRmOGYxYzAwIiwic3ViIjoiNmViMTc0YjEtYmJjZi00ZTIyLWE1ZDctYjNlMDZlZjY1MGIzIiwiYXV0aF90aW1lIjoxNzgyMjc3MTM0LCJpZHAiOiJhdXRoMHxiYXNpYyIsImVtYWlsIjoiYWRpdHlhLnByYXRhcC5zaW5naEBwd2MuY29tIiwiQXNwTmV0LklkZW50aXR5LlNlY3VyaXR5U3RhbXAiOiJPUjJKSFpOUUREVkY3R0JDNE1JVDZYTVNWQzVMUlNPQSIsImF1dGgwX2NvbiI6IlVzZXJuYW1lLVBhc3N3b3JkLUF1dGhlbnRpY2F0aW9uIiwiZXh0X3N1YiI6ImF1dGgwfDY4NGJjYjExMWQ3NWVhY2EwMTZmZmM5YyIsInBydF9pZCI6IjBhNDU4OGFkLTUwNTgtNDZkZi1iOTM5LTRhZjcyZTBiZTZlZCIsImhvc3QiOiJGYWxzZSIsImZpcnN0X25hbWUiOiJBZGl0eWEiLCJsYXN0X25hbWUiOiJTaW5naCIsInByZWZlcnJlZF91c2VybmFtZSI6ImFkaXR5YS5wcmF0YXAuc2luZ2hAcHdjLmNvbSIsIm5hbWUiOiJhZGl0eWEucHJhdGFwLnNpbmdoQHB3Yy5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiZXh0X2lkcF9pZCI6IjEiLCJleHRfaWRwX2Rpc3BfbmFtZSI6Ikdsb2JhbElkcCIsInNpZCI6IjlEMzJCQ0I1QzFGNENERDFCMUZEODI0NTZDRTFGRjIwIn0.aF-Ir25QW1ZpIRRYw_VaqyA6udqzZmiFmgcH_nTpswSPW9WpWojc6OKRSZ6IS6cL34DxVa5oUhLPvrAjbwTyuvG1ZqUTZl5eXBQlV2OhFj1jOb0M-H5eUJirVCQDhDxposqrBAIDXLTMax_TN9qIOWqBTOQLCkmeykCCadW6Y6gztcrd7w5Z4EAzWUpN0uBxPTSYNJzq3LLYnxUdjaUhgIa5L7imPSd5KC_mhVmxowV9CpHMR2oylEAJCvnZR1SqCyAPF5TxsXUu_EZCyDOs3IQSdowRwsGxSKtGPs_sMUhxGrKTnhq7zT8Yq8QEDVAORWsYyNi8KfjzHCuztlymcw")
VERIFY_SSL = os.environ.get("UIPATH_VERIFY_SSL", "1") != "0"
# ----------------------------------------------------------------------------

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _ssl_ctx():
    if VERIFY_SSL:
        return None
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _ctx_kwargs():
    ctx = _ssl_ctx()
    return {"context": ctx} if ctx is not None else {}


def get_read_uri():
    base = (
        f"{ORG_TENANT}/orchestrator_/odata/Buckets({BUCKET_ID})"
        f"/UiPath.Server.Configuration.OData.GetReadUri"
    )
    qs = urllib.parse.urlencode({"path": BLOB_PATH, "expiryInMinutes": EXPIRY_MIN})
    url = f"{base}?{qs}"

    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("X-UIPATH-OrganizationUnitId", str(FOLDER_ID))
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", BROWSER_UA)
    req.add_header("Accept-Language", "en-US,en;q=0.9")
    req.add_header("Referer", f"{ORG_TENANT}/orchestrator_/")
    req.add_header("Origin", ORG_TENANT.split("/orchestrator_")[0])

    with urllib.request.urlopen(req, timeout=30, **_ctx_kwargs()) as resp:
        body = resp.read().decode("utf-8", "ignore")
    data = json.loads(body)
    return data.get("Uri") or data.get("uri")


def inspect_url(url):
    """Fetch the signed URL's headers (and a few bytes) to read what Azure SERVES.
    Returns (status, content_type, content_length, first_bytes_are_pdf)."""
    # Azure SAS URLs are public; a plain GET with Range avoids downloading the whole file.
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", BROWSER_UA)
    req.add_header("Range", "bytes=0-7")  # just the %PDF- magic header
    try:
        with urllib.request.urlopen(req, timeout=30, **_ctx_kwargs()) as resp:
            status = resp.status
            ctype = resp.headers.get("Content-Type", "(none)")
            clen = resp.headers.get("Content-Range") or resp.headers.get("Content-Length") or "?"
            head = resp.read(8)
    except urllib.error.HTTPError as e:
        # Some setups reject Range; retry without it (reads more but still works)
        req2 = urllib.request.Request(url, method="GET")
        req2.add_header("User-Agent", BROWSER_UA)
        with urllib.request.urlopen(req2, timeout=30, **_ctx_kwargs()) as resp:
            status = resp.status
            ctype = resp.headers.get("Content-Type", "(none)")
            clen = resp.headers.get("Content-Length", "?")
            head = resp.read(8)
    is_pdf_bytes = head[:5] == b"%PDF-"
    return status, ctype, clen, is_pdf_bytes


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit(
            "Set UIPATH_TOKEN env var first (do NOT hardcode it).\n"
            "  PowerShell: $env:UIPATH_TOKEN=\"<token>\"\n"
            "  bash:       export UIPATH_TOKEN=\"<token>\""
        )
    try:
        uri = get_read_uri()
        if not uri:
            raise SystemExit("Call succeeded but no 'Uri' field in the response.")
        print("\nPRE-SIGNED URL (valid ~%d min):\n%s\n" % (EXPIRY_MIN, uri))

        # Show whether this is the clean bucket object or a job-storage copy.
        path_part = urllib.parse.urlparse(uri).path
        if "BlobFilePersistence" in path_part:
            print(">>> NOTE: this URL points at a BlobFilePersistence/ job-storage COPY,")
            print(">>> not the foreman-context bucket object. (Read-uri is reading the")
            print(">>> existing blob — if you uploaded a copy earlier, you may have two.)\n")

        status, ctype, clen, is_pdf_bytes = inspect_url(uri)
        print("Served by Azure for this URL:")
        print("  HTTP status   : %s" % status)
        print("  Content-Type  : %s" % ctype)
        print("  Size header   : %s" % clen)
        print("  First bytes %%PDF? : %s" % ("YES (real PDF bytes)" if is_pdf_bytes else "NO"))
        print()
        if ctype.lower().startswith("application/pdf"):
            print(">>> GOOD: Content-Type is application/pdf -> WhatsApp/phone will open it.")
        else:
            print(">>> PROBLEM: Content-Type is '%s', not application/pdf." % ctype)
            print(">>> This is why the phone says 'no proper app for viewing this content',")
            print(">>> even though the bytes are a real PDF and a browser opens it.")
            print(">>> FIX: re-upload the PDF to the bucket so it's stored as application/pdf")
            print(">>>      (delete the existing copies, use 'Upload files' fresh), OR set")
            print(">>>      content_type='application/pdf' when the supervisor writes it.")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        print("HTTP %s" % e.code)
        if "1010" in body or "not available in your country" in body:
            print("\n>>> Cloudflare 1010 blocking this client/IP (geo/UA). Mint inside")
            print(">>> Orchestrator instead, or use the browser DevTools->Network trick.")
        elif e.code in (401, 403):
            print("\n>>> 401/403: token expired or lacks folder/Orchestrator access.")
        elif e.code == 404:
            print("\n>>> 404: bucket id (%s) or blob path (%s) wrong." % (BUCKET_ID, BLOB_PATH))
        else:
            print(body[:800])
    except urllib.error.URLError as e:
        print("Network/URL error: %s" % e.reason)