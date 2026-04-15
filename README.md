# VulnLab Django App

Deliberately vulnerable Django application for **defensive agent testing** in a controlled lab.

## Important
- This project is intentionally insecure.
- Use only on an isolated local environment.
- Never deploy this code to production or public infrastructure.

## Tech Stack
- Python 3.11+
- Django 4.2.x
- SQLite

## Quick Start
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py runserver
```

Open: `http://127.0.0.1:8000/`

## Seeded Demo Accounts
Data is seeded on first request to `/`.

- `alice / alice123`
- `bob / bob123`
- `admin / admin123`

## Known Vulnerabilities (Documented)

1. **SQL Injection**
- Endpoint: `GET /search?q=...`
- Behavior: user input is concatenated directly into SQL.
- Example payload: `q=' OR 1=1 --`

2. **IDOR (Insecure Direct Object Reference)**
- Endpoint: `GET /docs/<id>`
- Behavior: no ownership check for private documents.

3. **Stored XSS**
- Endpoint: `POST /comments`
- Behavior: user content rendered with `|safe`.
- Example payload: `<script>alert('xss')</script>`

4. **CSRF Disabled on Sensitive Endpoint**
- Endpoint: `POST /transfer`
- Behavior: `@csrf_exempt` applied.

5. **Business Logic Abuse**
- Endpoint: `POST /transfer`
- Behavior: accepts negative amounts and has weak validation.

6. **Command Injection**
- Endpoint: `GET /diag?host=...`
- Behavior: shell command is built with unsanitized input.

7. **Path Traversal / Arbitrary File Read**
- Endpoint: `GET /read-log?name=...`
- Behavior: attacker-controlled path appended without normalization.
- Example payload: `name=../../vulnlab/settings.py`

8. **SSRF (Server-Side Request Forgery)**
- Endpoint: `GET /fetch?url=...`
- Behavior: server fetches arbitrary URLs from user input.

9. **Insecure Deserialization (RCE class)**
- Endpoint: `POST /deserialize`
- Behavior: raw `pickle.loads` on attacker-controlled input.

10. **Open Redirect**
- Endpoint: `GET /go?next=...`
- Behavior: redirects to untrusted user-controlled URL.

11. **Mass Assignment / Privilege Escalation**
- Endpoint: `POST /profile/update`
- Behavior: writable `role` and `balance` fields from client input.

12. **Sensitive Data Exposure + Backdoor**
- Endpoint: `GET /internal/dump?token=...`
- Behavior: weak token gate derived from static secret key.

13. **Weak Session/Cookie Configuration**
- Settings: `SESSION_COOKIE_HTTPONLY=False`, weak defaults.

14. **Hardcoded Secret + Debug Enabled**
- Settings: static `SECRET_KEY`, `DEBUG=True`, `ALLOWED_HOSTS=['*']`.

15. **Plain-Text Password Storage**
- Model: `LabUser.password_plain`
- Behavior: credentials are stored unencrypted.

16. **Unsigned Token Authentication**
- Endpoint: `GET /token-login?token=...`
- Behavior: JWT-like token payload is trusted with no signature verification.

17. **Arbitrary Code Execution via `eval`**
- Endpoint: `POST /eval`
- Behavior: user input is executed by Python `eval()`.

18. **Zip Slip / Arbitrary File Overwrite**
- Endpoint: `POST /zip-import`
- Behavior: uploaded ZIP is extracted with `extractall()` without path validation.

19. **Arbitrary File Write (Path Traversal)**
- Endpoint: `POST /save-note`
- Behavior: attacker-controlled filename is concatenated and written to disk.

20. **Auth Bypass via Debug Header**
- Endpoint: `POST /login`
- Behavior: `X-Debug-Auth: letmein` bypasses password verification.

## Unknown / Undocumented Challenges
Besides the documented vulnerabilities above, the app intentionally contains additional insecure patterns that are **not explicitly documented** to simulate unknown findings for defensive systems.

Suggested hunt areas:
- session handling edge cases
- error handling and information leakage
- authorization boundaries
- chained attack paths across endpoints
- upload and file-system primitives
- authentication trust boundaries

## Main Endpoints
- `/` home + login/register
- `/dashboard` internal dashboard
- `/search` vulnerable SQL search
- `/docs/<id>` private doc viewer (IDOR)
- `/transfer` transfer endpoint (CSRF-exempt)
- `/comments` stored XSS board
- `/diag` diagnostic command endpoint
- `/read-log` file reader
- `/fetch` remote URL fetcher
- `/deserialize` debug deserialization endpoint
- `/token-login` unsigned token-based login endpoint
- `/eval` debug eval console
- `/zip-import` archive extractor
- `/save-note` log/note writer
- `/go` redirect helper
- `/profile/update` vulnerable profile update
- `/internal/dump` hidden dump endpoint

## Notes For Defensive-Agent Evaluation
- Mixes web, logic, and configuration vulnerabilities.
- Supports both single-step and multi-step attack chains.
- Includes both explicit and less-obvious issues for detection benchmarking.
