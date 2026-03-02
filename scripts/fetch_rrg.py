#!/usr/bin/env python3
"""
RRG (Relative Rotation Graph) 데이터 계산
- SPY 대비 각 섹터 ETF의 상대강도(RS-Ratio)와 모멘텀(RS-Momentum) 계산
- JdK RS-Ratio / RS-Momentum 방식 (100 기준 정규화)
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    import subprocess
    subprocess.check_call(["pip", "install", "yfinance", "-q"])
    import yfinance as yf

# ============================================
# 섹터 ETF + 벤치마크
# ============================================

BENCHMARK = "SPY"

SECTORS = {
    "XLK":  {"name": "기술",       "color": "#3b82f6"},
    "XLF":  {"name": "금융",       "color": "#22c55e"},
    "XLV":  {"name": "헬스케어",   "color": "#ef4444"},
    "XLY":  {"name": "임의소비재", "color": "#f59e0b"},
    "XLC":  {"name": "커뮤니케이션", "color": "#8b5cf6"},
    "XLI":  {"name": "산업재",     "color": "#06b6d4"},
    "XLP":  {"name": "필수소비재", "color": "#ec4899"},
    "XLE":  {"name": "에너지",     "color": "#84cc16"},
    "XLU":  {"name": "유틸리티",   "color": "#f97316"},
    "XLRE": {"name": "부동산",     "color": "#14b8a6"},
    "XLB":  {"name": "소재",       "color": "#a855f7"},
}

# RRG 파라미터
RS_PERIOD = 50       # RS-Ratio SMA 기간 (거래일)
MOM_PERIOD = 10      # RS-Momentum SMA 기간
TRAIL_WEEKS = 4      # 꼬리 길이 (주 단위)
FETCH_DAYS = 400     # 데이터 수집 기간


def fetch_prices(symbols, days=FETCH_DAYS):
    """여러 심볼의 종가 데이터를 한 번에 다운로드"""
    print(f"\n📡 {len(symbols)}개 심볼 다운로드 중...")
    end = datetime.now()
    start = end - timedelta(days=days)

    try:
        df = yf.download(
            symbols, start=start, end=end,
            group_by="ticker", auto_adjust=True, progress=False
        )
    except Exception as e:
        print(f"  ❌ 일괄 다운로드 실패: {e}")
        return {}

    prices = {}
    for sym in symbols:
        try:
            if len(symbols) == 1:
                col = df["Close"]
            else:
                col = df[sym]["Close"]
            series = col.dropna()
            prices[sym] = {
                d.strftime("%Y-%m-%d"): round(float(v), 2)
                for d, v in series.items()
            }
            print(f"  ✅ {sym}: {len(prices[sym])}일")
        except Exception as e:
            print(f"  ⚠️ {sym} 파싱 실패: {e}")

    return prices


def sma(values, period):
    """단순이동평균 계산"""
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def calc_rrg(sector_prices, bench_prices):
    """
    RS-Ratio와 RS-Momentum 계산 (JdK 방식)

    1. RS = sector_close / bench_close  (상대강도 라인)
    2. RS-Ratio = (RS / SMA(RS, 50)) * 100
    3. RS-Momentum = (RS-Ratio / SMA(RS-Ratio, 10)) * 100
    """
    # 공통 날짜 정렬
    common = sorted(set(sector_prices.keys()) & set(bench_prices.keys()))
    if len(common) < RS_PERIOD + MOM_PERIOD + 20:
        return []

    # RS 계산
    rs_series = []
    for d in common:
        bp = bench_prices[d]
        if bp == 0:
            continue
        rs_series.append({"date": d, "rs": sector_prices[d] / bp})

    # RS-Ratio 계산
    ratio_series = []
    for i in range(RS_PERIOD, len(rs_series)):
        window = [x["rs"] for x in rs_series[i - RS_PERIOD + 1 : i + 1]]
        avg = sma(window, RS_PERIOD)
        if avg and avg > 0:
            ratio = (rs_series[i]["rs"] / avg) * 100
            ratio_series.append({"date": rs_series[i]["date"], "ratio": ratio})

    # RS-Momentum 계산
    result = []
    for i in range(MOM_PERIOD, len(ratio_series)):
        window = [x["ratio"] for x in ratio_series[i - MOM_PERIOD + 1 : i + 1]]
        avg = sma(window, MOM_PERIOD)
        if avg and avg > 0:
            momentum = (ratio_series[i]["ratio"] / avg) * 100
            result.append({
                "date": ratio_series[i]["date"],
                "rs_ratio": round(ratio_series[i]["ratio"], 3),
                "rs_momentum": round(momentum, 3),
            })

    return result


def extract_weekly_trail(rrg_data, weeks=TRAIL_WEEKS):
    """주 단위 스냅샷 추출 (매주 금요일 또는 마지막 거래일)"""
    if not rrg_data:
        return []

    # 주별 그룹핑
    from collections import OrderedDict
    weekly = OrderedDict()
    for d in rrg_data:
        # ISO week key
        dt = datetime.strptime(d["date"], "%Y-%m-%d")
        wk = dt.strftime("%Y-W%W")
        weekly[wk] = d  # 같은 주의 마지막 값

    points = list(weekly.values())
    trail = points[-(weeks + 1) :]  # +1 for current
    return trail


def get_quadrant(rs_ratio, rs_momentum):
    """4분면 판별"""
    if rs_ratio >= 100 and rs_momentum >= 100:
        return "leading"
    elif rs_ratio >= 100 and rs_momentum < 100:
        return "weakening"
    elif rs_ratio < 100 and rs_momentum < 100:
        return "lagging"
    else:
        return "improving"


def main():
    print("=" * 55)
    print("  RRG (Relative Rotation Graph) 데이터 생성")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    # 모든 심볼 다운로드
    all_symbols = [BENCHMARK] + list(SECTORS.keys())
    prices = fetch_prices(all_symbols)

    if BENCHMARK not in prices:
        print(f"\n❌ 벤치마크 {BENCHMARK} 데이터 없음 — 중단")
        return

    bench = prices[BENCHMARK]

    # 각 섹터 RRG 계산
    print(f"\n📊 RRG 좌표 계산 (RS기간={RS_PERIOD}일, MOM기간={MOM_PERIOD}일)")
    sectors_out = {}

    for sym, info in SECTORS.items():
        if sym not in prices:
            print(f"  ⚠️ {sym} 건너뜀")
            continue

        rrg = calc_rrg(prices[sym], bench)
        trail = extract_weekly_trail(rrg, TRAIL_WEEKS)

        if not trail:
            print(f"  ⚠️ {sym} 데이터 부족")
            continue

        current = trail[-1]
        quadrant = get_quadrant(current["rs_ratio"], current["rs_momentum"])

        sectors_out[sym] = {
            "name": info["name"],
            "color": info["color"],
            "quadrant": quadrant,
            "current": current,
            "trail": trail,
        }

        arrow = {"leading": "🟢", "weakening": "🟡", "lagging": "🔴", "improving": "🔵"}
        print(
            f"  {arrow[quadrant]} {sym:5} {info['name']:8} "
            f"RS-Ratio={current['rs_ratio']:.2f}  "
            f"RS-Mom={current['rs_momentum']:.2f}  "
            f"→ {quadrant}"
        )

    # 저장
    output = {
        "lastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "benchmark": BENCHMARK,
        "params": {
            "rs_period": RS_PERIOD,
            "mom_period": MOM_PERIOD,
            "trail_weeks": TRAIL_WEEKS,
        },
        "sectors": sectors_out,
    }

    out_path = Path(__file__).parent.parent / "data" / "rrg.json"
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False)

    print(f"\n✅ 저장: {out_path} ({len(sectors_out)}개 섹터)")
    print("완료!")


if __name__ == "__main__":
    main()
