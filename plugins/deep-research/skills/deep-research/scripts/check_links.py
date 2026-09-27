#!/usr/bin/env python3
"""Check that every URL in a report's sources section resolves.

    python3 check_links.py report.md [--timeout 15]

A URL is ok (2xx or 3xx), blocked (the site refuses scripts: 401, 403, 405,
429, 451; the page may well exist, open it by hand or rely on the verifiers
who opened it), or dead (404, 410, DNS failure, timeout). A TLS certificate error is
unchecked: it usually means this Python has no CA certificates installed, not
that the link is broken. Exit 1 if any URL is dead.
"""

import argparse
import re
import ssl
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BLOCKED = {401, 403, 405, 429, 451}
UA = 'Mozilla/5.0 (research link check)'
# a URL may contain one level of balanced parentheses (Wikipedia: .../Python_(language))
URL_RE = r'https?://(?:[^\s()<>\]]|\([^\s()<>]*\))+'


def sources_urls(text: str) -> dict:
    """{number: url} from lines like "[3] ... https://..." anywhere in the text."""
    out = {}
    for m in re.finditer(r'^\s*\[(\d+)\].*?(' + URL_RE + ')', text, flags=re.M):
        out.setdefault(int(m.group(1)), m.group(2).rstrip('.,;'))
    return out


def status(url: str, timeout: float) -> int:
    def fetch(method):
        req = urllib.request.Request(url, method=method, headers={'User-Agent': UA})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code
    code = fetch('HEAD')
    if code >= 400:
        code = fetch('GET')  # many servers reject HEAD from scripts (403, 404, 405, 400, 501)
    return code


def classify(url: str, timeout: float) -> tuple:
    try:
        code = status(url, timeout)
    except Exception as e:  # DNS, timeout: the link does not work from here
        if isinstance(getattr(e, 'reason', e), ssl.SSLCertVerificationError):
            return 'unchecked', 'TLS certificate not verified by this Python'
        return 'dead', str(e)[:80]
    if 200 <= code < 400:
        return 'ok', str(code)
    if code in BLOCKED:
        return 'blocked', str(code)
    return 'dead', str(code)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('report')
    ap.add_argument('--timeout', type=float, default=15)
    a = ap.parse_args()
    urls = sources_urls(Path(a.report).read_text(encoding='utf-8'))
    if not urls:
        print('No URLs found in the sources section.')
        sys.exit(0)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = dict(zip(urls, pool.map(lambda u: classify(u, a.timeout), urls.values())))
    dead = False
    for n in sorted(results):
        kind, detail = results[n]
        dead |= kind == 'dead'
        print(f'[{n}] {kind:7} {detail:>5}  {urls[n]}')
    blocked = [n for n, (k, _) in results.items() if k == 'blocked']
    if blocked:
        print(f'Check by hand (site refuses scripts): {sorted(blocked)}')
    if any(k == 'unchecked' for k, _ in results.values()):
        print('TLS certificate errors: this Python may lack CA certificates '
              '(python.org installer on macOS: run "Install Certificates.command").')
    print('FAILED: dead links' if dead else 'PASSED')
    sys.exit(1 if dead else 0)


if __name__ == '__main__':
    main()
