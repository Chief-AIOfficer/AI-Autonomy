# Источники

## Скиллы, на которые опирается метод

- **The Fool**, автор Jeff Allan, репозиторий `jeffallan/claude-skills`, лицензия MIT. https://github.com/jeffallan/claude-skills (папка `skills/the-fool/`). Отсюда идея разбирать позицию несколькими режимами (вопросы к допущениям, диалектика, пре-мортем, красная команда, проверка доказательств) и начинать с пересказа позиции в сильнейшей форме. Текст скилла написан заново, на русском; режимы переработаны и дополнены. Уведомление из файла LICENSE источника: «MIT License. Copyright (c) 2025» (имя правообладателя в файле не указано; автор скилла по его шапке: https://github.com/Jeffallan). Полный текст лицензии: https://github.com/jeffallan/claude-skills/blob/main/LICENSE.
- **brainstorm-diverge-converge**, репозиторий `lyndonkl/claude`. https://github.com/lyndonkl/claude (папка `skills/brainstorm-diverge-converge/`). Использована только общая идея порядка «развести, сгруппировать, оценить по явным критериям». Текст, шаблоны и рубрики оттуда не заимствованы: у репозитория на 14.10.2026 нет лицензии.
- Приём «каждый угол отдельным заходом, потом объединить» взят из практики автора.

## Исследования

- Deng, Brucks, Toubia. Examining and Addressing Barriers to Diversity in LLM-Generated Ideas. arXiv 2602.20408, 2026. https://arxiv.org/abs/2602.20408 – фиксация на первых ответах и сведение знаний к одному распределению; пошаговое рассуждение и обычные персоны повышают разнообразие.
- Terwiesch, Meincke, Girotra, Mollick, Nave, Ulrich. AI and Its Impact on Creativity and Diversity: An Empirical Study of LLM-Generated Product Ideas. arXiv 2607.27553, 2026. https://ideas.repec.org/p/arx/papers/2607.27553.html – идеи моделей выше по качеству, ниже по разнообразию; персоны, ограничения и пошаговое рассуждение возвращают разнообразие.
- Jiang и др. Artificial Hivemind: The Open-Ended Homogeneity of Language Models (and Beyond). arXiv 2510.22954, NeurIPS 2025. https://arxiv.org/abs/2510.22954 – модели повторяют себя и друг друга на открытых вопросах.
- Ueda и др. Exploring Design of Multi-Agent LLM Dialogues for Research Ideation. arXiv 2507.08350, SIGDIAL 2025. https://arxiv.org/abs/2507.08350 – разнородные персоны и критики повышают разнообразие и реализуемость.
- Panickssery, Bowman, Feng. LLM Evaluators Recognize and Favor Their Own Generations. NeurIPS 2024. https://arxiv.org/abs/2404.13076 – оценщик узнаёт свои тексты и завышает им оценку.
- Cheng, Yu и др. ELEPHANT: Measuring and understanding social sycophancy in LLMs. arXiv 2505.13995, ICLR 2026. https://arxiv.org/abs/2505.13995 – модели принимают постановку вопроса пользователя заметно чаще людей.
- Choi, Zhu, Li. Debate or Vote. arXiv 2508.17536, NeurIPS 2025. https://arxiv.org/abs/2508.17536 – выигрыш многоагентных дебатов в основном даёт голосование; поэтому в скилле не дебаты, а критик с проверяемыми условиями.

## Документация

- Claude Code, Skills: https://code.claude.com/docs/en/skills
- Skill authoring best practices: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
