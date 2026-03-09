#!/usr/bin/env python3
"""
섹터 ETF 일별 업데이트 스크립트 (GitHub Actions용)
- 기존 CSV의 마지막 날짜 이후 데이터만 가져와서 추가
- fetch_history.py로 초기 데이터를 먼저 세팅해야 함
"""

import os
from datetime import datetime, timedelta
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    import subprocess
    subprocess.check_call(['pip', 'install', 'yfinance', '-q'])
    import yfinance as yf

SYMBOLS = ["SPY", "XLK", "XLF", "XLV", "XLY", "XLC", "XLI", "XLP", "XLE", "XLU", "XLRE", "XLB"]
DATA_DIR = Path(__file__).parent.parent / "data" / "history"


def get_last_date(filepath):
    """CSV의 마지막 날짜 읽기"""
    if not filepath.exists():
        return None
    with open(filepath, "r") as f:
        lines = f.readlines()
    if len(lines) < 2:
        return None
    last_line = lines[-1].strip()
    if not last_line:
        last_line = lines[-2].strip()
    return last_line.split(",")[0]


def append_new_data(symbol, filepath):
    """마지막 날짜 이후 데이터를 가져와서 CSV에 추가"""
    last_date = get_last_date(filepath)
    
    if not last_date:
        print(f"  ⚠️ {symbol} CSV 없음 — fetch_history.py를 먼저 실행하세요")
        return 0
    
    # 마지막 날짜 다음날부터
    start = (datetime.strptime(last_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    end = datetime.now().strftime("%Y-%m-%d")
    
    if start >= end:
        print(f"  ✅ {symbol} 이미 최신 ({last_date})")
        return 0
    
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=start, end=end)
        
        if hist.empty:
            print(f"  ✅ {symbol} 새 데이터 없음 ({last_date} 이후)")
            return 0
        
        # 중복 방지: 마지막 날짜와 같은 행 제거
        new_rows = []
        for date, row in hist.iterrows():
            d = date.strftime("%Y-%m-%d")
            if d > last_date:
                new_rows.append(f"{d},{round(row['Close'], 2)}")
        
        if not new_rows:
            print(f"  ✅ {symbol} 새 데이터 없음")
            return 0
        
        # CSV에 추가
        with open(filepath, "a", encoding="utf-8") as f:
            for row in new_rows:
                f.write(row + "\n")
        
        print(f"  📈 {symbol} +{len(new_rows)}일 추가 ({new_rows[0].split(',')[0]} ~ {new_rows[-1].split(',')[0]})")
        return len(new_rows)
        
    except Exception as e:
        print(f"  ❌ {symbol} 오류: {e}")
        return 0


def main():
    print("=" * 55)
    print("  📊 섹터 ETF 일별 업데이트")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)
    
    total_new = 0
    for symbol in SYMBOLS:
        filepath = DATA_DIR / f"{symbol}.csv"
        total_new += append_new_data(symbol, filepath)
    
    print(f"\n✅ 완료! 총 {total_new}개 새 데이터 추가")


if __name__ == "__main__":
    main()
