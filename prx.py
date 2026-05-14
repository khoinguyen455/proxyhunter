import requests
import socket
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
lock = threading.Lock()
TIMEOUT = 6
RETRY = 2
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
CF_TEST = "https://www.cloudflare.com/cdn-cgi/trace"
ASN_CHECK = "http://ip-api.com/json/{}?fields=16983568"
PROXY_STATUS = {
    'LIVE': 0,
    'DIE': 0,
    'DATACENTER': 0,
    'RESIDENTIAL': 0
}
def socket_check(proxy):
    try:
        host, port = proxy.split(":")
        socket.setdefaulttimeout(2)
        s = socket.socket()
        s.connect((host, int(port)))
        s.close()
        return True
    except:
        return False
def request_proxy(url, proxy):
    proxies = {
        "http": f"http://{proxy}",
        "https": f"http://{proxy}"
    }
    try:
        start = time.time()
        r = requests.get(url, proxies=proxies, timeout=TIMEOUT)
        latency = (time.time() - start) * 1000
        return r, latency
    except:
        return None, None
def detect_type(text):
    if "X-Forwarded-For" in text or "Via" in text:
        return "ANONYMOUS"
    if "REMOTE_ADDR" in text:
        return "TRANSPARENT"
    return "ELITE"
def detect_network(ip):
    try:
        r = requests.get(ASN_CHECK.format(ip), timeout=5).json()
        org = r.get("org", "").lower()
        isp = r.get("isp", "").lower()
        if r.get("proxy", False) or r.get("hosting", False):
            return "DATACENTER", isp
        dc_keywords = [
            "amazon", "google", "ovh",
            "digitalocean", "microsoft", "vultr"
        ]
        if any(x in org for x in dc_keywords):
            return "DATACENTER", isp
        return "RESIDENTIAL", isp
    except:
        return "UNKNOWN", "UNKNOWN"
def calculate_score(proxy_type, network, google_ok, cf_ok, latency):
    score = 0
    score += 10
    if proxy_type == "ELITE":
        score += 30
    elif proxy_type == "ANONYMOUS":
        score += 20
    elif proxy_type == "TRANSPARENT":
        score += 5
    if network == "RESIDENTIAL":
        score += 25
    elif network == "DATACENTER":
        score += 10
    if google_ok:
        score += 10
    if cf_ok:
        score += 10
    if latency < 300:
        score += 15
    elif latency < 600:
        score += 10
    elif latency < 1000:
        score += 5
    return score
def check_proxy(proxy):
    result = {
        "proxy": proxy,
        "status": "DEAD"
    }
    if not socket_check(proxy):
        return result
    latencies = []
    judge_used = None
    proxy_type = "UNKNOWN"
    for judge in SSL_JUDGES:
        r, latency = request_proxy(judge, proxy)
        if r and r.status_code == 200:
            judge_used = judge
            latencies.append(latency)
            proxy_type = detect_type(r.text)
            break
    if not judge_used:
        for judge in HTTP_JUDGES:
            r, latency = request_proxy(judge, proxy)
            if r and r.status_code == 200:
                judge_used = judge
                latencies.append(latency)
                proxy_type = detect_type(r.text)
                break
    if not judge_used:
        return result
    google_ok = False
    r, latency = request_proxy(GOOGLE_TEST, proxy)
    if r and r.status_code == 204:
        google_ok = True
        latencies.append(latency)
    cf_ok = False
    r, latency = request_proxy(CF_TEST, proxy)
    if r and "fl=" in r.text:
        cf_ok = True
        latencies.append(latency)
    avg_latency = int(statistics.mean(latencies)) if latencies else 0
    ip = proxy.split(":")[0]
    network_type, isp = detect_network(ip)
    score = calculate_score(proxy_type, network_type, google_ok, cf_ok, avg_latency)
    result.update({
        "status": "LIVE",
        "type": proxy_type,
        "network": network_type,
        "google": google_ok,
        "cloudflare": cf_ok,
        "judge": judge_used,
        "avg_latency": avg_latency,
        "isp": isp,
        "score": score
    })
    return result
def save_proxy(res):
    proxy = res['proxy']
    proxy_type = res['type']        # ELITE / TRANSPARENT / ANONYMOUS
    network = res['network']        # DATACENTER / RESIDENTIAL / UNKNOWN
    filename = f"{proxy_type}_{network}.txt"
    full_line = (
        f"[LIVE] {res['proxy']} | "
        f"{res['type']} | "
        f"{res['network']} | "
        f"{res['avg_latency']}ms | "
        f"Score: {res['score']} | "
        f"ISP: {res['isp']} | "
        f"Google: {'✅' if res['google'] else '❌'} "
        f"CF: {'✅' if res['cloudflare'] else '❌'}"
    )
    with lock:
        with open(filename, "a") as f:
            f.write(proxy + "\n")
        with open("ALL_PROXY.txt", "a") as f:
            f.write(proxy + "\n")
        with open('Full_data_proxy.txt', 'a', encoding='utf-8') as f:
            f.write(full_line + '\n')
def run(proxies):
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(check_proxy, p.strip()) for p in proxies]
        for future in as_completed(futures):
            res = future.result()
            if res["status"] == "LIVE":
                print(f"[LIVE] {res['proxy']} | {res['type']} | {res['network']} | {res['avg_latency']}ms | Score: {res['score']} | ISP: {res['isp']} | Google: {'✅' if res['google'] else '❌'} CF: {'✅' if res['cloudflare'] else '❌'} ")
                save_proxy(res)
            else:
                print(f"{res['proxy']} DEAD")
if __name__ == "__main__":
    with open("proxy.txt") as f:
        proxies = f.readlines()
    run(proxies)