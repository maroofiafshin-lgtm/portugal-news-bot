import feedparser
import requests
import os
import json
import re
import time
import urllib3
import trafilatura
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl, urlencode
from datetime import datetime, timezone

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ─────────────────────────────────────────────
# تنظیمات اصلی
# ─────────────────────────────────────────────

GEMINI_KEY = os.environ["GEMINI_API_KEY"]
TG_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TG_CHANNEL = os.environ["TELEGRAM_CHANNEL_ID"]

TG_GROUP_LINK = "https://t.me/LifeInPortugalGroup"

SEEN_FILE = "seen_articles_v2.json"

MAX_PER_RUN = 5
MAX_ITEMS_PER_SOURCE = 20
MAX_AI_ATTEMPTS_PER_RUN = 12
MAX_HASHTAGS = 2


# ─────────────────────────────────────────────
# گزارش‌نویسی
# ─────────────────────────────────────────────

def log(text):
    print(text, flush=True)


# ─────────────────────────────────────────────
# منابع خبری و رسمی
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
# کلمات کلیدی
# ─────────────────────────────────────────────

KEYWORDS = [
    "AIMA",
    "SEF",
    "imigração",
    "imigrantes",
    "estrangeiros",
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
    "transportes públicos",
    "metro",
    "comboios",
    "aeroporto",
    "TAP",
    "SNS",
    "centro de saúde",
    "utente",
]


# ─────────────────────────────────────────────
# موارد غیرخبری
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
    "login",
    "iniciar sessão",
    "área reservada",
]


# ─────────────────────────────────────────────
# نرمال‌سازی لینک برای جلوگیری از تکرار
# ─────────────────────────────────────────────

def normalize_url(url):
    if not url:
        return ""

    try:
        parsed = urlparse(url.strip())

        query_items = []
        for key, value in parse_qsl(parsed.query, keep_blank_values=True):
            k = key.lower()
            if k.startswith("utm_"):
                continue
            if k in ["fbclid", "gclid", "mc_cid", "mc_eid"]:
                continue
            query_items.append((key, value))

        clean_query = urlencode(query_items, doseq=True)

        path = parsed.path
        if path != "/" and path.endswith("/"):
            path = path[:-1]

        normalized = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            "",
            clean_query,
            ""
        ))

        return normalized

    except:
        return url.strip()


# ─────────────────────────────────────────────
# حافظه
# ─────────────────────────────────────────────

def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)

            normalized = {}
            if isinstance(raw, dict):
                for key in raw.keys():
                    normalized[normalize_url(key)] = True

            return normalized

        except:
            return {}

    return {}


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────
# فیلترها
# ─────────────────────────────────────────────

def is_junk_title(title):
    if not title:
        return True

    title_lower = title.lower()

    if len(title_lower) < 20:
        return True

    for pattern in SKIP_PATTERNS:
        if pattern in title_lower:
            return True

    return False


def is_relevant(text):
    if not text:
        return False

    for keyword in KEYWORDS:
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, text, re.IGNORECASE):
            return True

    return False


# ─────────────────────────────────────────────
# استخراج متن کامل خبر
# ─────────────────────────────────────────────

def extract_full_text(url):
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=25,
            verify=False
        )

        if response.status_code != 200:
            return ""

        text = trafilatura.extract(
            response.text,
            include_comments=False,
            include_tables=False
        )

        if text:
            return text[:8000]

        soup = BeautifulSoup(response.text, "html.parser")
        fallback = soup.get_text(" ", strip=True)

        return fallback[:4000]

    except Exception as e:
        log(f"  خطا در دریافت متن کامل: {e}")
        return ""


# ─────────────────────────────────────────────
# RSS
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
        log(f"  خطا در RSS منبع {source['name']}: {e}")

    return items


# ─────────────────────────────────────────────
# HTML Scraping
# ─────────────────────────────────────────────

def get_html_items(source):
    items = []

    try:
        response = requests.get(
            source["url"],
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=25,
            verify=False
        )

        if response.status_code != 200:
            log(f"  پاسخ ناموفق HTML از {source['name']}: {response.status_code}")
            return items

        soup = BeautifulSoup(response.text, "html.parser")

        links = soup.find_all("a", href=True)
        used_links = set()

        for tag in links:
            title = tag.get_text(" ", strip=True)
            href = tag.get("href", "")

            if not title or not href:
                continue

            if is_junk_title(title):
                continue

            full_link = normalize_url(urljoin(source["url"], href))

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
        log(f"  خطا در HTML منبع {source['name']}: {e}")

    return items


def get_source_items(source):
    items = []

    if source.get("rss"):
        items = get_rss_items(source)

    if not items:
        items = get_html_items(source)

    return items


# ─────────────────────────────────────────────
# Gemini
# ─────────────────────────────────────────────

def get_gemini_model_candidates():
    fallback_models = [
        "models/gemini-2.0-flash",
        "models/gemini-2.5-flash-lite",
        "models/gemini-2.5-flash",
        "models/gemini-flash-latest",
    ]

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"

        response = requests.get(url, timeout=30)

        if response.status_code != 200:
            log("  نتوانستم لیست مدل‌های Gemini را بگیرم. استفاده از لیست پیش‌فرض.")
            return fallback_models

        data = response.json()
        models = data.get("models", [])

        usable = []

        for model in models:
            name = model.get("name", "")
            methods = model.get("supportedGenerationMethods", [])

            if "generateContent" not in methods:
                continue

            n = name.lower()

            if "gemini" not in n:
                continue

            if "tts" in n or "image" in n or "audio" in n or "vision" in n:
                continue

            usable.append(name)

        preferred = []

        for wanted in fallback_models:
            if wanted in usable:
                preferred.append(wanted)

        for name in usable:
            if name not in preferred:
                preferred.append(name)

        log("مدل‌های Gemini آماده شدند:")
        for m in preferred[:4]:
            log(f" - {m}")

        return preferred if preferred else fallback_models

    except Exception as e:
        log(f"  خطا در گرفتن مدل‌های Gemini: {e}")
        return fallback_models


GEMINI_MODEL_CANDIDATES = get_gemini_model_candidates()


def call_gemini(prompt):
    for model_path in GEMINI_MODEL_CANDIDATES:
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
                "maxOutputTokens": 1800
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
                    continue

                parts = candidates[0].get("content", {}).get("parts", [])

                if not parts:
                    continue

                text = parts[0].get("text", "")

                if text:
                    log(f"  پاسخ Gemini دریافت شد با مدل {model_path}")
                    return text

            else:
                log(f"  مدل {model_path} پاسخ نداد. کد: {response.status_code}")
                continue

        except Exception as e:
            log(f"  خطا در Gemini با مدل {model_path}: {e}")
            continue

    return None


# ─────────────────────────────────────────────
# ترجمه و ساختاردهی
# ─────────────────────────────────────────────

def translate_and_format(title, body, source_name, source_kind, category):
    body = body or ""

    prompt = f"""
تو سردبیر یک کانال خبری فارسی برای ایرانیان مقیم پرتغال هستی.

وظیفه تو تبدیل خبر پرتغالی یا انگلیسی به یک متن فارسی دقیق، روان، کوتاه و حرفه‌ای است.

قوانین محتوایی:
۱. فقط بر اساس اطلاعات موجود در متن بنویس. چیزی اضافه نکن و حدس نزن.
۲. تاریخ‌ها، اعداد، مهلت‌ها، نام نهادها و اصطلاحات رسمی را دقیق حفظ کن.
۳. اگر خبر درباره قانون است، مشخص کن قانون تصویب شده یا فقط پیشنهاد/طرح/بحث است.
۴. اگر تاریخ اجرا یا مهلت در متن مشخص نیست، بنویس: در متن منبع مشخص نشده است.
۵. اگر منبع رسانه‌ای است و رسمی نیست، با احتیاط اشاره کن که این خبر از منبع رسانه‌ای منتشر شده است.
۶. نثر فارسی باید روان، واضح و حرفه‌ای باشد.
۷. متن نباید تبلیغاتی، احساسی یا اغراق‌آمیز باشد.
۸. از کپی‌برداری طولانی از متن منبع خودداری کن.

قوانین قالب‌بندی:
۱. هرگز از ایموجی استفاده نکن.
۲. هرگز از علامت ستاره (*) یا Markdown استفاده نکن.
۳. SUMMARY حداکثر ۳ جمله کامل باشد.
۴. DETAILS حداکثر ۴ نکته کوتاه باشد.
۵. هر نکته در DETAILS با علامت • شروع شود.
۶. TITLE حداکثر ۶۰ حرف باشد.
۷. جمله‌ها را نیمه‌کاره رها نکن.
۸. در TAGS فقط ۲ هشتگ بده.

اطلاعات منبع:
نام منبع: {source_name}
نوع منبع: {source_kind}
دسته‌بندی: {category}

عنوان اصلی:
{title}

متن خبر:
{body[:4000]}

خروجی را دقیقاً با این ساختار بده:

TITLE: [عنوان فارسی کوتاه]

SUMMARY: [خلاصه خبر در حداکثر ۳ جمله کامل]

DETAILS: [حداکثر ۴ نکته کوتاه، هر نکته با •]

TAGS: [دو هشتگ]
"""

    ai_text = call_gemini(prompt)

    if not ai_text:
        return None

    return parse_ai_output(ai_text, title)


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
# تمیزکاری متن
# ─────────────────────────────────────────────

def clean_text(text):
    if not text:
        return ""

    text = text.replace("**", "")
    text = text.replace("__", "")
    text = text.replace("##", "")
    text = text.replace("*", "")

    cleaned_lines = []

    for line in text.split("\n"):
        line = line.strip()

        if not line:
            continue

        if line.startswith("- "):
            line = "• " + line[2:]

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def escape_html(text):
    if not text:
        return ""

    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")

    return text


def category_hashtags(category):
    mapping = {
        "immigration": "#پرتغال #مهاجرت",
        "citizenship": "#پرتغال #تابعیت",
        "law": "#پرتغال #قانون",
        "government": "#پرتغال #دولت",
        "tax": "#پرتغال #مالیات",
        "social_security": "#پرتغال #بیمه",
        "health": "#پرتغال #سلامت",
        "work": "#پرتغال #کار",
        "finance": "#پرتغال #مالی",
        "telecom": "#پرتغال #مخابرات",
        "energy": "#پرتغال #انرژی",
        "insurance": "#پرتغال #بیمه",
        "consumer_rights": "#پرتغال #حقوق",
        "strike": "#پرتغال #اعتصاب",
        "transport": "#پرتغال #حملونقل",
        "travel": "#پرتغال #سفر",
        "eu_rights": "#پرتغال #اروپا",
        "eu_law": "#پرتغال #اروپا",
        "eu_migration": "#پرتغال #مهاجرت",
        "economy": "#پرتغال #اقتصاد",
        "expats": "#پرتغال #مهاجرت",
        "housing": "#پرتغال #مسکن",
        "news": "#پرتغال #خبر"
    }

    return mapping.get(category, "#پرتغال #خبر")


# ─────────────────────────────────────────────
# ساخت پیام تلگرام
# ─────────────────────────────────────────────

def build_telegram_message(data, source_name, link, group_link, category):
    title = clean_text(data.get("title", ""))
    summary = clean_text(data.get("summary", ""))
    details = clean_text(data.get("details", ""))

    if not summary:
        summary = "خلاصه خبر در متن منبع مشخص نشده است."

    if not details:
        details = "جزئیات بیشتری در متن منبع ارائه نشده است."

    if len(details) > 900:
        details = details[:850] + "\nبرای مطالعه جزئیات کامل به لینک منبع مراجعه کنید."

    tags = category_hashtags(category)

    title_html = escape_html(title)
    summary_html = escape_html(summary)
    details_html = escape_html(details)
    source_html = escape_html(source_name)
    tags_html = escape_html(tags)

    message = f"""<b>{title_html}</b>

<b>خلاصه خبر</b>
{summary_html}

<b>جزئیات مهم خبر</b>
{details_html}

برای دانستن جزئیات بیشتر به لینک منبع مراجعه کنید:

<b>منبع:</b> {source_html}
{link}

{tags_html}

<b>گروه زندگی در پرتغال را با دیگران به اشتراک بگذارید</b>
{group_link}"""

    if len(message) > 3900:
        message = message[:3800] + "\n\n... متن کوتاه شد. برای جزئیات بیشتر به منبع مراجعه کنید."

    return message


# ─────────────────────────────────────────────
# ارسال به تلگرام
# ─────────────────────────────────────────────

def send_to_telegram(message, link):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"

    payload = {
        "chat_id": TG_CHANNEL,
        "text": message,
        "parse_mode": "HTML",
        "link_preview_options": {
            "url": link,
            "prefer_small_media": True
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=25)

        if response.status_code == 200:
            log("  پیام با موفقیت به تلگرام ارسال شد.")
            return True

        log(f"  خطا در ارسال تلگرام: {response.text[:300]}")

        plain_payload = {
            "chat_id": TG_CHANNEL,
            "text": message.replace("<b>", "").replace("</b>", ""),
            "link_preview_options": {
                "url": link,
                "prefer_small_media": True
            }
        }

        retry_response = requests.post(url, json=plain_payload, timeout=25)

        if retry_response.status_code == 200:
            log("  پیام در تلاش دوم ارسال شد.")
            return True

        log(f"  تلاش دوم هم ناموفق بود: {retry_response.text[:300]}")
        return False

    except Exception as e:
        log(f"  خطا در اتصال به تلگرام: {e}")
        return False


# ─────────────────────────────────────────────
# برنامه اصلی
# ─────────────────────────────────────────────

def main():
    log("شروع اجرای برنامه")
    log(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))

    seen = load_seen()

    log(f"تعداد لینک‌های موجود در حافظه: {len(seen)}")

    posted = 0
    ai_attempts = 0

    total_sources = 0
    total_items = 0
    skipped_seen = 0
    skipped_junk = 0
    skipped_not_relevant = 0
    relevant_found = 0

    for source in SOURCES:
        if posted >= MAX_PER_RUN:
            break

        if ai_attempts >= MAX_AI_ATTEMPTS_PER_RUN:
            log("به سقف تلاش‌های هوش مصنوعی در این اجرا رسیدیم.")
            break

        total_sources += 1

        log(f"بررسی منبع: {source['name']}")

        items = get_source_items(source)

        total_items += len(items)

        log(f"  تعداد آیتم پیدا شده در این منبع: {len(items)}")

        for item in items:
            if posted >= MAX_PER_RUN:
                break

            if ai_attempts >= MAX_AI_ATTEMPTS_PER_RUN:
                break

            title = item.get("title", "")
            link = normalize_url(item.get("link", ""))
            summary = item.get("summary", "")

            if not link:
                continue

            if link in seen:
                skipped_seen += 1
                continue

            if is_junk_title(title):
                skipped_junk += 1
                seen[link] = True
                continue

            combined_text = f"{title} {summary}"

            if not is_relevant(combined_text):
                skipped_not_relevant += 1
                seen[link] = True
                continue

            relevant_found += 1

            log(f"  خبر مرتبط پیدا شد: {title[:100]}")

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
                category=source["category"]
            )

            if not result:
                log("  خروجی قابل ارسال ساخته نشد. این لینک در حافظه ذخیره نمی‌شود.")
                continue

            telegram_message = build_telegram_message(
                data=result,
                source_name=source["name"],
                link=link,
                group_link=TG_GROUP_LINK,
                category=source["category"]
            )

            sent = send_to_telegram(telegram_message, link)

            if sent:
                posted += 1
                seen[link] = True
                time.sleep(3)
            else:
                log("  پیام ارسال نشد. این لینک در حافظه ذخیره نمی‌شود.")

    save_seen(seen)

    log("پایان اجرا")
    log(f"منابع بررسی‌شده: {total_sources}")
    log(f"کل آیتم‌های پیدا شده: {total_items}")
    log(f"خبرهای تکراری رد شده: {skipped_seen}")
    log(f"لینک‌های غیرخبری رد شده: {skipped_junk}")
    log(f"خبرهای غیرمرتبط رد شده: {skipped_not_relevant}")
    log(f"خبرهای مرتبط پیدا شده: {relevant_found}")
    log(f"تلاش‌های هوش مصنوعی: {ai_attempts}")
    log(f"تعداد پیام‌های ارسال‌شده: {posted}")


if __name__ == "__main__":
    main()
