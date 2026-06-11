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

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# تنظیمات اصلی
GEMINI_KEY = os.environ["GEMINI_API_KEY"]
TG_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TG_CHANNEL = os.environ["TELEGRAM_CHANNEL_ID"]
TG_GROUP_LINK = "https://t.me/LifeInPortugalGroup"
SEEN_FILE = "seen_articles_v2.json"

MAX_PER_RUN = 5
MAX_ITEMS_PER_SOURCE = 10
MAX_AI_ATTEMPTS_PER_RUN = 10

# همان لیست منابع قبلی
SOURCES = [
    {"name": "AIMA", "url": "https://aima.gov.pt/pt/noticias", "rss": "", "kind": "official", "category": "immigration"},
    {"name": "Diário da República - DRE", "url": "https://dre.pt", "rss": "", "kind": "official", "category": "law"},
    {"name": "Governo de Portugal", "url": "https://www.portugal.gov.pt/pt/gc23/comunicacao/noticias", "rss": "", "kind": "official", "category": "government"},
    {"name": "Assembleia da República", "url": "https://www.parlamento.pt/ActividadeParlamentar/Paginas/default.aspx", "rss": "", "kind": "official", "category": "law"},
    {"name": "IRN", "url": "https://irn.justica.gov.pt/Noticias", "rss": "", "kind": "official", "category": "citizenship"},
    {"name": "Justiça", "url": "https://justica.gov.pt/Noticias", "rss": "", "kind": "official", "category": "justice"},
    {"name": "ePortugal", "url": "https://eportugal.gov.pt/noticias", "rss": "", "kind": "official", "category": "public_services"},
    {"name": "Portal das Finanças", "url": "https://info.portaldasfinancas.gov.pt/pt/apoio_contribuinte/Noticias/", "rss": "", "kind": "official", "category": "tax"},
    {"name": "Segurança Social", "url": "https://www.seg-social.pt/noticias", "rss": "", "kind": "official", "category": "social_security"},
    {"name": "SNS24", "url": "https://www.sns24.gov.pt/noticias/", "rss": "", "kind": "official", "category": "health"},
    {"name": "IEFP", "url": "https://www.iefp.pt/noticias", "rss": "", "kind": "official", "category": "work"},
    {"name": "ACT", "url": "https://www.act.gov.pt/(pt-PT)/SobreACT/Noticias/Paginas/default.aspx", "rss": "", "kind": "official", "category": "work"},
    {"name": "Banco de Portugal", "url": "https://www.bportugal.pt/comunicados", "rss": "", "kind": "official", "category": "finance"},
    {"name": "ANACOM", "url": "https://www.anacom.pt/render.jsp?categoryId=2958", "rss": "", "kind": "official", "category": "telecom"},
    {"name": "ERSE", "url": "https://www.erse.pt/atividade/noticias/", "rss": "", "kind": "official", "category": "energy"},
    {"name": "ASF", "url": "https://www.asf.com.pt", "rss": "", "kind": "official", "category": "insurance"},
    {"name": "DECO Proteste", "url": "https://www.deco.proteste.pt", "rss": "", "kind": "specialized", "category": "consumer_rights"},
    {"name": "BTE", "url": "https://bte.gep.mtsss.gov.pt", "rss": "", "kind": "official", "category": "strike"},
    {"name": "CP - Comboios", "url": "https://www.cp.pt/passageiros/pt/noticias", "rss": "", "kind": "official", "category": "transport"},
    {"name": "Fertagus", "url": "https://www.fertagus.pt/pt/noticias", "rss": "", "kind": "official", "category": "transport"},
    {"name": "Metro Lisboa", "url": "https://www.metrolisboa.pt/informacao/noticias/", "rss": "", "kind": "official", "category": "transport"},
    {"name": "Carris", "url": "https://www.carris.pt/noticias/", "rss": "", "kind": "official", "category": "transport"},
    {"name": "STCP", "url": "https://www.stcp.pt/pt/noticias/", "rss": "", "kind": "official", "category": "transport"},
    {"name": "Metro do Porto", "url": "https://www.metrodoporto.pt", "rss": "", "kind": "official", "category": "transport"},
    {"name": "TAP", "url": "https://www.flytap.com/pt-pt/ultimas-noticias", "rss": "", "kind": "official", "category": "travel"},
    {"name": "Your Europe", "url": "https://europa.eu/youreurope/citizens/index_pt.htm", "rss": "", "kind": "official", "category": "eu_rights"},
    {"name": "Lusa", "url": "https://www.lusa.pt", "rss": "https://www.lusa.pt/rss", "kind": "media", "category": "news"},
    {"name": "Público", "url": "https://www.publico.pt", "rss": "https://feeds.feedburner.com/PublicoRSS", "kind": "media", "category": "news"},
    {"name": "Expresso", "url": "https://expresso.pt", "rss": "https://expresso.pt/rss", "kind": "media", "category": "news"},
    {"name": "Observador", "url": "https://observador.pt", "rss": "https://observador.pt/feed/", "kind": "media", "category": "news"},
    {"name": "RTP", "url": "https://www.rtp.pt/noticias", "rss": "https://www.rtp.pt/noticias/rss", "kind": "media", "category": "news"},
    {"name": "ECO", "url": "https://eco.sapo.pt", "rss": "https://eco.sapo.pt/feed/", "kind": "media", "category": "economy"},
    {"name": "Negócios", "url": "https://www.jornaldenegocios.pt", "rss": "https://www.jornaldenegocios.pt/rss", "kind": "media", "category": "economy"},
    {"name": "The Portugal News", "url": "https://www.theportugalnews.com", "rss": "https://www.theportugalnews.com/rss", "kind": "media", "category": "expats"},
    {"name": "Idealista", "url": "https://www.idealista.pt/news", "rss": "https://www.idealista.pt/news/rss", "kind": "media", "category": "housing"},
]

KEYWORDS = ["AIMA", "SEF", "imigração", "imigrantes", "residência", "visto", "nacionalidade", "cidadania", "IRS", "IVA", "NIF", "Segurança Social", "greve", "transportes", "SNS"]

SKIP_PATTERNS = ["privacidade", "cookies", "facebook", "instagram", "twitter", "newsletter", "contactos"]

def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=2)

def is_junk(title):
    t = title.lower()
    return any(p in t for p in SKIP_PATTERNS)

def is_relevant(text):
    t = text.lower()
    return any(k.lower() in t for k in KEYWORDS)

def get_source_items(source):
    items = []
    try:
        if source.get("rss"):
            feed = feedparser.parse(source["rss"])
            for e in feed.entries[:MAX_ITEMS_PER_SOURCE]:
                items.append({"title": e.title, "link": e.link, "summary": e.get("summary", "")})
        else:
            r = requests.get(source["url"], headers={"User-Agent": "Mozilla/5.0"}, timeout=20, verify=False)
            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup.find_all("a", href=True):
                title = tag.get_text(" ", strip=True)
                href = urljoin(source["url"], tag["href"])
                if len(title) > 25 and not is_junk(title):
                    items.append({"title": title, "link": href, "summary": ""})
                if len(items) >= MAX_ITEMS_PER_SOURCE: break
    except: pass
    return items

def call_gemini(prompt):
    models = ["models/gemini-2.0-flash", "models/gemini-1.5-flash"]
    for m in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/{m}:generateContent?key={GEMINI_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2}}
        try:
            r = requests.post(url, json=payload, timeout=40)
            if r.status_code == 200:
                return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except: continue
    return None

def build_msg(title, body, source_name, link):
    prompt = f"تو سردبیر خبر هستی. این خبر را برای ایرانیان پرتغال خلاصه کن. قوانین: ۱. بدون ستاره و ایموجی. ۲. حداکثر ۳ جمله خلاصه. ۳. ۴ نکته با علامت ●. ۴. ۳ هشتگ. ۵. عنوان بولد. منبع: {source_name}. خبر: {title} - {body[:2000]}"
    res = call_gemini(prompt)
    if not res: return None
    
    # تمیزکاری متن از ستاره‌های احتمالی
    res = res.replace("**", "").replace("*", "").replace("#", "")
    
    # جدا کردن بخش‌ها (ساده شده)
    lines = res.strip().split("\n")
    clean_title = lines[0].replace("TITLE:", "").strip()
    
    return f"<b>{clean_title}</b>\n\n{res}\n\n<b>منبع:</b> {source_name}\n{link}\n\n<b>گروه زندگی در پرتغال را با دیگران به اشتراک بگذارید:</b>\n{TG_GROUP_LINK}"

def main():
    seen = load_seen()
    posted = 0
    for source in SOURCES:
        if posted >= MAX_PER_RUN: break
        items = get_source_items(source)
        for item in items:
            if posted >= MAX_PER_RUN: break
            if item["link"] in seen: continue
            if not is_relevant(item["title"]):
                seen[item["link"]] = True
                continue
            
            full_text = trafilatura.extract(requests.get(item["link"], verify=False).text) or item["title"]
            msg = build_msg(item["title"], full_text, source["name"], item["link"])
            
            if msg:
                requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json={"chat_id": TG_CHANNEL, "text": msg, "parse_mode": "HTML"})
                posted += 1
                seen[item["link"]] = True
                time.sleep(3)
    save_seen(seen)

if __name__ == "__main__":
    main()
