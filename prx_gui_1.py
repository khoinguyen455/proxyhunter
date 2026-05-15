import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, colorchooser
import requests
import socket
import time
import statistics
import re
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import queue
import os
from datetime import datetime
from pathlib import Path
import sys
try:
    from PIL import Image, ImageTk, ImageFilter
    PIL_OK = True
except ImportError:
    PIL_OK = False

# ── Config ───────────────────────────────────────────────────────────────────
TIMEOUT     = 6
MAX_WORKERS = 100

SSL_JUDGES = [
    "https://ssl-judge1.api.proxyscrape.com/",
    "https://ssl-judge2.api.proxyscrape.com/",
]
HTTP_JUDGES = [
    "http://judge1.api.proxyscrape.com/",
    "http://judge2.api.proxyscrape.com/",
    "http://judge4.api.proxyscrape.com/",
    "http://judge5.api.proxyscrape.com/",
]
GOOGLE_TEST = "https://www.google.com/generate_204"
CF_TEST     = "https://www.cloudflare.com/cdn-cgi/trace"
ASN_CHECK   = "http://ip-api.com/json/{}?fields=16983568"

# ── Proxy sources ─────────────────────────────────────────────────────────────
def _src(url, t="http", p="plain"):
    return {"url": url, "type": t, "parse": p}

PROXY_SOURCES = {
    # ── ProxyScrape API
    "ProxyScrape HTTP v4":      _src("https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&protocol=http&anonymity=all&country=all&ssl=all&speed=all&limit=2000"),
    "ProxyScrape HTTP v1":      _src("https://api.proxyscrape.com/?request=displayproxies&proxytype=http"),
    "ProxyScrape HTTPS v1":     _src("https://api.proxyscrape.com/?request=displayproxies&proxytype=https", "https"),
    "ProxyScrape SOCKS4":       _src("https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&protocol=socks4&country=all&speed=all&limit=2000", "socks4"),
    "ProxyScrape SOCKS5":       _src("https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&protocol=socks5&country=all&speed=all&limit=2000", "socks5"),
    # ── GeoNode
    "GeoNode HTTP":             _src("https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols=http", "http", "geonode"),
    "GeoNode HTTPS":            _src("https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols=https", "https", "geonode"),
    "GeoNode SOCKS5":           _src("https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols=socks5", "socks5", "geonode"),
    "GeoNode All":              _src("https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc", "http", "geonode"),
    # ── ProxyList.to
    "ProxyList.to HTTP":        _src("https://www.proxy-list.download/api/v1/get?type=http"),
    "ProxyList.to HTTPS":       _src("https://www.proxy-list.download/api/v1/get?type=https", "https"),
    "ProxyList.to SOCKS4":      _src("https://www.proxy-list.download/api/v1/get?type=socks4", "socks4"),
    "ProxyList.to SOCKS5":      _src("https://www.proxy-list.download/api/v1/get?type=socks5", "socks5"),
    # ── ProxyShare
    "ProxyShare All":           _src("https://www.proxyshare.com/web_v1/free-proxy/list?country_code=&port=&protocol=&anonymity=&speed=&google_passed=&uptime=&asn=&page=1&page_size=99999&sort_by=lastChecked&sort_type=desc", "http", "geonode"),
    # ── ProxyScan.io
    "ProxyScan HTTP":           _src("https://www.proxyscan.io/download?type=http"),
    "ProxyScan SOCKS4":         _src("https://www.proxyscan.io/download?type=socks4", "socks4"),
    "ProxyScan SOCKS5":         _src("https://www.proxyscan.io/download?type=socks5", "socks5"),
    # ── ProxySpace
    "ProxySpace HTTP":          _src("https://proxyspace.pro/http.txt"),
    "ProxySpace HTTPS":         _src("https://proxyspace.pro/https.txt", "https"),
    "ProxySpace SOCKS4":        _src("https://proxyspace.pro/socks4.txt", "socks4"),
    "ProxySpace SOCKS5":        _src("https://proxyspace.pro/socks5.txt", "socks5"),
    # ── OpenProxyList
    "OpenProxyList HTTP":       _src("https://api.openproxylist.xyz/http.txt"),
    "OpenProxyList HTTP2":      _src("https://openproxylist.xyz/http.txt"),
    # ── OpenProxySpace
    "OpenProxySpace HTTP":      _src("https://openproxyspace.com/data/http"),
    "OpenProxySpace SOCKS5":    _src("https://openproxyspace.com/data/socks5", "socks5"),
    # ── Proxifly (jsDelivr CDN + raw)
    "Proxifly All CDN":         _src("https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/all/data.txt"),
    "Proxifly HTTP":            _src("https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt"),
    "Proxifly HTTP2":           _src("https://raw.githubusercontent.com/proxifly/free-proxy-list/refs/heads/main/proxies/protocols/http/data.txt"),
    "Proxifly HTTPS":           _src("https://raw.githubusercontent.com/proxifly/free-proxy-list/refs/heads/main/proxies/protocols/https/data.txt", "https"),
    # ── TheSpeedX
    "TheSpeedX HTTP":           _src("https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"),
    "TheSpeedX HTTP2":          _src("https://raw.githubusercontent.com/TheSpeedX/PROXY-List/refs/heads/master/http.txt"),
    "TheSpeedX SOCKS HTTP":     _src("https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt"),
    "TheSpeedX SOCKS4":         _src("https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks4.txt", "socks4"),
    "TheSpeedX SOCKS5":         _src("https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt", "socks5"),
    # ── Monosans
    "Monosans HTTP":            _src("https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"),
    "Monosans HTTP Ref":        _src("https://raw.githubusercontent.com/monosans/proxy-list/refs/heads/main/proxies/http.txt"),
    "Monosans HTTP Anon":       _src("https://raw.githubusercontent.com/monosans/proxy-list/main/proxies_anonymous/http.txt"),
    "Monosans HTTP Anon2":      _src("https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies_anonymous/http.txt"),
    # ── Jetkai
    "Jetkai HTTP":              _src("https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt"),
    "Jetkai HTTPS":             _src("https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-https.txt", "https"),
    # ── Roosterkid
    "Roosterkid HTTPS":         _src("https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt", "https"),
    "Roosterkid SOCKS5":        _src("https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt", "socks5"),
    # ── mmpx12
    "mmpx12 HTTP":              _src("https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt"),
    "mmpx12 HTTP Ref":          _src("https://raw.githubusercontent.com/mmpx12/proxy-list/refs/heads/master/http.txt"),
    "mmpx12 HTTPS":             _src("https://raw.githubusercontent.com/mmpx12/proxy-list/master/https.txt", "https"),
    "mmpx12 HTTPS Ref":         _src("https://raw.githubusercontent.com/mmpx12/proxy-list/refs/heads/master/https.txt", "https"),
    # ── ShiftyTR
    "ShiftyTR HTTP":            _src("https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt"),
    "ShiftyTR HTTPS":           _src("https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/https.txt", "https"),
    "ShiftyTR Proxy":           _src("https://raw.githubusercontent.com/shiftytr/proxy-list/master/proxy.txt"),
    # ── Sunny9577
    "Sunny9577 Raw":            _src("https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt"),
    "Sunny9577 Gen HTTP":       _src("https://sunny9577.github.io/proxy-scraper/generated/http_proxies.txt"),
    "Sunny9577 All":            _src("https://sunny9577.github.io/proxy-scraper/proxies.txt"),
    # ── ErcinDedeoglu
    "ErcinDedeoglu HTTP":       _src("https://raw.githubusercontent.com/ErcinDedeoglu/proxies/refs/heads/main/proxies/http.txt"),
    "ErcinDedeoglu HTTPS":      _src("https://raw.githubusercontent.com/ErcinDedeoglu/proxies/refs/heads/main/proxies/https.txt", "https"),
    "ErcinDedeoglu HTTP2":      _src("https://raw.githubusercontent.com/ErcinDedeoglu/proxies/main/proxies/http.txt"),
    "ErcinDedeoglu HTTPS2":     _src("https://raw.githubusercontent.com/ErcinDedeoglu/proxies/main/proxies/https.txt", "https"),
    # ── TuanMinPay
    "TuanMinPay HTTP":          _src("https://raw.githubusercontent.com/TuanMinPay/live-proxy/refs/heads/master/http.txt"),
    "TuanMinPay All":           _src("https://raw.githubusercontent.com/TuanMinPay/live-proxy/refs/heads/master/all.txt"),
    "TuanMinPay SOCKS4":        _src("https://raw.githubusercontent.com/TuanMinPay/live-proxy/refs/heads/master/socks4.txt", "socks4"),
    # ── Zaeem20
    "Zaeem20 HTTP":             _src("https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/refs/heads/master/http.txt"),
    "Zaeem20 HTTPS":            _src("https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/refs/heads/master/https.txt", "https"),
    # ── Vann-Dev
    "Vann-Dev HTTP":            _src("https://raw.githubusercontent.com/Vann-Dev/proxy-list/refs/heads/main/proxies/http.txt"),
    "Vann-Dev HTTPS":           _src("https://raw.githubusercontent.com/Vann-Dev/proxy-list/refs/heads/main/proxies/https.txt", "https"),
    # ── Skiddle-ID
    "Skiddle HTTP":             _src("https://raw.githubusercontent.com/Skiddle-ID/proxylist/refs/heads/main/generated/http_proxies.txt"),
    "Skiddle SOCKS4":           _src("https://raw.githubusercontent.com/Skiddle-ID/proxylist/refs/heads/main/generated/socks4_proxies.txt", "socks4"),
    # ── Clarketm
    "Clarketm HTTP":            _src("https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt"),
    # ── Almroot
    "Almroot HTTP":             _src("https://raw.githubusercontent.com/almroot/proxylist/master/list.txt"),
    # ── opsxcq
    "opsxcq HTTP":              _src("https://raw.githubusercontent.com/opsxcq/proxy-list/master/list.txt"),
    # ── Hookzof
    "Hookzof SOCKS5":           _src("https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt", "socks5"),
    # ── ALIILAPRO
    "ALIILAPRO HTTP":           _src("https://raw.githubusercontent.com/ALIILAPRO/Proxy/main/http.txt"),
    # ── B4RC0DE-TM
    "B4RC0DE HTTP":             _src("https://raw.githubusercontent.com/B4RC0DE-TM/proxy-list/main/HTTP.txt"),
    # ── aslisk
    "aslisk HTTPS":             _src("https://raw.githubusercontent.com/aslisk/proxyhttps/main/https.txt", "https"),
    # ── r00tee
    "r00tee HTTPS":             _src("https://raw.githubusercontent.com/r00tee/Proxy-List/main/Https.txt", "https"),
    # ── MuRongPIG
    "MuRongPIG HTTP":           _src("https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/http.txt"),
    # ── dpangestuw
    "dpangestuw HTTP":          _src("https://raw.githubusercontent.com/dpangestuw/Free-Proxy/refs/heads/main/http_proxies.txt"),
    "dpangestuw All":           _src("https://raw.githubusercontent.com/dpangestuw/Free-Proxy/refs/heads/main/allive.txt"),
    # ── vakhov
    "vakhov HTTP":              _src("https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/http.txt"),
    "vakhov HTTP (pages)":      _src("https://vakhov.github.io/fresh-proxy-list/http.txt"),
    "vakhov HTTPS":             _src("https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/https.txt", "https"),
    # ── zevtyardt
    "zevtyardt HTTP":           _src("https://raw.githubusercontent.com/zevtyardt/proxy-list/main/http.txt"),
    # ── proxy4parsing
    "proxy4parsing HTTP":       _src("https://raw.githubusercontent.com/proxy4parsing/proxy-list/main/http.txt"),
    # ── saisuiu / Lionkings
    "saisuiu Free":             _src("https://raw.githubusercontent.com/saisuiu/uiu/main/free.txt"),
    "Lionkings Free":           _src("https://raw.githubusercontent.com/saisuiu/Lionkings-Http-Proxys-Proxies/main/free.txt"),
    "Lionkings CN Free":        _src("https://raw.githubusercontent.com/saisuiu/Lionkings-Http-Proxys-Proxies/main/cnfree.txt"),
    # ── officialputuid / KangProxy
    "KangProxy All":            _src("https://raw.githubusercontent.com/officialputuid/KangProxy/KangProxy/xResults/Proxies.txt"),
    # ── BreakingTechFr
    "BreakingTech HTTP":        _src("https://raw.githubusercontent.com/BreakingTechFr/Proxy_Free/main/proxies/http.txt"),
    # ── Spys.me
    "Spys.me":                  _src("https://spys.me/proxy.txt"),
    # ── Proxy-Spider
    "Proxy-Spider":             _src("https://proxy-spider.com/api/proxies.example.txt"),
    # ── Rootjazz
    "Rootjazz HTTP":            _src("http://rootjazz.com/proxies/proxies.txt"),
    # ── Firet.io
    "Firet.io HTTP":            _src("https://firet.io/firetx_retro/datacanthiet/proxies.txt"),
}

# Tập hợp tên source mặc định — phân biệt với custom source khi save
_DEFAULT_SOURCE_NAMES = frozenset(PROXY_SOURCES.keys())

# ── Palette ───────────────────────────────────────────────────────────────────
BG      = "#0a0e14"
BG2     = "#0d1117"
PANEL   = "#111820"
BORDER  = "#1e2d3d"
ACCENT  = "#00d4ff"
ACCENT2 = "#00ff88"
WARN    = "#ff6b35"
DEAD    = "#ff3355"
TEXT    = "#c9d1d9"
MUTED   = "#4a5568"
GOLD    = "#ffd700"
PURPLE  = "#bd93f9"

FONT_MONO2 = ("Consolas", 9)
FONT_HEAD  = ("Consolas", 18, "bold")
FONT_SMALL = ("Consolas", 8)

IP_PORT_RE = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3}):(\d{2,5})\b")

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

SETTINGS_FILE = BASE_DIR / "configs" / "proxy_hunter_settings.json"

# ── Light theme palette ───────────────────────────────────────────────────────
LIGHT = {
    "BG":"#f0f2f5","BG2":"#e4e8ef","PANEL":"#ffffff","BORDER":"#c8d0dc",
    "ACCENT":"#0077cc","ACCENT2":"#00aa55","WARN":"#e06030","DEAD":"#cc2244",
    "TEXT":"#1a1f2e","MUTED":"#7a8599","GOLD":"#cc9900","PURPLE":"#7030b8",
}
DARK = {
    "BG":"#0a0e14","BG2":"#0d1117","PANEL":"#111820","BORDER":"#1e2d3d",
    "ACCENT":"#00d4ff","ACCENT2":"#00ff88","WARN":"#ff6b35","DEAD":"#ff3355",
    "TEXT":"#c9d1d9","MUTED":"#4a5568","GOLD":"#ffd700","PURPLE":"#bd93f9",
}
# CUSTOM palette – values filled from settings at runtime
CUSTOM_PALETTE = {
    "BG":"#0a0e14","BG2":"#0d1117","PANEL":"#111820","BORDER":"#1e2d3d",
    "ACCENT":"#00d4ff","ACCENT2":"#00ff88","WARN":"#ff6b35","DEAD":"#ff3355",
    "TEXT":"#c9d1d9","MUTED":"#4a5568","GOLD":"#ffd700","PURPLE":"#bd93f9",
}

# ── i18n strings ──────────────────────────────────────────────────────────────
I18N = {
    "EN": {
        "tab_scraper":"  ⛏  SCRAPER  ","tab_checker":"  ✔  CHECKER  ",
        "tab_recheck":"  ↺  RE-CHECK  ","tab_settings":"  ⚙  SETTINGS  ",
        "set_theme":"THEME","set_dark":"Dark","set_light":"Light",
        "set_lang":"LANGUAGE","set_judges":"PROXY JUDGES",
        "set_ssl_judges":"SSL JUDGES","set_http_judges":"HTTP JUDGES",
        "set_add_url":"Add URL…","set_add":"ADD","set_del":"DEL",
        "set_save":"SAVE SETTINGS","set_saved":"Settings saved!",
        "set_restart":"(restart to fully apply theme)",
        "set_test":"TEST","set_testing":"Testing…","set_ok":"OK","set_fail":"FAIL",
    },
    "VIE": {
        "tab_scraper":"  ⛏  SCRAPER  ","tab_checker":"  ✔  CHECKER  ",
        "tab_recheck":"  ↺  RE-CHECK  ","tab_settings":"  ⚙  CÀI ĐẶT  ",
        "set_theme":"GIAO DIỆN","set_dark":"Tối","set_light":"Sáng",
        "set_lang":"NGÔN NGỮ","set_judges":"PROXY JUDGES",
        "set_ssl_judges":"SSL JUDGES","set_http_judges":"HTTP JUDGES",
        "set_add_url":"Thêm URL…","set_add":"THÊM","set_del":"XÓA",
        "set_save":"LƯU CÀI ĐẶT","set_saved":"Đã lưu cài đặt!",
        "set_restart":"(khởi động lại để áp dụng giao diện)",
        "set_test":"THỬ","set_testing":"Đang thử…","set_ok":"OK","set_fail":"LỖI",
    },
}

def parse_plain(text):
    return [f"{m.group(1)}:{m.group(2)}" for m in IP_PORT_RE.finditer(text)]

def parse_geonode(text):
    try:
        data = json.loads(text)
        return [f"{i['ip']}:{i['port']}" for i in data.get("data",[]) if i.get("ip") and i.get("port")]
    except:
        return parse_plain(text)

def scrape_source(name, info):
    try:
        r = requests.get(info["url"], timeout=15, headers={"User-Agent":"Mozilla/5.0"})
        r.raise_for_status()
        proxies = parse_geonode(r.text) if info["parse"]=="geonode" else parse_plain(r.text)
        return name, info["type"], proxies, None
    except Exception as e:
        return name, info["type"], [], str(e)

def socket_check(proxy):
    try:
        host, port = proxy.split(":")
        s = socket.socket(); s.settimeout(2)
        s.connect((host, int(port))); s.close()
        return True
    except:
        return False

def request_proxy(url, proxy):
    proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
    try:
        start = time.time()
        r = requests.get(url, proxies=proxies, timeout=TIMEOUT)
        return r, (time.time()-start)*1000
    except:
        return None, None

def detect_type(text):
    if "X-Forwarded-For" in text or "Via" in text: return "ANONYMOUS"
    if "REMOTE_ADDR" in text: return "TRANSPARENT"
    return "ELITE"

def detect_network(ip):
    try:
        r = requests.get(ASN_CHECK.format(ip), timeout=5).json()
        org = r.get("org","").lower()
        if r.get("proxy") or r.get("hosting"):
            return "DATACENTER", r.get("isp","UNKNOWN")
        if any(x in org for x in ["amazon","google","ovh","digitalocean","microsoft","vultr"]):
            return "DATACENTER", r.get("isp","UNKNOWN")
        return "RESIDENTIAL", r.get("isp","UNKNOWN")
    except:
        return "UNKNOWN","UNKNOWN"

def calculate_score(proxy_type, network, google_ok, cf_ok, latency):
    s = 10
    s += {"ELITE":30,"ANONYMOUS":20,"TRANSPARENT":5}.get(proxy_type,0)
    s += {"RESIDENTIAL":25,"DATACENTER":10}.get(network,0)
    if google_ok: s+=10
    if cf_ok:     s+=10
    if latency<300: s+=15
    elif latency<600: s+=10
    elif latency<1000: s+=5
    return s

def check_proxy(proxy):
    res = {"proxy":proxy,"status":"DEAD"}
    if not socket_check(proxy): return res
    latencies, judge_used, proxy_type = [], None, "UNKNOWN"
    for judge in SSL_JUDGES:
        r,lat = request_proxy(judge, proxy)
        if r and r.status_code==200:
            judge_used,proxy_type=judge,detect_type(r.text); latencies.append(lat); break
    if not judge_used:
        for judge in HTTP_JUDGES:
            r,lat = request_proxy(judge, proxy)
            if r and r.status_code==200:
                judge_used,proxy_type=judge,detect_type(r.text); latencies.append(lat); break
    if not judge_used: return res
    google_ok=False; r,lat=request_proxy(GOOGLE_TEST,proxy)
    if r and r.status_code==204: google_ok=True; latencies.append(lat)
    cf_ok=False; r,lat=request_proxy(CF_TEST,proxy)
    if r and "fl=" in r.text: cf_ok=True; latencies.append(lat)
    avg_lat=int(statistics.mean(latencies)) if latencies else 0
    ip=proxy.split(":")[0]
    nt,isp=detect_network(ip)
    score=calculate_score(proxy_type,nt,google_ok,cf_ok,avg_lat)
    res.update({"status":"LIVE","type":proxy_type,"network":nt,
                "google":google_ok,"cloudflare":cf_ok,"judge":judge_used,
                "avg_latency":avg_lat,"isp":isp,"score":score})
    return res

# ═════════════════════════════════════════════════════════════════════════════
class ProxyHunterApp:
    def __init__(self, root):
        self.root     = root
        self.root.title("PROXY HUNTER // BY KHÔI NGUYÊN (KHOITOOL) - 2026 EDITION (v1.0)")
        self.root.geometry("1300x860")
        self.root.minsize(1000,700)
        self.root.configure(bg=BG)

        self.q         = queue.Queue()
        self.scrape_q  = queue.Queue()
        self.recheck_q = queue.Queue()
        self.running   = False
        self.scraping  = False
        self.rechecking= False
        self.proxies   = []
        self.scraped   = {}
        self.stats     = {"total":0,"live":0,"dead":0,"elite":0,"anon":0,"trans":0,"dc":0,"res":0}
        self.results   = []
        self.save_lock = threading.Lock()
        self._source_sel = {}
        self._src_iids   = {}

        self._settings = self._load_settings()
        self._load_custom_palette_from_settings()
        self._apply_palette(self._settings.get("theme","dark"))
        self._style_setup()
        self._build_ui()
        self._poll_queue()
        self._poll_scrape_queue()
        self._poll_recheck_queue()

    # ── Settings persistence ──────────────────────────────────────────────────
    def _load_settings(self):
        defaults = {
            "theme": "dark", "lang": "EN",
            "ssl_judges": list(SSL_JUDGES),
            "http_judges": list(HTTP_JUDGES),
            "ssl_enabled": {u: True for u in SSL_JUDGES},
            "http_enabled": {u: True for u in HTTP_JUDGES},
            "custom_palette": dict(CUSTOM_PALETTE),
            "custom_sources": [],
            "deleted_sources": [],
        }
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                s = json.load(f)
            for k, v in defaults.items():
                if k not in s:
                    s[k] = v
            # Xóa các source mặc định đã bị user xóa
            for name in s.get("deleted_sources", []):
                PROXY_SOURCES.pop(name, None)
            # Nạp custom sources đã lưu
            for cs in s.get("custom_sources", []):
                n, u, p = cs.get("name",""), cs.get("url",""), cs.get("proto","http")
                if n and u and n not in PROXY_SOURCES:
                    PROXY_SOURCES[n] = _src(u, p)
            return s
        except Exception:
            return defaults

    def _save_settings(self):
        s = self._settings
        # pull current state from settings tab widgets
        s["theme"]        = self._set_theme_var.get()
        s["lang"]         = self._set_lang_var.get()
        s["ssl_judges"]   = list(self._ssl_judges)
        s["http_judges"]  = list(self._http_judges)
        s["ssl_enabled"]  = {u: v.get() for u, v in self._ssl_chk_vars.items()}
        s["http_enabled"] = {u: v.get() for u, v in self._http_chk_vars.items()}
        # custom palette + bg
        s["custom_palette"] = dict(CUSTOM_PALETTE)
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(s, f, indent=2, ensure_ascii=False)
        except Exception as e:
            pass
        # apply active judges to global lists
        global SSL_JUDGES, HTTP_JUDGES
        SSL_JUDGES  = [u for u in self._ssl_judges  if self._ssl_chk_vars.get(u,  tk.BooleanVar(value=True)).get()]
        HTTP_JUDGES = [u for u in self._http_judges if self._http_chk_vars.get(u, tk.BooleanVar(value=True)).get()]
        # apply theme + background
        self._apply_palette(s["theme"])
        self._set_save_label.config(text=I18N[s["lang"]]["set_saved"], fg=ACCENT2)
        self.root.after(2000, lambda: self._set_save_label.config(text=I18N[s["lang"]]["set_restart"], fg=MUTED))

    def _apply_palette(self, theme):
        global BG,BG2,PANEL,BORDER,ACCENT,ACCENT2,WARN,DEAD,TEXT,MUTED,GOLD,PURPLE
        if theme == "custom":
            p = CUSTOM_PALETTE
        else:
            p = DARK if theme == "dark" else LIGHT
        BG=p["BG"]; BG2=p["BG2"]; PANEL=p["PANEL"]; BORDER=p["BORDER"]
        ACCENT=p["ACCENT"]; ACCENT2=p["ACCENT2"]; WARN=p["WARN"]; DEAD=p["DEAD"]
        TEXT=p["TEXT"]; MUTED=p["MUTED"]; GOLD=p["GOLD"]; PURPLE=p["PURPLE"]

    def _apply_bg_image(self):
        pass  # background image removed


    def _load_custom_palette_from_settings(self):
        """Sync CUSTOM_PALETTE global from stored settings."""
        saved = self._settings.get("custom_palette", {})
        for k in CUSTOM_PALETTE:
            if k in saved:
                CUSTOM_PALETTE[k] = saved[k]

    # ── Style ─────────────────────────────────────────────────────────────────
    def _style_setup(self):
        s = ttk.Style(); s.theme_use("clam")
        s.configure("Cyber.Horizontal.TProgressbar",
                    troughcolor=BG2,background=ACCENT,lightcolor=ACCENT,
                    darkcolor=ACCENT,bordercolor=BORDER,thickness=8)
        for name,fg in [("Cyber",ACCENT),("Src",PURPLE)]:
            s.configure(f"{name}.Treeview",background=PANEL,foreground=TEXT,
                        rowheight=22,fieldbackground=PANEL,bordercolor=BORDER,
                        borderwidth=0,font=FONT_MONO2)
            s.configure(f"{name}.Treeview.Heading",background=BG2,foreground=fg,
                        bordercolor=BORDER,relief="flat",font=("Consolas",9,"bold"))
            s.map(f"{name}.Treeview",
                  background=[("selected","#1a2744")],foreground=[("selected",fg)])
        s.configure("Tab.TNotebook",background=BG,borderwidth=0)
        s.configure("Tab.TNotebook.Tab",background=PANEL,foreground=MUTED,
                    font=("Consolas",10,"bold"),padding=[16,6],borderwidth=0)
        s.map("Tab.TNotebook.Tab",background=[("selected",BG2)],foreground=[("selected",ACCENT)])

    # ── Top bar ───────────────────────────────────────────────────────────────
    def _build_ui(self):

        self.main_container = tk.Frame(self.root, bg=BG)
        self.main_container.pack(fill="both", expand=True)

        top = tk.Frame(self.main_container, bg=BG, height=56)
        top.pack(fill="x")
        top.pack_propagate(False)

        tk.Label(top,text="◈ PROXY HUNTER", font=FONT_HEAD, bg=BG, fg=ACCENT).pack(side="left", padx=20, pady=8)
        tk.Label(top,text="// SCRAPE + CHECK v1.0 BY KHÔI NGUYÊN (KHOITOOL)",font=FONT_MONO2,bg=BG,fg=MUTED).pack(side="left", pady=14)
        self.ts_label = tk.Label(top, text="", font=FONT_SMALL, bg=BG, fg=MUTED)
        self.ts_label.pack(side="right", padx=20)
        self._update_clock() 
        self.global_status = tk.Label(top, text="● IDLE", font=("Consolas",10,"bold"), bg=BG, fg=MUTED)
        self.global_status.pack(side="right", padx=12)
        tk.Frame(self.main_container, bg=BORDER, height=1).pack(fill="x")
        nb = ttk.Notebook(self.main_container, style="Tab.TNotebook")
        nb.pack(fill="both", expand=True, padx=10, pady=6)

        self.tab_scraper = tk.Frame(nb, bg=BG)
        self.tab_checker = tk.Frame(nb, bg=BG)
        self.tab_recheck = tk.Frame(nb, bg=BG)
        self.tab_settings = tk.Frame(nb, bg=BG)

        nb.add(self.tab_scraper, text="  ⛏  SCRAPER  ")
        nb.add(self.tab_checker, text="  ✔  CHECKER  ")
        nb.add(self.tab_recheck, text="  ↺  RE-CHECK  ")
        nb.add(self.tab_settings, text="  ⚙  SETTINGS  ")

        self._nb = nb

        self._build_scraper_tab()
        self._build_checker_tab()
        self._build_recheck_tab()
        self._build_settings_tab()

    # ══════════════════════════════════════════════════════════════════════════
    # SCRAPER TAB
    # ══════════════════════════════════════════════════════════════════════════
    def _build_scraper_tab(self):
        p = self.tab_scraper

        ctrl = tk.Frame(p,bg=BG); ctrl.pack(fill="x",padx=8,pady=(8,4))
        self._btn(ctrl,"⛏  SCRAPE ALL",   self._scrape_all,      PURPLE, big=True).pack(side="left",padx=(0,5))
        self._btn(ctrl,"⛏  SCRAPE SEL",   self._scrape_selected, ACCENT, big=True).pack(side="left",padx=(0,5))
        self._btn(ctrl,"■  STOP",          self._stop_scrape,     DEAD,   big=True).pack(side="left",padx=(0,5))
        self._btn(ctrl,"→  SEND TO CHECK", self._send_to_checker, ACCENT2,big=True).pack(side="left",padx=(0,5))
        self._btn(ctrl,"⬇  EXPORT RAW",    self._export_scraped,  MUTED,  big=True).pack(side="left")
        self.scrape_prog_label = tk.Label(ctrl,text="",font=FONT_MONO2,bg=BG,fg=MUTED)
        self.scrape_prog_label.pack(side="right",padx=8)

        self.scrape_prog_var = tk.DoubleVar(value=0)
        ttk.Progressbar(p,variable=self.scrape_prog_var,maximum=100,
                        style="Cyber.Horizontal.TProgressbar").pack(fill="x",padx=8,pady=(0,4))

        main = tk.Frame(p,bg=BG); main.pack(fill="both",expand=True,padx=8)
        self._section(main,"SOURCES  —  click ☑ column to toggle")

        # Filter row
        frow = tk.Frame(main,bg=BG); frow.pack(fill="x",pady=(0,4))
        tk.Label(frow,text="Filter:",font=FONT_MONO2,bg=BG,fg=MUTED).pack(side="left")
        for lbl,proto in [("ALL","all"),("HTTP","http"),("HTTPS","https"),
                           ("SOCKS4","socks4"),("SOCKS5","socks5")]:
            self._filter_btn(frow,lbl,proto).pack(side="left",padx=2)
        tk.Label(frow,text=" | ",font=FONT_MONO2,bg=BG,fg=MUTED).pack(side="left")
        self._btn(frow,"SEL ALL",  lambda:self._select_sources("all"),  MUTED).pack(side="left",padx=2)
        self._btn(frow,"DESEL ALL",lambda:self._select_sources("none"), MUTED).pack(side="left",padx=2)
        self.scraped_total_label = tk.Label(frow,text="Scraped: 0",font=FONT_MONO2,bg=BG,fg=ACCENT2)
        self.scraped_total_label.pack(side="right")

        # ── ADD CUSTOM URL section ───────────────────────────────────────────
        self._section(main,"ADD CUSTOM SOURCE")
        add_card = tk.Frame(main, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        add_card.pack(fill="x", pady=(0,6))
        add_inner = tk.Frame(add_card, bg=PANEL); add_inner.pack(fill="x", padx=10, pady=8)

        # Row 1: Name + Protocol
        r1 = tk.Frame(add_inner, bg=PANEL); r1.pack(fill="x", pady=(0,5))
        tk.Label(r1, text="Source name:", font=FONT_MONO2, bg=PANEL, fg=TEXT, width=14, anchor="w").pack(side="left")
        self._custom_name_var = tk.StringVar(value="My Source")
        tk.Entry(r1, textvariable=self._custom_name_var, font=FONT_MONO2,
                 bg=BG2, fg=TEXT, insertbackground=ACCENT, relief="flat",
                 highlightbackground=BORDER, highlightthickness=1, width=28).pack(side="left", padx=(0,12))

        tk.Label(r1, text="Protocol:", font=FONT_MONO2, bg=PANEL, fg=TEXT).pack(side="left", padx=(0,6))
        self._custom_proto_var = tk.StringVar(value="http")
        for lbl, val in [("HTTP","http"),("HTTPS","https"),("SOCKS4","socks4"),("SOCKS5","socks5")]:
            rb = tk.Radiobutton(r1, text=lbl, variable=self._custom_proto_var, value=val,
                                font=FONT_SMALL, bg=PANEL, fg=TEXT, selectcolor=BG2,
                                activebackground=PANEL, activeforeground=ACCENT,
                                highlightthickness=0, cursor="hand2")
            rb.pack(side="left", padx=3)

        # Row 2: URL + ADD button
        r2 = tk.Frame(add_inner, bg=PANEL); r2.pack(fill="x")
        tk.Label(r2, text="URL:", font=FONT_MONO2, bg=PANEL, fg=TEXT, width=14, anchor="w").pack(side="left")
        self._custom_url_var = tk.StringVar(value="https://")
        tk.Entry(r2, textvariable=self._custom_url_var, font=FONT_MONO2,
                 bg=BG2, fg=TEXT, insertbackground=ACCENT, relief="flat",
                 highlightbackground=BORDER, highlightthickness=1).pack(side="left", fill="x", expand=True, padx=(0,8))
        self._btn(r2, "+ ADD", self._add_custom_source, ACCENT2, big=False).pack(side="left")
        self._btn(r2, "✕ DEL SEL", self._del_custom_source, DEAD, big=False).pack(side="left", padx=(4,0))

        # Source tree
        cols = ("sel","name","type","status","count","time")
        frame = tk.Frame(main,bg=BG); frame.pack(fill="both",expand=True)
        sb = tk.Scrollbar(frame,orient="vertical",bg=BG,troughcolor=BG2,activebackground=PURPLE)
        sb.pack(side="right",fill="y")
        self.src_tree = ttk.Treeview(frame,columns=cols,show="headings",
                                      style="Src.Treeview",yscrollcommand=sb.set,height=16)
        sb.config(command=self.src_tree.yview)
        for col,(lbl,w) in {"sel":("☑",30),"name":("SOURCE",230),"type":("PROTO",70),
                              "status":("STATUS",100),"count":("PROXIES",80),"time":("TIME",70)}.items():
            self.src_tree.heading(col,text=lbl)
            self.src_tree.column(col,width=w,anchor="center" if col!="name" else "w")
        self.src_tree.tag_configure("ok",     foreground=ACCENT2)
        self.src_tree.tag_configure("err",    foreground=DEAD)
        self.src_tree.tag_configure("pending",foreground=MUTED)
        self.src_tree.tag_configure("running",foreground=WARN)
        self.src_tree.bind("<Button-1>",self._toggle_source_sel)
        self.src_tree.pack(side="left",fill="both",expand=True)

        for name,info in PROXY_SOURCES.items():
            self._source_sel[name] = tk.BooleanVar(value=True)
            iid = self.src_tree.insert("","end",
                values=("☑",name,info["type"].upper(),"PENDING","—","—"),tags=("pending",))
            self._src_iids[name] = iid

        # Scrape log
        self._section(main,"SCRAPE LOG")
        self.scrape_log = scrolledtext.ScrolledText(
            main,height=6,font=FONT_MONO2,bg=BG2,fg=MUTED,
            insertbackground=ACCENT,relief="flat",
            highlightbackground=BORDER,highlightthickness=1,
            state="disabled",wrap="none")
        self.scrape_log.pack(fill="x",pady=(2,0))
        for tag,col in [("ok",ACCENT2),("err",DEAD),("info",ACCENT),("warn",WARN)]:
            self.scrape_log.tag_config(tag,foreground=col)

    def _add_custom_source(self):
        """Thêm URL custom vào PROXY_SOURCES và src_tree."""
        name  = self._custom_name_var.get().strip()
        url   = self._custom_url_var.get().strip()
        proto = self._custom_proto_var.get()

        if not name:
            self._slog("⚠ Thiếu dữ liệu: chưa nhập tên source!", "warn"); return
        if not url or url in ("https://", "http://") or not url.startswith("http"):
            self._slog("⚠ Thiếu dữ liệu: chưa nhập URL hợp lệ (phải bắt đầu bằng http/https)!", "warn"); return

        # Nếu trùng tên thì đổi suffix
        base = name
        idx = 1
        while name in PROXY_SOURCES:
            name = f"{base} ({idx})"
            idx += 1

        PROXY_SOURCES[name] = _src(url, proto)
        self._source_sel[name] = tk.BooleanVar(value=True)
        iid = self.src_tree.insert("", "end",
            values=("☑", name, proto.upper(), "PENDING", "—", "—"), tags=("pending",))
        self._src_iids[name] = iid
        self._slog(f"Đã thêm source: [{proto.upper()}] {name} → {url}", "ok")
        # Reset name gợi ý
        self._custom_name_var.set("My Source")
        self._custom_url_var.set("https://")
        # Lưu ngay để không mất khi tắt app
        self._save_custom_sources()

    def _del_custom_source(self):
        """Xóa các source đang tick ☑, phải còn ít nhất 1 source."""
        # Dùng trạng thái tick ☑/☐ thay vì tree selection (vì click bị intercept)
        checked_iids = [
            iid for iid in self.src_tree.get_children()
            if self.src_tree.item(iid, "values")[0] == "☑"
        ]
        total = len(self.src_tree.get_children())
        if not checked_iids:
            self._slog("⚠ Không có source nào được tick ☑ để xóa!", "warn"); return
        if len(checked_iids) >= total:
            self._slog("⚠ Phải giữ lại ít nhất 1 source, không thể xóa tất cả!", "warn"); return
        for iid in checked_iids:
            vals = self.src_tree.item(iid, "values")
            name = vals[1] if len(vals) > 1 else None
            if name and name in PROXY_SOURCES:
                del PROXY_SOURCES[name]
                self._source_sel.pop(name, None)
                self._src_iids.pop(name, None)
                self.src_tree.delete(iid)
                self._slog(f"Đã xóa source: {name}", "warn")
        self._save_custom_sources()

    def _save_custom_sources(self):
        """Lưu custom_sources và deleted_sources vào file settings ngay lập tức."""
        custom = [
            {"name": n, "url": info["url"], "proto": info["type"]}
            for n, info in PROXY_SOURCES.items()
            if n not in _DEFAULT_SOURCE_NAMES
        ]
        # Source mặc định đã bị xóa = tên trong _DEFAULT_SOURCE_NAMES nhưng không còn trong PROXY_SOURCES
        deleted = [n for n in _DEFAULT_SOURCE_NAMES if n not in PROXY_SOURCES]
        try:
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
            data["custom_sources"] = custom
            data["deleted_sources"] = deleted
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self._slog(f"Lỗi lưu source: {e}", "warn")

    def _filter_btn(self,parent,label,proto):
        b = tk.Button(parent,text=label,font=FONT_SMALL,
                      bg=PANEL,fg=MUTED,relief="flat",
                      highlightbackground=BORDER,highlightthickness=1,
                      padx=6,pady=2,cursor="hand2",
                      command=lambda p=proto:self._filter_sources(p))
        b.bind("<Enter>",lambda e:b.config(bg=BG2))
        b.bind("<Leave>",lambda e:b.config(bg=PANEL))
        return b

    def _filter_sources(self,proto):
        for name,info in PROXY_SOURCES.items():
            val = proto=="all" or info["type"]==proto
            self._source_sel[name].set(val)
            tick = "☑" if val else "☐"
            v = self.src_tree.item(self._src_iids[name],"values")
            self.src_tree.item(self._src_iids[name],values=(tick,)+tuple(v[1:]))

    def _select_sources(self,mode):
        for name in PROXY_SOURCES:
            val = mode=="all"
            self._source_sel[name].set(val)
            tick = "☑" if val else "☐"
            v = self.src_tree.item(self._src_iids[name],"values")
            self.src_tree.item(self._src_iids[name],values=(tick,)+tuple(v[1:]))

    def _toggle_source_sel(self,event):
        if self.src_tree.identify("region",event.x,event.y)=="cell" and \
           self.src_tree.identify_column(event.x)=="#1":
            iid = self.src_tree.identify_row(event.y)
            if not iid: return
            name = self.src_tree.item(iid,"values")[1]
            cur  = self._source_sel[name].get()
            self._source_sel[name].set(not cur)
            tick = "☐" if cur else "☑"
            v = self.src_tree.item(iid,"values")
            self.src_tree.item(iid,values=(tick,)+tuple(v[1:]))

    def _scrape_all(self):      self._do_scrape(list(PROXY_SOURCES.keys()))
    def _scrape_selected(self):
        sel = [n for n,v in self._source_sel.items() if v.get()]
        if not sel: self._slog("No sources selected!","warn"); return
        self._do_scrape(sel)

    def _do_scrape(self,names):
        if self.scraping: return
        self.scraping = True; self.scraped = {}
        self.scrape_prog_var.set(0)
        self.global_status.config(text="⛏ SCRAPING",fg=PURPLE)
        for n in names:
            iid=self._src_iids[n]; v=self.src_tree.item(iid,"values")
            self.src_tree.item(iid,values=(v[0],v[1],v[2],"RUNNING","—","—"),tags=("running",))
        self._slog(f"Scraping {len(names)} sources…","info")
        def worker():
            total=len(names); done=0
            with ThreadPoolExecutor(max_workers=20) as ex:
                futs={ex.submit(scrape_source,n,PROXY_SOURCES[n]):n for n in names}
                for fut in as_completed(futs):
                    if not self.scraping: break
                    name,ptype,proxies,err=fut.result(); done+=1
                    self.scrape_q.put(("result",name,ptype,proxies,err,done,total))
            self.scrape_q.put(("done",None,None,None,None,done,total))
        threading.Thread(target=worker,daemon=True).start()

    def _stop_scrape(self):
        self.scraping=False; self._slog("Scrape stopped","warn")

    def _send_to_checker(self):
        all_p=list(dict.fromkeys(p for lst in self.scraped.values() for p in lst))
        if not all_p: self._slog("No scraped proxies!","warn"); return
        self.paste_box.delete("1.0","end")
        self.paste_box.insert("1.0","\n".join(all_p))
        self.proxies=all_p
        self.count_label.config(text=f"{len(all_p)} proxies loaded")
        self._log(f"Received {len(all_p)} proxies from scraper","info")
        self._slog(f"Sent {len(all_p)} unique proxies → Checker","ok")

    def _export_scraped(self):
        all_p=list(dict.fromkeys(p for lst in self.scraped.values() for p in lst))
        if not all_p: self._slog("Nothing to export","warn"); return
        path=filedialog.asksaveasfilename(defaultextension=".txt",filetypes=[("Text","*.txt")])
        if path:
            with open(path,"w") as f: f.write("\n".join(all_p))
            self._slog(f"Exported {len(all_p)} → {path}","ok")

    def _slog(self,msg,tag=""):
        self.scrape_log.config(state="normal")
        self.scrape_log.insert("end",f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n",tag)
        self.scrape_log.see("end"); self.scrape_log.config(state="disabled")

    def _poll_scrape_queue(self):
        try:
            while True:
                kind,name,ptype,proxies,err,done,total=self.scrape_q.get_nowait()
                if kind=="result": self._handle_scrape_result(name,ptype,proxies,err,done,total)
                elif kind=="done": self._scrape_done(done,total)
        except queue.Empty: pass
        self.root.after(80,self._poll_scrape_queue)

    def _handle_scrape_result(self,name,ptype,proxies,err,done,total):
        pct=(done/total*100) if total else 0
        self.scrape_prog_var.set(pct)
        self.scrape_prog_label.config(text=f"{done}/{total} ({pct:.1f}%)")
        iid=self._src_iids[name]; v=self.src_tree.item(iid,"values")
        if err:
            self.src_tree.item(iid,values=(v[0],name,ptype.upper(),"ERROR","0","—"),tags=("err",))
            self._slog(f"[ERR] {name}: {err[:60]}","err")
        else:
            self.scraped[name]=proxies
            self.src_tree.item(iid,values=(v[0],name,ptype.upper(),"OK",str(len(proxies)),"—"),tags=("ok",))
            self._slog(f"[ OK] {name}: {len(proxies)} proxies","ok")
        total_raw=sum(len(v) for v in self.scraped.values())
        unique=len(set(p for lst in self.scraped.values() for p in lst))
        self.scraped_total_label.config(text=f"Scraped: {total_raw} raw | {unique} unique")

    def _scrape_done(self,done,total):
        self.scraping=False; self.scrape_prog_var.set(100)
        all_p=[p for lst in self.scraped.values() for p in lst]
        unique=len(set(all_p))
        self._slog(f"Done! {done}/{total} sources | {len(all_p)} raw | {unique} unique","ok")
        self.global_status.config(text="● IDLE",fg=MUTED)
        self.scrape_prog_label.config(text=f"DONE {done}/{total}")

    # ══════════════════════════════════════════════════════════════════════════
    # CHECKER TAB
    # ══════════════════════════════════════════════════════════════════════════
    def _build_checker_tab(self):
        p=self.tab_checker
        main=tk.Frame(p,bg=BG); main.pack(fill="both",expand=True,padx=8,pady=8)
        left=tk.Frame(main,bg=BG,width=285); left.pack(side="left",fill="y",padx=(0,8)); left.pack_propagate(False)
        self._section(left,"INPUT");     self._build_input_panel(left)
        self._section(left,"SETTINGS");  self._build_settings_panel(left)
        self._section(left,"STATISTICS");self._build_stats_panel(left)
        right=tk.Frame(main,bg=BG); right.pack(side="left",fill="both",expand=True)
        self._section(right,"SCAN RESULTS"); self._build_results_panel(right)
        self._section(right,"LIVE LOG");     self._build_log_panel(right)
        self._build_bottom_bar(p)

    def _build_input_panel(self,parent):
        inner=tk.Frame(self._card(parent),bg=PANEL); inner.pack(fill="both",padx=8,pady=8)
        frow=tk.Frame(inner,bg=PANEL); frow.pack(fill="x",pady=2)
        self.file_var=tk.StringVar(value="No file selected")
        tk.Label(frow,textvariable=self.file_var,font=FONT_MONO2,bg=PANEL,fg=MUTED,anchor="w").pack(side="left",fill="x",expand=True)
        self._btn(frow,"BROWSE",self._browse_file,ACCENT).pack(side="right")
        tk.Label(inner,text="or paste proxies (ip:port):",font=FONT_SMALL,bg=PANEL,fg=MUTED,anchor="w").pack(fill="x",pady=(6,2))
        self.paste_box=tk.Text(inner,height=7,font=FONT_MONO2,bg=BG2,fg=TEXT,insertbackground=ACCENT,
                                relief="flat",wrap="none",highlightbackground=BORDER,highlightthickness=1)
        self.paste_box.pack(fill="x")
        br=tk.Frame(inner,bg=PANEL); br.pack(fill="x",pady=(6,0))
        self._btn(br,"LOAD",self._load_proxies,ACCENT2).pack(side="left",padx=(0,4))
        self._btn(br,"CLEAR",self._clear_all,MUTED).pack(side="left")
        self.count_label=tk.Label(inner,text="0 proxies loaded",font=FONT_SMALL,bg=PANEL,fg=MUTED,anchor="w")
        self.count_label.pack(fill="x",pady=(4,0))

    def _build_settings_panel(self,parent):
        inner=tk.Frame(self._card(parent),bg=PANEL); inner.pack(fill="both",padx=8,pady=8)
        def row(lbl,var,lo,hi):
            r=tk.Frame(inner,bg=PANEL); r.pack(fill="x",pady=3)
            tk.Label(r,text=lbl,font=FONT_MONO2,bg=PANEL,fg=TEXT,width=12,anchor="w").pack(side="left")
            tk.Spinbox(r,from_=lo,to=hi,textvariable=var,width=6,font=FONT_MONO2,bg=BG2,fg=ACCENT,
                       insertbackground=ACCENT,relief="flat",highlightbackground=BORDER,
                       highlightthickness=1,buttonbackground=PANEL).pack(side="right")
        self.timeout_var=tk.IntVar(value=TIMEOUT); self.workers_var=tk.IntVar(value=MAX_WORKERS)
        row("TIMEOUT (s)",self.timeout_var,1,30); row("WORKERS",self.workers_var,1,500)
        tk.Label(inner,text="SAVE TO:",font=FONT_MONO2,bg=PANEL,fg=TEXT,anchor="w").pack(fill="x",pady=(6,2))
        self.save_dir_var=tk.StringVar(value=os.getcwd())
        dr=tk.Frame(inner,bg=PANEL); dr.pack(fill="x")
        tk.Label(dr,textvariable=self.save_dir_var,font=FONT_SMALL,bg=PANEL,fg=MUTED,anchor="w").pack(side="left",fill="x",expand=True)
        self._btn(dr,"DIR",self._browse_dir,MUTED).pack(side="right")

    def _build_stats_panel(self,parent):
        inner=tk.Frame(self._card(parent),bg=PANEL); inner.pack(fill="both",padx=8,pady=8)
        self.stat_labels={}
        for lbl,key,color in [("TOTAL","total",TEXT),("LIVE","live",ACCENT2),("DEAD","dead",DEAD),
                                ("ELITE","elite",GOLD),("ANON","anon",ACCENT),("TRANSP","trans",WARN),
                                ("DATA CTR","dc",WARN),("RESID","res",ACCENT2)]:
            r=tk.Frame(inner,bg=PANEL); r.pack(fill="x",pady=1)
            tk.Label(r,text=lbl,font=FONT_MONO2,bg=PANEL,fg=MUTED,width=10,anchor="w").pack(side="left")
            sl=tk.Label(r,text="0",font=("Consolas",10,"bold"),bg=PANEL,fg=color,anchor="e",width=6)
            sl.pack(side="right"); self.stat_labels[key]=sl
        tk.Frame(inner,bg=BORDER,height=1).pack(fill="x",pady=6)
        self.progress_var=tk.DoubleVar(value=0)
        ttk.Progressbar(inner,variable=self.progress_var,maximum=100,
                        style="Cyber.Horizontal.TProgressbar").pack(fill="x")
        self.prog_label=tk.Label(inner,text="IDLE",font=FONT_SMALL,bg=PANEL,fg=MUTED)
        self.prog_label.pack(fill="x",pady=(2,0))

    def _build_results_panel(self,parent):
        frame=tk.Frame(parent,bg=BG); frame.pack(fill="both",expand=True)
        cols=("proxy","type","network","latency","score","isp","google","cf")
        sb=tk.Scrollbar(frame,orient="vertical",bg=BG,troughcolor=BG2,activebackground=ACCENT)
        sb.pack(side="right",fill="y")
        self.tree=ttk.Treeview(frame,columns=cols,show="headings",style="Cyber.Treeview",
                                yscrollcommand=sb.set,height=12)
        sb.config(command=self.tree.yview)
        for col,(lbl,w) in {"proxy":("PROXY",160),"type":("TYPE",90),"network":("NETWORK",100),
                              "latency":("LATENCY",75),"score":("SCORE",60),
                              "isp":("ISP",160),"google":("GOOGLE",60),"cf":("CF",50)}.items():
            self.tree.heading(col,text=lbl)
            self.tree.column(col,width=w,anchor="center" if col not in ("proxy","isp") else "w")
        self.tree.tag_configure("live", foreground=ACCENT2)
        self.tree.tag_configure("elite",foreground=GOLD)
        self.tree.pack(side="left",fill="both",expand=True)

    def _build_log_panel(self,parent):
        frame=tk.Frame(parent,bg=BG,height=120); frame.pack(fill="x"); frame.pack_propagate(False)
        self.log=scrolledtext.ScrolledText(frame,font=FONT_MONO2,bg=BG2,fg=MUTED,
                                            insertbackground=ACCENT,relief="flat",
                                            highlightbackground=BORDER,highlightthickness=1,
                                            state="disabled",wrap="none")
        self.log.pack(fill="both",expand=True)
        for tag,col in [("live",ACCENT2),("dead",DEAD),("elite",GOLD),("info",ACCENT),("warn",WARN)]:
            self.log.tag_config(tag,foreground=col)

    def _build_bottom_bar(self,parent):
        bar=tk.Frame(parent,bg=PANEL,highlightbackground=BORDER,highlightthickness=1)
        bar.pack(fill="x",side="bottom",pady=(0,4))
        inner=tk.Frame(bar,bg=PANEL); inner.pack(fill="x",padx=8,pady=6)
        self.start_btn=self._btn(inner,"▶  START SCAN",self._start_scan,ACCENT2,big=True)
        self.start_btn.pack(side="left",padx=(0,6))
        self.stop_btn=self._btn(inner,"■  STOP",self._stop_scan,DEAD,big=True)
        self.stop_btn.pack(side="left",padx=(0,6)); self.stop_btn.config(state="disabled")
        self._btn(inner,"⬇  EXPORT",self._export_results,ACCENT,big=True).pack(side="left",padx=(0,6))
        self._btn(inner,"✕  CLEAR LOG",self._clear_log,MUTED,big=True).pack(side="left")
        self.status_label=tk.Label(inner,text="● IDLE",font=("Consolas",10,"bold"),bg=PANEL,fg=MUTED)
        self.status_label.pack(side="right",padx=8)

    # ══════════════════════════════════════════════════════════════════════════
    # RE-CHECK TAB
    # ══════════════════════════════════════════════════════════════════════════
    def _build_recheck_tab(self):
        p = self.tab_recheck
        main = tk.Frame(p, bg=BG); main.pack(fill="both", expand=True, padx=8, pady=8)

        # ── Left panel ────────────────────────────────────────────────────────
        left = tk.Frame(main, bg=BG, width=285)
        left.pack(side="left", fill="y", padx=(0,8)); left.pack_propagate(False)

        self._section(left, "SOURCE FILE")
        fc = self._card(left)
        inner_f = tk.Frame(fc, bg=PANEL); inner_f.pack(fill="both", padx=8, pady=8)
        self.rc_file_var = tk.StringVar(value="")
        # Path display (truncated, shows full path as tooltip via label)
        self.rc_file_label = tk.Label(inner_f, text="No file selected", font=FONT_SMALL,
                                       bg=PANEL, fg=MUTED, anchor="w", wraplength=220, justify="left")
        self.rc_file_label.pack(fill="x", pady=(0,4))
        fr = tk.Frame(inner_f, bg=PANEL); fr.pack(fill="x", pady=2)
        self._btn(fr, "📂  BROWSE FILE", self._rc_browse, ACCENT, big=False).pack(side="left", fill="x", expand=True)
        self._btn(fr, "↺", self._rc_reload, MUTED).pack(side="right", padx=(4,0))
        # Format hint
        self.rc_fmt_label = tk.Label(inner_f, text="", font=FONT_SMALL, bg=PANEL, fg=PURPLE, anchor="w")
        self.rc_fmt_label.pack(fill="x", pady=(4,0))
        self.rc_count_label = tk.Label(inner_f, text="0 entries loaded", font=FONT_SMALL,
                                        bg=PANEL, fg=MUTED, anchor="w")
        self.rc_count_label.pack(fill="x", pady=(2,0))

        self._section(left, "SETTINGS")
        sc = self._card(left)
        inner_s = tk.Frame(sc, bg=PANEL); inner_s.pack(fill="both", padx=8, pady=8)
        def srow(lbl, var, lo, hi):
            r = tk.Frame(inner_s, bg=PANEL); r.pack(fill="x", pady=3)
            tk.Label(r, text=lbl, font=FONT_MONO2, bg=PANEL, fg=TEXT,
                     width=12, anchor="w").pack(side="left")
            tk.Spinbox(r, from_=lo, to=hi, textvariable=var, width=6, font=FONT_MONO2,
                       bg=BG2, fg=ACCENT, insertbackground=ACCENT, relief="flat",
                       highlightbackground=BORDER, highlightthickness=1,
                       buttonbackground=PANEL).pack(side="right")
        self.rc_timeout_var = tk.IntVar(value=TIMEOUT)
        srow("TIMEOUT (s)", self.rc_timeout_var, 1, 30)
        tk.Label(inner_s, text="WORKERS: 1  (fixed)", font=FONT_SMALL, bg=PANEL, fg=MUTED, anchor="w").pack(fill="x", pady=2)
        tk.Frame(inner_s, bg=BORDER, height=1).pack(fill="x", pady=6)
        self.rc_only_unknown = tk.BooleanVar(value=True)
        tk.Checkbutton(inner_s, text="Only fix UNKNOWN ISP/network",
                        variable=self.rc_only_unknown, font=FONT_SMALL,
                        bg=PANEL, fg=TEXT, selectcolor=BG2,
                        activebackground=PANEL, activeforeground=ACCENT,
                        relief="flat",
                        command=self._rc_update_mode_hint).pack(anchor="w")
        self._rc_mode_hint = tk.Label(inner_s,
                        text="→ Mode: NET ONLY  (detect network/ISP)",
                        font=FONT_SMALL, bg=PANEL, fg=PURPLE, anchor="w", wraplength=230, justify="left")
        self._rc_mode_hint.pack(anchor="w", pady=(2,0))

        self._section(left, "PROGRESS")
        pc = self._card(left)
        inner_p = tk.Frame(pc, bg=PANEL); inner_p.pack(fill="both", padx=8, pady=8)
        self.rc_stat_labels = {}
        for lbl, key, color in [("TOTAL","rc_total",TEXT),("LIVE","rc_live",ACCENT2),
                                  ("DEAD","rc_dead",DEAD),("UPDATED","rc_updated",ACCENT),
                                  ("UNCHANGED","rc_unchanged",MUTED),("FAILED","rc_failed",WARN)]:
            r = tk.Frame(inner_p, bg=PANEL); r.pack(fill="x", pady=1)
            tk.Label(r, text=lbl, font=FONT_MONO2, bg=PANEL, fg=MUTED,
                     width=12, anchor="w").pack(side="left")
            sl = tk.Label(r, text="0", font=("Consolas",10,"bold"),
                           bg=PANEL, fg=color, anchor="e", width=6)
            sl.pack(side="right"); self.rc_stat_labels[key] = sl
        tk.Frame(inner_p, bg=BORDER, height=1).pack(fill="x", pady=6)
        self.rc_prog_var = tk.DoubleVar(value=0)
        ttk.Progressbar(inner_p, variable=self.rc_prog_var, maximum=100,
                        style="Cyber.Horizontal.TProgressbar").pack(fill="x")
        self.rc_prog_label = tk.Label(inner_p, text="IDLE", font=FONT_SMALL, bg=PANEL, fg=MUTED)
        self.rc_prog_label.pack(fill="x", pady=(2,0))

        # ── Right panel ───────────────────────────────────────────────────────
        right = tk.Frame(main, bg=BG); right.pack(side="left", fill="both", expand=True)

        self._section(right, "RE-CHECK RESULTS")
        rc_frame = tk.Frame(right, bg=BG); rc_frame.pack(fill="both", expand=True)
        rc_cols = ("proxy","old_net","new_net","old_isp","new_isp","status")
        rc_sb = tk.Scrollbar(rc_frame, orient="vertical", bg=BG,
                              troughcolor=BG2, activebackground=ACCENT)
        rc_sb.pack(side="right", fill="y")
        self.rc_tree = ttk.Treeview(rc_frame, columns=rc_cols, show="headings",
                                     style="Cyber.Treeview", yscrollcommand=rc_sb.set, height=14)
        rc_sb.config(command=self.rc_tree.yview)
        for col,(lbl,w) in {"proxy":("PROXY",150),"old_net":("OLD NET",95),
                              "new_net":("NEW NET",95),"old_isp":("OLD ISP",155),
                              "new_isp":("NEW ISP",155),"status":("STATUS",80)}.items():
            self.rc_tree.heading(col, text=lbl)
            self.rc_tree.column(col, width=w,
                                 anchor="w" if col in ("old_isp","new_isp","proxy") else "center")
        self.rc_tree.tag_configure("updated",   foreground=ACCENT2)
        self.rc_tree.tag_configure("unchanged", foreground=MUTED)
        self.rc_tree.tag_configure("failed",    foreground=DEAD)
        self.rc_tree.pack(side="left", fill="both", expand=True)

        self._section(right, "RE-CHECK LOG")
        log_frame = tk.Frame(right, bg=BG, height=120)
        log_frame.pack(fill="x"); log_frame.pack_propagate(False)
        self.rc_log = scrolledtext.ScrolledText(
            log_frame, font=FONT_MONO2, bg=BG2, fg=MUTED,
            insertbackground=ACCENT, relief="flat",
            highlightbackground=BORDER, highlightthickness=1,
            state="disabled", wrap="none")
        self.rc_log.pack(fill="both", expand=True)
        for tag, col in [("updated",ACCENT2),("failed",DEAD),("info",ACCENT),("warn",WARN),("ok",ACCENT2)]:
            self.rc_log.tag_config(tag, foreground=col)

        # Bottom bar
        bar = tk.Frame(p, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        bar.pack(fill="x", side="bottom", pady=(0,4))
        inner = tk.Frame(bar, bg=PANEL); inner.pack(fill="x", padx=8, pady=6)
        self.rc_start_btn = self._btn(inner, "↺  START RE-CHECK", self._rc_start, ACCENT2, big=True)
        self.rc_start_btn.pack(side="left", padx=(0,6))
        self.rc_stop_btn = self._btn(inner, "■  STOP", self._rc_stop, DEAD, big=True)
        self.rc_stop_btn.pack(side="left", padx=(0,6))
        self.rc_stop_btn.config(state="disabled")
        self.rc_status_label = tk.Label(inner, text="● IDLE",
                                         font=("Consolas",10,"bold"), bg=PANEL, fg=MUTED)
        self.rc_status_label.pack(side="right", padx=8)

    # ── RE-CHECK helpers ──────────────────────────────────────────────────────
    def _rclog(self, msg, tag=""):
        self.rc_log.config(state="normal")
        self.rc_log.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n", tag)
        self.rc_log.see("end"); self.rc_log.config(state="disabled")

    def _rc_browse(self):
        path = filedialog.askopenfilename(
            title="Select proxy file",
            initialdir=os.getcwd(),
            filetypes=[("Text files","*.txt"),("All files","*.*")])
        if path:
            self.rc_file_var.set(path)
            self._rc_do_load(path)

    def _rc_reload(self):
        path = self.rc_file_var.get()
        if path:
            self._rc_do_load(path)
        else:
            self._rclog("No file selected. Use BROWSE first.", "warn")

    def _rc_load_file(self):          # kept for compatibility
        self._rc_reload()

    def _rc_do_load(self, path):
        """Load file — supports Full_data_proxy format AND plain ip:port list."""
        if not os.path.isfile(path):
            alt = os.path.join(os.getcwd(), path)
            if os.path.isfile(alt):
                path = alt; self.rc_file_var.set(path)
            else:
                self._rclog(f"File not found: {path}", "warn"); return

        # Short display name (last 2 path components)
        parts = path.replace("\\","/").split("/")
        short = "/".join(parts[-2:]) if len(parts)>=2 else path
        self.rc_file_label.config(text=short, fg=ACCENT)

        with open(path, "r", encoding="utf-8") as f:
            raw = [l.rstrip("\n") for l in f if l.strip()]

        # Auto-detect format: full-data vs plain ip:port
        full_data_lines = [l for l in raw if self._parse_full_data_line(l) is not None]
        plain_lines     = [l for l in raw if IP_PORT_RE.match(l.strip())]

        if len(full_data_lines) > 0:
            # Full_data_proxy.txt format
            self._rc_raw_lines = raw
            fmt = f"Full_data format  ({len(full_data_lines)} valid entries)"
            self.rc_fmt_label.config(text=f"▸ {fmt}", fg=PURPLE)
            self.rc_count_label.config(text=f"{len(full_data_lines)} entries loaded")
            self._rclog(f"Loaded {len(full_data_lines)} full-data entries ← {os.path.basename(path)}", "info")
        else:
            # Plain ip:port list — convert to minimal full-data lines
            converted = []
            for l in raw:
                m = IP_PORT_RE.search(l.strip())
                if m:
                    px = f"{m.group(1)}:{m.group(2)}"
                    converted.append(
                        f"[LIVE] {px} | UNKNOWN | UNKNOWN | 0ms | Score: 0 | ISP: UNKNOWN | Google: ❌ CF: ❌")
            self._rc_raw_lines = converted
            fmt = f"Plain ip:port  ({len(converted)} proxies)"
            self.rc_fmt_label.config(text=f"▸ {fmt}", fg=WARN)
            self.rc_count_label.config(text=f"{len(converted)} proxies loaded")
            self._rclog(f"Loaded {len(converted)} plain proxies (converted) ← {os.path.basename(path)}", "info")

    @staticmethod
    def _parse_full_data_line(line):
        """Parse a Full_data_proxy.txt line; return dict or None."""
        m = re.match(
            r"\[LIVE\]\s+(\S+)\s*\|\s*(\S+)\s*\|\s*(\S+)\s*\|\s*(\d+)ms\s*\|"
            r"\s*Score:\s*(\d+)\s*\|\s*ISP:\s*(.*?)\s*\|\s*Google:\s*([✅❌])\s+CF:\s*([✅❌])",
            line)
        if not m:
            return None
        return {
            "proxy":   m.group(1),
            "type":    m.group(2),
            "network": m.group(3),
            "latency": int(m.group(4)),
            "score":   int(m.group(5)),
            "isp":     m.group(6).strip(),
            "google":  m.group(7) == "✅",
            "cf":      m.group(8) == "✅",
        }

    def _rc_update_mode_hint(self):
        """Cập nhật label mô tả mode khi toggle checkbox."""
        if self.rc_only_unknown.get():
            self._rc_mode_hint.config(
                text="→ Mode: NET ONLY  (chỉ detect lại network/ISP cho UNKNOWN)", fg=PURPLE)
        else:
            self._rc_mode_hint.config(
                text="→ Mode: FULL CHECK  (check_proxy đầy đủ — live/dead/type/network)", fg=WARN)

    def _rc_start(self):
        if not hasattr(self, "_rc_raw_lines") or not self._rc_raw_lines:
            self._rclog("Load a file first!", "warn"); return
        entries = []
        only_unk = self.rc_only_unknown.get()
        for line in self._rc_raw_lines:
            d = self._parse_full_data_line(line)
            if d is None: continue
            if only_unk and d["network"] != "UNKNOWN" and d["isp"] != "UNKNOWN":
                continue
            entries.append(d)
        if not entries:
            msg = "No UNKNOWN entries to re-check." if only_unk else "File is empty or no valid entries."
            self._rclog(msg, "warn"); return

        # Mode: "net_only" = chỉ detect_network (fast), "full" = check_proxy đầy đủ
        self._rc_mode = "net_only" if only_unk else "full"

        self.rechecking = True
        self._rc_entries     = entries
        self._rc_all_lines   = list(self._rc_raw_lines)
        self._rc_updated_map = {}
        self._rc_failed_set  = set()
        self._rc_dead_set    = set()
        self._rc_stats = {"rc_total": len(entries), "rc_live": 0, "rc_dead": 0,
                           "rc_updated": 0, "rc_unchanged": 0, "rc_failed": 0}
        for k, v in self._rc_stats.items():
            self.rc_stat_labels[k].config(text=str(v))
        self.rc_prog_var.set(0); self.rc_prog_label.config(text="SCANNING…")
        mode_txt = "NET ONLY" if only_unk else "FULL CHECK"
        self.rc_status_label.config(text=f"● {mode_txt}", fg=ACCENT2)
        self.global_status.config(text="↺ RE-CHECKING", fg=ACCENT2)
        self.rc_start_btn.config(state="disabled")
        self.rc_stop_btn.config(state="normal")
        for row in self.rc_tree.get_children(): self.rc_tree.delete(row)
        wk_display = "2" if only_unk else str(self.rc_timeout_var.get() and MAX_WORKERS // 2 or 50)
        self._rclog(f"Mode: {mode_txt} | {len(entries)} entries…", "info")

        def worker():
            global TIMEOUT; TIMEOUT = self.rc_timeout_var.get()
            total = len(entries); done = 0
            if self._rc_mode == "net_only":
                # Fast path: only re-detect network/ISP
                wk = 1
                with ThreadPoolExecutor(max_workers=wk) as ex:
                    futs = {ex.submit(detect_network, e["proxy"].split(":")[0]): e
                            for e in entries}
                    for fut in as_completed(futs):
                        if not self.rechecking:
                            ex.shutdown(wait=False, cancel_futures=True); break
                        entry = futs[fut]; done += 1
                        try:   new_net, new_isp = fut.result()
                        except: new_net, new_isp = "UNKNOWN", "UNKNOWN"
                        self.recheck_q.put(("result_net", entry, new_net, new_isp, done, total))
            else:
                # Full path: full proxy check (live/dead + type + network + latency)
                wk = min(MAX_WORKERS // 2, 50)
                with ThreadPoolExecutor(max_workers=wk) as ex:
                    futs = {ex.submit(check_proxy, e["proxy"]): e for e in entries}
                    for fut in as_completed(futs):
                        if not self.rechecking:
                            ex.shutdown(wait=False, cancel_futures=True); break
                        entry = futs[fut]; done += 1
                        try:   res = fut.result()
                        except: res = {"proxy": entry["proxy"], "status": "DEAD"}
                        self.recheck_q.put(("result_full", entry, res, done, total))
            self.recheck_q.put(("done", None, None, None, done, total))
        threading.Thread(target=worker, daemon=True).start()

    def _rc_stop(self):
        self.rechecking = False
        self._rclog("Re-check stopped.", "warn")

    def _poll_recheck_queue(self):
        try:
            while True:
                item = self.recheck_q.get_nowait()
                kind = item[0]
                if kind == "result_net":
                    _, entry, new_net, new_isp, done, total = item
                    self._rc_handle_net(entry, new_net, new_isp, done, total)
                elif kind == "result_full":
                    _, entry, res, done, total = item
                    self._rc_handle_full(entry, res, done, total)
                elif kind == "done":
                    _, _, _, _, done, total = item
                    self._rc_done(done, total)
        except queue.Empty: pass
        self.root.after(50, self._poll_recheck_queue)

    def _rc_update_progress(self, done, total):
        pct = (done / total * 100) if total else 0
        self.rc_prog_var.set(pct)
        self.rc_prog_label.config(text=f"{done}/{total} ({pct:.1f}%)")
        for k, v in self._rc_stats.items():
            self.rc_stat_labels[k].config(text=str(v))

    def _rc_handle_net(self, entry, new_net, new_isp, done, total):
        """Handle result from net-only mode (detect_network)."""
        self._rc_update_progress(done, total)
        old_net = entry["network"]; old_isp = entry["isp"]
        changed = new_net != "UNKNOWN" and (new_net != old_net or new_isp != old_isp)

        if changed:
            self._rc_stats["rc_live"] += 1
            self._rc_stats["rc_updated"] += 1
            tag = "updated"; status = "UPDATED"
            entry["network"] = new_net; entry["isp"] = new_isp
            entry["score"] = calculate_score(entry["type"], new_net,
                                              entry["google"], entry["cf"], entry["latency"])
            self._rc_updated_map[entry["proxy"]] = entry
            self._rclog(f"[UPD] {entry['proxy']:22} net:{old_net}→{new_net}  isp:{old_isp[:18]}→{new_isp[:18]}", "updated")
        elif new_net == "UNKNOWN":
            self._rc_stats["rc_failed"] += 1
            tag = "failed"; status = "FAILED"
            self._rc_failed_set.add(entry["proxy"])
            self._rclog(f"[DEL] {entry['proxy']:22} still UNKNOWN → will be removed", "warn")
        else:
            self._rc_stats["rc_live"] += 1
            self._rc_stats["rc_unchanged"] += 1
            tag = "unchanged"; status = "OK"

        self.rc_tree.insert("", "end", values=(
            entry["proxy"], old_net,
            new_net if new_net != "UNKNOWN" else "—",
            old_isp[:22],
            new_isp[:22] if new_isp != "UNKNOWN" else "—",
            status), tags=(tag,))
        self.rc_tree.yview_moveto(1)

    def _rc_handle_full(self, entry, res, done, total):
        """Handle result from full check_proxy mode."""
        self._rc_update_progress(done, total)
        old_net = entry["network"]; old_isp = entry["isp"]

        if res["status"] == "DEAD":
            self._rc_stats["rc_dead"] += 1
            self._rc_dead_set.add(entry["proxy"])
            self._rc_failed_set.add(entry["proxy"])
            tag = "failed"; status = "DEAD"
            self._rclog(f"[DEAD] {entry['proxy']:22} → removed", "warn")
            self.rc_tree.insert("", "end", values=(
                entry["proxy"], old_net, "DEAD", old_isp[:22], "—", "DEAD"), tags=(tag,))
        else:
            self._rc_stats["rc_live"] += 1
            new_net = res["network"]; new_isp = res["isp"]
            new_type = res["type"]; new_lat = res["avg_latency"]
            new_score = res["score"]
            changed = (new_net != old_net or new_isp != old_isp or
                       new_type != entry["type"] or abs(new_lat - entry["latency"]) > 0)
            # Always update with fresh data in full mode
            entry.update({"network": new_net, "isp": new_isp, "type": new_type,
                           "latency": new_lat, "score": new_score,
                           "google": res["google"], "cf": res["cloudflare"]})
            self._rc_updated_map[entry["proxy"]] = entry
            if changed:
                self._rc_stats["rc_updated"] += 1
                tag = "updated"; status = "UPDATED"
                self._rclog(
                    f"[UPD] {entry['proxy']:22} {new_type:12} net:{old_net}→{new_net}  "
                    f"{new_lat}ms  score:{new_score}", "updated")
            else:
                self._rc_stats["rc_unchanged"] += 1
                tag = "unchanged"; status = "OK"
            self.rc_tree.insert("", "end", values=(
                entry["proxy"], old_net, new_net, old_isp[:22], new_isp[:22], status), tags=(tag,))
        self.rc_tree.yview_moveto(1)

    def _rc_done(self, done, total):
        self.rechecking = False
        self.rc_prog_var.set(100)
        self.rc_prog_label.config(text=f"DONE {done}/{total}")
        self.rc_status_label.config(text="● DONE", fg=ACCENT)
        self.global_status.config(text="● IDLE", fg=MUTED)
        self.rc_start_btn.config(state="normal")
        self.rc_stop_btn.config(state="disabled")
        upd  = self._rc_stats["rc_updated"]
        dead = self._rc_stats.get("rc_dead", 0)
        fail = self._rc_stats["rc_failed"]
        live = self._rc_stats.get("rc_live", 0)
        unch = self._rc_stats.get("rc_unchanged", 0)
        if getattr(self, "_rc_mode", "net_only") == "full":
            self._rclog(
                f"Full check done — {live} LIVE  {dead} DEAD removed  "
                f"{upd} updated  {unch} unchanged", "ok")
        else:
            self._rclog(f"Net-only done — {upd} updated, {fail} still UNKNOWN removed", "ok")
        if upd > 0 or fail > 0:
            self._rc_overwrite_file()

    def _rc_overwrite_file(self):
        """Rewrite Full_data_proxy.txt and sync TYPE_NETWORK.txt / ALL_PROXY.txt."""
        path = self.rc_file_var.get()
        if not os.path.isfile(path):
            alt = os.path.join(os.getcwd(), path)
            if os.path.isfile(alt): path = alt
            else:
                self._rclog(f"Cannot write — file not found: {path}", "warn"); return

        sd = os.path.dirname(os.path.abspath(path))
        full_mode = getattr(self, "_rc_mode", "net_only") == "full"

        # ── 1. Rewrite Full_data_proxy.txt ───────────────────────────────────
        new_lines = []
        removed = 0
        for line in self._rc_all_lines:
            d = self._parse_full_data_line(line)
            if d and d["proxy"] in self._rc_failed_set:
                removed += 1
                continue
            if d and d["proxy"] in self._rc_updated_map:
                u = self._rc_updated_map[d["proxy"]]
                g = "✅" if u["google"] else "❌"
                c = "✅" if u["cf"]     else "❌"
                line = (f"[LIVE] {u['proxy']} | {u['type']} | {u['network']} | "
                        f"{u['latency']}ms | Score: {u['score']} | ISP: {u['isp']} | "
                        f"Google: {g} CF: {c}")
            new_lines.append(line)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines) + "\n")

        # ── 2. Update TYPE_NETWORK.txt files ─────────────────────────────────
        if full_mode:
            # FULL MODE: xóa DEAD khỏi tất cả TYPE_NETWORK files trong cùng thư mục
            dead_set = getattr(self, "_rc_dead_set", set())
            if dead_set:
                import glob
                for txt_file in glob.glob(os.path.join(sd, "*.txt")):
                    if os.path.abspath(txt_file) == os.path.abspath(path):
                        continue  # skip Full_data file itself
                    try:
                        with open(txt_file, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                        new_txt = [l for l in lines if l.strip() not in dead_set]
                        if len(new_txt) != len(lines):
                            with open(txt_file, "w", encoding="utf-8") as f:
                                f.writelines(new_txt)
                            self._rclog(
                                f"Removed {len(lines)-len(new_txt)} dead proxies from "
                                f"{os.path.basename(txt_file)}", "warn")
                    except Exception:
                        pass

            # Cập nhật proxy sống: xóa khỏi file cũ, thêm vào file mới
            for u in self._rc_updated_map.values():
                # Tìm và xóa khỏi mọi file TYPE_* (tránh duplicate ở file cũ)
                for txt_file in glob.glob(os.path.join(sd, f"{u['type']}_*.txt")):
                    try:
                        with open(txt_file, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                        new_txt = [l for l in lines if l.strip() != u["proxy"]]
                        if len(new_txt) != len(lines):
                            with open(txt_file, "w", encoding="utf-8") as f:
                                f.writelines(new_txt)
                    except Exception:
                        pass
                # Thêm vào đúng file TYPE_NETWORK
                new_type_file = os.path.join(sd, f"{u['type']}_{u['network']}.txt")
                existing = set()
                if os.path.isfile(new_type_file):
                    with open(new_type_file, "r", encoding="utf-8") as f:
                        existing = {l.strip() for l in f}
                if u["proxy"] not in existing:
                    with open(new_type_file, "a", encoding="utf-8") as f:
                        f.write(u["proxy"] + "\n")
        else:
            # NET-ONLY MODE: chỉ di chuyển từ *_UNKNOWN sang TYPE_NETWORK đúng
            for u in self._rc_updated_map.values():
                old_unk = os.path.join(sd, f"{u['type']}_UNKNOWN.txt")
                new_tf  = os.path.join(sd, f"{u['type']}_{u['network']}.txt")
                if os.path.isfile(old_unk):
                    with open(old_unk, "r", encoding="utf-8") as f:
                        lines = [l for l in f.readlines() if l.strip() != u["proxy"]]
                    with open(old_unk, "w", encoding="utf-8") as f:
                        f.writelines(lines)
                existing = set()
                if os.path.isfile(new_tf):
                    with open(new_tf, "r", encoding="utf-8") as f:
                        existing = {l.strip() for l in f}
                if u["proxy"] not in existing:
                    with open(new_tf, "a", encoding="utf-8") as f:
                        f.write(u["proxy"] + "\n")

        # ── 3. Rebuild ALL_PROXY.txt ──────────────────────────────────────────
        all_proxies = [self._parse_full_data_line(l)["proxy"]
                       for l in new_lines if self._parse_full_data_line(l)]
        all_proxy_file = os.path.join(sd, "ALL_PROXY.txt")
        with open(all_proxy_file, "w", encoding="utf-8") as f:
            f.write("\n".join(all_proxies) + "\n")

        mode_txt = "FULL" if full_mode else "NET-ONLY"
        self._rclog(
            f"[{mode_txt}] File saved — {removed} removed, "
            f"{self._rc_stats['rc_updated']} updated, "
            f"ALL_PROXY rebuilt ({len(all_proxies)} proxies)", "ok")

    # ══════════════════════════════════════════════════════════════════════════
    # SETTINGS TAB
    # ══════════════════════════════════════════════════════════════════════════
    def _build_settings_tab(self):
        s    = self._settings
        lang = s.get("lang","EN")
        T    = I18N[lang]
        p    = self.tab_settings

        # Init judge lists from settings
        self._ssl_judges  = list(s.get("ssl_judges",  list(SSL_JUDGES)))
        self._http_judges = list(s.get("http_judges", list(HTTP_JUDGES)))
        self._ssl_chk_vars  = {}
        self._http_chk_vars = {}

        canvas = tk.Canvas(p, bg=BG, highlightthickness=0)
        vsb = tk.Scrollbar(p, orient="vertical", command=canvas.yview, bg=BG, troughcolor=BG2)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(canvas, bg=BG)
        win_id = canvas.create_window((0,0), window=inner, anchor="nw")
        def _on_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(win_id, width=canvas.winfo_width())
        inner.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)),"units"))

        body = tk.Frame(inner, bg=BG); body.pack(fill="both", padx=20, pady=16)

        # ── Row 1: Theme + Language side by side ──────────────────────────────
        row1 = tk.Frame(body, bg=BG); row1.pack(fill="x", pady=(0,12))

        # THEME card
        tc = tk.Frame(row1, bg=PANEL, relief="flat",
                      highlightbackground=BORDER, highlightthickness=1)
        tc.pack(side="left", fill="both", expand=True, padx=(0,8))
        tk.Label(tc, text=f"▸ {T['set_theme']}", font=("Consolas",9,"bold"),
                 bg=PANEL, fg=ACCENT).pack(anchor="w", padx=12, pady=(10,6))
        tk.Frame(tc, bg=BORDER, height=1).pack(fill="x", padx=12)
        self._set_theme_var = tk.StringVar(value=s.get("theme","dark"))
        thf = tk.Frame(tc, bg=PANEL); thf.pack(padx=12, pady=10, anchor="w")
        for val, ico, label in [("dark","🌙","Dark / Tối"), ("light","☀️","Light / Sáng"),
                                  ("custom","🎨","Custom")]:
            tk.Radiobutton(thf, text=f"  {ico}  {label}", variable=self._set_theme_var,
                           value=val, font=FONT_MONO2, bg=PANEL, fg=TEXT,
                           selectcolor=BG2, activebackground=PANEL,
                           activeforeground=ACCENT, relief="flat",
                           indicatoron=True).pack(anchor="w", pady=3)
        tk.Label(tc, text="↻ Restart to fully apply / Khởi động lại để áp dụng",
                 font=FONT_SMALL, bg=PANEL, fg=MUTED).pack(anchor="w", padx=12, pady=(0,8))

        # LANGUAGE card
        lc = tk.Frame(row1, bg=PANEL, relief="flat",
                      highlightbackground=BORDER, highlightthickness=1)
        lc.pack(side="left", fill="both", expand=True)
        tk.Label(lc, text=f"▸ {T['set_lang']}", font=("Consolas",9,"bold"),
                 bg=PANEL, fg=ACCENT).pack(anchor="w", padx=12, pady=(10,6))
        tk.Frame(lc, bg=BORDER, height=1).pack(fill="x", padx=12)
        self._set_lang_var = tk.StringVar(value=s.get("lang","EN"))
        lf = tk.Frame(lc, bg=PANEL); lf.pack(padx=12, pady=10, anchor="w")
        for val, ico in [("EN","🇬🇧  English"), ("VIE","🇻🇳  Tiếng Việt")]:
            tk.Radiobutton(lf, text=f"  {ico}", variable=self._set_lang_var,
                           value=val, font=FONT_MONO2, bg=PANEL, fg=TEXT,
                           selectcolor=BG2, activebackground=PANEL,
                           activeforeground=ACCENT, relief="flat").pack(anchor="w", pady=3)

        # ── Custom Palette card ────────────────────────────────────────────────
        self._section(body, "🎨  CUSTOM PALETTE  (chỉ dùng khi chọn Custom theme)")
        cp_card = tk.Frame(body, bg=PANEL, relief="flat",
                           highlightbackground=BORDER, highlightthickness=1)
        cp_card.pack(fill="x", pady=(0,8))
        cp_inner = tk.Frame(cp_card, bg=PANEL); cp_inner.pack(fill="x", padx=12, pady=10)

        # Color keys to expose in UI
        _CP_KEYS = [
            ("BG",     "Background chính"),
            ("BG2",    "Background phụ"),
            ("PANEL",  "Panel / Card"),
            ("BORDER", "Viền"),
            ("ACCENT", "Accent 1 (xanh cyan)"),
            ("ACCENT2","Accent 2 (xanh lá)"),
            ("WARN",   "Cảnh báo"),
            ("DEAD",   "Proxy chết"),
            ("TEXT",   "Chữ chính"),
            ("MUTED",  "Chữ mờ"),
            ("GOLD",   "Vàng / Điểm cao"),
            ("PURPLE", "Tím / Header"),
        ]
        self._cp_vars = {}
        cols_per_row = 3
        grid = tk.Frame(cp_inner, bg=PANEL); grid.pack(fill="x")
        for idx, (key, label) in enumerate(_CP_KEYS):
            col = idx % cols_per_row
            row = idx // cols_per_row
            cell = tk.Frame(grid, bg=PANEL); cell.grid(row=row, column=col, padx=6, pady=4, sticky="w")
            cur_color = CUSTOM_PALETTE.get(key, "#000000")
            var = tk.StringVar(value=cur_color)
            self._cp_vars[key] = var
            swatch = tk.Label(cell, bg=cur_color, width=3, height=1, relief="solid", bd=1)
            swatch.pack(side="left", padx=(0,4))
            tk.Label(cell, text=label, font=FONT_SMALL, bg=PANEL, fg=TEXT, width=20, anchor="w").pack(side="left")
            def _pick(k=key, v=var, sw=swatch):
                color = colorchooser.askcolor(color=v.get(), title=f"Chọn màu: {k}")
                if color and color[1]:
                    v.set(color[1]); sw.config(bg=color[1])
                    CUSTOM_PALETTE[k] = color[1]
            tk.Button(cell, textvariable=var, font=FONT_SMALL, bg=BG2, fg=ACCENT,
                      relief="flat", bd=0, cursor="hand2",
                      command=_pick, width=8).pack(side="left", padx=(2,0))

        tk.Button(cp_inner, text="↩ Reset về Dark", font=FONT_SMALL, bg=BG2, fg=MUTED,
                  relief="flat", bd=0, cursor="hand2",
                  command=self._reset_custom_palette).pack(anchor="w", pady=(8,0))

        # ── Row 2: SSL Judges ──────────────────────────────────────────────────
        self._section(body, T["set_ssl_judges"])
        ssl_card = tk.Frame(body, bg=PANEL, relief="flat",
                            highlightbackground=BORDER, highlightthickness=1)
        ssl_card.pack(fill="x", pady=(0,8))
        ssl_inner = tk.Frame(ssl_card, bg=PANEL); ssl_inner.pack(fill="x", padx=12, pady=10)
        self._ssl_list_frame = tk.Frame(ssl_inner, bg=PANEL)
        self._ssl_list_frame.pack(fill="x")
        ssl_en = s.get("ssl_enabled", {})
        for url in self._ssl_judges:
            self._add_judge_row(self._ssl_list_frame, url, "ssl",
                                ssl_en.get(url, True))
        # Add URL row
        self._ssl_add_frame = tk.Frame(ssl_inner, bg=PANEL)
        self._ssl_add_frame.pack(fill="x", pady=(8,0))
        self._ssl_new_var = tk.StringVar()
        tk.Entry(self._ssl_add_frame, textvariable=self._ssl_new_var,
                 font=FONT_MONO2, bg=BG2, fg=TEXT, insertbackground=ACCENT,
                 relief="flat", highlightbackground=BORDER, highlightthickness=1,
                 width=55).pack(side="left", fill="x", expand=True, padx=(0,6))
        self._btn(self._ssl_add_frame, "＋ ADD",
                  lambda: self._judge_add("ssl"), ACCENT2, big=False).pack(side="left")
        self._btn(self._ssl_add_frame, "⚡ PING ALL",
                  lambda: self._ping_all_judges("ssl"), GOLD, big=False).pack(side="left", padx=(8,0))

        # ── Row 3: HTTP Judges ─────────────────────────────────────────────────
        self._section(body, T["set_http_judges"])
        http_card = tk.Frame(body, bg=PANEL, relief="flat",
                             highlightbackground=BORDER, highlightthickness=1)
        http_card.pack(fill="x", pady=(0,8))
        http_inner = tk.Frame(http_card, bg=PANEL); http_inner.pack(fill="x", padx=12, pady=10)
        self._http_list_frame = tk.Frame(http_inner, bg=PANEL)
        self._http_list_frame.pack(fill="x")
        http_en = s.get("http_enabled", {})
        for url in self._http_judges:
            self._add_judge_row(self._http_list_frame, url, "http",
                                http_en.get(url, True))
        # Add URL row
        self._http_add_frame = tk.Frame(http_inner, bg=PANEL)
        self._http_add_frame.pack(fill="x", pady=(8,0))
        self._http_new_var = tk.StringVar()
        tk.Entry(self._http_add_frame, textvariable=self._http_new_var,
                 font=FONT_MONO2, bg=BG2, fg=TEXT, insertbackground=ACCENT,
                 relief="flat", highlightbackground=BORDER, highlightthickness=1,
                 width=55).pack(side="left", fill="x", expand=True, padx=(0,6))
        self._btn(self._http_add_frame, "＋ ADD",
                  lambda: self._judge_add("http"), ACCENT2, big=False).pack(side="left")
        self._btn(self._http_add_frame, "⚡ PING ALL",
                  lambda: self._ping_all_judges("http"), GOLD, big=False).pack(side="left", padx=(8,0))

        # ── Save button + status ───────────────────────────────────────────────
        tk.Frame(body, bg=BORDER, height=1).pack(fill="x", pady=12)
        save_row = tk.Frame(body, bg=BG); save_row.pack(fill="x", pady=(0,16))
        self._btn(save_row, "💾  SAVE SETTINGS", self._save_settings, ACCENT, big=True).pack(side="left")
        self._set_save_label = tk.Label(save_row, text="",
                                        font=FONT_MONO2, bg=BG, fg=MUTED)
        self._set_save_label.pack(side="left", padx=12)

    def _reset_custom_palette(self):
        """Reset custom palette to dark theme defaults."""
        for k,v in DARK.items():
            CUSTOM_PALETTE[k] = v
        if hasattr(self, "_cp_vars"):
            for k, var in self._cp_vars.items():
                var.set(CUSTOM_PALETTE[k])


    def _add_judge_row(self, parent, url, kind, enabled=True):
        var = tk.BooleanVar(value=enabled)
        if kind == "ssl":
            self._ssl_chk_vars[url] = var
        else:
            self._http_chk_vars[url] = var

        row = tk.Frame(parent, bg=PANEL); row.pack(fill="x", pady=2)
        # Tick
        cb = tk.Checkbutton(row, variable=var, bg=PANEL, fg=ACCENT,
                            selectcolor=BG2, activebackground=PANEL,
                            activeforeground=ACCENT, relief="flat",
                            highlightthickness=0)
        cb.pack(side="left")
        # URL label
        lbl = tk.Label(row, text=url, font=FONT_MONO2, bg=PANEL,
                       fg=TEXT if enabled else MUTED, anchor="w")
        lbl.pack(side="left", fill="x", expand=True, padx=(4,8))
        def _toggle_color(*_):
            lbl.config(fg=TEXT if var.get() else MUTED)
        var.trace_add("write", _toggle_color)
        # Ping label (shows result inline)
        ping_lbl = tk.Label(row, text="", font=("Consolas",8,"bold"),
                            bg=PANEL, fg=MUTED, width=18, anchor="e")
        ping_lbl.pack(side="right", padx=(0,4))

        def _ping_color(ms):
            if ms < 200:  return ACCENT2   # green  ≤200ms
            if ms < 500:  return GOLD      # yellow ≤500ms
            if ms < 1000: return WARN      # orange ≤1s
            return DEAD                    # red    >1s

        def _test(u=url, pl=ping_lbl):
            pl.config(text="⏱ pinging…", fg=WARN)
            def do():
                import socket, time, urllib.parse, ssl as _ssl
                parsed   = urllib.parse.urlparse(u)
                host     = parsed.hostname
                port     = parsed.port or (443 if parsed.scheme=="https" else 80)
                use_ssl  = parsed.scheme == "https"
                ROUNDS   = 3
                tcp_times, http_times = [], []

                for _ in range(ROUNDS):
                    # ── TCP handshake time ──────────────────────────────────
                    try:
                        t0 = time.perf_counter()
                        sock = socket.create_connection((host, port), timeout=5)
                        if use_ssl:
                            ctx = _ssl.create_default_context()
                            sock = ctx.wrap_socket(sock, server_hostname=host)
                        tcp_ms = (time.perf_counter() - t0) * 1000
                        sock.close()
                        tcp_times.append(tcp_ms)
                    except Exception:
                        tcp_times.append(None)

                    # ── Full HTTP response time ─────────────────────────────
                    try:
                        import requests as _req
                        t1 = time.perf_counter()
                        resp = _req.get(u, timeout=6,
                                        headers={"User-Agent":"ProxyHunter/3.0"},
                                        allow_redirects=False)
                        http_ms = (time.perf_counter() - t1) * 1000
                        status  = resp.status_code
                        http_times.append(http_ms)
                    except Exception:
                        http_ms = None
                        status  = 0
                        http_times.append(None)

                # ── Aggregate ───────────────────────────────────────────────
                tcp_ok  = [x for x in tcp_times  if x is not None]
                http_ok = [x for x in http_times if x is not None]
                alive   = len(http_ok) > 0

                if alive:
                    tcp_avg  = sum(tcp_ok)  / len(tcp_ok)  if tcp_ok  else 0
                    http_avg = sum(http_ok) / len(http_ok)
                    col = _ping_color(http_avg)
                    # jitter = max - min
                    jitter = (max(http_ok) - min(http_ok)) if len(http_ok) > 1 else 0
                    txt = (f"TCP {tcp_avg:>5.0f}ms  "
                           f"HTTP {http_avg:>5.0f}ms  "
                           f"±{jitter:>3.0f}ms  "
                           f"[{status}] ✓")
                else:
                    col = DEAD
                    txt = "UNREACHABLE ✗"

                pl.config(text=txt, fg=col)
                # Reset URL label back to normal after 8s
                self.root.after(8000, lambda: pl.config(
                    text="", fg=MUTED))
            import threading
            threading.Thread(target=do, daemon=True).start()
        self._btn(row, "PING", _test, MUTED, big=False).pack(side="right", padx=(0,2))
        # Delete button
        def _del(r=row, u=url, k=kind):
            r.destroy()
            if k == "ssl":
                self._ssl_judges = [x for x in self._ssl_judges if x != u]
                self._ssl_chk_vars.pop(u, None)
            else:
                self._http_judges = [x for x in self._http_judges if x != u]
                self._http_chk_vars.pop(u, None)
        self._btn(row, "✕", _del, DEAD, big=False).pack(side="right", padx=(0,2))

    def _ping_all_judges(self, kind):
        """Trigger PING on every judge row of the given kind simultaneously."""
        frame = self._ssl_list_frame if kind == "ssl" else self._http_list_frame
        for row in frame.winfo_children():
            # Each row has a PING button — find and invoke it
            for w in row.winfo_children():
                if isinstance(w, tk.Button) and w.cget("text") == "PING":
                    try: w.invoke()
                    except Exception: pass
                    break

    def _judge_add(self, kind):
        if kind == "ssl":
            url = self._ssl_new_var.get().strip()
            var_ref = self._ssl_new_var
            frame   = self._ssl_list_frame
            lst     = self._ssl_judges
        else:
            url = self._http_new_var.get().strip()
            var_ref = self._http_new_var
            frame   = self._http_list_frame
            lst     = self._http_judges
        if not url or not url.startswith(("http://","https://")):
            return
        if url in lst:
            return
        lst.append(url)
        self._add_judge_row(frame, url, kind, enabled=True)
        var_ref.set("")

    # ── Shared helpers ────────────────────────────────────────────────────────
    def _section(self,parent,title):
        row=tk.Frame(parent,bg=BG); row.pack(fill="x",pady=(8,2))
        tk.Label(row,text=f"▸ {title}",font=("Consolas",8,"bold"),bg=BG,fg=ACCENT).pack(side="left")
        tk.Frame(row,bg=BORDER,height=1).pack(side="left",fill="x",expand=True,padx=(6,0),pady=4)

    def _card(self,parent,**kw):
        f=tk.Frame(parent,bg=PANEL,relief="flat",highlightbackground=BORDER,highlightthickness=1,**kw)
        f.pack(fill="x",pady=2); return f

    def _btn(self,parent,text,cmd,color,big=False):
        font=("Consolas",10,"bold") if big else FONT_MONO2
        b=tk.Button(parent,text=text,command=cmd,bg=PANEL,fg=color,font=font,relief="flat",
                    activebackground=BG2,activeforeground=color,highlightbackground=color,
                    highlightthickness=1,padx=10,pady=4 if big else 2,cursor="hand2")
        b.bind("<Enter>",lambda e:b.config(bg=BG2))
        b.bind("<Leave>",lambda e:b.config(bg=PANEL))
        return b

    def _update_clock(self):
        self.ts_label.config(text=datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))
        self.root.after(1000,self._update_clock)

    def _log(self,msg,tag=""):
        self.log.config(state="normal")
        self.log.insert("end",f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n",tag)
        self.log.see("end"); self.log.config(state="disabled")

    def _update_stats(self):
        for key,lbl in self.stat_labels.items(): lbl.config(text=str(self.stats[key]))

    # ── Checker actions ───────────────────────────────────────────────────────
    def _browse_file(self):
        path=filedialog.askopenfilename(filetypes=[("Text","*.txt"),("All","*.*")])
        if path:
            self.file_var.set(os.path.basename(path))
            with open(path) as f: content=f.read()
            self.paste_box.delete("1.0","end"); self.paste_box.insert("1.0",content)
            self._log(f"Loaded: {path}","info")

    def _browse_dir(self):
        d=filedialog.askdirectory()
        if d: self.save_dir_var.set(d)

    def _load_proxies(self):
        raw=self.paste_box.get("1.0","end").strip().splitlines()
        self.proxies=[p.strip() for p in raw if p.strip() and ":" in p]
        self.count_label.config(text=f"{len(self.proxies)} proxies loaded")
        self._log(f"{len(self.proxies)} proxies ready","info")

    def _clear_all(self):
        self.paste_box.delete("1.0","end"); self.proxies=[]
        self.count_label.config(text="0 proxies loaded")

    def _clear_log(self):
        self.log.config(state="normal"); self.log.delete("1.0","end"); self.log.config(state="disabled")

    def _export_results(self):
        if not self.results: self._log("No results","warn"); return
        path=filedialog.asksaveasfilename(defaultextension=".txt",filetypes=[("Text","*.txt"),("CSV","*.csv")])
        if path:
            with open(path,"w",encoding="utf-8") as f:
                for r in self.results:
                    f.write(f"[LIVE] {r['proxy']} | {r['type']} | {r['network']} | {r['avg_latency']}ms | "
                            f"Score: {r['score']} | ISP: {r['isp']} | "
                            f"Google: {'✅' if r['google'] else '❌'} CF: {'✅' if r['cloudflare'] else '❌'}\n")
            self._log(f"Exported {len(self.results)} → {path}","info")

    def _start_scan(self):
        if not self.proxies: self._load_proxies()
        if not self.proxies: self._log("No proxies loaded!","warn"); return
        self.running=True
        self.stats={"total":len(self.proxies),"live":0,"dead":0,"elite":0,"anon":0,"trans":0,"dc":0,"res":0}
        self.results=[]; self._update_stats()
        self.progress_var.set(0); self.prog_label.config(text="SCANNING…")
        self.status_label.config(text="● SCANNING",fg=ACCENT2)
        self.global_status.config(text="✔ CHECKING",fg=ACCENT2)
        self.start_btn.config(state="disabled"); self.stop_btn.config(state="normal")
        for row in self.tree.get_children(): self.tree.delete(row)
        self._log(f"Scan: {len(self.proxies)} proxies | workers={self.workers_var.get()}","info")
        # ── reset output files ────────────────────────────────────────────────
        sd = self.save_dir_var.get()
        reset_files = ["ALL_PROXY.txt", "Full_data_proxy.txt"]
        for fname in os.listdir(sd):
            if fname.endswith(".txt") and ("ELITE" in fname or "ANONYMOUS" in fname or
               "TRANSPARENT" in fname or "UNKNOWN" in fname or
               "DATACENTER" in fname or "RESIDENTIAL" in fname):
                reset_files.append(fname)
        for fname in reset_files:
            fpath = os.path.join(sd, fname)
            if os.path.isfile(fpath):
                open(fpath, "w").close()
                self._log(f"Reset: {fname}", "info")
        # ─────────────────────────────────────────────────────────────────────
        def worker():
            global TIMEOUT; TIMEOUT=self.timeout_var.get()
            wk=self.workers_var.get(); total=len(self.proxies); done=0
            with ThreadPoolExecutor(max_workers=wk) as ex:
                futs={ex.submit(check_proxy,p):p for p in self.proxies}
                for fut in as_completed(futs):
                    if not self.running: ex.shutdown(wait=False,cancel_futures=True); break
                    res=fut.result(); done+=1; self.q.put(("result",res,done,total))
            self.q.put(("done",None,done,total))
        threading.Thread(target=worker,daemon=True).start()

    def _stop_scan(self): self.running=False; self._log("Scan stopped","warn")

    def _poll_queue(self):
        try:
            while True:
                kind,res,done,total=self.q.get_nowait()
                if kind=="result": self._handle_result(res,done,total)
                elif kind=="done": self._scan_done(done,total)
        except queue.Empty: pass
        self.root.after(50,self._poll_queue)

    def _handle_result(self,res,done,total):
        pct=(done/total*100) if total else 0
        self.progress_var.set(pct); self.prog_label.config(text=f"{done}/{total} ({pct:.1f}%)")
        if res["status"]=="LIVE":
            self.stats["live"]+=1; t=res["type"]
            if t=="ELITE": self.stats["elite"]+=1
            elif t=="ANONYMOUS": self.stats["anon"]+=1
            elif t=="TRANSPARENT": self.stats["trans"]+=1
            if res["network"]=="DATACENTER": self.stats["dc"]+=1
            elif res["network"]=="RESIDENTIAL": self.stats["res"]+=1
            self.results.append(res)
            tag="elite" if t=="ELITE" else "live"
            self.tree.insert("","end",values=(res["proxy"],res["type"],res["network"],
                f"{res['avg_latency']}ms",res["score"],res["isp"],
                "v" if res["google"] else "x","v" if res["cloudflare"] else "x"),tags=(tag,))
            self.tree.yview_moveto(1)
            self._log(f"[LIVE] {res['proxy']:22} {res['type']:12} {res['network']:12} "
                      f"{res['avg_latency']:>5}ms  Score:{res['score']:3}  {res['isp']}",tag)
            self._save_to_disk(res)
        else:
            self.stats["dead"]+=1; self._log(f"[DEAD] {res['proxy']}","dead")
        self._update_stats()

    def _scan_done(self,done,total):
        self.running=False; self.progress_var.set(100)
        self.prog_label.config(text=f"DONE {done}/{total}")
        self.status_label.config(text="● DONE",fg=ACCENT)
        self.global_status.config(text="● IDLE",fg=MUTED)
        self.start_btn.config(state="normal"); self.stop_btn.config(state="disabled")
        live=self.stats["live"]; rate=(live/done*100) if done else 0
        self._log(f"Done: {live}/{done} live ({rate:.1f}%) | "
                  f"Elite:{self.stats['elite']} Anon:{self.stats['anon']} Resid:{self.stats['res']}","info")

    def _save_to_disk(self,res):
        t,n=res["type"],res["network"]; sd=self.save_dir_var.get()
        line=(f"[LIVE] {res['proxy']} | {t} | {n} | {res['avg_latency']}ms | "
              f"Score: {res['score']} | ISP: {res['isp']} | "
              f"Google: {'✅' if res['google'] else '❌'} CF: {'✅' if res['cloudflare'] else '❌'}\n")
        with self.save_lock:
            with open(os.path.join(sd,f"{t}_{n}.txt"),"a",encoding="utf-8") as f: f.write(res["proxy"]+"\n")
            with open(os.path.join(sd,"ALL_PROXY.txt"),"a",encoding="utf-8") as f: f.write(res["proxy"]+"\n")
            with open(os.path.join(sd,"Full_data_proxy.txt"),"a",encoding="utf-8") as f: f.write(line)

if __name__=="__main__":
    root=tk.Tk()
    app=ProxyHunterApp(root)
    root.mainloop()
