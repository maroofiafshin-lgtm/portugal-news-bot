import feedparser
import requests
import os
import json
import re
import time
import urllib3
import trafilatura
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timezone

# ─────────────────────────────────────────────
# غیرفعال کردن هشدارهای SSL
# بعضی سایت‌های رسمی پرتغال در GitHub Actions
# ممکن است خطای certificate بدهند.
# ─────────────────────────────────────────────

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ─────────────────────────────────────────────
# تنظیمات اصلی
# ─────────────────────────────────────────────

GEMINI_KEY = os.environ["GEMINI_API_KEY"]
TG_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TG_CHANNEL = os.environ["TELEGRAM_CHANNEL_ID"]

TG_GROUP_LINK = "https://t.me/LifeInPortugalGroup"

# نسخه جدید فایل حافظه، تا لینک‌هایی که قبلاً به خاطر خطای Gemini ارسال نشدند دوباره بررسی شوند
SEEN_FILE = "seen_articles_v2.json"

MAX_PER_RUN = 5
MAX_ITEMS_PER_SOURCE = 10
MAX_AI_ATTEMPTS_PER_RUN = 10


# ─────────────────────────────────────────────
# منابع خبری و رسمی فاز اول
# ─────────────────────────────────────────────

SOURCES = [
    {
        "name": "AIMA",
        "url": "https://aima.gov.pt/pt/noticias",
        "rss": "",
        "kind": "official",
        "category": "immigration"
    },
    {
        "name": "Diário da República Eletrónico - DRE",
        "url": "https://dre.pt",
        "rss": "",
        "kind": "official",
        "category": "law"
    },
    {
        "name": "Governo de Portugal",
        "url": "https://www.portugal.gov.pt/pt/gc23/comunicacao/noticias",
        "rss": "",
        "kind": "official",
        "category": "government"
    },
    {
        "name": "Assembleia da República",
        "url": "https://www.parlamento.pt/ActividadeParlamentar/Paginas/default.aspx",
        "rss": "",
        "kind": "official",
        "category": "law"
    },
    {
        "name": "IRN - Instituto dos Registos e do Notariado",
        "url": "https://irn.justica.gov.pt/Noticias",
        "rss": "",
        "kind": "official",
        "category": "citizenship"
    },
    {
        "name": "Justiça",
        "url": "https://justica.gov.pt/Noticias",
        "rss": "",
        "kind": "official",
        "category": "justice"
    },
    {
        "name": "ePortugal",
        "url": "https://eportugal.gov.pt/noticias",
        "rss": "",
        "kind": "official",
        "category": "public_services"
    },
    {
        "name": "Portal das Finanças / Autoridade Tributária",
        "url": "https://info.portaldasfinancas.gov.pt/pt/apoio_contribuinte/Noticias/",
        "rss": "",
        "kind": "official",
        "category": "tax"
    },
    {
        "name": "Segurança Social",
        "url": "https://www.seg-social.pt/noticias",
        "rss": "",
        "kind": "official",
        "category": "social_security"
    },
    {
        "name": "SNS24",
        "url": "https://www.sns24.gov.pt/noticias/",
        "rss": "",
        "kind": "official",
        "category": "health"
    },
    {
        "name": "IEFP",
        "url": "https://www.iefp.pt/noticias",
        "rss": "",
        "kind": "official",
        "category": "work"
    },
    {
        "name": "ACT - Autoridade para as Condições do Trabalho",
        "url": "https://www.act.gov.pt/(pt-PT)/SobreACT/Noticias/Paginas/default.aspx",
        "rss": "",
        "kind": "official",
        "category": "work"
    },
    {
        "name": "Banco de Portugal",
        "url": "https://www.bportugal.pt/comunicados",
        "rss": "",
        "kind": "official",
        "category": "finance"
    },
    {
        "name": "ANACOM",
        "url": "https://www.anacom.pt/render.jsp?categoryId=2958",
        "rss": "",
        "kind": "official",
        "category": "telecom"
    },
    {
        "name": "ERSE",
        "url": "https://www.erse.pt/atividade/noticias/",
        "rss": "",
        "kind": "official",
        "category": "energy"
    },
    {
        "name": "ASF",
        "url": "https://www.asf.com.pt",
        "rss": "",
        "kind": "official",
        "category": "insurance"
    },
    {
        "name": "DECO Proteste",
        "url": "https://www.deco.proteste.pt",
        "rss": "",
        "kind": "specialized",
        "category": "consumer_rights"
    },
    {
        "name": "BTE - Boletim do Trabalho e Emprego",
        "url": "https://bte.gep.mtsss.gov.pt",
        "rss": "",
        "kind": "official",
        "category": "strike"
    },
    {
        "name": "CP - Comboios de Portugal",
        "url": "https://www.cp.pt/passageiros/pt/noticias",
        "rss": "",
        "kind": "official",
        "category": "transport"
    },
    {
        "name": "Fertagus",
        "url": "https://www.fertagus.pt/pt/noticias",
        "rss": "",
        "kind": "official",
        "category": "transport"
    },
    {
        "name": "Metropolitano de Lisboa",
        "url": "https://www.metrolisboa.pt/informacao/noticias/",
        "rss": "",
        "kind": "official",
        "category": "transport"
    },
    {
        "name": "Carris",
        "url": "https://www.carris.pt/noticias/",
        "rss": "",
        "kind": "official",
        "category": "transport"
    },
    {
        "name": "STCP",
        "url": "https://www.stcp.pt/pt/noticias/",
        "rss": "",
        "kind": "official",
        "category": "transport"
    },
    {
        "name": "Metro do Porto",
        "url": "https://www.metrodoporto.pt",
        "rss": "",
        "kind": "official",
        "category": "transport"
    },
    {
        "name": "Transtejo / Soflusa",
        "url": "https://ttsl.pt",
        "rss": "",
        "kind": "official",
        "category": "transport"
    },
    {
        "name": "ANA Aeroportos",
        "url": "https://www.ana.pt",
        "rss": "",
        "kind": "official",
        "category": "travel"
    },
    {
        "name": "TAP Air Portugal",
        "url": "https://www.flytap.com/pt-pt/ultimas-noticias",
        "rss": "",
        "kind": "official",
        "category": "travel"
    },
    {
        "name": "Your Europe",
        "url": "https://europa.eu/youreurope/citizens/index_pt.htm",
        "rss": "",
        "kind": "official",
        "category": "eu_rights"
    },
    {
        "name": "EUR-Lex",
        "url": "https://eur-lex.europa.eu/homepage.html",
        "rss": "",
        "kind": "official",
        "category": "eu_law"
    },
    {
        "name": "European Commission - Migration and Home Affairs",
        "url": "https://home-affairs.ec.europa.eu/news_en",
        "rss": "",
        "kind": "official",
        "category": "eu_migration"
    },
    {
        "name": "Lusa",
        "url": "https://www.lusa.pt",
        "rss": "https://www.lusa.pt/rss",
        "kind": "media",
        "category": "news"
    },
    {
        "name": "Público",
        "url": "https://www.publico.pt",
        "rss": "https://feeds.feedburner.com/PublicoRSS",
        "kind": "media",
        "category": "news"
    },
    {
        "name": "Expresso",
        "url": "https://expresso.pt",
        "rss": "https://expresso.pt/rss",
        "kind": "media",
        "category": "news"
    },
    {
        "name": "Observador",
        "url": "https://observador.pt",
        "rss": "https://observador.pt/feed/",
        "kind": "media",
        "category": "news"
    },
    {
        "name": "Diário de Notícias",
        "url": "https://www.dn.pt",
        "rss": "https://www.dn.pt/rss",
        "kind": "media",
        "category": "news"
    },
    {
        "name": "RTP Notícias",
        "url": "https://www.rtp.pt/noticias",
        "rss": "https://www.rtp.pt/noticias/rss",
        "kind": "media",
        "category": "news"
    },
    {
        "name": "Rádio Renascença",
        "url": "https://rr.sapo.pt",
        "rss": "https://rr.sapo.pt/rss/rss.aspx",
        "kind": "media",
        "category": "news"
    },
    {
        "name": "ECO",
        "url": "https://eco.sapo.pt",
        "rss": "https://eco.sapo.pt/feed/",
        "kind": "media",
        "category": "economy"
    },
    {
        "name": "Jornal de Negócios",
        "url": "https://www.jornaldenegocios.pt",
        "rss": "https://www.jornaldenegocios.pt/rss",
        "kind": "media",
        "category": "economy"
    },
    {
        "name": "Dinheiro Vivo",
        "url": "https://www.dinheirovivo.pt",
        "rss": "https://www.dinheirovivo.pt/feed/",
        "kind": "media",
        "category": "economy"
    },
    {
        "name": "The Portugal News",
        "url": "https://www.theportugalnews.com",
        "rss": "https://www.theportugalnews.com/rss",
        "kind": "media",
        "category": "expats"
    },
    {
        "name": "Portugal Resident",
        "url": "https://www.portugalresident.com",
        "rss": "https://www.portugalresident.com/feed/",
        "kind": "media",
        "category": "expats"
    },
    {
        "name": "Idealista News",
        "url": "https://www.idealista.pt/news",
        "rss": "https://www.idealista.pt/news/rss",
        "kind": "media",
        "category": "housing"
    },
]


# ─────────────────────────────────────────────
# کلمات کلیدی برای تشخیص خبرهای مرتبط
# ─────────────────────────────────────────────

KEYWORDS = [
    "AIMA",
    "SEF",
    "imigração",
    "imigrantes",
    "residência",
    "autorização de residência",
    "visto",
    "vistos",
    "asilo",
    "reagrupamento familiar",
    "manifestação de interesse",
    "cartão de residência",
    "nacionalidade",
    "cidadania",
    "IRS",
    "IRC",
    "IVA",
    "IMI",
    "NHR",
    "Autoridade Tributária",
    "NIF",
    "declaração",
    "imposto",
    "benefício fiscal",
    "finanças",
    "Segurança Social",
    "contrato de trabalho",
    "salário mínimo",
    "subsídio",
    "desemprego",
    "ACT",
    "trabalhadores estrangeiros",
    "greve",
    "paralisação",
    "sindicato",
    "transportes",
    "aeroporto",
    "SNS",
    "centro de saúde",
    "utente",
]


# ─────────────────────────────────────────────
# عبارات غیرخبری که باید حذف شوند
# ─────────────────────────────────────────────

SKIP_PATTERNS = [
    "privacidade",
    "privacy",
    "cookie",
    "cookies",
    "newsletter",
    "facebook",
    "instagram",
    "twitter",
    "x.com",
    "linkedin",
    "youtube",
    "logótipo",
    "logo",
    "contactar",
    "contacto",
    "contact us",
    "oferta exclusiva",
    "subscrever",
    "subscribe",
    "miles&go",
    "programa de fidelidade",
    "business activity",
    "our business",
    "termos e condições",
    "terms and conditions",
    "mapa do site",
    "sitemap",
    "dados pessoais",
    "personal data",
    "política de",
    "política de privacidade",
]


# ─────────────────────────────────────────────
# حافظه برنامه
# ─────────────────────────────────────────────

def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────
# فیلتر موارد غیرخبری
# ─────────────────────────────────────────────

def is_junk_title(title):
    if not title:
        return True

    title_lower = title.lower()

    for pattern in SKIP_PATTERNS:
        if pattern in title_lower:
            return True

    return False


# ─────────────────────────────────────────────
# تشخیص مرتبط بودن خبر
# ─────────────────────────────────────────────

def is_relevant(text):
    if not text:
        return False

    for keyword in KEYWORDS:
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, text, re.IGNORECASE):
            return True

    return False


# ─────────────────────────────────────────────
# دریافت متن کامل خبر
# ─────────────────────────────────────────────

def extract_full_text(url):
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=25,
            verify=False
        )

        if response.status_code == 200:
            text = trafilatura.extract(
                response.text,
                include_comments=False,
                include_tables=False
            )
            if text:
                return text

    except Exception as e:
        print(f"  خطا در دریافت متن کامل: {e}")

    return ""


# ─────────────────────────────────────────────
# دریافت خبر از RSS
# ─────────────────────────────────────────────

def get_rss_items(source):
    items = []

    rss_url = source.get("rss", "")

    if not rss_url:
        return items

    try:
        feed = feedparser.parse(rss_url)

        for entry in feed.entries[:MAX_ITEMS_PER_SOURCE]:
            title = entry.get("title", "")
            link = entry.get("link", "")
            summary = entry.get("summary", "")

            if title and link:
                items.append({
                    "title": title,
                    "link": link,
                    "summary": summary,
                })

    except Exception as e:
        print(f"  خطا در RSS منبع {source['name']}: {e}")

    return items


# ─────────────────────────────────────────────
# دریافت خبر از HTML / اسکرپینگ ساده
# ─────────────────────────────────────────────

def get_html_items(source):
    items = []

    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(
            source["url"],
            headers=headers,
            timeout=25,
            verify=False
        )

        soup = BeautifulSoup(response.text, "html.parser")

        links = soup.find_all("a", href=True)
        used_links = set()

        for tag in links:
            title = tag.get_text(" ", strip=True)
            href = tag.get("href", "")

            if not title or not href:
                continue

            if len(title) < 25:
                continue

            if is_junk_title(title):
                continue

            full_link = urljoin(source["url"], href)

            if full_link in used_links:
                continue

            used_links.add(full_link)

            items.append({
                "title": title,
                "link": full_link,
                "summary": ""
            })

            if len(items) >= MAX_ITEMS_PER_SOURCE:
                break

    except Exception as e:
        print(f"  خطا در HTML منبع {source['name']}: {e}")

    return items


# ─────────────────────────────────────────────
# دریافت آیتم‌ها از منبع
# ─────────────────────────────────────────────

def get_source_items(source):
    items = []

    if source.get("rss"):
        items = get_rss_items(source)

    if not items:
        items = get_html_items(source)

    return items


# ─────────────────────────────────────────────
# پیدا کردن مدل فعال Gemini به شکل خودکار
# ─────────────────────────────────────────────

def get_gemini_model_candidates():
    fallback_models = [
        "models/gemini-2.5-flash",
        "models/gemini-2.5-flash-lite",
        "models/gemini-2.0-flash",
        "models/gemini-2.0-flash-lite",
        "models/gemini-flash-latest",
        "models/gemini-2.0-flash-001",
        "models/gemini-1.5-flash-latest"
    ]

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"

        response = requests.get(
            url,
            timeout=30
        )

        if response.status_code != 200:
            print(f"  نتوانستم لیست مدل‌های Gemini را بگیرم. استفاده از لیست پیش‌فرض. پاسخ: {response.status_code}")
            return fallback_models

        data = response.json()
        models = data.get("models", [])

        usable = []

        for model in models:
            name = model.get("name", "")
            methods = model.get("supportedGenerationMethods", [])

            if "generateContent" not in methods:
                continue

            if "gemini" not in name.lower():
                continue

            usable.append(name)

        if not usable:
            print("  هیچ مدل قابل استفاده‌ای از Gemini پیدا نشد. استفاده از لیست پیش‌فرض.")
            return fallback_models

        def score_model(name):
            n = name.lower()

            if "2.5" in n and "flash" in n:
                return 100
            if "2.0" in n and "flash" in n:
                return 90
            if "flash" in n:
                return 80
            if "pro" in n:
                return 60
            return 10

        usable = sorted(usable, key=score_model, reverse=True)

        print("  مدل‌های قابل استفاده Gemini پیدا شدند:")
        for m in usable[:5]:
            print(f"   - {m}")

        return usable + fallback_models

    except Exception as e:
        print(f"  خطا در گرفتن لیست مدل‌های Gemini: {e}")
        return fallback_models


GEMINI_MODEL_CANDIDATES = get_gemini_model_candidates()


# ─────────────────────────────────────────────
# فراخوانی Gemini با REST API
# ─────────────────────────────────────────────

def call_gemini(prompt):
    for model_name in GEMINI_MODEL_CANDIDATES:
        if not model_name.startswith("models/"):
            model_path = f"models/{model_name}"
        else:
            model_path = model_name

        api_url = f"https://generativelanguage.googleapis.com/v1beta/{model_path}:generateContent?key={GEMINI_KEY}"

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1000
            }
        }

        try:
            response = requests.post(
                api_url,
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                candidates = data.get("candidates", [])

                if not candidates:
                    print(f"  Gemini پاسخ بدون candidates داد با مدل {model_path}")
                    continue

                parts = candidates[0].get("content", {}).get("parts", [])

                if not parts:
                    print(f"  Gemini پاسخ بدون متن داد با مدل {model_path}")
                    continue

                text = parts[0].get("text", "")

                if text:
                    print(f"  پاسخ Gemini با مدل {model_path} دریافت شد.")
                    return text

            elif response.status_code == 404:
                print(f"  مدل در دسترس نیست، امتحان مدل بعدی: {model_path}")
                continue

            else:
                print(f"  خطای Gemini با مدل {model_path}: {response.status_code}")
                print(f"  پاسخ کوتاه Gemini: {response.text[:500]}")
                continue

        except Exception as e:
            print(f"  خطا در تماس با Gemini با مدل {model_path}: {e}")
            continue

    return None


# ─────────────────────────────────────────────
# ارسال متن به Gemini برای ترجمه و بازنویسی
# ─────────────────────────────────────────────

def translate_and_format(title, body, source_name, source_kind, link, category):
    body = body or ""

    prompt = f"""
تو سردبیر یک کانال خبری فارسی برای ایرانیان مقیم پرتغال هستی.

یک خبر یا اطلاعیه پرتغالی/انگلیسی داری که باید آن را برای مخاطبان فارسی‌زبان آماده کنی.

هدف:
تولید یک متن فارسی دقیق، روان، قابل فهم برای عموم، و در عین حال حرفه‌ای.

قوانین بسیار مهم:
۱. فقط بر اساس اطلاعات موجود در متن بنویس. چیزی اضافه نکن و حدس نزن.
۲. تاریخ‌ها، اعداد، مهلت‌ها، نام نهادها و اصطلاحات رسمی را دقیق حفظ کن.
۳. اگر خبر درباره قانون است، دقت کن که آیا قانون تصویب شده یا فقط پیشنهاد/طرح/بحث است.
۴. اگر در متن منبع تاریخ اجرا، مهلت یا جزئیات مهم مشخص نشده، بنویس: در متن منبع مشخص نشده است.
۵. اگر منبع رسانه‌ای است و نه رسمی، در جزئیات با احتیاط اشاره کن که این خبر از منبع رسانه‌ای منتشر شده است.
۶. نثر فارسی باید روان، واضح و حرفه‌ای باشد. نه خشک و نه خیلی عامیانه.
۷. اگر خبر برای ایرانیان مقیم پرتغال اهمیت عملی ندارد، متن را خیلی کوتاه و محتاطانه بنویس.
۸. متن نباید تبلیغاتی، احساسی یا اغراق‌آمیز باشد.
۹. از کپی‌برداری طولانی از متن منبع خودداری کن.
۱۰. خروجی باید برای انتشار در تلگرام مناسب باشد.

اطلاعات منبع:
نام منبع: {source_name}
نوع منبع: {source_kind}
دسته‌بندی: {category}
لینک: {link}

عنوان اصلی:
{title}

متن خبر:
{body[:4000]}

خروجی را دقیقاً با این ساختار بده و هیچ متن اضافه‌ای قبل یا بعد از آن ننویس:

TITLE: [عنوان فارسی کوتاه، واضح و خبری]

SUMMARY: [خلاصه خبر در ۲ تا ۴ جمله، به اندازه‌ای که اصل موضوع را بیان کند و کاربر دچار ابهام نشود]

DETAILS: [جزئیات مهم خبر در چند نکته کوتاه و کاربردی. اگر جزئیات مهمی در متن نیست، بنویس: جزئیات بیشتری در متن منبع ارائه نشده است.]

TAGS: [۳ تا ۵ هشتگ مرتبط فارسی، مثل #پرتغال #مهاجرت #اقامت]
"""

    try:
        ai_text = call_gemini(prompt)

        if not ai_text:
            print(f"  Gemini نتوانست متن تولید کند برای: {title[:60]}")
            return None

        return parse_ai_output(ai_text, title)

    except Exception as e:
        print(f"  خطا در هوش مصنوعی برای [{title[:60]}]: {type(e).__name__}: {e}")
        return None


# ─────────────────────────────────────────────
# تبدیل خروجی Gemini به بخش‌های مشخص
# ─────────────────────────────────────────────

def parse_ai_output(text, fallback_title):
    data = {
        "title": fallback_title,
        "summary": "",
        "details": "",
        "tags": ""
    }

    if not text:
        return data

    lines = text.strip().split("\n")

    current_key = None
    buffer = []

    key_map = {
        "TITLE": "title",
        "SUMMARY": "summary",
        "DETAILS": "details",
        "TAGS": "tags"
    }

    for line in lines:
        line = line.strip()

        matched = False

        for key, field in key_map.items():
            prefix = f"{key}:"

            if line.startswith(prefix):
                if current_key and buffer:
                    data[current_key] = "\n".join(buffer).strip()

                current_key = field
                buffer = [line[len(prefix):].strip()]
                matched = True
                break

        if not matched and current_key:
            buffer.append(line)

    if current_key and buffer:
        data[current_key] = "\n".join(buffer).strip()

    return data


# ─────────────────────────────────────────────
# ساخت پیام نهایی تلگرام
# ─────────────────────────────────────────────

def build_telegram_message(data, source_name, link, group_link):
    title = data.get("title", "").strip()
    summary = data.get("summary", "").strip()
    details = data.get("details", "").strip()
    tags = data.get("tags", "").strip()

    if not summary:
        summary = "خلاصه خبر در متن منبع مشخص نشده است."

    if not details:
        details = "جزئیات بیشتری در متن منبع ارائه نشده است."

    if not tags:
        tags = "#پرتغال"

    message = f"""📰 {title}

{summary}

📋 جزئیات مهم خبر:
{details}

برای دانستن جزئیات بیشتر به لینک منبع مراجعه کنید:

🔗 {source_name}
{link}

{tags}

👥 گروه زندگی در پرتغال:
{group_link}"""

    if len(message) > 3900:
        message = message[:3800] + "\n\n... متن کوتاه شد. برای جزئیات بیشتر به منبع مراجعه کنید."

    return message


# ─────────────────────────────────────────────
# ارسال پیام به تلگرام
# ─────────────────────────────────────────────

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"

    payload = {
        "chat_id": TG_CHANNEL,
        "text": message,
        "disable_web_page_preview": False
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=25
        )

        if response.status_code == 200:
            print("  پیام با موفقیت به تلگرام ارسال شد.")
            return True
        else:
            print(f"  خطا در ارسال تلگرام: {response.text}")
            return False

    except Exception as e:
        print(f"  خطا در اتصال به تلگرام: {e}")
        return False


# ─────────────────────────────────────────────
# برنامه اصلی
# ─────────────────────────────────────────────

def main():
    print("شروع اجرای برنامه")
    print(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))

    seen = load_seen()
    posted = 0
    ai_attempts = 0

    for source in SOURCES:
        if posted >= MAX_PER_RUN:
            break

        if ai_attempts >= MAX_AI_ATTEMPTS_PER_RUN:
            print("به سقف تلاش‌های هوش مصنوعی در این اجرا رسیدیم.")
            break

        print(f"بررسی منبع: {source['name']}")

        items = get_source_items(source)

        for item in items:
            if posted >= MAX_PER_RUN:
                break

            if ai_attempts >= MAX_AI_ATTEMPTS_PER_RUN:
                print("به سقف تلاش‌های هوش مصنوعی در این اجرا رسیدیم.")
                break

            title = item.get("title", "")
            link = item.get("link", "")
            summary = item.get("summary", "")

            if not link:
                continue

            if link in seen:
                continue

            if is_junk_title(title):
                seen[link] = True
                continue

            combined_text = f"{title} {summary}"

            if not is_relevant(combined_text):
                seen[link] = True
                continue

            print(f"  خبر مرتبط پیدا شد: {title[:80]}")

            full_text = extract_full_text(link)

            if not full_text:
                full_text = summary

            if not full_text:
                full_text = title

            ai_attempts += 1

            result = translate_and_format(
                title=title,
                body=full_text,
                source_name=source["name"],
                source_kind=source["kind"],
                link=link,
                category=source["category"]
            )

            if result:
                telegram_message = build_telegram_message(
                    data=result,
                    source_name=source["name"],
                    link=link,
                    group_link=TG_GROUP_LINK
                )

                sent = send_to_telegram(telegram_message)

                if sent:
                    posted += 1
                    seen[link] = True
                    time.sleep(3)
                else:
                    print("  پیام ارسال نشد، بنابراین این لینک به عنوان دیده‌شده ذخیره نمی‌شود.")
            else:
                print("  خروجی قابل ارسال ساخته نشد، بنابراین این لینک به عنوان دیده‌شده ذخیره نمی‌شود.")

    save_seen(seen)

    print(f"پایان اجرا. تعداد پیام‌های ارسال‌شده: {posted}")


if __name__ == "__main__":
    main()
