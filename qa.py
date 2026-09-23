#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Doctor Plus — فحص آلي شامل للموقع (بدون أي عمل يدوي).

يشتغل تلقائياً من GitHub Actions ويفحص:
  1) كل الصفحات: أخطاء JavaScript، ملفات ناقصة (404)، دوال أزرار غير معرّفة
  2) Chromium (أندرويد/لابتوب) و WebKit (محرك سفاري: آيفون/آيباد)
  3) PWA: manifest والأيقونات وSW والعمل بدون إنترنت
  4) تجاوب الشاشة (آيفون/آيباد/لابتوب): تجاوز العرض الأفقي
  5) الأمان من الخارج بمفتاح anon: قراءة الجداول والدوال والـ Edge Functions
  6) اتصال الواجهة المباشر بقاعدة البيانات (يجب أن يمر كله عبر Edge Functions)
  7) (اختياري) دخول فعلي بحساب تجريبي وزيارة كل أقسام لوحة التحكم (قراءة فقط)

متغيرات البيئة:
  QA_ACCOUNTS  حسابات تجريبية بصيغة  07xxxxxxxxx:كلمة_المرور;07yyyyyyyyy:كلمة_المرور
  QA_BROWSERS  chromium,webkit  (الافتراضي)
"""
import functools
import http.server
import json
import os
import pathlib
import re
import socketserver
import struct
import sys
import threading
import urllib.error
import urllib.request
import base64

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "qa-out"
OUT.mkdir(exist_ok=True)

MOCK = os.getenv("QA_MOCK") == "1"          # للاختبار الذاتي فقط (يزيّف السيرفر)
SANDBOX = os.getenv("QA_SANDBOX") == "1"    # بيئة بلا إنترنت: يتجاهل الموارد الخارجية
BROWSERS = [b.strip() for b in os.getenv("QA_BROWSERS", "chromium,webkit").split(",") if b.strip()]

RESULTS = []


def rec(status, area, name, detail=""):
    RESULTS.append((status, area, name, detail))
    icon = {"PASS": "PASS", "FAIL": "FAIL", "WARN": "WARN", "SKIP": "SKIP"}[status]
    print(f"[{icon}] {area} :: {name}" + (f" — {detail}" if detail else ""), flush=True)


def read(p):
    return pathlib.Path(p).read_text(encoding="utf-8", errors="ignore")


HTML_FILES = sorted(p.name for p in ROOT.glob("*.html"))
DASH = read(ROOT / "dashboard.html") if (ROOT / "dashboard.html").exists() else ""


def find(pat, txt):
    m = re.search(pat, txt)
    return m.group(1) if m else None


SUPABASE_URL = find(r'SUPABASE_URL\s*=\s*["\'](https://[^"\']+)["\']', DASH)
ANON_KEY = find(r'SUPABASE_ANON_KEY\s*=\s*["\']([^"\']+)["\']', DASH)


# ------------------------------------------------------------ خادم محلي
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def start_server():
    handler = functools.partial(Quiet, directory=str(ROOT))
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_address[1]}"


# ------------------------------------------------------------ HTTP بسيط
def http(method, url, headers=None, body=None, timeout=25):
    data = None
    h = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode()
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers or {})
    except Exception as e:  # noqa
        return 0, str(e).encode(), {}


def anon_headers():
    return {"apikey": ANON_KEY, "Authorization": f"Bearer {ANON_KEY}"}


# ------------------------------------------------------------ مراقبة الصفحة
class Watch:
    def __init__(self, page, base):
        self.base = base
        self.js_errors = []
        self.console_errors = []
        self.bad_files = []      # 404 لملفات الموقع نفسه
        self.fn_errors = []      # ردود >=400 من Edge Functions
        self.direct_db = set()   # وصول مباشر لـ /rest/v1
        page.on("pageerror", lambda e: self.js_errors.append(str(e)[:220]))
        page.on("console", self._console)
        page.on("response", self._response)
        page.on("request", self._request)

    def _external_noise(self, text):
        return SANDBOX and ("Failed to load resource" in text or "ERR_" in text or "net::" in text)

    def _console(self, msg):
        if msg.type != "error":
            return
        t = msg.text[:220]
        if self._external_noise(t):
            return
        self.console_errors.append(t)

    def _response(self, r):
        try:
            url, st = r.url, r.status
        except Exception:
            return
        if st < 400:
            return
        if url.startswith(self.base):
            if not url.endswith("favicon.ico"):
                self.bad_files.append(f"{st} {url.replace(self.base, '')}")
        elif "/functions/v1/" in url:
            self.fn_errors.append(f"{st} {url.split('/functions/v1/')[1].split('?')[0]}")

    def _request(self, r):
        u = r.url
        if "/rest/v1/" in u:
            table = u.split("/rest/v1/")[1].split("?")[0]
            self.direct_db.add(f"{r.method} {table}")

    def snapshot(self):
        return (len(self.js_errors), len(self.console_errors), len(self.bad_files),
                len(self.fn_errors), len(self.direct_db))


MISSING_HANDLERS_JS = """
() => {
  const missing = new Set();
  document.querySelectorAll('[onclick]').forEach(el => {
    const code = el.getAttribute('onclick') || '';
    const m = code.match(/^\\s*(?:return\\s+)?([A-Za-z_$][\\w$]*)\\s*\\(/);
    if (m && typeof window[m[1]] !== 'function') missing.add(m[1]);
  });
  return [...missing];
}
"""

OVERFLOW_JS = "() => document.documentElement.scrollWidth - window.innerWidth"


def launch(pw, name):
    return getattr(pw, name).launch()


# ------------------------------------------------------------ 0) فحص أسرار في الملفات
def phase_static():
    bad = []
    jwt_re = re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.([A-Za-z0-9_-]{10,})\.[A-Za-z0-9_-]{10,}")
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in {".html", ".js", ".json", ".txt", ".md", ".ts", ".env", ".yml"}:
            continue
        if any(x in p.parts for x in ("node_modules", "qa-out", ".git")):
            continue
        txt = read(p)
        if "sb_secret_" in txt:
            bad.append(f"{p.name}: sb_secret_")
        for m in jwt_re.finditer(txt):
            try:
                pad = m.group(1) + "=" * (-len(m.group(1)) % 4)
                role = json.loads(base64.urlsafe_b64decode(pad)).get("role")
                if role == "service_role":
                    bad.append(f"{p.name}: مفتاح service_role")
            except Exception:
                pass
    if (ROOT / ".env").exists():
        bad.append(".env موجود في المستودع")
    if bad:
        for b in bad:
            rec("FAIL", "أسرار", "مفتاح سري داخل الملفات", b)
    else:
        rec("PASS", "أسرار", "لا توجد مفاتيح سرية داخل ملفات المشروع")


# ------------------------------------------------------------ 1) تحميل الصفحات
def add_mocks(ctx):
    """للاختبار الذاتي فقط: يزيّف Edge Functions"""
    from datetime import datetime, timedelta, timezone
    fut = (datetime.now(timezone.utc) + timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
    user = {"id": "c1", "clinic_id": "c1", "phone": "07700000000", "clinic_name": "QA Clinic",
            "full_name": "QA", "role": "manager", "plan": "large", "status": "active", "expires_at": fut}

    def auth(route):
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"ok": True, "token": "mock-token", "user": user}))

    def data(route):
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"ok": True, "data": [], "count": 0}))

    def status(route):
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"ok": True, "data": {"status": "active", "plan": "large", "expires_at": fut}}))

    def generic(route):
        route.fulfill(status=200, content_type="application/json", body=json.dumps({"ok": True, "data": []}))

    ctx.route("**/functions/v1/auth-handler", auth)
    ctx.route("**/functions/v1/data-handler", data)
    ctx.route("**/functions/v1/clinic-status", status)
    ctx.route("**/functions/v1/lab-files", generic)
    ctx.route("**/functions/v1/verify-lab-report", generic)


def phase_pages(pw, base, bname):
    try:
        browser = launch(pw, bname)
    except Exception as e:  # noqa
        rec("WARN", f"متصفح {bname}", "غير متوفر", str(e).splitlines()[0][:120])
        return
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, service_workers="block")
    if MOCK:
        add_mocks(ctx)
    for name in HTML_FILES:
        page = ctx.new_page()
        w = Watch(page, base)
        url = f"{base}/{name}"
        if name == "verify-report.html":
            url += "?r=qa-invalid-000"
        try:
            resp = page.goto(url, wait_until="load", timeout=30000)
            page.wait_for_timeout(1500)
        except Exception as e:  # noqa
            rec("FAIL", f"{bname}", f"{name} لا يفتح", str(e)[:150])
            page.close()
            continue
        label = f"{bname} / {name}"
        if resp and resp.status >= 400:
            rec("FAIL", label, f"حالة HTTP {resp.status}")
        if name == "dashboard.html":
            if "auth-system" in page.url:
                rec("PASS", label, "يحوّل غير المسجّل إلى صفحة الدخول")
            else:
                rec("FAIL", label, "يفتح بدون تسجيل دخول!", page.url.replace(base, ""))
        else:
            missing = page.evaluate(MISSING_HANDLERS_JS)
            if missing:
                rec("FAIL", label, "أزرار تستدعي دوال غير معرّفة", ", ".join(missing[:8]))
        for e in sorted(set(w.js_errors))[:5]:
            rec("FAIL", label, "خطأ JavaScript", e)
        for e in sorted(set(w.bad_files))[:5]:
            rec("FAIL", label, "ملف ناقص", e)
        for e in sorted(set(w.console_errors))[:3]:
            rec("WARN", label, "خطأ في الكونسول", e)
        for d in sorted(w.direct_db):
            rec("FAIL", label, "الواجهة تتصل بقاعدة البيانات مباشرة (يجب عبر Edge Function)", d)
        if not (w.js_errors or w.bad_files) and not w.direct_db:
            rec("PASS", label, "يحمّل بدون أخطاء")
        page.close()
    ctx.close()
    browser.close()


# ------------------------------------------------------------ 2) PWA
def png_size(data):
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", data[16:24])


def phase_pwa(pw, base):
    st, body, _ = http("GET", f"{base}/manifest.json")
    if st != 200:
        rec("FAIL", "PWA", "manifest.json غير موجود")
        return
    try:
        m = json.loads(body)
    except Exception as e:  # noqa
        rec("FAIL", "PWA", "manifest.json غير صالح", str(e)[:100])
        return
    for k in ("name", "short_name", "start_url", "display", "icons"):
        if not m.get(k):
            rec("FAIL", "PWA", f"manifest ينقصه الحقل {k}")
    if m.get("orientation") in ("portrait", "portrait-primary"):
        rec("WARN", "PWA", "الاتجاه مقفول portrait (يضايق الآيباد واللابتوب)")
    sizes_seen = set()
    for ic in m.get("icons", []):
        src = ic.get("src", "")
        s, b, h = http("GET", f"{base}/{src.lstrip('./')}")
        if s != 200:
            rec("FAIL", "PWA", f"الأيقونة {src} غير موجودة ({s})")
            continue
        real = png_size(b)
        want = ic.get("sizes", "")
        if real and want and want != "any" and f"{real[0]}x{real[1]}" != want:
            rec("WARN", "PWA", f"مقاس الأيقونة {src} الحقيقي {real[0]}x{real[1]} وليس {want}")
        sizes_seen.add(want)
    if not {"192x192", "512x512"} <= sizes_seen:
        rec("FAIL", "PWA", "لازم أيقونتان على الأقل 192x192 و512x512")
    else:
        rec("PASS", "PWA", "manifest والأيقونات سليمة")
    st, _, _ = http("GET", f"{base}/{m.get('start_url', '').lstrip('./')}")
    if st != 200:
        rec("FAIL", "PWA", "start_url لا يفتح", str(st))
    # apple-touch-icon و viewport
    for name in HTML_FILES:
        txt = read(ROOT / name)
        if "viewport" not in txt:
            rec("FAIL", "PWA", f"{name} بدون meta viewport")
        for tag in re.findall(r"<link[^>]+apple-touch-icon[^>]*>", txt):
            href = find(r'href=["\']([^"\']+)["\']', tag)
            if href and not href.startswith("http"):
                s, _, _ = http("GET", f"{base}/{href.lstrip('./')}")
                if s != 200:
                    rec("FAIL", "PWA", f"{name}: apple-touch-icon يشير لملف مفقود", href)
    # Service Worker + offline
    try:
        browser = launch(pw, "chromium")
        ctx = browser.new_context(service_workers="allow")
        page = ctx.new_page()
        page.goto(f"{base}/auth-system-3-1-1.html", wait_until="load")
        ready = page.evaluate("navigator.serviceWorker.ready.then(r => !!r.active)")
        page.wait_for_timeout(1200)
        cached = page.evaluate("caches.keys().then(async ks => { let n = 0; for (const k of ks) n += (await (await caches.open(k)).keys()).length; return n; })")
        if not ready:
            rec("FAIL", "PWA", "Service Worker لا يفعّل")
        elif not cached:
            rec("FAIL", "PWA", "Service Worker فعّال لكن لا يخزّن أي ملف (غالباً مسارات خاطئة في sw.js)")
        else:
            rec("PASS", "PWA", f"Service Worker يعمل ويخزّن {cached} ملف")
        page.reload(wait_until="load")   # ليصبح الـ SW مسيطراً
        page.wait_for_timeout(800)
        ctx.set_offline(True)
        try:
            page.reload(wait_until="load", timeout=15000)
            ok = page.locator("#login-identifier").count() > 0
            rec("PASS" if ok else "FAIL", "PWA", "صفحة الدخول تفتح بدون إنترنت" if ok else "لا تفتح بدون إنترنت")
        except Exception as e:  # noqa
            rec("FAIL", "PWA", "لا تفتح بدون إنترنت", str(e)[:100])
        ctx.close()
        browser.close()
    except Exception as e:  # noqa
        rec("WARN", "PWA", "تعذر فحص Service Worker", str(e).splitlines()[0][:120])


# ------------------------------------------------------------ 3) تجاوب الشاشات
VIEWPORTS = {"آيفون": (390, 844), "آيباد": (820, 1180), "لابتوب": (1366, 768)}


def phase_responsive(pw, base):
    for bname in BROWSERS:
        try:
            browser = launch(pw, bname)
        except Exception:
            continue
        for label, (w_, h_) in VIEWPORTS.items():
            ctx = browser.new_context(viewport={"width": w_, "height": h_}, service_workers="block")
            page = ctx.new_page()
            page.goto(f"{base}/auth-system-3-1-1.html", wait_until="load")
            page.wait_for_timeout(800)
            over = page.evaluate(OVERFLOW_JS)
            shot = OUT / f"login-{bname}-{label}.png"
            page.screenshot(path=str(shot))
            if over > 2:
                rec("WARN", f"{bname} / {label}", "صفحة الدخول أعرض من الشاشة (تمرير أفقي)", f"+{over}px")
            else:
                rec("PASS", f"{bname} / {label}", "صفحة الدخول تناسب الشاشة")
            ctx.close()
        browser.close()


# ------------------------------------------------------------ 4) الأمان من الخارج
BASE_TABLES = [
    "super_admins", "otp_codes", "clinics_auth", "clinic_users", "sessions", "clinic_sessions",
    "login_attempts", "backups", "daily_backups", "subscription_logs", "trial_history",
    "patients", "appointments", "prescriptions", "invoices", "medical_records", "medications",
    "lab_requests", "lab_results", "lab_orders", "lab_files", "lab_reports", "lab_tests_catalog",
    "pharmacy_orders", "prescription_pharmacy", "pharmacy_audit_log", "patient_attachments",
    "patient_payments", "patient_audit_log", "financial_transactions", "debt_payments",
    "clinic_settings", "user_settings", "notifications", "secretary_doctor_assignments", "doctor_services",
]
READ_ONLY_RPC_PREFIX = ("get_", "print_", "list_", "check_", "fetch_", "search_")
ZERO = "00000000-0000-0000-0000-000000000000"


def phase_security():
    if SANDBOX or not SUPABASE_URL or not ANON_KEY:
        rec("SKIP", "أمان", "فحص Supabase الخارجي", "بدون إنترنت/بدون إعدادات")
        return
    ah = anon_headers()
    # اكتشاف الجداول والدوال
    tables, rpcs = set(BASE_TABLES), {}
    st, body, _ = http("GET", f"{SUPABASE_URL}/rest/v1/", ah)
    if st == 200:
        try:
            spec = json.loads(body)
            for path, item in (spec.get("paths") or {}).items():
                if path.startswith("/rpc/"):
                    props = {}
                    for prm in (item.get("post", {}).get("parameters") or []):
                        sch = (prm.get("schema") or {}).get("properties") or {}
                        props.update(sch)
                    rpcs[path[5:]] = props
                elif path != "/":
                    tables.add(path[1:])
        except Exception:
            pass
    if "get_lab_statistics" not in rpcs:
        rpcs["get_lab_statistics"] = {"p_clinic_id": {"format": "uuid"}}
    if "print_lab_report" not in rpcs:
        rpcs["print_lab_report"] = {"p_order_id": {"format": "uuid"}, "p_clinic_id": {"format": "uuid"}}

    exposed = []
    for t in sorted(tables):
        s, b, _ = http("GET", f"{SUPABASE_URL}/rest/v1/{t}?select=*&limit=1", ah)
        if s == 200:
            try:
                rows = json.loads(b)
                if isinstance(rows, list) and rows:
                    exposed.append(t)
            except Exception:
                pass
    if exposed:
        for t in exposed:
            rec("FAIL", "أمان قاعدة البيانات", f"الجدول {t} مقروء بمفتاح anon (يرجع بيانات)")
    else:
        rec("PASS", "أمان قاعدة البيانات", f"{len(tables)} جدول: لا يرجع أي بيانات لمفتاح anon")

    callable_ = []
    for fn, props in sorted(rpcs.items()):
        if not fn.startswith(READ_ONLY_RPC_PREFIX):
            continue
        args = {}
        for k, v in props.items():
            f = (v or {}).get("format", "")
            tp = (v or {}).get("type", "")
            args[k] = ZERO if ("uuid" in f or k.endswith("_id")) else (0 if tp in ("integer", "number") else "qa")
        s, b, _ = http("POST", f"{SUPABASE_URL}/rest/v1/rpc/{fn}", ah, args)
        if s == 200:
            callable_.append(fn)
    if callable_:
        for fn in callable_:
            rec("FAIL", "أمان قاعدة البيانات", f"الدالة {fn} تُستدعى بمفتاح anon")
    else:
        rec("PASS", "أمان قاعدة البيانات", "دوال القراءة مقفلة على anon")

    s, b, _ = http("GET", f"{SUPABASE_URL}/storage/v1/bucket", ah)
    if s == 200:
        try:
            buckets = json.loads(b)
            if isinstance(buckets, list) and buckets:
                rec("WARN", "أمان التخزين", f"anon يرى {len(buckets)} bucket", ", ".join(x.get("name", "?") for x in buckets[:5]))
            else:
                rec("PASS", "أمان التخزين", "anon لا يرى أي bucket")
        except Exception:
            pass
    else:
        rec("PASS", "أمان التخزين", "anon لا يرى الـ buckets")

    s, b, _ = http("GET", f"{SUPABASE_URL}/auth/v1/settings", {"apikey": ANON_KEY})
    if s == 200:
        try:
            cfg = json.loads(b)
            if cfg.get("disable_signup") is False:
                rec("WARN", "أمان Auth", "التسجيل العام مفتوح في Supabase Auth (أي شخص يحصل على دور authenticated)")
            else:
                rec("PASS", "أمان Auth", "التسجيل العام في Supabase Auth مغلق")
        except Exception:
            pass

    # Edge Functions بدون جلسة
    fh = anon_headers()
    fbase = f"{SUPABASE_URL}/functions/v1"
    for tok in (None, "invalid-qa-token"):
        s, b, _ = http("POST", f"{fbase}/data-handler", fh, {"token": tok, "table": "patients", "operation": "select"})
        leaked = False
        try:
            j = json.loads(b)
            leaked = bool(j.get("ok")) and bool(j.get("data"))
        except Exception:
            pass
        rec("FAIL" if leaked else "PASS", "أمان Edge Functions",
            f"data-handler {'بدون توكن' if tok is None else 'بتوكن مزوّر'}", "يرجع بيانات!" if leaked else f"مرفوض ({s})")
    s, b, _ = http("POST", f"{fbase}/auth-handler", fh, {"action": "getAllClinics", "payload": {}})
    leaked = False
    try:
        j = json.loads(b)
        leaked = bool(j.get("ok"))
    except Exception:
        pass
    rec("FAIL" if leaked else "PASS", "أمان Edge Functions", "auth-handler/getAllClinics بدون جلسة أدمن",
        "يرجع بيانات!" if leaked else f"مرفوض ({s})")
    s, b, _ = http("POST", f"{fbase}/lab-files", fh, {})
    rec("PASS" if s in (400, 401, 403, 404, 405) else "WARN", "أمان Edge Functions", "lab-files بدون جلسة", f"({s})")
    # admin-action: السر الفارغ/الخاطئ
    ph = "+964" + "7711149039"
    s1, b1, _ = http("POST", f"{fbase}/admin-action", fh, {"action": "qa_noop", "adminSecret": "qa-wrong-secret", "adminPhone": ph})
    s2, b2, _ = http("POST", f"{fbase}/admin-action", fh, {"action": "qa_noop", "adminSecret": "", "adminPhone": ph})
    if s1 == 404 and s2 == 404:
        rec("PASS", "أمان Edge Functions", "admin-action غير منشورة (لا سطح هجوم)")
    elif s1 == 401 and s2 == 401:
        rec("PASS", "أمان Edge Functions", "admin-action يرفض السر الخاطئ والفارغ")
    elif s2 != 401 and s2 != 0:
        rec("FAIL", "أمان Edge Functions", "admin-action يقبل سراً فارغاً — المتغير ADMIN_SECRET غير مضبوط في Supabase!", f"({s2})")
    elif s1 == 0:
        rec("SKIP", "أمان Edge Functions", "admin-action لا يرد")
    else:
        rec("WARN", "أمان Edge Functions", "admin-action رد غير متوقع", f"({s1}/{s2})")


# ------------------------------------------------------------ 5) دخول فعلي وزيارة كل الأقسام
def parse_accounts():
    if MOCK:
        return [("07700000000", "password123")]
    raw = os.getenv("QA_ACCOUNTS", "").strip()
    out = []
    for part in raw.split(";"):
        if ":" in part:
            p, pw = part.split(":", 1)
            if p.strip() and pw:
                out.append((p.strip(), pw))
    return out


TOAST_HOOK = """
() => {
  window.__toasts = [];
  const o = window.showToast;
  if (typeof o === 'function') window.showToast = function(m, t) { window.__toasts.push([String(m), String(t)]); return o.apply(this, arguments); };
}
"""


def phase_logged_in(pw, base):
    accounts = parse_accounts()
    if not accounts:
        rec("SKIP", "دخول فعلي", "لا توجد حسابات تجريبية (QA_ACCOUNTS)", "أضف Secret باسم QA_ACCOUNTS لتفعيل الفحص العميق")
        return
    browser = launch(pw, "chromium")
    for phone, pwd in accounts:
        tag = f"حساب ***{phone[-3:]}"
        ctx = browser.new_context(viewport={"width": 1366, "height": 850}, service_workers="block")
        if MOCK:
            add_mocks(ctx)
        page = ctx.new_page()
        w = Watch(page, base)
        page.goto(f"{base}/auth-system-3-1-1.html", wait_until="load")
        page.fill("#login-identifier", phone)
        page.fill("#login-password", pwd)
        page.evaluate("doLogin()")
        try:
            page.wait_for_url("**/dashboard.html*", timeout=30000)
        except Exception:
            alert = ""
            try:
                alert = page.inner_text("#auth-alert", timeout=1500)[:120]
            except Exception:
                pass
            rec("FAIL", tag, "تسجيل الدخول فشل", alert or page.url.replace(base, ""))
            ctx.close()
            continue
        rec("PASS", tag, "تسجيل الدخول نجح")
        page.wait_for_load_state("load")
        page.wait_for_timeout(3500)
        page.evaluate(TOAST_HOOK)
        load_label = f"{tag} / تحميل لوحة التحكم"
        for e in sorted(set(w.js_errors))[:5]:
            rec("FAIL", load_label, "خطأ JavaScript", e)
        for e in sorted(set(w.bad_files))[:5]:
            rec("FAIL", load_label, "ملف ناقص", e)
        for e in sorted(set(w.fn_errors))[:5]:
            rec("FAIL", load_label, "ردّ خطأ من الخادم", e)
        for d in sorted(w.direct_db):
            rec("FAIL", load_label, "الواجهة تتصل بقاعدة البيانات مباشرة (يجب عبر Edge Function)", d)
        if not (w.js_errors or w.bad_files or w.fn_errors or w.direct_db):
            rec("PASS", load_label, "تحمّل بدون أخطاء")
        w.direct_db.clear()
        items = page.locator(".nav-item")
        n = items.count()
        visited = 0
        for i in range(n):
            el = items.nth(i)
            try:
                if not el.is_visible():
                    continue
                oc = el.get_attribute("onclick") or ""
                m = re.search(r"goTo\(\s*['\"]([^'\"]+)['\"]", oc)
                if not m:
                    continue
                target = m.group(1)
                before = w.snapshot()
                page.evaluate("window.__toasts = []")
                el.click(timeout=4000)
                page.wait_for_timeout(2200)
                active = page.evaluate("document.querySelector('.page.active') && document.querySelector('.page.active').id")
                toasts = page.evaluate("window.__toasts || []")
                after = w.snapshot()
                visited += 1
                label = f"{tag} / {target}"
                problems = False
                if after[0] > before[0]:
                    for e in w.js_errors[before[0]:][:3]:
                        rec("FAIL", label, "خطأ JavaScript", e)
                    problems = True
                if after[3] > before[3]:
                    rec("FAIL", label, "ردّ خطأ من الخادم", ", ".join(sorted(set(w.fn_errors[before[3]:]))[:4]))
                    problems = True
                if after[2] > before[2]:
                    rec("FAIL", label, "ملف ناقص", ", ".join(sorted(set(w.bad_files[before[2]:]))[:3]))
                    problems = True
                if after[4] > before[4]:
                    rec("FAIL", label, "اتصال مباشر بقاعدة البيانات", ", ".join(sorted(w.direct_db)))
                    problems = True
                errs = [t for t in toasts if t[1] == "error"]
                if errs:
                    rec("WARN", label, "ظهرت رسالة خطأ للمستخدم", errs[0][0][:100])
                    problems = True
                elif active != f"page-{target}":
                    rec("WARN", label, "القسم لم يُفتح", f"active={active}")
                    problems = True
                page.screenshot(path=str(OUT / f"{phone[-3:]}-{target}.png"))
                if not problems:
                    rec("PASS", label, "يفتح ويحمّل بيانات بدون أخطاء")
            except Exception as e:  # noqa
                rec("WARN", f"{tag} / nav#{i}", "تعذر فتح القسم", str(e)[:100])
        if visited == 0:
            rec("FAIL", tag, "لم أجد أي قسم في القائمة الجانبية")
        # مستخدم عائد: فتح صفحة الدخول وهو مسجّل (يشغّل تحديث حالة الاشتراك)
        w.direct_db.clear()
        try:
            page.goto(f"{base}/auth-system-3-1-1.html", wait_until="load")
            page.wait_for_timeout(3500)
        except Exception:
            pass
        if w.direct_db:
            for d in sorted(w.direct_db):
                rec("FAIL", f"{tag} / مستخدم عائد", "اتصال مباشر بقاعدة البيانات", d)
        else:
            rec("PASS", f"{tag} / مستخدم عائد", "لا اتصال مباشر بقاعدة البيانات")
        try:
            page.goto(f"{base}/dashboard.html", wait_until="load")
            page.wait_for_timeout(2500)
        except Exception:
            pass
        # تجاوب لوحة التحكم
        for label, (w_, h_) in VIEWPORTS.items():
            page.set_viewport_size({"width": w_, "height": h_})
            page.wait_for_timeout(500)
            over = page.evaluate(OVERFLOW_JS)
            page.screenshot(path=str(OUT / f"dashboard-{label}.png"))
            rec("WARN" if over > 2 else "PASS", f"{tag} / لوحة التحكم / {label}",
                "أعرض من الشاشة" if over > 2 else "تناسب الشاشة", f"+{over}px" if over > 2 else "")
        ctx.close()
    browser.close()


# ============================================================
# محاكاة كاملة: تسجيل عيادة + إضافة موظف من كل دور + تجربة ميزاته
# + فحص ثغرة تجاوز رمز OTP (تسجيل بدون تحقق فعلي من البريد)
# ============================================================
QA_TAG = os.getenv("QA_TAG", "zzqa")            # بادئة لتمييز بيانات الفحص عن بيانات حقيقية
QA_LAB_ACCOUNT = os.getenv("QA_LAB_ACCOUNT", "")  # "07xxxxxxxx:password" — حساب دائم بباقة "كبير" لفحص المختبر
QA_SERVICE_ROLE_KEY = os.getenv("QA_SERVICE_ROLE_KEY", "")  # مفتاح service_role — لحذف عيادة الفحص عند نجاح كامل فقط
QA_PASSWORD = "QaTest#" + os.getenv("GITHUB_RUN_ID", "12345")[-5:]

EMAILJS_STUB = """
(() => {
  window.__qa_otp = null;
  window.emailjs = {
    init: () => {},
    send: (svc, tpl, params) => { window.__qa_otp = params && params.passcode; return Promise.resolve({status:200,text:'OK'}); }
  };
})();
"""


def _qa_seed():
    import time
    return int(time.time() * 1000) % 100000000


def stub_emailjs(ctx):
    """يمنع أي إرسال بريد فعلي أثناء الفحص (نتيجته ستذهب لبريد حقيقي غير مرغوب) ويلتقط
    رمز الـ OTP من نفس الصفحة بدل انتظار بريد."""
    ctx.route(re.compile(r"emailjs"), lambda route: route.abort())
    ctx.add_init_script(EMAILJS_STUB)


def _fill_step3(page, clinic, full_name, phone, email, password):
    page.fill("#reg-clinic-name", clinic)
    page.fill("#reg-full-name", full_name)
    page.fill("#reg-phone", phone)
    page.fill("#reg-email", email)
    page.fill("#reg-password", password)


def register_trial_owner(page, base, tag):
    """يسجّل عيادة بباقة (تجريبي) — تشمل دكتور+سكرتير+صيدلاني. تنبيه: النظام لا
    يحذف بيانات التجربة تلقائياً (دالة الحذف أُزيلت من الكود عمداً)، لذا نحذفها
    نحن يدوياً بنهاية هذا التشغيل عبر cleanup_qa_data — بس فقط لو التشغيل نجح
    بالكامل بدون أي FAIL."""
    seed = _qa_seed()
    phone = f"07{seed % 100000000:08d}"
    email = f"{QA_TAG}.{tag}.{seed}@example.com"
    clinic = f"{QA_TAG}-{tag}-{seed}"
    page.goto(f"{base}/auth-system-3-1-1.html", wait_until="load")
    page.evaluate(f"switchTab('register')")
    page.evaluate("selectPlan('trial')")
    page.click("text=التالي ←")
    _fill_step3(page, clinic, f"{QA_TAG} owner", phone, email, QA_PASSWORD)
    page.evaluate("window.__qa_otp = null")
    page.click("text=إرسال رمز التحقق ←")
    try:
        page.wait_for_function("window.__qa_otp !== null", timeout=15000)
    except Exception:
        rec("FAIL", "محاكاة التسجيل", "لم يصل رمز OTP (تحقق من emailjs)", clinic)
        return None
    otp = page.evaluate("window.__qa_otp")
    page.fill("#otp-single", otp)
    page.click("text=تحقق والمتابعة ←")
    try:
        page.wait_for_url("**/dashboard.html*", timeout=20000)
    except Exception:
        alert = ""
        try:
            alert = page.inner_text(".alert, #auth-alert", timeout=1500)[:150]
        except Exception:
            pass
        rec("FAIL", "محاكاة التسجيل", "فشل إكمال التسجيل بعد التحقق", alert or clinic)
        return None
    rec("PASS", "محاكاة التسجيل", "تسجيل عيادة تجريبية + تحقق OTP نجح", clinic)
    clinic_user = page.evaluate("JSON.parse(localStorage.getItem('clinic_user')||'{}')")
    clinic_id = clinic_user.get("clinic_id") or clinic_user.get("id")
    return {"phone": phone, "password": QA_PASSWORD, "clinic": clinic, "clinic_id": clinic_id}


def cleanup_qa_data(page, clinic_id):
    """يحذف عيادة الفحص وموظفيها نهائياً — يُستدعى فقط إذا نجح التشغيل بالكامل.
    يحتاج Secret باسم QA_SERVICE_ROLE_KEY (مفتاح service_role من إعدادات Supabase
    API). بدونه تبقى بيانات العيادة موجودة وتحتاج حذفاً يدوياً."""
    if not clinic_id:
        return
    if not QA_SERVICE_ROLE_KEY:
        rec("SKIP", "تنظيف بيانات QA", "أضف Secret باسم QA_SERVICE_ROLE_KEY لتفعيل الحذف التلقائي عند النجاح",
            clinic_id)
        return
    result = page.evaluate(
        """
        async ({url, key, id}) => {
          const h = {apikey:key, Authorization:'Bearer '+key, 'Content-Type':'application/json'};
          const del = (table) => fetch(url+'/rest/v1/'+table+'?clinic_id=eq.'+id, {method:'DELETE', headers:h}).then(r=>r.status);
          const statuses = {};
          for (const t of ['financial_transactions','invoices','prescriptions','appointments','patients','clinic_users']) {
            statuses[t] = await del(t);
          }
          statuses['clinics_auth'] = await fetch(url+'/rest/v1/clinics_auth?id=eq.'+id, {method:'DELETE', headers:h}).then(r=>r.status);
          return statuses;
        }
        """,
        {"url": SUPABASE_URL, "key": QA_SERVICE_ROLE_KEY, "id": clinic_id},
    )
    if result.get("clinics_auth", 0) < 300:
        rec("PASS", "تنظيف بيانات QA", "حُذفت عيادة الفحص وكل سجلاتها بعد نجاح كامل للتشغيل", clinic_id)
    else:
        rec("WARN", "تنظيف بيانات QA", "فشل حذف عيادة الفحص — راجعها يدوياً", f"{clinic_id} :: {result}")


def check_otp_bypass(page, base):
    """فحص أمني: يحاول إنشاء حساب عبر استدعاء register مباشرة بدون أي دليل على
    التحقق من OTP. إذا نجح السيرفر بإنشاء الحساب، فهذه ثغرة حقيقية (راجع
    generateAndSendOTP/verifyOTP بملف auth-system — التحقق يصير بالمتصفح فقط)."""
    seed = _qa_seed()
    phone = f"07{(seed + 1) % 100000000:08d}"
    email = f"{QA_TAG}.otpbypass.{seed}@example.com"
    page.goto(f"{base}/auth-system-3-1-1.html", wait_until="load")
    result = page.evaluate(
        """
        async ({url, key, clinic, phone, email, password}) => {
          const res = await fetch(url + '/functions/v1/auth-handler', {
            method: 'POST',
            headers: {'Content-Type':'application/json','Authorization':'Bearer '+key,'apikey':key},
            body: JSON.stringify({action:'register', payload:{
              clinicName: clinic, fullName: 'QA Bypass', phone, email, password,
              plan: 'trial', role: 'doctor', status: 'trial'
            }})
          });
          return { status: res.status, body: await res.text() };
        }
        """,
        {"url": SUPABASE_URL, "key": ANON_KEY, "clinic": f"{QA_TAG}-otpbypass-{seed}",
         "phone": phone, "email": email, "password": QA_PASSWORD},
    )
    try:
        ok = json.loads(result["body"]).get("ok")
    except Exception:
        ok = None
    if ok:
        rec("FAIL", "أمان OTP", "السيرفر أنشأ حساباً بدون أي تحقق من رمز OTP — ثغرة تجاوز التحقق",
            f"HTTP {result['status']}")
    elif ok is False:
        rec("PASS", "أمان OTP", "السيرفر رفض التسجيل بدون دليل تحقق من OTP")
    else:
        rec("WARN", "أمان OTP", "رد غير متوقع من auth-handler", str(result)[:150])


def add_employee(page, role, tag):
    seed = _qa_seed()
    phone = f"07{seed % 100000000:08d}"
    name = f"{QA_TAG} {role} {seed}"
    page.evaluate(f"openAddEmployee('{role}')")
    page.fill("#ae-full-name", name)
    page.fill("#ae-phone", phone)
    page.select_option("#ae-role", role)
    page.fill("#ae-password", QA_PASSWORD)
    page.click("#modal-add-employee button.btn-primary")
    try:
        page.wait_for_selector("#add-employee-alert:visible", timeout=8000)
        alert_text = page.inner_text("#add-employee-alert")
    except Exception:
        alert_text = ""
    if "✅" in alert_text or "بنجاح" in alert_text:
        rec("PASS", "إضافة موظف", f"إضافة {role} نجحت", name)
        return {"phone": phone, "password": QA_PASSWORD}
    rec("FAIL", "إضافة موظف", f"فشل إضافة {role}", alert_text[:150] or "لا رسالة")
    return None


def create_clinical_records(page, tag):
    """يضيف مريضاً حقيقياً + موعداً + وصفة + فاتورة عبر نفس دوال الحفظ الفعلية
    بالتطبيق (savePatient/saveAppointment/savePrescription/saveInvoice) —
    بحساب الدكتور فقط، لأن السكرتير/الصيدلاني يحتاجون ربطاً مسبقاً بدكتور
    غير متوفر تلقائياً بحساب فحص جديد."""
    label = f"{tag}/سجلات سريرية"
    seed = _qa_seed()

    try:
        page.evaluate("() => { window.__toasts = []; openModal('modal-patient'); "
                       "if (typeof populatePatientDoctorSelect==='function') populatePatientDoctorSelect(); }")
        page.fill("#pat-name", f"{QA_TAG} مريض {seed}")
        page.fill("#pat-dob", "1990-01-01")
        page.fill("#pat-phone", f"07{seed % 100000000:08d}")
        page.evaluate("savePatient()")
        page.wait_for_timeout(1500)
        ok = any("✅" in t[0] for t in page.evaluate("window.__toasts || []"))
        rec("PASS" if ok else "WARN", label, "إضافة مريض" + (" نجحت" if ok else " — ما ظهرت رسالة نجاح"))
    except Exception as e:  # noqa
        rec("FAIL", label, "فشل إضافة مريض", str(e)[:150])

    try:
        page.evaluate("() => { window.__toasts = []; openModal('modal-appt'); "
                       "if (typeof populateApptDoctorSelect==='function') populateApptDoctorSelect(); }")
        page.fill("#appt-patient-name", f"{QA_TAG} موعد {seed}")
        page.fill("#appt-phone", f"07{seed % 100000000:08d}")
        page.fill("#appt-date", "2027-01-01")
        page.fill("#appt-time", "10:00")
        page.evaluate("saveAppointment()")
        page.wait_for_timeout(1500)
        ok = any("✅" in t[0] for t in page.evaluate("window.__toasts || []"))
        rec("PASS" if ok else "WARN", label, "إضافة موعد" + (" نجحت" if ok else " — ما ظهرت رسالة نجاح"))
    except Exception as e:  # noqa
        rec("FAIL", label, "فشل إضافة موعد", str(e)[:150])

    try:
        page.evaluate("() => { window.__toasts = []; openModal('modal-rx'); }")
        page.wait_for_timeout(800)
        if page.evaluate("(document.getElementById('rx-patient-select')?.options.length||0) > 0"):
            page.select_option("#rx-patient-select", index=0)
            page.evaluate("addDrug()")
            page.fill(".drug-name", "دواء فحص QA")
            page.fill(".drug-dose", "حبة واحدة")
            page.evaluate("savePrescription()")
            page.wait_for_timeout(1500)
            ok = any("✅" in t[0] for t in page.evaluate("window.__toasts || []"))
            rec("PASS" if ok else "WARN", label, "إضافة وصفة" + (" نجحت" if ok else " — ما ظهرت رسالة نجاح"))
        else:
            rec("WARN", label, "لا يوجد مريض بالقائمة لإضافة وصفة له")
    except Exception as e:  # noqa
        rec("FAIL", label, "فشل إضافة وصفة", str(e)[:150])

    try:
        page.evaluate("() => { window.__toasts = []; openModal('modal-invoice'); "
                       "if (typeof populateInvoiceServices==='function') populateInvoiceServices(); }")
        page.wait_for_timeout(800)
        if page.evaluate("(document.getElementById('invoice-patient-select')?.options.length||0) > 0"):
            page.select_option("#invoice-patient-select", index=0)
            page.evaluate("saveInvoice()")
            page.wait_for_timeout(1500)
            ok = any("✅" in t[0] for t in page.evaluate("window.__toasts || []"))
            rec("PASS" if ok else "WARN", label, "إضافة فاتورة" + (" نجحت" if ok else " — ما ظهرت رسالة نجاح"))
        else:
            rec("WARN", label, "لا يوجد مريض بالقائمة لإضافة فاتورة له")
    except Exception as e:  # noqa
        rec("FAIL", label, "فشل إضافة فاتورة", str(e)[:150])


def exercise_role(pw_ctx, base, role, creds, tag):
    """يسجّل دخول بحساب الموظف، يفتح كل قسم ظاهر بالقائمة الجانبية، ويتأكد من
    عدم وجود أخطاء JS/خادم، وأن لا تظهر له أقسام محظورة على دوره."""
    page = pw_ctx.new_page()
    w = Watch(page, base)
    page.goto(f"{base}/auth-system-3-1-1.html", wait_until="load")
    page.fill("#login-identifier", creds["phone"])
    page.fill("#login-password", creds["password"])
    page.evaluate("doLogin()")
    label_login = f"{tag}/{role}"
    try:
        page.wait_for_url("**/dashboard.html*", timeout=20000)
    except Exception:
        rec("FAIL", label_login, "فشل تسجيل الدخول بحساب الموظف الجديد")
        page.close()
        return
    rec("PASS", label_login, "دخول الموظف نجح")
    page.wait_for_timeout(2500)
    page.evaluate(TOAST_HOOK)
    for e in sorted(set(w.js_errors))[:5]:
        rec("FAIL", f"{label_login}/تحميل", "خطأ JavaScript", e)
    for e in sorted(set(w.fn_errors))[:5]:
        rec("FAIL", f"{label_login}/تحميل", "ردّ خطأ من الخادم", e)

    items = page.locator(".nav-item")
    n = items.count()
    visited = 0
    for i in range(n):
        el = items.nth(i)
        try:
            if not el.is_visible():
                continue
            oc = el.get_attribute("onclick") or ""
            m = re.search(r"goTo\(\s*['\"]([^'\"]+)['\"]", oc)
            if not m:
                continue
            target = m.group(1)
            before = w.snapshot()
            page.evaluate("window.__toasts = []")
            el.click(timeout=4000)
            page.wait_for_timeout(1800)
            after = w.snapshot()
            visited += 1
            errs = [t for t in page.evaluate("window.__toasts || []") if t[1] == "error"]
            label = f"{label_login}/{target}"
            problems = False
            if after[0] > before[0]:
                for e in w.js_errors[before[0]:][:3]:
                    rec("FAIL", label, "خطأ JavaScript", e)
                problems = True
            if after[3] > before[3]:
                rec("FAIL", label, "ردّ خطأ من الخادم", ", ".join(sorted(set(w.fn_errors[before[3]:]))[:4]))
                problems = True
            if errs:
                rec("WARN", label, "رسالة خطأ ظهرت للمستخدم", errs[0][0][:100])
                problems = True
            if not problems:
                rec("PASS", label, "يفتح ويحمّل بدون أخطاء")
        except Exception as e:  # noqa
            rec("WARN", f"{label_login}/nav#{i}", "تعذر فتح القسم", str(e)[:100])
    if visited == 0:
        rec("WARN", label_login, "لم يظهر أي قسم بالقائمة لهذا الدور — تأكد أن هذا متوقع")
    if role == "doctor":
        create_clinical_records(page, tag)
    page.close()


def phase_role_pipeline(pw, base):
    if os.getenv("QA_ROLE_SIM", "1") != "1":
        rec("SKIP", "محاكاة الأدوار", "معطّل عبر QA_ROLE_SIM=0")
        return
    browser = launch(pw, "chromium")
    ctx = browser.new_context(viewport={"width": 1366, "height": 850}, service_workers="block")
    stub_emailjs(ctx)
    page = ctx.new_page()

    check_otp_bypass(page, base)

    fails_before_trial = sum(1 for r in RESULTS if r[0] == "FAIL")
    owner = register_trial_owner(page, base, "trial")
    if owner:
        page.wait_for_timeout(1500)
        for role in ("doctor", "secretary", "pharmacist"):  # المشمولة بالباقة التجريبية
            creds = add_employee(page, role, "trial")
            if creds:
                exercise_role(ctx, base, role, creds, "trial")
            page.bring_to_front()
        fails_after_trial = sum(1 for r in RESULTS if r[0] == "FAIL")
        if fails_after_trial == fails_before_trial:
            cleanup_qa_data(page, owner.get("clinic_id"))
        else:
            rec("WARN", "تنظيف بيانات QA", "صارت مشكلة بهذا التشغيل، تُركت عيادة الفحص بدون حذف للمراجعة",
                owner.get("clinic_id"))

    # المختبر متاح فقط بباقة "مجمع كبير". لا نحذف حساب QA_LAB_ACCOUNT الدائم إطلاقاً —
    # لذا نعتمد على حساب دائم مُجهّز يدوياً بدل إنشاء واحد جديد بكل تشغيل.
    if QA_LAB_ACCOUNT and ":" in QA_LAB_ACCOUNT:
        lab_phone, lab_pwd = QA_LAB_ACCOUNT.split(":", 1)
        owner_page = ctx.new_page()
        owner_page.goto(f"{base}/auth-system-3-1-1.html", wait_until="load")
        owner_page.fill("#login-identifier", lab_phone)
        owner_page.fill("#login-password", lab_pwd)
        owner_page.evaluate("doLogin()")
        try:
            owner_page.wait_for_url("**/dashboard.html*", timeout=20000)
            creds = add_employee(owner_page, "lab", "large")
            owner_page.close()
            if creds:
                exercise_role(ctx, base, "lab", creds, "large")
        except Exception:
            rec("FAIL", "محاكاة الأدوار/مختبر", "تعذر الدخول لحساب QA_LAB_ACCOUNT الدائم")
    else:
        rec("SKIP", "محاكاة الأدوار/مختبر", "أضف Secret باسم QA_LAB_ACCOUNT (07xxxxxxxx:كلمة_المرور)",
            "حساب دائم بباقة كبير لاختبار دور المختبر")

    ctx.close()
    browser.close()


# ------------------------------------------------------------ التقرير
def write_report():
    counts = {k: sum(1 for r in RESULTS if r[0] == k) for k in ("PASS", "FAIL", "WARN", "SKIP")}
    lines = ["# نتيجة الفحص الآلي — Doctor Plus", "",
             f"✅ نجح: **{counts['PASS']}**  |  ❌ فشل: **{counts['FAIL']}**  |  ⚠️ تحذير: **{counts['WARN']}**  |  ⏭️ تخطّى: **{counts['SKIP']}**", ""]
    for status, title in (("FAIL", "❌ مشاكل لازم تنحل"), ("WARN", "⚠️ تحذيرات"), ("SKIP", "⏭️ تخطّى")):
        rows = [r for r in RESULTS if r[0] == status]
        if rows:
            lines += [f"## {title}", ""]
            lines += [f"- **{a}** — {n}" + (f" ← `{d}`" if d else "") for _, a, n, d in rows]
            lines.append("")
    text = "\n".join(lines)
    (OUT / "report.md").write_text(text, encoding="utf-8")
    summ = os.getenv("GITHUB_STEP_SUMMARY")
    if summ:
        with open(summ, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    print("\n" + "=" * 60)
    print(f"نجح {counts['PASS']} | فشل {counts['FAIL']} | تحذير {counts['WARN']} | تخطّى {counts['SKIP']}")
    print("=" * 60)
    return counts["FAIL"]


def main():
    base = start_server()
    print(f"الخادم المحلي: {base} | الملفات: {', '.join(HTML_FILES)}")
    phase_static()
    with sync_playwright() as pw:
        for b in BROWSERS:
            phase_pages(pw, base, b)
        phase_pwa(pw, base)
        phase_responsive(pw, base)
        phase_security()
        phase_logged_in(pw, base)
        phase_role_pipeline(pw, base)
    fails = write_report()
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
