#!/usr/bin/env python3
"""Fetch the raw text of one page from this machine, the way a person's browser would.

    python3 fetch_raw.py URL [--out FILE] [--min-delay 4] [--max-delay 12] [--timeout 30]
    python3 fetch_raw.py URL --encode-only

The step between cloud fetch tools and the user's own browser. Cloud tools run on
foreign data-center IPs; many Russian sites refuse them, and their fetchers do not
trust the Russian Trusted Root CA that banks and state sites use. This script runs
where the user is, so it gets the user's network route.

- Non-ASCII URLs are encoded (IDNA host, percent-encoded path and query).
- Requests to one host are spaced by a random pause, shared between parallel
  collectors through a lock file, so a run never hammers a site.
- If the normal certificate check fails, the page is retried trusting the bundled
  Russian Trusted Root CA (fingerprint pinned below) and the summary says so.
- A 4xx page that has real content (tadviser answers 404 with the article) is kept.
- A redirect from https to plain http on the same host is followed over https:
  egrul.nalog.ru sends / to http://, and port 80 there is closed.
- On a network failure or a refusal the summary says which network interface the
  site's address goes through. A VPN interface means the domain is missing from
  the VPN's split-tunnel exceptions; the hint names the domain to add.

Prints one JSON line: url, final_url, status, verdict, chars, title, tls, out, hint,
and on network or blocked also route: ip, interface, vpn, tcp (port open or not).
verdict: ok | not_found | antibot | blocked | network | tls | error.
Exit 0 on ok, 1 otherwise. The text goes to --out (a temp file by default).
"""

import argparse
import base64
import gzip
import hashlib
import json
import os
import random
import re
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib

try:
    import fcntl  # Unix only; on Windows pacing still works within one process
except ImportError:
    fcntl = None
from html.parser import HTMLParser
from pathlib import Path

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36')
HEADERS = {
    'User-Agent': UA,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.7,en;q=0.6',
    'Accept-Encoding': 'gzip, deflate',
}
CERTS = Path(__file__).resolve().parent.parent / 'certs'
# Mintsifry root and two intermediates signed by it: some servers (rosstat.gov.ru) do not send the
# intermediate. Sub CA from gu-st.ru expires 2027-03-06, subca_ssl_rsa2024 from nuc-cdp expires 2029-07-19.
RU_CA = {CERTS / 'russian_trusted_root_ca.pem': 'd26d2d0231b7c39f92cc738512ba54103519e4405d68b5bd703e9788ca8ecf31',
         CERTS / 'russian_trusted_sub_ca.pem': 'bbbde2103e790b999ec62bd03cf625a5a2e7c316e10afe6a490eedead8b3fd9b',
         CERTS / 'russian_trusted_sub_ca_2024.pem': '2155785036c900dbb5f1bb2a1569c80c55595bd6bf94867a29bbddbc7d88a3f2'}
PACE_FILE = Path(tempfile.gettempdir()) / 'deep_research_fetch_pace.json'
ANTIBOT = re.compile(
    r'captcha|ddos-guard|qrator|servicepipe|variti|checking your browser|just a moment|'
    r'enable javascript|проверяем браузер|вы не робот|не с ботом|подтвердите, что вы', re.I)
BLOCKED = {401, 403, 405, 418, 429, 451}
VPN_IFACE = re.compile(r'^(utun|tun|tap|wg|awg|ppp|ipsec|gpd|zt)\d*', re.I)
HINTS = {
    'network': 'Connection refused or timed out. Open it in the user\'s browser.',
    'antibot': 'Bot check page, not the content. Open it in the user\'s browser (see method.md).',
    'blocked': 'The site refused a script. Open it in the user\'s browser (see method.md).',
    'tls': 'Certificate not trusted even with the Russian root CA. Open it in the user\'s browser.',
    'not_found': 'The page does not exist at this URL. Search for its new address.',
}


def encode_url(url: str) -> str:
    """IDNA-encode the host and percent-encode non-ASCII in path, query and fragment."""
    p = urllib.parse.urlsplit(url.strip())
    host = p.hostname or ''
    try:
        host = host.encode('idna').decode('ascii')
    except UnicodeError:
        pass
    netloc = host + (f':{p.port}' if p.port else '')
    safe = "/:@!$&'()*+,;=%-._~?"
    return urllib.parse.urlunsplit((
        p.scheme, netloc, urllib.parse.quote(p.path, safe=safe),
        urllib.parse.quote(p.query, safe=safe), urllib.parse.quote(p.fragment, safe=safe)))


def ru_ca_ok() -> bool:
    """The bundled CA files exist and are the pinned certificates."""
    return all(f.exists() and hashlib.sha256(ssl.PEM_cert_to_DER_cert(f.read_text())).hexdigest() == pin
               for f, pin in RU_CA.items())


def ssl_context(with_ru_ca: bool) -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if Path('/etc/ssl/cert.pem').exists():  # macOS system roots; python.org builds ship none
        ctx.load_verify_locations('/etc/ssl/cert.pem')
    if with_ru_ca:
        for f in RU_CA:
            ctx.load_verify_locations(str(f))
    return ctx


def pace(host: str, min_delay: float, max_delay: float) -> None:
    """Wait so that requests to one host are min..max seconds apart, across processes."""
    PACE_FILE.touch(exist_ok=True)
    with open(PACE_FILE, 'r+') as f:
        if fcntl:
            fcntl.flock(f, fcntl.LOCK_EX)
        try:
            state = json.loads(f.read() or '{}')
        except ValueError:
            state = {}
        now = time.time()
        slot = max(now, state.get(host, 0) + random.uniform(min_delay, max_delay))
        state[host] = slot
        state = {h: t for h, t in state.items() if t > now - 3600}
        f.seek(0), f.truncate(), f.write(json.dumps(state))
    time.sleep(max(0.0, slot - now))


class TextExtractor(HTMLParser):
    SKIP = {'script', 'style', 'noscript', 'svg', 'template', 'iframe'}
    BLOCK = {'p', 'div', 'br', 'li', 'tr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'section',
             'article', 'header', 'footer', 'table', 'ul', 'ol', 'blockquote', 'pre', 'dd', 'dt'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.title, self._skip, self._in_title = [], '', 0, False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag == 'title':
            self._in_title = True
        elif tag in self.BLOCK:
            self.parts.append('\n')
        elif tag in ('td', 'th'):
            self.parts.append(' | ')

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        elif tag == 'title':
            self._in_title = False
        elif tag in self.BLOCK:
            self.parts.append('\n')

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self._skip:
            self.parts.append(data)


def html_to_text(html: str) -> tuple:
    """(title, text) with scripts dropped and blank runs collapsed."""
    p = TextExtractor()
    p.feed(html)
    text = re.sub(r'[ \t\xa0]+', ' ', ''.join(p.parts))
    text = re.sub(r'\n\s*\n\s*', '\n\n', text).strip()
    return ' '.join(p.title.split()), text


def decode(body: bytes, content_type: str) -> str:
    m = re.search(r'charset=([\w-]+)', content_type, re.I) or \
        re.search(rb'<meta[^>]+charset=["\']?([\w-]+)', body[:4096], re.I)
    enc = m.group(1) if m else 'utf-8'
    enc = enc.decode() if isinstance(enc, bytes) else enc
    for e in (enc, 'utf-8', 'cp1251'):
        try:
            return body.decode(e)
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode('utf-8', 'replace')


def verdict(status: int, title: str, text: str) -> str:
    """Classify a response that arrived. Short pages with bot-check markers are antibot."""
    probe = title + ' ' + text[:3000]
    if len(text) < 2000 and ANTIBOT.search(probe):
        return 'antibot'
    if status in BLOCKED:
        return 'blocked' if len(text) < 1500 else 'ok'
    if status in (404, 410):
        return 'not_found' if len(text) < 1500 else 'ok'
    if status >= 300:  # a redirect still unresolved here is a loop, not a page
        return 'error'
    return 'ok' if text.strip() else 'antibot'


def https_upgrade(old_url: str, new_url: str) -> str:
    """The redirect target, kept on https when the site downgrades to http on the same host."""
    old, new = urllib.parse.urlsplit(old_url), urllib.parse.urlsplit(new_url)
    if old.scheme == 'https' and new.scheme == 'http' and old.hostname == new.hostname:
        upgraded = urllib.parse.urlunsplit(new._replace(scheme='https', netloc=new.netloc.replace(':80', '')))
        if upgraded != old_url:  # the same URL again would be a loop; then follow the site
            return upgraded
    return new_url


class KeepHttps(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, code, msg, headers, https_upgrade(req.full_url, newurl))


def request(url: str, timeout: float, ctx: ssl.SSLContext):
    req = urllib.request.Request(url, headers=HEADERS)
    # cookies kept across redirects: some sites (cntd.ru) set one and redirect to the same URL
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(), KeepHttps(),
                                         urllib.request.HTTPSHandler(context=ctx))
    try:
        r = opener.open(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        r = e
    body = r.read()
    enc = (r.headers.get('Content-Encoding') or '').lower()
    if enc == 'gzip':
        body = gzip.decompress(body)
    elif enc == 'deflate':
        body = zlib.decompress(body, -zlib.MAX_WBITS)
    return r.status if hasattr(r, 'status') else r.code, r.geturl(), r.headers.get('Content-Type', ''), body


DOH_URL = 'https://common.dot.dns.yandex.net/dns-query'  # a Russian resolver: some .gov.ru names fail abroad


def dns_query(host: str) -> bytes:
    """A-record query in DNS wire format (RFC 1035), id 0 as RFC 8484 recommends."""
    qname = b''.join(bytes([len(p)]) + p for p in host.encode('idna').split(b'.')) + b'\0'
    return b'\0\0\x01\0\0\x01\0\0\0\0\0\0' + qname + b'\0\x01\0\x01'


def parse_a_records(msg: bytes) -> list:
    """IPv4 addresses from the answer section of a DNS response."""
    ancount = int.from_bytes(msg[6:8], 'big')
    i = 12
    while msg[i]:  # skip the question name
        i += msg[i] + 1
    i += 5
    ips = []
    for _ in range(ancount):
        i += 2 if msg[i] >= 0xC0 else msg[i:].index(0) + 1  # name: pointer or labels
        rtype, rdlen = int.from_bytes(msg[i:i + 2], 'big'), int.from_bytes(msg[i + 8:i + 10], 'big')
        i += 10
        if rtype == 1 and rdlen == 4:
            ips.append('.'.join(str(b) for b in msg[i:i + 4]))
        i += rdlen
    return ips


def doh_resolve(host: str, timeout: float = 10) -> list:
    """Resolve through Yandex DNS-over-HTTPS. It speaks only HTTP/2, which urllib lacks, so curl."""
    q = base64.urlsafe_b64encode(dns_query(host)).decode().rstrip('=')
    try:
        out = subprocess.run(['curl', '-s', '--http2', '--max-time', str(timeout),
                              '-H', 'accept: application/dns-message', f'{DOH_URL}?dns={q}'],
                             capture_output=True, timeout=timeout + 5).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return parse_a_records(out) if len(out) > 12 else []


def pin_host(host: str, ip: str) -> None:
    """Make this process connect to ip for host; SNI and the Host header stay the name."""
    orig = socket.getaddrinfo

    def getaddrinfo(h, *args, **kw):
        return orig(ip if h == host else h, *args, **kw)
    socket.getaddrinfo = getaddrinfo


def route_interface(ip: str) -> str:
    """The network interface the OS sends ip through ('' when it cannot tell)."""
    cmd = (['route', '-n', 'get', ip] if sys.platform == 'darwin'
           else ['ip', 'route', 'get', ip] if sys.platform.startswith('linux') else None)
    if not cmd:
        return ''
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return ''
    m = re.search(r'interface:\s*(\S+)', out) or re.search(r'\bdev\s+(\S+)', out)
    return m.group(1) if m else ''


def tcp_open(ip: str, port: int, timeout: float = 5) -> bool:
    try:
        socket.create_connection((ip, port), timeout=timeout).close()
        return True
    except OSError:
        return False


def diagnose_route(url: str) -> dict:
    """Where the site's address goes and whether its port answers at all."""
    p = urllib.parse.urlsplit(url)
    try:
        ip = socket.getaddrinfo(p.hostname, None, socket.AF_INET)[0][4][0]
    except (socket.gaierror, OSError, IndexError):
        return {}
    iface = route_interface(ip)
    return {'ip': ip, 'interface': iface, 'vpn': bool(VPN_IFACE.match(iface)),
            'tcp': tcp_open(ip, p.port or (443 if p.scheme == 'https' else 80))}


def route_hint(verdict: str, host: str, route: dict) -> str:
    """Replace the guess about foreign IPs with what the route shows."""
    if not route:
        return ''
    where = f'{route["ip"]} goes through {route["interface"] or "an unknown interface"}'
    if route['vpn']:
        return (f'{where}, a VPN interface: the request left the country. Add {host} to the VPN\'s '
                f'split-tunnel exceptions (sites that bypass the VPN), reconnect, and retry. '
                f'Until then, the user\'s browser.')
    if verdict == 'network' and route['tcp']:
        return (f'{where}, outside the VPN, and the port accepts connections: the server is slow or this '
                f'URL hangs. Retry once with a longer --timeout, then the user\'s browser.')
    if verdict == 'network':
        return (f'{where}, outside the VPN, and the port does not answer: the site is down or blocks this '
                f'network too. Open it in the user\'s browser.')
    return ''


def is_cert_error(e: Exception) -> bool:
    reason = getattr(e, 'reason', e)
    return isinstance(reason, ssl.SSLCertVerificationError)


def fetch(url: str, out: Path, timeout: float, min_delay: float, max_delay: float) -> dict:
    url = encode_url(url)
    res = {'url': url, 'final_url': url, 'status': 0, 'verdict': 'error', 'chars': 0,
           'title': '', 'tls': 'default', 'out': str(out), 'hint': ''}
    host = urllib.parse.urlsplit(url).hostname or ''
    pace(host, min_delay, max_delay)
    try:
        socket.getaddrinfo(host, None)
    except socket.gaierror:
        try:
            ips = doh_resolve(host)
        except (OSError, ValueError, IndexError):
            ips = []
        if ips:
            pin_host(host, ips[0])
            res['dns'] = f'doh:{ips[0]}'
    try:
        try:
            status, final, ctype, body = request(url, timeout, ssl_context(False))
        except urllib.error.URLError as e:
            if not (is_cert_error(e) and ru_ca_ok()):
                raise
            res['tls'] = 'russian_trusted_root_ca'
            status, final, ctype, body = request(url, timeout, ssl_context(True))
    except urllib.error.URLError as e:
        res['verdict'] = 'tls' if is_cert_error(e) else 'network'
        res['hint'] = f'{HINTS[res["verdict"]]} ({e.reason})'
        if isinstance(e.reason, socket.gaierror):
            res['hint'] = ('The name did not resolve. Some Russian state domains do not resolve '
                           'through foreign DNS (1.1.1.1, 8.8.8.8 behind a VPN); try the user\'s browser. '
                           f'({e.reason})')
        elif res['verdict'] == 'network':
            add_route(res, url, host, str(e.reason))
        return res
    except (socket.timeout, TimeoutError, ConnectionError) as e:
        res['verdict'] = 'network'
        add_route(res, url, host, str(e))
        return res
    res.update(status=status, final_url=final)
    if 'pdf' in ctype.lower() or body[:5] == b'%PDF-':
        out = out.with_suffix('.pdf')
        out.write_bytes(body)
        res.update(out=str(out), verdict='ok' if status < 400 else 'error', chars=len(body),
                   hint='PDF saved; read it with the Read tool or a PDF skill.')
        return res
    title, text = html_to_text(decode(body, ctype))
    out.write_text(f'URL: {final}\nTitle: {title}\nHTTP: {status}\n\n{text}\n', encoding='utf-8')
    res.update(title=title[:120], chars=len(text), verdict=verdict(status, title, text))
    res['hint'] = HINTS.get(res['verdict'], '')
    if res['verdict'] == 'blocked':
        route = diagnose_route(final)
        if route:
            res['route'] = route
            if route['vpn']:  # a 403 or 451 from abroad is often a geo block
                res['hint'] = route_hint('blocked', urllib.parse.urlsplit(final).hostname, route)
    return res


def add_route(res: dict, url: str, host: str, reason: str) -> None:
    """Attach the route diagnosis and the hint it implies to a network failure."""
    route = diagnose_route(url)
    if route:
        res['route'] = route
    res['hint'] = f'{route_hint("network", host, route) or HINTS["network"]} ({reason})'


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('url')
    ap.add_argument('--out', type=Path, help='where to write the text (default: a temp file)')
    ap.add_argument('--timeout', type=float, default=30)
    ap.add_argument('--min-delay', type=float, default=4, help='seconds between requests to one host')
    ap.add_argument('--max-delay', type=float, default=12)
    ap.add_argument('--encode-only', action='store_true', help='print the encoded URL and exit')
    a = ap.parse_args(argv)
    if a.encode_only:
        print(encode_url(a.url))
        return 0
    out = a.out or Path(tempfile.mkstemp(prefix='fetch_raw_', suffix='.txt')[1])
    res = fetch(a.url, out, a.timeout, a.min_delay, a.max_delay)
    print(json.dumps(res, ensure_ascii=False))
    return 0 if res['verdict'] == 'ok' else 1


if __name__ == '__main__':
    sys.exit(main())
