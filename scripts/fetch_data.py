#!/usr/bin/env python3
"""
S&P 500 섹터 ETF 성과 데이터 수집 스크립트
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    import subprocess
    subprocess.check_call(['pip', 'install', 'yfinance', '-q'])
    import yfinance as yf

# ============================================
# S&P 500 섹터 ETF 정의
# ============================================

ASSETS = {
    "XLK": {"name": "기술", "color": "#3b82f6"},
    "XLF": {"name": "금융", "color": "#22c55e"},
    "XLV": {"name": "헬스케어", "color": "#ef4444"},
    "XLY": {"name": "임의소비재", "color": "#f59e0b"},
    "XLC": {"name": "커뮤니케이션", "color": "#8b5cf6"},
    "XLI": {"name": "산업재", "color": "#06b6d4"},
    "XLP": {"name": "필수소비재", "color": "#ec4899"},
    "XLE": {"name": "에너지", "color": "#84cc16"},
    "XLU": {"name": "유틸리티", "color": "#f97316"},
    "XLRE": {"name": "부동산", "color": "#14b8a6"},
    "XLB": {"name": "소재", "color": "#a855f7"},
}


def get_date_ranges():
    """기간별 시작 날짜 계산"""
    today = datetime.now()
    
    return {
        "1W": today - timedelta(days=7),
        "1M": today - timedelta(days=30),
        "3M": today - timedelta(days=90),
        "12M": today - timedelta(days=365),
        "YTD": datetime(today.year, 1, 1),
    }


def fetch_etf_data(symbol, days=400):
    """yfinance로 ETF 데이터 가져오기"""
    print(f"  📈 {symbol} 데이터 수집 중...")
    
    try:
        ticker = yf.Ticker(symbol)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        hist = ticker.history(start=start_date, end=end_date)
        
        if hist.empty:
            print(f"  ⚠️ {symbol} 데이터 없음")
            return None
        
        # 날짜와 종가만 추출
        data = []
        for date, row in hist.iterrows():
            data.append({
                "date": date.strftime("%Y-%m-%d"),
                "price": round(row["Close"], 2)
            })
        
        print(f"  ✅ {symbol}: {len(data)}일 데이터")
        return data
        
    except Exception as e:
        print(f"  ❌ {symbol} 오류: {e}")
        return None


def calculate_performance(prices, start_date):
    """특정 날짜부터의 수익률 계산"""
    start_str = start_date.strftime("%Y-%m-%d")
    
    # 시작 날짜에 가장 가까운 데이터 찾기
    start_price = None
    for p in prices:
        if p["date"] >= start_str:
            start_price = p["price"]
            break
    
    if not start_price or not prices:
        return None
    
    end_price = prices[-1]["price"]
    return round((end_price - start_price) / start_price * 100, 2)


def main():
    print("=" * 50)
    print("🚀 S&P 500 섹터 ETF 데이터 수집 시작")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    date_ranges = get_date_ranges()
    all_data = {}
    
    # 모든 ETF 데이터 수집
    print("\n📊 섹터 ETF 데이터 수집")
    for symbol, info in ASSETS.items():
        prices = fetch_etf_data(symbol)
        if prices:
            all_data[symbol] = {
                "name": info["name"],
                "color": info["color"],
                "prices": prices,
                "performance": {}
            }
            
            # 기간별 수익률 계산
            for period, start_date in date_ranges.items():
                perf = calculate_performance(prices, start_date)
                all_data[symbol]["performance"][period] = perf
    
    # 결과 저장
    output = {
        "lastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "assets": all_data
    }
    
    output_path = Path(__file__).parent.parent / "data" / "performance.json"
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False)
    
    print("\n" + "=" * 50)
    print(f"✅ 완료! {len(all_data)}개 섹터 저장됨")
    print(f"📁 {output_path}")
    print("=" * 50)
    
    # YTD 성과 출력
    print("\n📊 YTD 성과:")
    for symbol, data in sorted(all_data.items(), key=lambda x: x[1]["performance"].get("YTD", 0) or 0, reverse=True):
        perf = data["performance"].get("YTD", "N/A")
        if perf is not None:
            sign = "+" if perf >= 0 else ""
            print(f"  {symbol:5} {data['name']:10} {sign}{perf}%")


if __name__ == "__main__":
    main()
