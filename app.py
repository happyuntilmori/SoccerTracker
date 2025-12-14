import streamlit as st
import aiohttp
import asyncio
import urllib.parse
import time
from datetime import datetime

# --- 페이지 설정 ---
st.set_page_config(page_title="🏆 Ezy's Live Tracker", page_icon="⚽", layout="centered")

# --- CSS 커스텀 ---
st.markdown("""
<style>
    body, .stApp, p, div, span, b, strong { color: #E0E0E0 !important; }
    .stApp { background-color: #121212; }
    
    .team-card {
        padding: 15px; border-radius: 12px; margin-bottom: 12px;
        background-color: #1E1E1E; border: 1px solid #333;
        box-shadow: 0 4px 6px rgba(0,0,0,0.4); position: relative;
    }
    .card-red { border-left: 6px solid #ff4b4b; background: linear-gradient(90deg, rgba(60, 10, 10, 0.9) 0%, rgba(30, 30, 30, 1) 100%); }
    .card-orange { border-left: 6px solid #ffa500; background: linear-gradient(90deg, rgba(60, 40, 0, 0.9) 0%, rgba(30, 30, 30, 1) 100%); }
    .card-normal { border-left: 6px solid #00c853; }
    
    .league-tag { font-size: 0.7rem; color: #AAA !important; text-transform: uppercase; margin-bottom: 4px; }
    
    a.sofascore-link { text-decoration: none !important; display: block; }
    
    .team-name { font-size: 1.4rem; font-weight: 800; color: #FFF !important; margin-bottom: 8px; display: flex; align-items: center; }
    
    .sofa-icon { 
        font-size: 0.7rem; background-color: #374df5; color: white !important; 
        padding: 3px 6px; border-radius: 4px; margin-left: 8px; font-weight: bold; 
        box-shadow: 0 2px 2px rgba(0,0,0,0.5);
    }
    .rank-badge { background: #444; color: #FFF !important; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; margin-right: 6px; }
    
    .match-row { font-size: 0.85rem; margin-top: 6px; padding-top: 6px; border-top: 1px solid #333; color: #CCC !important; display: flex; align-items: center; }
    .match-row:first-of-type { border-top: none; padding-top: 0; }
    .next-row { font-size: 0.85rem; margin-top: 10px; padding-top: 8px; border-top: 1px dashed #555; color: #81d4fa !important; display: flex; align-items: center; font-weight: bold; }
    
    .res-box { display: inline-block; width: 22px; text-align: center; font-weight: bold; margin-right: 8px; border-radius: 3px; }
    .res-w { color: #4caf50 !important; background: rgba(76, 175, 80, 0.1); }
    .res-d { color: #ff9800 !important; background: rgba(255, 152, 0, 0.1); }
    .res-l { color: #f44336 !important; background: rgba(244, 67, 54, 0.1); }
    .latest-tag { background-color: #ffd700; color: #000 !important; font-size: 0.65rem; padding: 1px 4px; border-radius: 3px; font-weight: bold; margin-left: auto; }
</style>
""", unsafe_allow_html=True)

# 🔑 API 키 설정
try:
    API_KEY = st.secrets["api_key"]
BASE_URL = f"https://www.thesportsdb.com/api/v1/json/{API_KEY}"
DEFAULT_SEASON = "2025-2026"
CALENDAR_SEASON = "2025"

# ==========================================
# 📋 리그 리스트
# ==========================================
LEAGUES = {
    "EPL (ENG)": "4328", "La Liga (ESP)": "4335", "Bundesliga (GER)": "4331",
    "Serie A (ITA)": "4332", "Ligue 1 (FRA)": "4334", "Eredivisie (NED)": "4337",
    "Primeira Liga (POR)": "4344", "Super Lig (TUR)": "4339", "Russian Premier": "4355",
    "Superliga (DEN)": "4340", "Eliteserien (NOR)": "4358", "Scottish Prem": "4330",
    "Championship (ENG)": "4329", "La Liga 2 (ESP)": "4361", "2. Bundesliga (GER)": "4399",
    "Serie B (ITA)": "4394", "Ligue 2 (FRA)": "4401", "UCL (Champions)": "4480",
    "UEL (Europa)": "4481", "UECL (Conf)": "4857", "K League 1 (KOR)": "4689",
    "J1 League (JPN)": "4633", "J2 League (JPN)": "4824", "Saudi Pro League": "4668",
    "Indian Super League": "4791", "A-League (AUS)": "4356", "Brazil Serie A": "4351",
    "Primera Argentina": "4406", "MLS (USA)": "4346", "Liga MX (MEX)": "4350",
    "Concacaf Nations": "4866"
}

CALENDAR_LEAGUES = [
    "K League 1 (KOR)", "J1 League (JPN)", "J2 League (JPN)", "MLS (USA)", 
    "Brazil Serie A", "Primera Argentina", "Eliteserien (NOR)", 
    "Russian Premier", "Liga MX (MEX)", "Concacaf Nations"
]

def get_season_for_league(league_name):
    if league_name in CALENDAR_LEAGUES: return CALENDAR_SEASON
    return DEFAULT_SEASON

async def fetch_url(session, url):
    nocache_url = f"{url}&t={int(time.time())}"
    headers = {"User-Agent": "Mozilla/5.0"}
    for attempt in range(3):
        try:
            async with session.get(nocache_url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    return await response.json()
        except:
            if attempt < 2: await asyncio.sleep(1)
    return None

async def process_team_data(session, team, league_name):
    t_id = team['idTeam']
    # [디버그용] Raw 데이터를 함께 반환하도록 수정
    res_last, res_next = await asyncio.gather(
        fetch_url(session, f"{BASE_URL}/eventslast.php?id={t_id}"),
        fetch_url(session, f"{BASE_URL}/eventsnext.php?id={t_id}")
    )
    
    raw = res_last.get('results', []) if res_last else []
    valid = [m for m in raw if m.get('dateEvent')]
    valid.sort(key=lambda x: x['dateEvent'])
    recent_3 = valid[-3:]
    
    matches = []
    outcomes = []
    for idx, m in enumerate(recent_3):
        home, away = int(m['intHomeScore'] or 0), int(m['intAwayScore'] or 0)
        if m['idHomeTeam'] == t_id:
            res = "W" if home > away else ("D" if home == away else "L")
            opp, score = m['strAwayTeam'], f"{home}-{away}"
        else:
            res = "W" if away > home else ("D" if away == home else "L")
            opp, score = m['strHomeTeam'], f"{away}-{home}"
        outcomes.append(res)
        matches.append({"res": res, "date": m['dateEvent'][5:].replace("-", "/"), "opp": opp, "score": score, "is_latest": idx==len(recent_3)-1})

    next_info = "🏁 시즌 종료"
    if res_next and res_next.get('events'):
        ev = res_next['events'][0]
        n_opp = ev.get('strAwayTeam') if ev.get('idHomeTeam') == t_id else ev.get('strHomeTeam')
        next_info = f"📅 {ev.get('dateEvent','')[5:].replace('-', '/')} vs {n_opp}"

    status = "normal"
    if outcomes:
        if outcomes[-1] != "W":
            status = "orange"
            if len(outcomes) >= 2 and outcomes[-2] != "W":
                status = "red"
            
    # [디버그용] raw_last, raw_next 데이터를 리턴에 포함
    return {
        "league": league_name, "rank": team['intRank'], "name": team['strTeam'], 
        "matches": matches, "next": next_info, "status": status,
        "raw_last": res_last, "raw_next": res_next # 디버그 데이터
    }

async def fetch_all(leagues):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for name, lid in LEAGUES.items():
            if name in leagues:
                target_season = get_season_for_league(name)
                data = await fetch_url(session, f"{BASE_URL}/lookuptable.php?l={lid}&s={target_season}")
                if data and 'table' in data:
                    teams = [t for t in data['table'] if int(t['intRank']) <= 2]
                    tasks.extend([process_team_data(session, t, name) for t in teams])
        return await asyncio.gather(*tasks)

st.title("📱 Ezy's Live Tracker")

with st.sidebar:
    st.header("설정")
    if 'last_update' not in st.session_state:
        st.session_state.last_update = datetime.now().strftime("%H:%M:%S")
    st.caption(f"최근 업데이트: {st.session_state.last_update}")
    
    # 🔴 [새로운 기능] 디버그 모드 스위치
    debug_mode = st.toggle("🔧 디버그 모드 (API 원본 확인)")
    
    selected = st.multiselect("리그 선택", list(LEAGUES.keys()), default=list(LEAGUES.keys()))
    if st.button("🔄 데이터 강제 새로고침", type="primary"):
        st.cache_data.clear()
        st.session_state.last_update = datetime.now().strftime("%H:%M:%S")
        st.rerun()

if selected:
    with st.spinner("최신 데이터를 가져오는 중입니다..."):
        data = asyncio.run(fetch_all(selected))
        
        if not data:
            st.error("⚠️ 데이터를 가져오지 못했습니다.")
        else:
            for t in data:
                rows = ""
                for m in reversed(t['matches']):
                    tag = "<span class='latest-tag'>LATEST</span>" if m['is_latest'] else ""
                    rows += f"<div class='match-row'><span class='res-box res-{m['res'].lower()}'>{m['res']}</span> {m['date']} vs {m['opp']} ({m['score']}) {tag}</div>"
                
                search_query = urllib.parse.quote(f"{t['name']} SofaScore")
                sofa_url = f"https://www.google.com/search?q={search_query}"
                
                st.markdown(f"""
                <div class='team-card card-{t['status']}'>
                    <div class='league-tag'>{t['league']}</div>
                    <a href='{sofa_url}' target='_blank' class='sofascore-link'>
                        <div class='team-name'>
                            <span class='rank-badge'>#{t['rank']}</span>{t['name']} 
                            <span class='sofa-icon'>SofaScore</span>
                        </div>
                    </a>
                    {rows if rows else "<div class='match-row'>기록 없음</div>"}
                    <div class='next-row'><span class='next-tag'>NEXT</span> {t['next']}</div>
                </div>""", unsafe_allow_html=True)

                # 🔴 [디버그 출력] 스위치가 켜져 있을 때만 원본 데이터를 보여줌
                if debug_mode:
                    with st.expander(f"🕵️‍♂️ {t['name']} - API 원본 데이터 확인"):
                        st.caption("API가 보낸 '지난 경기' 데이터:")
                        st.json(t['raw_last'])
                        st.caption("API가 보낸 '다음 경기' 데이터:")
                        st.json(t['raw_next'])

            st.success(f"✅ 업데이트 완료: {st.session_state.last_update}")

