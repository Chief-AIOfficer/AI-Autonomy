"""Приёмы подачи данных для дек: одна функция на приём, цвета и шрифт только из темы.
Каталог и правила выбора: ../INDEX.md, рецепт приёма: ../cards/<имя>.md."""
from .core import load_theme, num, FitError, DataError, Fig, Exhibit
from .bars import bar_ranked, columns
from .delta import waterfall, pair_delta, gap_to_target, group_delta, dumbbell
from .parts import stacked_100, share_bar, stacked_columns, breakdown_column, nested_market
from .lines import lines, hstack, panels
from .tables import table, heat_grid
from .matrix import matrix_2x2, risk_map
from .schemes import points, pillars, framework, exec_summary, share_cards, quotes, kpi_cards, hub, fan
from .flow import stages, gantt, lanes, spectrum, driver_tree, segment_map, layers
from .preview import sheet, shot, font_face, find_chrome
