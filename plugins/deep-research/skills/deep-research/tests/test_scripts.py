#!/usr/bin/env python3
"""Tests for the skill's scripts (standard library unittest, no network)."""

import datetime as dt
import os
import re
import sys
import tempfile
import time
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import check_links  # noqa: E402
import fetch_raw  # noqa: E402
import init_run  # noqa: E402
import md_to_html  # noqa: E402
import validate_report  # noqa: E402

SOURCES = '\n'.join(f'[{i}] Org ({2025}). "Title {i}". Pub. https://example.org/{i} (accessed 2026-09-27)'
                    for i in range(1, 4))


def report(answer_words=250, extra='', drop=None, heads=None):
    heads = heads or {
        'answer': 'Главное', 'method_intro': 'Вопрос и метод', 'findings': 'Находки',
        'conclusions': 'Выводы', 'limitations': 'Ограничения', 'sources': 'Источники', 'method': 'Метод'}
    body = {
        'answer': ' '.join(['слово'] * answer_words) + ' [1].',
        'method_intro': 'Вопрос и рамки [2].',
        'findings': '### Находка первая\n\nФакт [3] и ещё факт [1, 2].' + extra,
        'conclusions': 'Что следует.',
        'limitations': 'Не найдено этим поиском: запросы такие-то.',
        'sources': SOURCES,
        'method': 'Режим standard.',
    }
    return '# Отчёт\n\n' + '\n\n'.join(f'## {heads[k]}\n\n{body[k]}' for k in heads if k != drop) + '\n'


class TestInitRun(unittest.TestCase):
    def test_creates_folder_with_brief_and_suffix_on_repeat(self):
        with tempfile.TemporaryDirectory() as d:
            day = dt.date(2026, 9, 27)
            a = init_run.create_run('Рынок ИИ: цены / 2026', Path(d), 'deep', day)
            b = init_run.create_run('Рынок ИИ: цены / 2026', Path(d), 'deep', day)
            self.assertEqual(a.name, 'Рынок_ИИ_цены_2026_20260927')
            self.assertEqual(b.name, a.name + '_2')
            self.assertIn('Mode: deep', (a / '_work' / '01_brief.md').read_text(encoding='utf-8'))
            self.assertTrue((a / '_work' / '00_run.json').is_file())
            self.assertEqual(sorted(p.name for p in a.iterdir()), ['_work'])

    def test_parent_dir_priority(self):
        os.environ['DEEP_RESEARCH_DIR'] = '/tmp/env-dir'
        try:
            self.assertEqual(init_run.parent_dir('/tmp/cli'), Path('/tmp/cli'))
            self.assertEqual(init_run.parent_dir(None), Path('/tmp/env-dir'))
        finally:
            del os.environ['DEEP_RESEARCH_DIR']
        self.assertEqual(init_run.parent_dir(None), Path.home() / 'Documents' / 'Research')


class TestValidate(unittest.TestCase):
    def test_russian_report_passes(self):
        errors, warnings, _ = validate_report.validate(report())
        self.assertEqual(errors, [], errors)
        self.assertEqual(warnings, [], warnings)

    def test_english_and_bilingual_headings(self):
        heads = {'answer': 'Answer. Главное', 'method_intro': 'Question and method', 'findings': 'Findings',
                 'conclusions': 'Conclusions', 'limitations': 'Limitations', 'sources': 'Sources', 'method': 'Method'}
        errors, _, _ = validate_report.validate(report(heads=heads))
        self.assertEqual(errors, [], errors)

    def test_missing_section(self):
        errors, _, _ = validate_report.validate(report(drop='limitations'))
        self.assertTrue(any('limitations' in e for e in errors))

    def test_citation_without_source(self):
        errors, _, _ = validate_report.validate(report(extra=' Ещё [7].'))
        self.assertTrue(any('[7]' in e for e in errors), errors)

    def test_placeholder(self):
        errors, _, _ = validate_report.validate(report(extra=' TODO дописать.'))
        self.assertTrue(any('placeholder' in e for e in errors))

    def test_length_ceiling(self):
        errors, _, _ = validate_report.validate(report(extra=' ' + ' '.join(['слово'] * 3000)), 'quick')
        self.assertTrue(any('ceiling' in e for e in errors))

    def test_short_answer_warns(self):
        _, warnings, _ = validate_report.validate(report(answer_words=40))
        self.assertTrue(any('answer' in w for w in warnings))

    def test_heading_with_question_word_is_not_method_intro(self):
        self.assertEqual(validate_report.classify('Ответ на вопрос'), 'answer')
        self.assertEqual(validate_report.classify('Ограничения и открытый вопрос'), 'limitations')
        self.assertEqual(validate_report.classify('Вопрос и метод'), 'method_intro')


class TestCheckLinks(unittest.TestCase):
    def test_extracts_urls_from_sources(self):
        urls = check_links.sources_urls(SOURCES)
        self.assertEqual(urls[2], 'https://example.org/2')

    def test_url_with_parentheses(self):
        urls = check_links.sources_urls('[1] W. https://en.wikipedia.org/wiki/Python_(language) (accessed)\n'
                                        '[2] [Title](https://example.org/a).\n')
        self.assertEqual(urls[1], 'https://en.wikipedia.org/wiki/Python_(language)')
        self.assertEqual(urls[2], 'https://example.org/a')

    def test_certificate_error_is_not_a_dead_link(self):
        import ssl
        import urllib.error
        orig = check_links.status

        def fail(url, t):
            raise urllib.error.URLError(ssl.SSLCertVerificationError('certificate verify failed'))
        try:
            check_links.status = fail
            self.assertEqual(check_links.classify('https://x.org', 1)[0], 'unchecked')
        finally:
            check_links.status = orig

    def test_classification(self):
        orig = check_links.status
        try:
            for code, kind in [(200, 'ok'), (301, 'ok'), (403, 'blocked'), (429, 'blocked'), (404, 'dead')]:
                check_links.status = lambda url, t, c=code: c
                self.assertEqual(check_links.classify('https://x.org', 1)[0], kind)
        finally:
            check_links.status = orig


class TestFetchRaw(unittest.TestCase):
    def test_encode_url_cyrillic_path_query_and_host(self):
        self.assertEqual(fetch_raw.encode_url('https://www.tadviser.ru/index.php/Компания:Центр_(РНКО)?q=НКО'),
                         'https://www.tadviser.ru/index.php/%D0%9A%D0%BE%D0%BC%D0%BF%D0%B0%D0%BD%D0%B8%D1%8F:'
                         '%D0%A6%D0%B5%D0%BD%D1%82%D1%80_(%D0%A0%D0%9D%D0%9A%D0%9E)?q=%D0%9D%D0%9A%D0%9E')
        self.assertEqual(fetch_raw.encode_url('https://кремль.рф/a'), 'https://xn--e1ajeds9e.xn--p1ai/a')

    def test_encode_url_keeps_already_encoded(self):
        u = 'https://ru.wikipedia.org/wiki/%D0%A1%D0%BF%D0%B8%D1%81%D0%BE%D0%BA?a=1&b=%20'
        self.assertEqual(fetch_raw.encode_url(u), u)

    def test_verdicts(self):
        long = 'текст статьи ' * 300
        self.assertEqual(fetch_raw.verdict(200, 'Статья', long), 'ok')
        self.assertEqual(fetch_raw.verdict(200, 'Проверяем браузер', 'Подождите'), 'antibot')
        self.assertEqual(fetch_raw.verdict(200, '', ''), 'antibot')
        self.assertEqual(fetch_raw.verdict(403, '403 Forbidden', 'nginx'), 'blocked')
        self.assertEqual(fetch_raw.verdict(404, 'Not found', 'нет'), 'not_found')
        self.assertEqual(fetch_raw.verdict(404, 'Платежный центр', long), 'ok')  # tadviser answers 404 with content
        self.assertEqual(fetch_raw.verdict(307, 'Redirecting', 'Redirecting to https://docs.cntd.ru/'), 'error')

    def test_html_to_text_drops_scripts_keeps_title_and_cells(self):
        title, text = fetch_raw.html_to_text(
            '<html><head><title> Банк  России </title><script>var x=1</script></head>'
            '<body><p>Первый&nbsp;абзац</p><table><tr><td>A</td><td>1</td></tr></table></body></html>')
        self.assertEqual(title, 'Банк России')
        self.assertIn('Первый абзац', text)
        self.assertIn('A | 1', text)
        self.assertNotIn('var x', text)

    def test_dns_wire_query_and_answer(self):
        q = fetch_raw.dns_query('council.gov.ru')
        self.assertIn(b'\x07council\x03gov\x02ru\x00\x00\x01\x00\x01', q)
        answer = lambda ip: b'\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04' + bytes(ip)
        cname = b'\xc0\x0c\x00\x05\x00\x01\x00\x00\x00\x3c\x00\x02\xc0\x0c'
        msg = b'\x00\x00\x81\x80\x00\x01\x00\x03\x00\x00\x00\x00' + q[12:] + cname + answer([95, 173, 132, 31]) + answer([95, 173, 132, 73])
        self.assertEqual(fetch_raw.parse_a_records(msg), ['95.173.132.31', '95.173.132.73'])

    def test_https_kept_on_downgrade_redirect(self):
        up = fetch_raw.https_upgrade
        self.assertEqual(up('https://egrul.nalog.ru/', 'http://egrul.nalog.ru/index.html'),
                         'https://egrul.nalog.ru/index.html')
        self.assertEqual(up('https://a.ru/x', 'http://a.ru:80/y'), 'https://a.ru/y')
        self.assertEqual(up('https://a.ru/x', 'http://b.ru/x'), 'http://b.ru/x')  # other host: follow the site
        self.assertEqual(up('http://a.ru/x', 'http://a.ru/y'), 'http://a.ru/y')
        self.assertEqual(up('https://a.ru/x', 'http://a.ru/x'), 'http://a.ru/x')  # upgrading would loop

    def test_vpn_interfaces(self):
        for name in ('utun4', 'tun0', 'wg0', 'awg0', 'ppp0', 'ipsec0'):
            self.assertTrue(fetch_raw.VPN_IFACE.match(name), name)
        for name in ('en0', 'eth0', 'wlan0', 'bridge100', ''):
            self.assertFalse(fetch_raw.VPN_IFACE.match(name), name)

    def test_route_hints(self):
        vpn = {'ip': '194.226.26.36', 'interface': 'utun4', 'vpn': True, 'tcp': False}
        self.assertIn('split-tunnel exceptions', fetch_raw.route_hint('network', 'fas.gov.ru', vpn))
        self.assertIn('fas.gov.ru', fetch_raw.route_hint('blocked', 'fas.gov.ru', vpn))
        slow = {'ip': '213.24.64.183', 'interface': 'en0', 'vpn': False, 'tcp': True}
        self.assertIn('slow', fetch_raw.route_hint('network', 'egrul.nalog.ru', slow))
        dead = dict(slow, tcp=False)
        self.assertIn('does not answer', fetch_raw.route_hint('network', 'egrul.nalog.ru', dead))
        self.assertEqual(fetch_raw.route_hint('blocked', 'x.ru', slow), '')  # outside the VPN a 403 is the site's
        self.assertEqual(fetch_raw.route_hint('network', 'x.ru', {}), '')

    def test_route_interface_parses_macos_and_linux(self):
        outs = {'darwin': '   route to: 1.2.3.4\n  gateway: 10.0.0.1\n  interface: utun4\n      flags: <UP>',
                'linux': '1.2.3.4 dev wg0 table 51820 src 10.12.0.2 uid 0'}
        for platform, out in outs.items():
            with mock.patch.object(fetch_raw.sys, 'platform', platform), \
                 mock.patch.object(fetch_raw.subprocess, 'run', return_value=mock.Mock(stdout=out)):
                self.assertEqual(fetch_raw.route_interface('1.2.3.4'), 'utun4' if platform == 'darwin' else 'wg0')

    def test_bundled_ru_ca_matches_pin(self):
        self.assertTrue(fetch_raw.ru_ca_ok())

    def test_pace_spaces_requests_to_one_host(self):
        with tempfile.TemporaryDirectory() as d:
            fetch_raw.PACE_FILE = Path(d) / 'pace.json'
            t = time.time()
            fetch_raw.pace('example.ru', 0.3, 0.3)
            fetch_raw.pace('other.ru', 0.3, 0.3)
            self.assertLess(time.time() - t, 0.2)
            fetch_raw.pace('example.ru', 0.3, 0.3)
            self.assertGreaterEqual(time.time() - t, 0.29)


class TestMdToHtml(unittest.TestCase):
    TEMPLATE = '<html lang="{{lang}}"><title>{{title}}</title>{{kicker}}|{{meta}}|{{toc}}|{{content}}|{{footer}}</html>'

    def render(self, md):
        return md_to_html.render(md, self.TEMPLATE)

    def test_title_citations_and_sources_anchor(self):
        page = self.render(report())
        self.assertIn('<title>Отчёт</title>', page)
        self.assertIn('lang="ru"', page)
        self.assertIn('<a class="cite" href="#ref-3">[3]</a>', page)
        self.assertIn('id="ref-2"', page)
        self.assertIn('<section class="answer">', page)
        self.assertIn('<section class="sources">', page)
        self.assertIn('Содержание', page)

    def test_table_callout_list_escaping(self):
        md = ('# T\n\n## Находки\n\n| A | B |\n|---|---|\n| 1 | **2** |\n\n'
              '> [!warning] Осторожно\n> Текст <script>.\n\n- один\n  - вложенный\n- два\n\n'
              '`код <b>` и [ссылка](https://example.org).')
        page = self.render(md)
        self.assertIn('<table>', page)
        self.assertIn('<td><strong>2</strong></td>', page)
        self.assertIn('<div class="note warn"><div class="lbl">Осторожно</div>', page)
        self.assertIn('&lt;script&gt;', page)
        self.assertNotIn('<script>', page)
        self.assertEqual(page.count('<ul>'), 2)
        self.assertIn('<code>код &lt;b&gt;</code>', page)
        self.assertIn('<a href="https://example.org">ссылка</a>', page)

    def test_urls_with_underscores_and_parentheses(self):
        page = self.render('## Находки\n\nСм. https://site.org/_next_/a_b и '
                           '[вики](https://en.wikipedia.org/wiki/Python_(language)).')
        self.assertIn('<a href="https://site.org/_next_/a_b">https://site.org/_next_/a_b</a>', page)
        self.assertIn('<a href="https://en.wikipedia.org/wiki/Python_(language)">вики</a>.', page)
        self.assertNotIn('href="javascript', self.render('[x](javascript:alert.html) [y](notes/a.md)'))

    def test_front_matter_title(self):
        page = self.render('---\ntitle: "Из шапки"\ndate: 2026-09-27\n---\n\n## Главное\n\nТекст.')
        self.assertIn('<title>Из шапки</title>', page)
        self.assertIn('2026-09-27', page)

    def test_real_template_renders(self):
        tpl = (ROOT / 'templates' / 'report.html').read_text(encoding='utf-8')
        page = md_to_html.render(report(), tpl)
        self.assertNotIn('{{', page)


if __name__ == '__main__':
    unittest.main()
