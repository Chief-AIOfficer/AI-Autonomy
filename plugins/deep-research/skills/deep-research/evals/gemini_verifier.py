#!/usr/bin/env python3
"""
Run the skill's phase 6 verifier prompt on Gemini (Google Search + URL
context grounding) over the verifier eval cases: a second model family for
comparison, not part of the skill's mandatory flow.

  python3 gemini_verifier.py --model gemini-3.1-pro-preview --out results.jsonl
  python3 score.py verifier-score --results results.jsonl

Key: the GEMINI_API_KEY environment variable.
Proxy: GEMINI_PROXY is not supported here; Gemini must be reachable directly.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score  # noqa: E402

BASE = 'https://generativelanguage.googleapis.com/v1beta'
NOTE = ('\n\nTool note for this run: you have Google Search and URL context instead of '
        'WebFetch/BrightData/Tavily; open the cited URL with URL context first, then search. '
        'Reply with the JSON line only.')


def api_key() -> str:
    key = os.environ.get('GEMINI_API_KEY')
    if not key:
        sys.exit('Set the GEMINI_API_KEY environment variable')
    return key


def ask(model: str, prompt: str, key: str, retries: int = 2) -> dict:
    body = json.dumps({'contents': [{'role': 'user', 'parts': [{'text': prompt + NOTE}]}],
                       'tools': [{'google_search': {}}, {'url_context': {}}]}).encode()
    for attempt in range(retries + 1):
        req = urllib.request.Request(f'{BASE}/models/{model}:generateContent', data=body,
                                     headers={'x-goog-api-key': key, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.loads(r.read())
        except Exception as e:  # network or HTTP error: report, do not crash the batch
            if attempt == retries:
                return {'error': str(e)[:300]}
            continue
        parts = d.get('candidates', [{}])[0].get('content', {}).get('parts', [])
        text = ''.join(p.get('text', '') for p in parts)
        m = re.search(r'\{.*"verdict".*\}', text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        if attempt == retries:
            return {'raw': text[:500]}
    return {'error': 'unreachable'}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--model', default='gemini-3.1-pro-preview')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    key = api_key()
    with open(a.out, 'a', encoding='utf-8') as f:
        for c in score.load_jsonl(HERE / 'verifier_cases.jsonl'):
            t0 = time.time()
            r = ask(a.model, score.verifier_prompt(c), key)
            r.setdefault('id', c['id'])
            r['seconds'] = round(time.time() - t0, 1)
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
            f.flush()
            print(c['id'], r.get('verdict'), r.get('error', ''), flush=True)


if __name__ == '__main__':
    main()
