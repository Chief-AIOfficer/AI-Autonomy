"""Тесты scripts/check.py. Запуск: python3 -m unittest discover -s tests"""

import io
import os
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import check  # noqa: E402

EM = chr(0x2014)  # emdash-ok: символ как объект теста
EN = chr(0x2013)


def rules(text, channel="post"):
    return [f["rule"] for f in check.check(text, channel)]


def errors(text, channel="post"):
    return [f["rule"] for f in check.check(text, channel) if f["level"] == "error"]


class Dashes(unittest.TestCase):
    def test_em_dash_is_error_in_every_channel(self):
        for ch in ("post", "docx", "deck"):
            self.assertIn("длинное тире", errors(f"Он {EM} инженер.", ch))

    def test_en_dash_in_post_is_error(self):
        self.assertIn("тире не своего канала", errors(f"Он {EN} инженер.", "post"))

    def test_hyphen_in_post_is_fine(self):
        self.assertEqual(rules("Он - инженер.", "post"), [])

    def test_hyphen_in_docx_is_warning(self):
        self.assertIn("тире не своего канала", rules("Он - инженер.", "docx"))

    def test_en_dash_in_docx_is_fine(self):
        self.assertEqual(rules(f"Он {EN} инженер.", "docx"), [])

    def test_list_marker_is_not_a_dash(self):
        self.assertEqual(rules("- первый пункт\n- второй пункт", "docx"), [])

    def test_ranges_and_compounds_are_not_dashes(self):
        self.assertEqual(rules(f"Цена 20{EN}30 тысяч, кое-где выше.", "docx"), [])

    def test_density(self):
        text = "А - б, и в - г.\n\nД - е, и ж - з.\n\nИ - к."
        self.assertIn("плотность тире", rules(text, "post"))

    def test_code_and_quotes_are_skipped(self):
        text = f"Пример: `a {EM} b`.\n\n> Цитата {EM} чужая.\n\n```\nx {EM} y\n```"
        self.assertNotIn("длинное тире", rules(text, "post"))


class Quotes(unittest.TestCase):
    def test_curly_in_russian_is_error(self):
        self.assertIn("фигурные кавычки", errors("Он сказал “привет”.", "docx"))

    def test_lapki_inside_guillemets_are_fine(self):
        self.assertEqual(rules("Он сказал: «читал „Анну“».", "docx"), [])

    def test_guillemets_in_post_warn(self):
        self.assertIn("кавычки не своего канала", rules("Проект «Альфа» стартовал.", "post"))

    def test_straight_in_docx_warn(self):
        self.assertIn("кавычки не своего канала", rules('Проект "Альфа" стартовал.', "docx"))

    def test_mixed(self):
        self.assertIn("разнобой кавычек", rules('Проект «Альфа» и "Бета".', "post"))


class HardBans(unittest.TestCase):
    def test_contrast(self):
        self.assertIn("пустой контраст", errors("Это не просто CRM, а целая экосистема."))
        self.assertIn("пустой контраст", errors("Он не только пишет код, но и ведёт клиентов."))
        self.assertIn("пустой контраст", errors("Дело не в деньгах."))

    def test_not_easy_is_not_contrast(self):
        self.assertNotIn("пустой контраст", rules("Это было не просто сделать."))

    def test_lead_ins_and_openers(self):
        self.assertIn("подводка", errors("Стоит отметить, что продажи выросли."))
        self.assertIn("пустое открытие", errors("В современном мире всё меняется."))
        self.assertIn("анонс", errors("Давайте разберёмся, как это работает."))

    def test_dannyi_but_not_data(self):
        self.assertIn("«данный»", errors("Данный отчёт готов."))
        self.assertNotIn("«данный»", rules("Данные за май собраны."))

    def test_chat_wrapper(self):
        self.assertIn("обвязка чата", errors("Вот вариант поста:\n\nТекст."))
        self.assertIn("обвязка чата", errors("Привет, [Имя]!"))

    def test_vague_authority_and_self_description(self):
        self.assertIn("размытый авторитет", errors("Эксперты отмечают, что рынок растёт.", "report"))
        self.assertIn("текст про сам текст", errors("Таблица ниже сравнивает трёх вендоров.", "report"))
        self.assertIn("текст про сам текст", errors("Данные собраны из открытых источников.", "report"))

    def test_quoted_mention_is_not_use(self):
        self.assertEqual(errors("Убираем обороты «стоит отметить» и «данный».", "docx"), [])

    def test_wikilinks_are_skipped(self):
        self.assertNotIn("длинное тире", rules(f"См. [[Заметка#Пост 1 {EM} знакомство]].", "post"))

    def test_clean_text(self):
        text = ("Бот запустили в марте. К июню через него шло 40% обращений, "
                "а жалоб пришло две. Следующий шаг - подключить оплату.")
        self.assertEqual(errors(text), [])


class EmailFormulas(unittest.TestCase):
    def test_formulas_in_email(self):
        text = ("Доброго времени суток, уважаемые коллеги!\n\nУбедительная просьба прислать отчёт ASAP. "
                "Заранее спасибо!\n\nС надеждой на скорейший ответ")
        found = [f for f in check.check(text, "email") if f["rule"] == "формула переписки"]
        self.assertGreaterEqual(len(found), 5)
        self.assertTrue(all(f["level"] == "warning" for f in found))

    def test_only_in_email_channel(self):
        self.assertNotIn("формула переписки", rules("Доброго времени суток!", "post"))

    def test_clean_letter(self):
        text = "Ирина, добрый день!\n\nПришлите, пожалуйста, акт сверки до пятницы, 11 октября: без него не закроем квартал."
        self.assertEqual(rules(text, "email"), [])

    def test_quoted_formula_is_mention(self):
        self.assertNotIn("формула переписки", rules("Не пишите «Доброго времени суток».", "email"))


class Genre(unittest.TestCase):
    def test_legal_allows_bureaucratese(self):
        text = "Данное постановление является незаконным. Таким образом, прошу его отменить."
        self.assertIn("«данный»", errors(text, "docx"))
        legal = [f["rule"] for f in check.check(text, "docx", "legal") if f["level"] == "error"]
        self.assertEqual(legal, [])

    def test_legal_still_catches_chat_wrapper(self):
        legal = [f["rule"] for f in check.check("Вот вариант жалобы:\n\nТекст.", "docx", "legal")]
        self.assertIn("обвязка чата", legal)


class Structure(unittest.TestCase):
    def test_bold_labels(self):
        text = "- **Скорость:** выросла.\n- **Качество:** лучше."
        self.assertIn("список «Термин: описание»", rules(text, "report"))

    def test_fragments(self):
        self.assertIn("рубленые фрагменты", rules("Без пафоса. Без воды. Просто факты."))

    def test_title_case(self):
        self.assertIn("Title Case", rules("## Ранняя Жизнь Героя", "article"))
        self.assertNotIn("Title Case", rules("## Ранняя жизнь героя", "article"))

    def test_copula_density(self):
        text = "Он является лидером. Она является автором. Это является нормой."
        self.assertIn("«является»", rules(text, "report"))


class Cli(unittest.TestCase):
    def test_exit_codes(self):
        path = os.path.join(os.path.dirname(__file__), "_tmp_input.md")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"Он {EM} инженер.")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(check.main([path, "--channel", "post"]), 1)
            with open(path, "w", encoding="utf-8") as f:
                f.write("Он - инженер.")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(check.main([path, "--channel", "post"]), 0)
        finally:
            os.remove(path)

    def test_missing_file(self):
        self.assertEqual(check.main(["/nonexistent/x.md", "--channel", "post"]), 2)


if __name__ == "__main__":
    unittest.main()
