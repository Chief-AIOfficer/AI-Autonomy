#!/usr/bin/env python3
"""Tests for evals/score.py and the integrity of the eval case files."""

import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

EVALS = Path(__file__).resolve().parent.parent / 'evals'
sys.path.insert(0, str(EVALS))
import score  # noqa: E402


class TestCaseFiles(unittest.TestCase):
    def test_case_counts(self):
        self.assertEqual(len(score.load_jsonl(EVALS / 'cases.jsonl')), 11)
        self.assertEqual(len(score.load_jsonl(EVALS / 'verifier_cases.jsonl')), 10)

    def test_case_fields_and_hints_compile(self):
        for c in score.load_jsonl(EVALS / 'cases.jsonl'):
            for k in ('id', 'origin', 'mode', 'question', 'key_facts', 'known_errors', 'expect', 'ground_truth'):
                self.assertIn(k, c, c.get('id'))
            self.assertIn(c['mode'], ('quick', 'standard', 'deep', 'ultradeep'))
            for it in c['key_facts'] + c['known_errors']:
                if it.get('hint'):
                    re.compile(it['hint'])

    def test_verifier_expected_verdicts_are_valid(self):
        allowed = {'confirmed', 'partial', 'misleading', 'refuted', 'not_verifiable'}
        for c in score.load_jsonl(EVALS / 'verifier_cases.jsonl'):
            self.assertTrue(set(c['expected']) <= allowed, c['id'])


class TestCheck(unittest.TestCase):
    def test_hints_found_and_known_error_flagged(self):
        case = score.get_case('E06')
        report = 'Неявные требования и синтез дают 45–50% провалов [1], лучшие ниже 68% [2]. Ранее писали 45-49% [3].'
        r = score.check(case, report)
        self.assertTrue(r['key_facts'][0]['hint_found'])
        self.assertTrue(r['known_errors'][0]['hint_found'])
        self.assertEqual(r['citations'], 3)

    def test_not_found_phrase(self):
        r = score.check(score.get_case('E11'), 'Замеров не найдено этим поиском (запросы: …).')
        self.assertTrue(r['not_found_phrase'])


class TestPrompts(unittest.TestCase):
    def test_judge_prompt_hides_fields_the_grader_should_not_see(self):
        p = score.judge_prompt(score.get_case('E02'), 'отчёт', 'coverage')
        self.assertIn('challenge_premise', p)
        self.assertNotIn('ground_truth', p)
        self.assertIn('## Отчёт', p)

    def test_verifier_prompt_has_claim_but_not_expected_verdict(self):
        case = score.get_case('V04', EVALS / 'verifier_cases.jsonl')
        p = score.verifier_prompt(case)
        self.assertIn(case['claim'], p)
        self.assertNotIn(case['why'], p)


class TestScoring(unittest.TestCase):
    def test_verifier_score(self):
        cases = score.load_jsonl(EVALS / 'verifier_cases.jsonl')
        res = score.verifier_score([{'id': 'V03', 'verdict': 'confirmed'}, {'id': 'V08', 'verdict': 'confirmed'}], cases)
        self.assertEqual((res['passed'], res['total']), (1, 2))
        self.assertIn('V01', res['missing'])

    def test_summary(self):
        with tempfile.TemporaryDirectory() as d:
            run = Path(d) / '20260926_test'
            for t, s in (('t1', 0.6), ('t2', 0.8)):
                (run / 'E01' / t).mkdir(parents=True)
                (run / 'E01' / t / 'grades.jsonl').write_text(
                    json.dumps({'grader': 'coverage', 'score': s}) + '\n', encoding='utf-8')
            text = score.summary(run)
            self.assertIn('| E01 |', text)
            self.assertIn('0.70', text)


if __name__ == '__main__':
    unittest.main()
