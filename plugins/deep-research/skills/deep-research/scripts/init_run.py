#!/usr/bin/env python3
"""Create the folder for one research run and a brief skeleton.

    python3 init_run.py "Topic of the research" [--dir PARENT] [--mode standard]

Parent folder, first match wins: --dir, the DEEP_RESEARCH_DIR environment
variable, ~/Documents/Research. The run folder is <Topic>_<YYYYMMDD>; if it
exists, a numeric suffix is added. Prints the path of the run folder.
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

MODES = ('quick', 'standard', 'deep', 'ultradeep')

BRIEF = """# Brief: {topic}

Mode: {mode}. Created: {date}. This brief is frozen; amendments go to the report's method section.

## Question

## Decision it feeds

## Reader

## Boundaries

## Evidence rules

## Assumptions

## Tools
"""


def slug(topic: str) -> str:
    """Folder-safe name that keeps Cyrillic and Latin letters and digits."""
    s = re.sub(r'[^\w\s-]', '', topic, flags=re.UNICODE).strip()
    s = re.sub(r'[\s-]+', '_', s)
    return s[:80] or 'Research'


def parent_dir(cli_dir):
    if cli_dir:
        return Path(cli_dir).expanduser()
    if os.environ.get('DEEP_RESEARCH_DIR'):
        return Path(os.environ['DEEP_RESEARCH_DIR']).expanduser()
    return Path.home() / 'Documents' / 'Research'


def create_run(topic: str, parent: Path, mode: str, today=None) -> Path:
    today = today or dt.date.today()
    base = parent / f'{slug(topic)}_{today:%Y%m%d}'
    run, n = base, 2
    while run.exists():
        run = base.with_name(f'{base.name}_{n}')
        n += 1
    run.mkdir(parents=True)
    (run / '00_brief.md').write_text(BRIEF.format(topic=topic, mode=mode, date=today.isoformat()), encoding='utf-8')
    (run / 'run.json').write_text(json.dumps(
        {'topic': topic, 'mode': mode, 'created': today.isoformat()}, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8')
    return run


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('topic')
    ap.add_argument('--dir', help='parent folder for the run')
    ap.add_argument('--mode', choices=MODES, default='standard')
    a = ap.parse_args()
    try:
        run = create_run(a.topic, parent_dir(a.dir), a.mode)
    except OSError as e:
        sys.exit(f'Cannot create the run folder: {e}')
    print(run)


if __name__ == '__main__':
    main()
