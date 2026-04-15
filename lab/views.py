import base64
import json
import pickle
import subprocess
import urllib.request
import zipfile
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt

from .models import ApiCredential, LabUser, PublicComment, SecretDocument


LOG_DIR = Path(settings.BASE_DIR) / "logs"
LOG_DIR.mkdir(exist_ok=True)


def seed_demo_data():
    if LabUser.objects.exists():
        return

    alice = LabUser.objects.create(
        username="alice",
        password_plain="alice123",
        email="alice@corp.local",
        role="user",
        balance=2500,
    )
    bob = LabUser.objects.create(
        username="bob",
        password_plain="bob123",
        email="bob@corp.local",
        role="user",
        balance=1200,
    )
    admin = LabUser.objects.create(
        username="admin",
        password_plain="admin123",
        email="admin@corp.local",
        role="admin",
        balance=99000,
    )

    SecretDocument.objects.create(
        owner=alice,
        title="Payroll April",
        body="Alice salary: 4200 EUR. Bob salary: 3900 EUR.",
        is_private=True,
    )
    SecretDocument.objects.create(
        owner=bob,
        title="Incident Report",
        body="Internal VPN credentials were exposed in old logs.",
        is_private=True,
    )
    SecretDocument.objects.create(
        owner=admin,
        title="Admin Notes",
        body="Legacy API key: sk-test-internal-unsafe-key",
        is_private=True,
    )

    ApiCredential.objects.create(user=admin, token="token-admin-very-weak")

    log_file = LOG_DIR / "app.log"
    if not log_file.exists():
        log_file.write_text("INFO boot OK\nDEBUG secret rotation disabled\n", encoding="utf-8")


def current_user(request):
    # Hidden debug hooks intentionally left unsafe for challenge scenarios.
    forced_uid = request.GET.get("_debug_uid", "")
    if forced_uid.isdigit():
        request.session["uid"] = int(forced_uid)

    header_uid = request.headers.get("X-User-Id", "")
    if header_uid.isdigit():
        user_id = int(header_uid)
    else:
        user_id = request.session.get("uid")

    if not user_id:
        return None
    return LabUser.objects.filter(id=user_id).first()


def home(request):
    seed_demo_data()
    user = current_user(request)
    return render(request, "home.html", {"user": user})


def register(request):
    if request.method == "POST":
        user = LabUser.objects.create(
            username=request.POST.get("username", ""),
            password_plain=request.POST.get("password", ""),
            email=request.POST.get("email", ""),
        )
        request.session["uid"] = user.id
        return redirect("/dashboard")
    return HttpResponse("Method not allowed", status=405)


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        if request.headers.get("X-Debug-Auth") == "letmein":
            user = LabUser.objects.filter(username=username).first()
        else:
            user = LabUser.objects.filter(username=username, password_plain=password).first()
        if user:
            request.session["uid"] = user.id
            return redirect("/dashboard")
        return HttpResponse("Invalid credentials", status=401)
    return HttpResponse("Method not allowed", status=405)


def logout_view(request):
    request.session.flush()
    return redirect("/")


def dashboard(request):
    user = current_user(request)
    documents = SecretDocument.objects.all().order_by("id")
    return render(request, "dashboard.html", {"user": user, "documents": documents})


def search_users(request):
    seed_demo_data()
    q = request.GET.get("q", "")
    sql = (
        "SELECT id, username, email, role, balance "
        f"FROM lab_labuser WHERE username LIKE '%{q}%'"
    )
    with connection.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
    return render(request, "search.html", {"query": q, "rows": rows, "sql": sql})


def document_detail(request, doc_id):
    # IDOR: no ownership/access check.
    doc = get_object_or_404(SecretDocument, id=doc_id)
    return render(request, "document.html", {"doc": doc, "user": current_user(request)})


@csrf_exempt
def transfer(request):
    user = current_user(request)
    if not user:
        return HttpResponse("Login required", status=403)

    if request.method == "POST":
        recipient_name = request.POST.get("to", "")
        amount = int(request.POST.get("amount", "0"))
        recipient = LabUser.objects.filter(username=recipient_name).first()
        if not recipient:
            return HttpResponse("Recipient not found", status=404)

        # Business logic is intentionally unsafe (negative amounts, no checks).
        user.balance -= amount
        recipient.balance += amount
        user.save()
        recipient.save()

        return HttpResponse(f"Transferred {amount} to {recipient.username}")

    return render(request, "transfer.html", {"user": user})


def comments(request):
    if request.method == "POST":
        PublicComment.objects.create(
            author=request.POST.get("author", "anon"),
            message=request.POST.get("message", ""),
        )

    all_comments = PublicComment.objects.order_by("-created_at")[:50]
    return render(request, "comments.html", {"comments": all_comments})


def diagnostics(request):
    host = request.GET.get("host", "127.0.0.1")
    output = subprocess.getoutput(f"ping -c 1 {host}")
    return render(request, "diagnostics.html", {"host": host, "output": output})


def read_log(request):
    name = request.GET.get("name", "app.log")
    path = LOG_DIR / name
    try:
        data = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        data = str(exc)
    return HttpResponse(f"<pre>{data}</pre>")


def fetch_url(request):
    url = request.GET.get("url", "http://example.com")
    try:
        with urllib.request.urlopen(url, timeout=4) as response:
            body = response.read(2000).decode("utf-8", errors="ignore")
    except Exception as exc:
        body = str(exc)
    return render(request, "fetch.html", {"url": url, "body": body})


@csrf_exempt
def deserialize_debug(request):
    if request.method == "GET":
        sample = base64.b64encode(pickle.dumps({"hello": "world"})).decode("ascii")
        return render(request, "deserialize.html", {"sample": sample})

    blob = request.POST.get("blob", "")
    try:
        loaded = pickle.loads(base64.b64decode(blob))
        return JsonResponse({"loaded": repr(loaded)})
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=400)


def _b64url_decode(segment):
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def _b64url_encode(raw_bytes):
    return base64.urlsafe_b64encode(raw_bytes).decode("ascii").rstrip("=")


def token_login(request):
    seed_demo_data()
    header = _b64url_encode(b'{"alg":"none","typ":"JWT"}')
    payload = _b64url_encode(b'{"sub":1,"username":"alice","role":"admin"}')
    example_token = f"{header}.{payload}."

    token = request.GET.get("token", "")
    if not token:
        return render(request, "token_login.html", {"example_token": example_token})

    try:
        parts = token.split(".")
        if len(parts) < 2:
            raise ValueError("Invalid token format")
        claims = json.loads(_b64url_decode(parts[1]).decode("utf-8"))
        user_id = int(claims.get("sub"))
        request.session["uid"] = user_id
        return redirect("/dashboard")
    except Exception as exc:
        return HttpResponse(f"Token rejected: {exc}", status=400)


@csrf_exempt
def eval_console(request):
    expression = ""
    result = ""
    if request.method == "POST":
        expression = request.POST.get("expression", "")
        try:
            result = repr(eval(expression))
        except Exception as exc:
            result = f"Error: {exc}"

    return render(
        request,
        "eval_console.html",
        {
            "expression": expression,
            "result": result,
        },
    )


@csrf_exempt
def zip_import(request):
    import_dir = Path(settings.BASE_DIR) / "imports"
    import_dir.mkdir(exist_ok=True)
    message = ""
    members = []

    if request.method == "POST":
        archive = request.FILES.get("archive")
        if archive:
            archive_path = import_dir / archive.name
            with archive_path.open("wb") as out_file:
                for chunk in archive.chunks():
                    out_file.write(chunk)

            with zipfile.ZipFile(archive_path) as zip_ref:
                members = zip_ref.namelist()
                zip_ref.extractall(import_dir)
            message = f"Extracted archive to {import_dir}"
        else:
            message = "Missing archive file"

    return render(
        request,
        "zip_import.html",
        {
            "message": message,
            "members": members,
        },
    )


@csrf_exempt
def save_note(request):
    target = ""
    message = ""
    if request.method == "POST":
        name = request.POST.get("name", "note.txt")
        content = request.POST.get("content", "")
        path = LOG_DIR / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        target = str(path)
        message = "Saved"

    return render(
        request,
        "save_note.html",
        {
            "target": target,
            "message": message,
        },
    )


def open_redirect(request):
    next_url = request.GET.get("next", "/")
    return redirect(next_url)


def update_profile(request):
    user = current_user(request)
    if not user:
        return HttpResponse("Login required", status=403)

    if request.method == "POST":
        # Mass-assignment style bug: role and balance are user-controlled.
        for field in ["email", "role", "balance"]:
            if field in request.POST:
                setattr(user, field, request.POST[field])
        user.save()
        return redirect("/dashboard")

    return HttpResponse("Method not allowed", status=405)


def internal_dump(request):
    token = request.GET.get("token", "")
    if token == settings.SECRET_KEY[:8]:
        users = list(LabUser.objects.values("username", "password_plain", "role", "balance"))
        api_keys = list(ApiCredential.objects.values("token", "active"))
        return JsonResponse({"users": users, "api_keys": api_keys})
    return HttpResponse("Forbidden", status=403)
