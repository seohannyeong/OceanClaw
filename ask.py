#!/usr/bin/env python3
"""질의응답 진입점.

사용법:
    python ask.py                      # 대화형(REPL) 모드
    python ask.py "메인 베어링 볼트 토크 값은?"   # 단발 질문
"""

import sys

from oceanclaw.cli import ask_once, run_repl

if __name__ == "__main__":
    if len(sys.argv) > 1:
        ask_once(" ".join(sys.argv[1:]))
    else:
        run_repl()
