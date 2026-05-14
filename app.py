import os
import math
import requests
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from pathlib import Path
import xml.etree.ElementTree as ET

load_dotenv()

APP_TITLE = "Veðurvefur Árborgar og Suðurlands"
APP_VERSION = "2.6.1"
TZ = ZoneInfo("Atlantic/Reykjavik")

PLACES = {
    "Selfoss": {"lat": 63.9335, "lon": -20.9971, "kind": "bær"},
    "Eyrarbakki": {"lat": 63.8635, "lon": -21.1492, "kind": "sjávarþorp"},
    "Stokkseyri": {"lat": 63.8370, "lon": -21.0608, "kind": "sjávarþorp"},
    "Hveragerði": {"lat": 64.0005, "lon": -21.1860, "kind": "bær"},
    "Þorlákshöfn": {"lat": 63.8559, "lon": -21.3834, "kind": "höfn"},
    "Hellisheiði": {"lat": 64.0359, "lon": -21.3797, "kind": "fjallvegur"},
    "Hella": {"lat": 63.8350, "lon": -20.4000, "kind": "bær"},
    "Hvolsvöllur": {"lat": 63.7533, "lon": -20.2243, "kind": "bær"},
    "Flúðir": {"lat": 64.1333, "lon": -20.3333, "kind": "sveit"},
    "Laugarvatn": {"lat": 64.2177, "lon": -20.7347, "kind": "skólastaður"},
    "Þingvellir": {"lat": 64.2559, "lon": -21.1295, "kind": "þjóðgarður"},
    "Vestmannaeyjar": {"lat": 63.4427, "lon": -20.2734, "kind": "eyjar"},
    "Landeyjahöfn": {"lat": 63.5307, "lon": -20.1154, "kind": "höfn/ferja"},
    "Vík í Mýrdal": {"lat": 63.4186, "lon": -19.0060, "kind": "bær"},
    "Reykjavík": {"lat": 64.1466, "lon": -21.9426, "kind": "samanburður"},
}

ROUTES = {
    "Selfoss → Reykjavík": ["Selfoss", "Hveragerði", "Hellisheiði", "Reykjavík"],
    "Selfoss → Þorlákshöfn": ["Selfoss", "Eyrarbakki", "Stokkseyri", "Þorlákshöfn"],
    "Selfoss → Vík": ["Selfoss", "Hella", "Hvolsvöllur", "Vík í Mýrdal"],
    "Selfoss → Flúðir/Laugarvatn": ["Selfoss", "Flúðir", "Laugarvatn"],
    "Selfoss → Þingvellir": ["Selfoss", "Laugarvatn", "Þingvellir"],
    "Selfoss → Vestmannaeyjar": ["Selfoss", "Hvolsvöllur", "Landeyjahöfn", "Vestmannaeyjar"],
}

WEATHER_EMOJI = {
    "Thunderstorm": "⛈️",
    "Drizzle": "🌦️",
    "Rain": "🌧️",
    "Snow": "❄️",
    "Mist": "🌫️",
    "Smoke": "🌫️",
    "Haze": "🌫️",
    "Dust": "🌫️",
    "Fog": "🌫️",
    "Sand": "🌫️",
    "Ash": "🌋",
    "Squall": "💨",
    "Tornado": "🌪️",
    "Clear": "☀️",
    "Clouds": "☁️",
}

FACTS = [
    {
        "title": "Hvað er vindkæling?",
        "text": "Vindkæling lýsir því að líkaminn tapar hita hraðar þegar vindur blæs. Þess vegna getur 2°C og 12 m/s vindur verið mun kaldara á húð en 2°C og logn.",
        "classroom": "Gott umræðuefni fyrir útiveru: Hvernig klæðum við okkur eftir vindi, ekki bara hitatölu?"
    },
    {
        "title": "Hvað þýðir loftþrýstingur?",
        "text": "Loftþrýstingur er þyngd loftsins yfir okkur. Lægri þrýstingur tengist oft lægðum, vindi og úrkomu, en hærri þrýstingur tengist oft stöðugra veðri.",
        "classroom": "Láttu nemendur fylgjast með þrýstingi í viku og bera saman við veðrið sem þau upplifa."
    },
    {
        "title": "Af hverju eru fjallvegir oft verri?",
        "text": "Á fjallvegum er oft kaldara, meiri vindur og minni skjól. Það getur valdið hálku eða skafrenningi þó veður virðist skaplegt í bænum.",
        "classroom": "Berið saman Selfoss og Hellisheiði áður en farið er til Reykjavíkur."
    },
    {
        "title": "Loftslag og jöklar",
        "text": "Hækkandi meðalhiti hefur áhrif á jökla, vatnafar og náttúru. Jöklar geta hopað og vatnsmagn í ám breyst eftir árstíðum.",
        "classroom": "Góð tenging við náttúrufræði: Hvað gerist þegar snjór og ís bráðna fyrr á vorin?"
    },
    {
        "title": "Af hverju breytist veðrið hratt á Suðurlandi?",
        "text": "Suðurland er opið fyrir lægðum úr Atlantshafi, vindur magnast við fjöll og veður getur verið allt annað á heiði en í bæ.",
        "classroom": "Láttu nemendur bera saman Selfoss, Hellisheiði og Reykjavík sama dag."
    },
    {
        "title": "Hvað er góð veðurathugun?",
        "text": "Góð athugun segir ekki bara hitann heldur líka vind, úrkomu, ský, skyggni og hvernig veðrið hefur áhrif á fólk.",
        "classroom": "Nemendur gera eigin veðurdagbók í eina viku með tölum og lýsingum."
    },
]

def get_api_key():
    """Sækir API lykil án þess að sýna rauða Streamlit secrets-villu ef secrets.toml er ekki til."""
    env_key = os.getenv("OPENWEATHER_API_KEY", "").strip()
    if env_key:
        return env_key

    possible_secret_files = [
        Path.cwd() / ".streamlit" / "secrets.toml",
        Path.home() / ".streamlit" / "secrets.toml",
    ]
    if any(path.exists() for path in possible_secret_files):
        try:
            secret_key = st.secrets.get("OPENWEATHER_API_KEY", "")
            if secret_key:
                return str(secret_key).strip()
        except Exception:
            return ""
    return ""

def deg_to_compass(deg):
    if deg is None:
        return "?"
    dirs = ["N", "NA", "A", "SA", "S", "SV", "V", "NV"]
    ix = int((deg + 22.5) // 45) % 8
    return dirs[ix]

def fmt_time(ts):
    if not ts:
        return "—"
    return datetime.fromtimestamp(ts, TZ).strftime("%H:%M")

def fmt_day(ts):
    if not ts:
        return "—"
    return datetime.fromtimestamp(ts, TZ).strftime("%a %d.%m.")

def weather_icon(main):
    return WEATHER_EMOJI.get(main, "🌤️")

def wind_chill(temp_c, wind_ms):
    if temp_c is None or wind_ms is None:
        return None
    wind_kmh = wind_ms * 3.6
    if temp_c > 10 or wind_kmh < 4.8:
        return temp_c
    return 13.12 + 0.6215 * temp_c - 11.37 * (wind_kmh ** 0.16) + 0.3965 * temp_c * (wind_kmh ** 0.16)

def school_weather_score(temp, wind, rain_mm, weather_main):
    score = 100
    reasons = []
    if temp is None:
        return 50, ["Engin hitagögn fundust."]
    if temp < -5:
        score -= 35; reasons.append("mjög kalt")
    elif temp < 0:
        score -= 20; reasons.append("frost")
    elif temp < 5:
        score -= 10; reasons.append("kalt")
    if wind and wind >= 15:
        score -= 35; reasons.append("mjög hvasst")
    elif wind and wind >= 10:
        score -= 20; reasons.append("hvasst")
    elif wind and wind >= 7:
        score -= 10; reasons.append("nokkur vindur")
    if rain_mm and rain_mm >= 5:
        score -= 30; reasons.append("mikil úrkoma")
    elif rain_mm and rain_mm >= 1:
        score -= 15; reasons.append("úrkoma")
    if weather_main in ["Thunderstorm", "Snow", "Squall", "Tornado"]:
        score -= 35; reasons.append("varasamt veður")
    score = max(0, min(100, score))
    if not reasons:
        reasons.append("gott útiveður")
    return score, reasons

def score_label(score):
    if score >= 80:
        return "Frábært"
    if score >= 60:
        return "Gott"
    if score >= 40:
        return "Varúð"
    return "Inni / fresta"

def score_class(score):
    if score >= 75:
        return "good"
    if score >= 45:
        return "warn"
    return "danger"

def clothing_tip(temp, wind, rain):
    tips = []
    wc = wind_chill(temp, wind) if temp is not None and wind is not None else temp
    if wc is not None and wc < 0:
        tips.append("hlý úlpa, húfa og vettlingar")
    elif wc is not None and wc < 6:
        tips.append("hlý peysa eða jakki")
    else:
        tips.append("léttur jakki gæti dugað")
    if rain and rain > 0.5:
        tips.append("regnföt/skór sem þola bleytu")
    if wind and wind >= 10:
        tips.append("forðast opin svæði í miklum vindi")
    return ", ".join(tips)

def _friendly_time_label(ts):
    """Skilar læsilegum tíma fyrir skóladag, t.d. 'Í dag 10:00' eða 'Á morgun 09:00'."""
    try:
        now_date = pd.Timestamp.now().date()
        d = pd.to_datetime(ts).date()
        hhmm = pd.to_datetime(ts).strftime("%H:%M")
        if d == now_date:
            return f"Í dag {hhmm}"
        if d == (now_date + timedelta(days=1)):
            return f"Á morgun {hhmm}"
        return pd.to_datetime(ts).strftime("%d.%m. %H:%M")
    except Exception:
        return str(ts)

def pick_best_windows(hourly, limit=3, school_hours=True):
    if hourly.empty or "time" not in hourly.columns:
        return pd.DataFrame()

    # Fyrir skólanotkun viljum við ekki velja miðnætti sem "besta tíma".
    # Þess vegna eru bestu gluggar miðaðir við skólatíma 08:00-16:59.
    df = hourly.head(48).copy()
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["time"])
    if school_hours:
        school_df = df[(df["time"].dt.hour >= 8) & (df["time"].dt.hour <= 16)].copy()
        if not school_df.empty:
            df = school_df

    rows = []
    for _, r in df.iterrows():
        score, reasons = school_weather_score(r.get("temp"), r.get("wind"), r.get("rain"), r.get("main"))
        rows.append({
            "Tími": _friendly_time_label(r["time"]),
            "Mat": score,
            "Hiti": round(r.get("temp", 0), 1),
            "Vindur": round(r.get("wind", 0), 1),
            "Úrkoma": round(r.get("rain", 0), 1),
            "Ábending": ", ".join(reasons),
            "_time": r["time"],
        })

    if not rows:
        return pd.DataFrame()

    out = pd.DataFrame(rows).sort_values(["Mat", "_time"], ascending=[False, True])
    # Forðumst tvítekna tímaglugga sem geta komið úr fallback-gögnum eða næstu dögum.
    out = out.drop_duplicates(subset=["Tími"]).head(limit)
    return out.drop(columns=["_time"], errors="ignore")

def travel_score(rows):
    score = 100
    reasons = []
    for r in rows:
        t = r.get("temp")
        w = r.get("wind")
        rain = r.get("rain")
        if t is not None and t < 0:
            score -= 10
            reasons.append(f"frost við {r['place']}")
        if w is not None and w >= 12:
            score -= 15
            reasons.append(f"hvass vindur við {r['place']}")
        if rain is not None and rain >= 2:
            score -= 8
            reasons.append(f"úrkoma við {r['place']}")
    score = max(0, min(100, score))
    if score >= 75:
        label = "Gott ferðaveður"
    elif score >= 45:
        label = "Varúð — skoða færð og nýjustu spá"
    else:
        label = "Erfitt ferðaveður — skoða Umferðina og Veðurstofu áður en lagt er af stað"
    return score, label, sorted(set(reasons))

@st.cache_data(ttl=600)
def call_openweather_onecall(lat, lon, api_key):
    if not api_key:
        raise ValueError("API lykil vantar.")
    url = "https://api.openweathermap.org/data/3.0/onecall"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric",
        "lang": "is",
        "exclude": "minutely"
    }
    r = requests.get(url, params=params, timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"One Call skilaði villu {r.status_code}: {r.text[:250]}")
    return r.json()

@st.cache_data(ttl=600)
def call_openweather_fallback(lat, lon, api_key):
    if not api_key:
        raise ValueError("API lykil vantar.")
    base = "https://api.openweathermap.org/data/2.5"
    current = requests.get(f"{base}/weather", params={
        "lat": lat, "lon": lon, "appid": api_key, "units": "metric", "lang": "is"
    }, timeout=20)
    forecast = requests.get(f"{base}/forecast", params={
        "lat": lat, "lon": lon, "appid": api_key, "units": "metric", "lang": "is"
    }, timeout=20)
    if current.status_code != 200:
        raise RuntimeError(f"Current Weather skilaði villu {current.status_code}: {current.text[:250]}")
    if forecast.status_code != 200:
        raise RuntimeError(f"Forecast skilaði villu {forecast.status_code}: {forecast.text[:250]}")
    return {"current": current.json(), "forecast": forecast.json(), "fallback": True}

def normalize_weather(data):
    """Return current dict, hourly dataframe, daily dataframe, alerts list."""
    if data.get("fallback"):
        c = data["current"]
        f = data["forecast"]
        weather = c.get("weather", [{}])[0]
        current = {
            "temp": c.get("main", {}).get("temp"),
            "feels_like": c.get("main", {}).get("feels_like"),
            "humidity": c.get("main", {}).get("humidity"),
            "pressure": c.get("main", {}).get("pressure"),
            "wind_speed": c.get("wind", {}).get("speed"),
            "wind_gust": c.get("wind", {}).get("gust"),
            "wind_deg": c.get("wind", {}).get("deg"),
            "clouds": c.get("clouds", {}).get("all"),
            "uvi": None,
            "visibility": c.get("visibility"),
            "sunrise": c.get("sys", {}).get("sunrise"),
            "sunset": c.get("sys", {}).get("sunset"),
            "main": weather.get("main"),
            "description": weather.get("description", "—"),
            "rain_1h": c.get("rain", {}).get("1h", 0),
            "snow_1h": c.get("snow", {}).get("1h", 0),
            "dt": c.get("dt"),
        }
        hourly_rows = []
        for item in f.get("list", []):
            weather = item.get("weather", [{}])[0]
            hourly_rows.append({
                "time": datetime.fromtimestamp(item.get("dt"), TZ),
                "temp": item.get("main", {}).get("temp"),
                "feels_like": item.get("main", {}).get("feels_like"),
                "wind": item.get("wind", {}).get("speed"),
                "gust": item.get("wind", {}).get("gust"),
                "rain": item.get("rain", {}).get("3h", 0) + item.get("snow", {}).get("3h", 0),
                "humidity": item.get("main", {}).get("humidity"),
                "pressure": item.get("main", {}).get("pressure"),
                "clouds": item.get("clouds", {}).get("all"),
                "main": weather.get("main"),
                "description": weather.get("description", "—"),
            })
        hourly = pd.DataFrame(hourly_rows)
        daily = pd.DataFrame()
        if not hourly.empty:
            tmp = hourly.copy()
            tmp["day"] = tmp["time"].dt.date
            daily = tmp.groupby("day").agg(
                temp_min=("temp", "min"),
                temp_max=("temp", "max"),
                wind_max=("wind", "max"),
                rain_sum=("rain", "sum"),
                humidity=("humidity", "mean"),
            ).reset_index()
            daily["label"] = pd.to_datetime(daily["day"]).dt.strftime("%a %d.%m.")
        return current, hourly, daily, []

    weather = data.get("current", {}).get("weather", [{}])[0]
    current = {
        "temp": data.get("current", {}).get("temp"),
        "feels_like": data.get("current", {}).get("feels_like"),
        "humidity": data.get("current", {}).get("humidity"),
        "pressure": data.get("current", {}).get("pressure"),
        "wind_speed": data.get("current", {}).get("wind_speed"),
        "wind_gust": data.get("current", {}).get("wind_gust"),
        "wind_deg": data.get("current", {}).get("wind_deg"),
        "clouds": data.get("current", {}).get("clouds"),
        "uvi": data.get("current", {}).get("uvi"),
        "visibility": data.get("current", {}).get("visibility"),
        "sunrise": data.get("current", {}).get("sunrise"),
        "sunset": data.get("current", {}).get("sunset"),
        "main": weather.get("main"),
        "description": weather.get("description", "—"),
        "rain_1h": data.get("current", {}).get("rain", {}).get("1h", 0),
        "snow_1h": data.get("current", {}).get("snow", {}).get("1h", 0),
        "dt": data.get("current", {}).get("dt"),
    }
    hourly_rows = []
    for item in data.get("hourly", []):
        weather = item.get("weather", [{}])[0]
        hourly_rows.append({
            "time": datetime.fromtimestamp(item.get("dt"), TZ),
            "temp": item.get("temp"),
            "feels_like": item.get("feels_like"),
            "wind": item.get("wind_speed"),
            "gust": item.get("wind_gust"),
            "rain": item.get("rain", {}).get("1h", 0) + item.get("snow", {}).get("1h", 0),
            "humidity": item.get("humidity"),
            "pressure": item.get("pressure"),
            "clouds": item.get("clouds"),
            "main": weather.get("main"),
            "description": weather.get("description", "—"),
        })
    daily_rows = []
    for item in data.get("daily", []):
        weather = item.get("weather", [{}])[0]
        daily_rows.append({
            "date": datetime.fromtimestamp(item.get("dt"), TZ).date(),
            "label": fmt_day(item.get("dt")),
            "temp_min": item.get("temp", {}).get("min"),
            "temp_max": item.get("temp", {}).get("max"),
            "wind_max": item.get("wind_speed"),
            "gust": item.get("wind_gust"),
            "rain_sum": item.get("rain", 0) + item.get("snow", 0),
            "humidity": item.get("humidity"),
            "uvi": item.get("uvi"),
            "main": weather.get("main"),
            "description": weather.get("description", "—"),
            "sunrise": item.get("sunrise"),
            "sunset": item.get("sunset"),
        })
    return current, pd.DataFrame(hourly_rows), pd.DataFrame(daily_rows), data.get("alerts", [])

def load_weather(place, show_messages=True):
    api_key = get_api_key()
    coords = PLACES[place]
    try:
        data = call_openweather_onecall(coords["lat"], coords["lon"], api_key)
        source = "OpenWeather One Call 3.0"
    except Exception as e:
        try:
            data = call_openweather_fallback(coords["lat"], coords["lon"], api_key)
            source = "OpenWeather 2.5 fallback"
            # One Call 3.0 þarf sérstaka áskrift hjá OpenWeather.
            # Ef hún er ekki virk notum við OpenWeather 2.5 fallback í hljóði,
            # svo venjulegir notendur sjái ekki tækniskilaboð á síðunni.
            pass
        except Exception as e2:
            st.error("Náði ekki að sækja veðurgögn. Athugaðu OPENWEATHER_API_KEY í .env eða secrets.")
            with st.expander("Sjá villu"):
                st.code(str(e2))
            st.stop()
    return (*normalize_weather(data), source)

def render_header():
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="🌦️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown("""
    <style>
    .main .block-container {padding-top: 1.3rem; padding-bottom: 3rem;}
    .weather-hero {
        border-radius: 28px;
        padding: 28px;
        background: radial-gradient(circle at top left, rgba(105,176,255,.34), transparent 35%),
                    linear-gradient(135deg, #0b1220 0%, #172554 48%, #0369a1 100%);
        color: white;
        box-shadow: 0 18px 55px rgba(15,23,42,.25);
    }
    .metric-card {
        border: 1px solid rgba(148,163,184,.22);
        border-radius: 22px;
        padding: 18px;
        background: rgba(255,255,255,.78);
        box-shadow: 0 10px 30px rgba(15,23,42,.08);
    }
    .metric-label {font-size: .9rem; color: #475569; margin-bottom: .15rem;}
    .metric-value {font-size: 1.55rem; font-weight: 800; color: #0f172a;}
    .small-muted {color: #64748b; font-size: .92rem;}
    .pill {
        display:inline-block; padding: .35rem .65rem; border-radius:999px;
        background:#e0f2fe; color:#075985; font-weight:700; font-size:.85rem;
        margin:.12rem;
    }
    .danger {background:#fee2e2; color:#991b1b;}
    .warn {background:#fef3c7; color:#92400e;}
    .good {background:#dcfce7; color:#166534;}
    .edu-card {
        border-radius: 24px;
        padding: 22px;
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e2e8f0;
        min-height: 185px;
    }

    /* v1.2 responsive polish fyrir síma og iPad */
    div[data-testid="stSidebar"] {min-width: 285px;}
    .sudurland-score {
        border-radius: 30px;
        padding: 26px;
        background: linear-gradient(135deg, #082f49 0%, #0f766e 58%, #65a30d 100%);
        color: white;
        box-shadow: 0 18px 55px rgba(15,23,42,.22);
        margin-bottom: 18px;
    }
    .decision-card {
        border: 1px solid rgba(148,163,184,.22);
        border-radius: 22px;
        padding: 18px;
        background: rgba(255,255,255,.88);
        box-shadow: 0 10px 25px rgba(15,23,42,.08);
        min-height: 158px;
    }
    .big-score {font-size:4.6rem; font-weight:950; line-height:.95;}
    .action-title {font-size:1.05rem; font-weight:850; color:#0f172a; margin-bottom:.35rem;}
    .action-status {font-size:1.55rem; font-weight:950; margin:.15rem 0 .35rem 0;}
    .mobile-only-note {display:none;}
    @media (max-width: 900px) {
        .main .block-container {padding-left: .8rem; padding-right: .8rem; padding-top: .75rem;}
        .weather-hero, .sudurland-score {border-radius: 20px; padding: 18px;}
        .weather-hero div[style*="font-size:3.2rem"] {font-size:2.15rem !important;}
        .big-score {font-size:3.0rem;}
        .metric-card, .edu-card, .decision-card {border-radius: 18px; padding: 14px; min-height: auto;}
        .metric-value {font-size:1.25rem;}
        .pill {font-size:.78rem; padding:.3rem .52rem;}
        .mobile-only-note {display:block;}
    }
    @media (max-width: 520px) {
        .weather-hero div[style*="font-size:3.2rem"] {font-size:1.75rem !important;}
        .weather-hero div[style*="font-size:4.2rem"] {font-size:2.7rem !important;}
        .sudurland-score h1 {font-size:1.6rem !important;}
        .big-score {font-size:2.45rem;}
        .metric-label {font-size:.82rem;}
        .small-muted {font-size:.84rem;}
    }

    .map-hub-hero {
        border-radius: 28px;
        padding: 26px;
        background: radial-gradient(circle at top left, rgba(255,255,255,.24), transparent 34%),
                    linear-gradient(135deg, #0f172a 0%, #155e75 48%, #0f766e 100%);
        color: white;
        box-shadow: 0 18px 55px rgba(15,23,42,.22);
        margin-bottom: 18px;
    }
    .map-link-card {
        border: 1px solid rgba(148,163,184,.25);
        border-radius: 22px;
        padding: 18px;
        background: rgba(255,255,255,.88);
        box-shadow: 0 10px 25px rgba(15,23,42,.07);
        min-height: 148px;
    }
    .projector-card {
        border-radius: 30px;
        padding: 30px;
        background: linear-gradient(135deg, #020617 0%, #0f172a 44%, #075985 100%);
        color: white;
        min-height: 390px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        box-shadow: 0 20px 65px rgba(15,23,42,.28);
    }

    .diary-hero {
        border-radius: 30px;
        padding: 26px;
        background: radial-gradient(circle at top left, rgba(255,255,255,.22), transparent 34%),
                    linear-gradient(135deg, #312e81 0%, #0369a1 48%, #16a34a 100%);
        color: white;
        box-shadow: 0 18px 55px rgba(15,23,42,.22);
        margin-bottom: 18px;
    }
    .diary-card {
        border: 1px solid rgba(148,163,184,.25);
        border-radius: 22px;
        padding: 18px;
        background: rgba(255,255,255,.9);
        box-shadow: 0 10px 25px rgba(15,23,42,.07);
        min-height: 142px;
    }
    .badge-row {display:flex; gap:8px; flex-wrap:wrap; margin-top:8px;}
    @media (max-width: 900px) {
        .diary-hero {border-radius:20px; padding:18px;}
        .diary-card {border-radius:18px; padding:14px; min-height:auto;}
    }



    .distance-hero {
        border-radius: 30px;
        padding: 26px;
        background: radial-gradient(circle at top left, rgba(255,255,255,.24), transparent 34%),
                    linear-gradient(135deg, #14532d 0%, #0f766e 46%, #0369a1 100%);
        color: white;
        box-shadow: 0 18px 55px rgba(15,23,42,.22);
        margin-bottom: 18px;
    }
    .distance-card {
        border: 1px solid rgba(148,163,184,.25);
        border-radius: 22px;
        padding: 18px;
        background: rgba(255,255,255,.9);
        box-shadow: 0 10px 25px rgba(15,23,42,.07);
        min-height: 130px;
    }
    .route-step {
        border-radius: 16px;
        padding: 10px 12px;
        margin: 6px 0;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
    }
    @media (max-width: 900px) {
        .distance-hero {border-radius:20px; padding:18px;}
        .distance-card {border-radius:18px; padding:14px; min-height:auto;}
    }


    /* v1.7 Veðurleiðangrar */
    .challenge-hero {
        border-radius: 28px;
        padding: 26px;
        background: radial-gradient(circle at top left, rgba(255,255,255,.26), transparent 36%),
                    linear-gradient(135deg, #1e1b4b 0%, #0369a1 52%, #15803d 100%);
        color: white;
        box-shadow: 0 18px 55px rgba(15,23,42,.22);
        margin-bottom: 18px;
    }
    .challenge-card, .symbol-card {
        border: 1px solid rgba(148,163,184,.25);
        border-radius: 22px;
        padding: 18px;
        background: rgba(255,255,255,.90);
        box-shadow: 0 10px 25px rgba(15,23,42,.07);
        min-height: 160px;
    }
    .symbol-emoji {font-size:2.4rem; line-height:1; margin-bottom:.25rem;}
    .challenge-title {font-size:1.18rem; font-weight:900; color:#0f172a; margin-bottom:.35rem;}
    @media (max-width: 900px) {
        .challenge-hero {border-radius:20px; padding:18px;}
        .challenge-card, .symbol-card {border-radius:18px; padding:14px; min-height:auto;}
        .symbol-emoji {font-size:2rem;}
    }


    /* v1.9 Veðurborð skólans / upplýsingaskjár */
    .school-board-hero {
        border-radius: 34px;
        padding: 34px;
        background: radial-gradient(circle at top left, rgba(255,255,255,.22), transparent 34%),
                    linear-gradient(135deg, #020617 0%, #0f172a 42%, #075985 100%);
        color: white;
        box-shadow: 0 24px 75px rgba(15,23,42,.32);
        margin-bottom: 18px;
    }
    .board-temp {font-size:6.4rem; font-weight:950; line-height:.9; letter-spacing:-.06em;}
    .board-place {font-size:2.2rem; font-weight:900; line-height:1.05;}
    .board-sub {font-size:1.2rem; opacity:.9;}
    .board-card {
        border-radius: 28px;
        padding: 24px;
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e2e8f0;
        box-shadow: 0 14px 35px rgba(15,23,42,.09);
        min-height: 170px;
    }
    .board-card-dark {
        border-radius: 28px;
        padding: 24px;
        background: linear-gradient(135deg, #0f172a 0%, #164e63 100%);
        color: white;
        box-shadow: 0 14px 35px rgba(15,23,42,.18);
        min-height: 170px;
    }
    .board-status {font-size:2.1rem; font-weight:950; line-height:1.05; margin:.2rem 0 .4rem 0;}
    .traffic-light {
        display:inline-flex; align-items:center; gap:10px;
        padding:.55rem .8rem; border-radius:999px; font-weight:900; font-size:1rem;
    }
    .board-message {
        border-radius: 24px;
        padding: 22px;
        background:#f8fafc;
        border:1px dashed #94a3b8;
        font-size:1.08rem;
        line-height:1.55;
    }
    @media (max-width: 900px) {
        .school-board-hero {border-radius:22px; padding:20px;}
        .board-temp {font-size:4.2rem;}
        .board-place {font-size:1.55rem;}
        .board-sub {font-size:1rem;}
        .board-card, .board-card-dark {border-radius:20px; padding:16px; min-height:auto;}
        .board-status {font-size:1.55rem;}
    }
    @media (max-width: 520px) {
        .board-temp {font-size:3.2rem;}
        .board-place {font-size:1.35rem;}
        .traffic-light {font-size:.88rem; padding:.45rem .62rem;}
    }


    .place-grid-card {
        border: 1px solid rgba(148,163,184,.22);
        border-radius: 22px;
        padding: 18px;
        background: linear-gradient(180deg, rgba(255,255,255,.96) 0%, rgba(248,250,252,.96) 100%);
        box-shadow: 0 10px 28px rgba(15,23,42,.08);
        min-height: 142px;
        transition: transform .16s ease, box-shadow .16s ease;
    }
    .place-grid-card:hover {transform: translateY(-2px); box-shadow: 0 16px 36px rgba(15,23,42,.12);}
    .place-title {font-size:1.15rem; font-weight:900; color:#0f172a; margin-bottom:.2rem;}
    .place-kind {font-size:.88rem; color:#475569; margin-bottom:.45rem;}
    .place-meta {font-size:.82rem; color:#64748b; line-height:1.35;}
    .place-active {border: 2px solid #0284c7; background: linear-gradient(180deg, #eff6ff 0%, #ecfeff 100%);}
    @media (max-width: 900px) {.place-grid-card {min-height:auto; padding:14px; border-radius:18px;}}
    </style>
    """, unsafe_allow_html=True)

def render_daily_weather_card(place, current, hourly):
    temp = current.get("temp")
    wind = current.get("wind_speed") or 0
    rain = (current.get("rain_1h") or 0) + (current.get("snow_1h") or 0)
    score, reasons = school_weather_score(temp, wind, rain, current.get("main"))
    best = pick_best_windows(hourly, 3)
    best_text = " · ".join(best["Tími"].tolist()) if not best.empty else "—"
    tip = clothing_tip(temp, wind, rain)
    klass = score_class(score)
    st.markdown(f"""
    <div class="edu-card" style="margin-top:18px;">
      <div style="display:flex; justify-content:space-between; gap:18px; flex-wrap:wrap; align-items:center;">
        <div>
          <h3 style="margin:0 0 8px 0;">🌤️ Veðurkort dagsins fyrir {place}</h3>
          <p style="margin:.2rem 0;"><b>Útiverumat:</b> <span class="pill {klass}">{score}% · {score_label(score)}</span></p>
          <p style="margin:.2rem 0;"><b>Bestu gluggar næstu 24 klst.:</b> {best_text}</p>
          <p style="margin:.2rem 0;"><b>Klæðnaður:</b> {tip}</p>
        </div>
        <div style="min-width:230px; text-align:right;">
          <div class="small-muted">Kennara-minnisblað</div>
          <div style="font-size:1.15rem; font-weight:800;">{', '.join(reasons)}</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

def render_current(place, current, source):
    temp = current.get("temp")
    wind = current.get("wind_speed")
    rain = (current.get("rain_1h") or 0) + (current.get("snow_1h") or 0)
    wc = wind_chill(temp, wind)
    score, reasons = school_weather_score(temp, wind, rain, current.get("main"))
    score_label = "Frábært í útiveru" if score >= 75 else "Skoða aðstæður" if score >= 45 else "Frekar inni eða mjög stutt útivera"
    score_class = "good" if score >= 75 else "warn" if score >= 45 else "danger"

    st.markdown(f"""
    <div class="weather-hero">
      <div style="display:flex; justify-content:space-between; gap:20px; align-items:flex-start; flex-wrap:wrap;">
        <div>
          <div style="font-size:1rem; opacity:.82;">{APP_TITLE} · v{APP_VERSION}</div>
          <div style="font-size:3.2rem; font-weight:900; line-height:1.03; margin-top:.35rem;">
            {weather_icon(current.get("main"))} {place}: {temp:.1f}°C
          </div>
          <div style="font-size:1.25rem; opacity:.95; margin-top:.4rem;">{current.get("description", "—").capitalize()}</div>
          <div style="margin-top:1rem;">
            <span class="pill {score_class}">Skólaveður: {score_label}</span>
            <span class="pill">Heimild: {source}</span>
            <span class="pill">Uppfært: {fmt_time(current.get("dt"))}</span>
          </div>
        </div>
        <div style="min-width:250px; text-align:right;">
          <div style="font-size:.9rem; opacity:.8;">Útikennslumælir</div>
          <div style="font-size:4.2rem; font-weight:900;">{score}%</div>
          <div style="opacity:.88;">{", ".join(reasons)}</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    metrics = [
        ("Tilfinning", f"{current.get('feels_like', temp):.1f}°C", f"Vindkæling: {wc:.1f}°C" if wc is not None else "—"),
        ("Vindur", f"{wind or 0:.1f} m/s", f"{deg_to_compass(current.get('wind_deg'))} · hviður {current.get('wind_gust') or 0:.1f} m/s"),
        ("Úrkoma", f"{rain:.1f} mm", "síðasta klst. / núverandi"),
        ("Sólin", f"{fmt_time(current.get('sunrise'))}–{fmt_time(current.get('sunset'))}", "sólupprás – sólsetur"),
    ]
    for col, (label, value, helptext) in zip([c1,c2,c3,c4], metrics):
        with col:
            st.markdown(f"""
            <div class="metric-card">
              <div class="metric-label">{label}</div>
              <div class="metric-value">{value}</div>
              <div class="small-muted">{helptext}</div>
            </div>
            """, unsafe_allow_html=True)

    c5, c6, c7, c8 = st.columns(4)
    extra = [
        ("Rakastig", f"{current.get('humidity') or 0:.0f}%", "loftið er rakara eftir því sem talan hækkar"),
        ("Loftþrýstingur", f"{current.get('pressure') or 0:.0f} hPa", "lækkandi þrýstingur getur bent til lægðar"),
        ("Skýjahula", f"{current.get('clouds') or 0:.0f}%", "hversu mikið af himni er skýjað"),
        ("UV", f"{current.get('uvi') if current.get('uvi') is not None else '—'}", "fæst í One Call 3.0"),
    ]
    for col, (label, value, helptext) in zip([c5,c6,c7,c8], extra):
        with col:
            st.markdown(f"""
            <div class="metric-card">
              <div class="metric-label">{label}</div>
              <div class="metric-value">{value}</div>
              <div class="small-muted">{helptext}</div>
            </div>
            """, unsafe_allow_html=True)


def _place_tile_emoji(kind):
    kind = (kind or "").lower()
    if "fjall" in kind:
        return "🏔️"
    if "höfn" in kind or "ferja" in kind:
        return "⛴️"
    if "ey" in kind:
        return "🏝️"
    if "þjóðgar" in kind:
        return "🌿"
    if "skóla" in kind:
        return "🏫"
    if "sjávar" in kind:
        return "🌊"
    if "sveit" in kind:
        return "🌾"
    if "samanbur" in kind:
        return "🏙️"
    return "📍"


def _distance_from_selfoss(place):
    if place == "Selfoss" or place not in PLACES:
        return 0
    a = PLACES["Selfoss"]
    b = PLACES[place]
    return haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])


def render_place_tiles(selected_place):
    st.markdown("### 🧭 Staðaflísar Suðurlands")
    st.caption("Smelltu á flís til að færa yfirlitið strax yfir á þann stað. Þetta virkar líka vel á síma og iPad.")

    search = st.text_input("Leita í stöðum", placeholder="t.d. Selfoss, Hella, Vík, Hellisheiði...", key="place_tile_search")
    kind_filter = st.selectbox(
        "Sía eftir tegund",
        ["Allir"] + sorted({v.get("kind", "staður") for v in PLACES.values()}),
        key="place_tile_kind_filter",
    )

    places = []
    for name, info in PLACES.items():
        if search and search.lower() not in name.lower() and search.lower() not in info.get("kind", "").lower():
            continue
        if kind_filter != "Allir" and info.get("kind") != kind_filter:
            continue
        places.append((name, info, _distance_from_selfoss(name)))

    places.sort(key=lambda item: item[2])
    if not places:
        st.info("Enginn staður fannst með þessari leit/síu.")
        return

    cols_per_row = 4
    for i in range(0, len(places), cols_per_row):
        cols = st.columns(cols_per_row)
        for col, (name, info, dist) in zip(cols, places[i:i+cols_per_row]):
            active = name == selected_place
            card_class = "place-grid-card place-active" if active else "place-grid-card"
            emoji = _place_tile_emoji(info.get("kind"))
            with col:
                st.markdown(f"""
                <div class="{card_class}">
                  <div class="place-title">{emoji} {name}</div>
                  <div class="place-kind">{info.get('kind', 'staður')}</div>
                  <div class="place-meta">Loftlína frá Selfossi: <b>{dist:.0f} km</b><br>Hnit: {info.get('lat'):.3f}, {info.get('lon'):.3f}</div>
                </div>
                """, unsafe_allow_html=True)
                label = "Opnað" if active else "Opna yfirlit"
                if st.button(label, key=f"tile_open_{name}", use_container_width=True, disabled=active):
                    st.session_state["selected_place"] = name
                    st.rerun()

    st.markdown("#### 💡 Kennsluhugmynd með flísunum")
    st.info("Láttu nemendur velja þrjá staði á Suðurlandi, bera saman veður, loftlínu frá Selfossi, vind og úrkomu. Síðan rökstyðja þau hvar væri best að fara í útikennslu eða vettvangsferð í dag.")

def render_forecast(hourly, daily):
    st.subheader("📈 Spá fram í tímann")
    if hourly.empty:
        st.warning("Engin klukkustundaspá fannst.")
        return

    h = hourly.head(48).copy()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=h["time"], y=h["temp"], mode="lines+markers", name="Hiti °C"))
    fig.add_trace(go.Scatter(x=h["time"], y=h["feels_like"], mode="lines", name="Tilfinning °C"))
    fig.update_layout(
        height=360,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h"),
        yaxis_title="°C",
        xaxis_title="Tími",
    )
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        fig2 = px.bar(h, x="time", y="rain", title="Úrkoma næstu 48 klst.", labels={"rain": "mm", "time": "Tími"})
        fig2.update_layout(height=320, margin=dict(l=10, r=10, t=45, b=10))
        st.plotly_chart(fig2, use_container_width=True)
    with c2:
        fig3 = px.line(h, x="time", y="wind", title="Vindur næstu 48 klst.", labels={"wind": "m/s", "time": "Tími"}, markers=True)
        fig3.update_layout(height=320, margin=dict(l=10, r=10, t=45, b=10))
        st.plotly_chart(fig3, use_container_width=True)

    st.subheader("🗓️ Dagaspá")
    if daily.empty:
        st.info("Dagaspá er takmörkuð í fallback-ham, en hér má sjá samantekt úr 3 klst. spá.")
        return
    cols = st.columns(min(4, len(daily)))
    for idx, row in daily.head(8).iterrows():
        with cols[idx % len(cols)]:
            title = row.get("label") or str(row.get("date"))
            main = row.get("main") or ""
            desc = row.get("description") or ""
            st.markdown(f"""
            <div class="metric-card">
              <div class="metric-label">{title}</div>
              <div class="metric-value">{weather_icon(main)} {row.get('temp_min', 0):.0f}° / {row.get('temp_max', 0):.0f}°</div>
              <div class="small-muted">{desc.capitalize()}</div>
              <div class="small-muted">Vindur allt að {row.get('wind_max', 0):.1f} m/s · úrkoma {row.get('rain_sum', 0):.1f} mm</div>
            </div>
            """, unsafe_allow_html=True)

def render_school(hourly):
    st.subheader("🏫 Skólaveður og útikennsla")
    st.write("Kerfið metur næstu tíma út frá hita, vindi, úrkomu og veðurlýsingu. Þetta kemur ekki í stað opinberra viðvarana, en hjálpar kennara að taka fljóta ákvörðun.")
    if hourly.empty:
        st.warning("Engin klukkustundaspá til að meta.")
        return
    rows = []
    for _, r in hourly.head(16).iterrows():
        score, reasons = school_weather_score(r.get("temp"), r.get("wind"), r.get("rain"), r.get("main"))
        rows.append({
            "Tími": r["time"].strftime("%H:%M"),
            "Hiti": round(r.get("temp", 0), 1),
            "Vindur m/s": round(r.get("wind", 0), 1),
            "Úrkoma mm": round(r.get("rain", 0), 1),
            "Mat": score,
            "Ábending": ", ".join(reasons),
        })
    df = pd.DataFrame(rows)
    best = df.sort_values("Mat", ascending=False).head(3)
    st.success("Bestu tímarnir fyrir útiveru í dag: " + " · ".join(best["Tími"].tolist()))
    st.info("Klæðnaður núna: " + clothing_tip(hourly.iloc[0].get("temp"), hourly.iloc[0].get("wind"), hourly.iloc[0].get("rain")))
    fig = px.bar(df, x="Tími", y="Mat", hover_data=["Ábending", "Hiti", "Vindur m/s", "Úrkoma mm"], title="Útikennslumælir næstu tíma")
    fig.update_layout(height=330, margin=dict(l=10, r=10, t=45, b=10), yaxis_range=[0, 100])
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("#### Fljótleg kennaraákvörðun")
    c1, c2, c3 = st.columns(3)
    c1.info("**Grænt:** útikennsla, gönguferð eða leikur líklega í góðu lagi.")
    c2.warning("**Gult:** styttri útivera, betri klæðnaður, skoða vind og úrkomu.")
    c3.error("**Rautt:** halda sig inni eða fara aðeins út í mjög stuttan tíma.")

    st.markdown("#### Tillögur eftir aðstæðum")
    st.markdown("""
    - **Frímínútur:** skoða sérstaklega vind og úrkomu næstu 1–3 klst.
    - **Útikennsla:** velja besta gluggann og hafa styttri fyrirmæli inni áður en farið er út.
    - **Íþróttir úti:** varast mikinn vind, hálku og kulda í fingrum/andliti.
    - **Ferð með bekk:** nota Ferðaveður-flipann og opna Umferðina áður en lagt er af stað.
    """)

def render_travel(selected_route):
    st.subheader("🚗 Ferðaveður á Suðurlandi")
    st.write("Hér er einfalt ferðamat byggt á veðri á nokkrum punktum á leiðinni. Skoðaðu alltaf opinberar upplýsingar um færð áður en lagt er af stað.")
    points = ROUTES[selected_route]
    rows = []
    for p in points:
        current, hourly, daily, alerts, source = load_weather(p, show_messages=False)
        rows.append({
            "place": p,
            "temp": current.get("temp"),
            "wind": current.get("wind_speed"),
            "gust": current.get("wind_gust"),
            "rain": (current.get("rain_1h") or 0) + (current.get("snow_1h") or 0),
            "desc": current.get("description", "—"),
            "main": current.get("main"),
        })
    score, label, reasons = travel_score(rows)
    st.metric("Ferðamat", label, f"{score}%")
    if reasons:
        st.warning("Athuga sérstaklega: " + " · ".join(reasons))
    else:
        st.success("Engin stór veðurmerki komu upp í einföldu mati.")
    cols = st.columns(len(rows))
    for col, r in zip(cols, rows):
        with col:
            st.markdown(f"""
            <div class="metric-card">
              <div class="metric-label">{r['place']}</div>
              <div class="metric-value">{weather_icon(r['main'])} {r['temp']:.1f}°C</div>
              <div class="small-muted">{r['desc'].capitalize()}</div>
              <div class="small-muted">Vindur {r['wind'] or 0:.1f} m/s · hviður {r['gust'] or 0:.1f} m/s</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("#### Opinberir tenglar")
    st.link_button("Opna Umferðina.is", "https://umferdin.is/")
    st.link_button("Opna Vegagerðina – ferðaupplýsingar", "https://www.vegagerdin.is/ferdaupplysingar")
    st.link_button("Opna Veðurstofu Íslands", "https://www.vedur.is/")


def slugify_place_for_zoom(place):
    mapping = {
        "Selfoss": "selfoss",
        "Eyrarbakki": "eyrarbakki",
        "Stokkseyri": "stokkseyri",
        "Hveragerði": "hveragerdi",
        "Þorlákshöfn": "thorlakshofn",
        "Hella": "hella",
        "Hvolsvöllur": "hvolsvollur",
        "Vík í Mýrdal": "vik",
        "Reykjavík": "reykjavik",
        "Vestmannaeyjar": "vestmannaeyjar",
    }
    return mapping.get(place, "selfoss")

def zoom_earth_place_url(place, layer="wind-speed", model="icon"):
    # Zoom Earth styður ekki endilega alla smærri staði sem sérslóð, svo Selfoss er fallback.
    slug = slugify_place_for_zoom(place)
    return f"https://zoom.earth/places/iceland/{slug}/#map={layer}/model={model}"

def zoom_earth_iceland_url(layer="wind-speed", model="icon"):
    return f"https://zoom.earth/maps/{layer}/#view=63.93,-20.99,7z/model={model}"

def render_external_map_buttons(place, selected_route):
    st.markdown("#### 🌍 Lifandi veðurkort")
    st.caption("Kortin opnast í nýjum flipa. Það er öruggara en iframe-innfelling, því sumir kortavefir loka á að vera felldir beint inn í önnur forrit.")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="map-link-card"><h3>🌬️ Vindhraði</h3><p class="small-muted">ICON vindkort fyrir Selfoss eða valinn stað.</p></div>', unsafe_allow_html=True)
        st.link_button("Opna vindhraða á Zoom Earth", zoom_earth_place_url(place, "wind-speed", "icon"), use_container_width=True)
    with c2:
        st.markdown('<div class="map-link-card"><h3>💨 Vindhviður</h3><p class="small-muted">Mjög gagnlegt fyrir Hellisheiði, ferðir og útiveru.</p></div>', unsafe_allow_html=True)
        st.link_button("Opna vindhviður", zoom_earth_iceland_url("wind-gusts", "icon"), use_container_width=True)
    with c3:
        st.markdown('<div class="map-link-card"><h3>🌧️ Úrkoma</h3><p class="small-muted">Skoða rigningu/snjó og hvort úrkoma sé að nálgast.</p></div>', unsafe_allow_html=True)
        st.link_button("Opna úrkomukort", zoom_earth_iceland_url("precipitation", "icon"), use_container_width=True)

    c4, c5, c6 = st.columns(3)
    with c4:
        st.markdown('<div class="map-link-card"><h3>🌡️ Hiti</h3><p class="small-muted">Hitakort gagnast vel til samanburðar milli staða.</p></div>', unsafe_allow_html=True)
        st.link_button("Opna hitakort", zoom_earth_iceland_url("temperature", "icon"), use_container_width=True)
    with c5:
        st.markdown('<div class="map-link-card"><h3>🛰️ Gervitungl</h3><p class="small-muted">Sjá skýjakerfi og lægðir nálgast Ísland.</p></div>', unsafe_allow_html=True)
        st.link_button("Opna gervitunglakort", "https://zoom.earth/maps/satellite/#view=63.93,-20.99,6z", use_container_width=True)
    with c6:
        st.markdown('<div class="map-link-card"><h3>🧭 Loftþrýstingur</h3><p class="small-muted">Gott til að útskýra lægðir, hæðir og vind.</p></div>', unsafe_allow_html=True)
        st.link_button("Opna þrýstikort", zoom_earth_iceland_url("pressure", "icon"), use_container_width=True)

    st.markdown("#### 🚗 Ferðaleiða-hnappar")
    st.write(f"Valin leið: **{selected_route}**")
    route_points = ROUTES.get(selected_route, [])
    if route_points:
        cols = st.columns(min(4, len(route_points)))
        for col, point in zip(cols, route_points):
            with col:
                kind = PLACES.get(point, {}).get("kind", "staður")
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">{kind}</div>
                    <div class="metric-value">{point}</div>
                    <div class="small-muted">Opna vindkort fyrir þennan punkt eða næsta þekkta stað.</div>
                </div>
                """, unsafe_allow_html=True)
                st.link_button(f"🌬️ {point}", zoom_earth_place_url(point, "wind-speed", "icon"), use_container_width=True)

    st.markdown("#### 🇮🇸 Íslensk lykilkort og opinberar síður")
    a, b, c, d = st.columns(4)
    with a:
        st.link_button("🚦 Umferðin.is", "https://umferdin.is/", use_container_width=True)
    with b:
        st.link_button("⚠️ Viðvaranir VÍ", "https://www.vedur.is/vidvaranir/", use_container_width=True)
    with c:
        st.link_button("🌦️ Veðurstofa", "https://www.vedur.is/", use_container_width=True)
    with d:
        st.link_button("🛣️ Vegagerðin", "https://www.vegagerdin.is/ferdaupplysingar", use_container_width=True)

def render_projector_mode(place, current, hourly):
    temp = current.get("temp")
    wind = current.get("wind_speed") or 0
    rain = (current.get("rain_1h") or 0) + (current.get("snow_1h") or 0)
    score, reasons = school_weather_score(temp, wind, rain, current.get("main"))
    label, klass, emoji = status_from_score(score)
    best = get_best_window_text(hourly) if "get_best_window_text" in globals() else "—"
    st.markdown("#### 📺 Skjávarpahamur")
    st.markdown(f"""
    <div class="projector-card">
      <div style="display:flex; justify-content:space-between; gap:24px; flex-wrap:wrap; align-items:center;">
        <div>
          <div style="font-size:1.15rem; opacity:.82; font-weight:800;">Veðurvefur · skjávarpi</div>
          <div style="font-size:4.1rem; font-weight:950; line-height:1.02; margin:.3rem 0;">{weather_icon(current.get('main'))} {place}</div>
          <div style="font-size:2.15rem; font-weight:850;">{temp:.1f}°C · {current.get('description', '—').capitalize()}</div>
          <div style="font-size:1.25rem; opacity:.9; margin-top:1rem;">Vindur {wind:.1f} m/s · úrkoma {rain:.1f} mm · {', '.join(reasons)}</div>
        </div>
        <div style="text-align:right; min-width:240px;">
          <div style="font-size:1.05rem; opacity:.8;">Útikennslumælir</div>
          <div style="font-size:5.2rem; font-weight:950;">{score}%</div>
          <div style="font-size:1.35rem; font-weight:800;">{emoji} {label}</div>
        </div>
      </div>
      <div style="margin-top:2rem; font-size:1.25rem;"><b>Besti útigluggi:</b> {best}</div>
    </div>
    """, unsafe_allow_html=True)
    st.caption("Þessi hluti er hugsaður fyrir skjávarpa eða upplýsingaskjá í anddyri/stofu.")

def render_map_center(place, current, hourly, selected_route):
    st.subheader("🗺️ Kortamiðstöð Suðurlands")
    st.caption("v1.4: lifandi kort, ferðaleiðir, Zoom Earth, íslenskir tenglar og skjávarpahamur.")

    temp = current.get("temp")
    wind = current.get("wind_speed") or 0
    rain = (current.get("rain_1h") or 0) + (current.get("snow_1h") or 0)
    score, reasons = school_weather_score(temp, wind, rain, current.get("main"))
    label, klass, emoji = status_from_score(score)
    st.markdown(f"""
    <div class="map-hub-hero">
      <div style="display:flex; justify-content:space-between; gap:18px; flex-wrap:wrap; align-items:center;">
        <div>
          <div style="opacity:.88; font-weight:800;">Kortamiðstöð · {place}</div>
          <h1 style="font-size:2.3rem; margin:.25rem 0 .55rem 0;">{emoji} Vindur, úrkoma, færi og ferðamat á einum stað</h1>
          <div>
            <span class="pill {klass}">Staða {score}% · {label}</span>
            <span class="pill">Hiti {temp:.1f}°C</span>
            <span class="pill">Vindur {wind:.1f} m/s</span>
            <span class="pill">Úrkoma {rain:.1f} mm</span>
          </div>
        </div>
        <div style="text-align:right; min-width:210px;">
          <div style="opacity:.82;">Snögg ákvörðun</div>
          <div class="big-score">{score}%</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    tabs = st.tabs(["🌍 Lifandi kort", "📍 Staðakort", "📺 Skjávarpi", "🧑‍🏫 Kennsluhugmyndir"])
    with tabs[0]:
        render_external_map_buttons(place, selected_route)
    with tabs[1]:
        render_map(place)
    with tabs[2]:
        render_projector_mode(place, current, hourly)
    with tabs[3]:
        st.markdown("#### Verkefni með kortamiðstöðinni")
        st.success("**Vindverkefni:** Opnaðu vindhraða og vindhviður. Berðu saman Selfoss, Hellisheiði og Reykjavík. Hvar er vindurinn mestur?")
        st.info("**Úrkomuverkefni:** Opnaðu úrkomukort. Spáðu hvort það rigni á skólalóð næstu 2 klst. Berðu svo saman við raunveður.")
        st.warning("**Ferðaverkefni:** Veldu Selfoss → Reykjavík. Skoðaðu vind, hviður og Umferðina. Skrifaðu 3 atriði sem skipta máli fyrir örugga ferð.")
        st.markdown("""
        **Kennslutenging:** Kortamiðstöðin hentar vel í náttúrufræði, landafræði, stærðfræði og upplýsingatækni.
        Nemendur æfa að lesa kort, bera saman tölur, taka rökstudda ákvörðun og greina á milli spár og raunmælinga.
        """)

def render_map(selected_place):
    st.subheader("🗺️ Staðir í vefnum")
    df = pd.DataFrame([
        {"staður": k, "lat": v["lat"], "lon": v["lon"], "tegund": v["kind"]}
        for k, v in PLACES.items()
    ])
    st.map(df, latitude="lat", longitude="lon", size=80, zoom=8)
    st.caption(f"Valinn staður: {selected_place}")



# =========================
# Veðurstofa Íslands - CAP viðvaranir
# =========================
CAP_ACTIVE_DETAILED_URL = "https://api.vedur.is/cap/v1/capbroker/active/detailed/all"
CAP_ACTIVE_DETAILED_URL_ALT = "https://api.vedur.is/cap/capbroker/active/detailed/all"
CAP_ACTIVE_FEED_URL = "https://api.vedur.is/cap/v1/capbroker/active/feed/met"
CAP_ACTIVE_FEED_URL_ALT = "https://api.vedur.is/cap/capbroker/active/feed/met"
CAP_BASE_URL = "https://api.vedur.is/cap/v1"
CAP_SOURCE_URLS = [
    CAP_ACTIVE_DETAILED_URL,
    CAP_ACTIVE_DETAILED_URL + "/",
    CAP_ACTIVE_DETAILED_URL_ALT,
    CAP_ACTIVE_DETAILED_URL_ALT + "/",
    CAP_ACTIVE_FEED_URL,
    CAP_ACTIVE_FEED_URL_ALT,
]

SOUTH_ALERT_TERMS = [
    "suðurland", "sudurland", "south iceland", "south", "suðausturland", "sudausturland",
    "miðhálend", "mid highland", "hellisheiði", "hellisheidi", "vestmannaeyjar",
    "eyjafjall", "mýrdal", "myrdal", "vík", "vik", "selfoss", "árborg", "arborg",
    "hvolsvöllur", "hvolsvollur", "hella", "landeyjahöfn", "landeyjahofn"
]

SEVERITY_ORDER = {
    "Extreme": 4, "Severe": 3, "Moderate": 2, "Minor": 1, "Unknown": 0,
    "Rauð": 4, "Appelsínugul": 3, "Gul": 2, "Græn": 1,
}

SEVERITY_ICELANDIC = {
    "Extreme": "Rauð / mjög alvarleg",
    "Severe": "Appelsínugul / alvarleg",
    "Moderate": "Gul / varúð",
    "Minor": "Minni háttar",
    "Unknown": "Óþekkt",
}


def _text_contains_south(text):
    txt = str(text or "").lower()
    return any(term in txt for term in SOUTH_ALERT_TERMS)


def _cap_get(d, *keys, default=""):
    if not isinstance(d, dict):
        return default
    for k in keys:
        if k in d and d.get(k) not in (None, ""):
            return d.get(k)
    return default


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _find_cap_messages(payload):
    """Finnur CAP skilaboð í mismunandi JSON-formum án þess að treysta á eitt fast schema."""
    messages = []
    def walk(obj):
        if isinstance(obj, dict):
            # CAP skilaboð hafa oft identifier/sent/info eða properties.info
            if ("info" in obj and ("identifier" in obj or "sent" in obj or "msgType" in obj)):
                messages.append(obj)
                return
            if "properties" in obj and isinstance(obj["properties"], dict) and "info" in obj["properties"]:
                merged = dict(obj["properties"])
                if "geometry" in obj:
                    merged["geometry"] = obj.get("geometry")
                messages.append(merged)
                return
            for key in ["features", "messages", "items", "alerts", "data", "results"]:
                if key in obj:
                    walk(obj[key])
            # fallback: leita dýpra en passa að tvítaka ekki of mikið
            for v in obj.values():
                if isinstance(v, (list, dict)):
                    walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)
    walk(payload)
    # Hreinsa tvítekningar eftir identifier + sent
    unique = []
    seen = set()
    for msg in messages:
        key = (str(_cap_get(msg, "identifier", "id", default="")), str(_cap_get(msg, "sent", default="")))
        if key not in seen:
            seen.add(key)
            unique.append(msg)
    return unique


def _format_cap_time(value):
    if not value:
        return "—"
    txt = str(value)
    try:
        # styður bæði Z og ISO offset
        dt = datetime.fromisoformat(txt.replace("Z", "+00:00"))
        return dt.astimezone(TZ).strftime("%d.%m.%Y kl. %H:%M")
    except Exception:
        return txt


def _normalize_cap_alerts(payload):
    rows = []
    for msg in _find_cap_messages(payload):
        infos = _as_list(msg.get("info"))
        if not infos:
            infos = [msg]
        for info in infos:
            if not isinstance(info, dict):
                continue
            areas = _as_list(info.get("area"))
            area_names = []
            for area in areas:
                if isinstance(area, dict):
                    area_names.append(str(_cap_get(area, "areaDesc", "area", "name", default="")))
                elif area:
                    area_names.append(str(area))
            area_text = ", ".join([a for a in area_names if a]) or str(_cap_get(info, "areaDesc", "area", default=""))
            event = str(_cap_get(info, "event", "headline", default="Veðurviðvörun"))
            headline = str(_cap_get(info, "headline", "event", default=event))
            description = str(_cap_get(info, "description", "text", "summary", default=""))
            instruction = str(_cap_get(info, "instruction", "web", default=""))
            severity = str(_cap_get(info, "severity", "awareness_level", default="Unknown"))
            urgency = str(_cap_get(info, "urgency", default=""))
            certainty = str(_cap_get(info, "certainty", default=""))
            category = _cap_get(info, "category", default="")
            if isinstance(category, list):
                category = ", ".join(map(str, category))
            combined = " ".join([event, headline, description, instruction, area_text, str(category)])
            rows.append({
                "identifier": _cap_get(msg, "identifier", "id", default=""),
                "sent": _cap_get(msg, "sent", default=""),
                "sender": _cap_get(msg, "sender", "senderName", default="Veðurstofa Íslands"),
                "event": event,
                "headline": headline,
                "description": description,
                "instruction": instruction,
                "severity": severity,
                "severity_is": SEVERITY_ICELANDIC.get(severity, severity),
                "severity_score": SEVERITY_ORDER.get(severity, 0),
                "urgency": urgency,
                "certainty": certainty,
                "category": str(category),
                "area": area_text or "Ótilgreint svæði",
                "effective": _cap_get(info, "effective", default=""),
                "onset": _cap_get(info, "onset", default=""),
                "expires": _cap_get(info, "expires", default=""),
                "snertir_sudurland": _text_contains_south(combined),
            })
    return rows


def _xml_text(elem, tag_name):
    """Sækir texta úr XML án þess að þurfa að þekkja namespace nákvæmlega."""
    if elem is None:
        return ""
    for child in list(elem):
        if child.tag.split("}")[-1] == tag_name:
            return (child.text or "").strip()
    return ""


def _xml_children(elem, tag_name):
    if elem is None:
        return []
    return [child for child in list(elem) if child.tag.split("}")[-1] == tag_name]


def _normalize_cap_xml(xml_text):
    """Les CAP XML eða RSS/Atom feed frá Veðurstofu og skilar sömu röðum og JSON-lesarinn."""
    try:
        root = ET.fromstring(xml_text.encode("utf-8") if isinstance(xml_text, str) else xml_text)
    except Exception:
        return []

    rows = []
    # 1) Raunveruleg CAP <alert> skilaboð, ef þau eru í XML-inu.
    alerts = [el for el in root.iter() if el.tag.split("}")[-1] == "alert"]
    for alert in alerts:
        msg = {
            "identifier": _xml_text(alert, "identifier"),
            "sender": _xml_text(alert, "sender") or "Veðurstofa Íslands",
            "sent": _xml_text(alert, "sent"),
            "info": [],
        }
        for info in _xml_children(alert, "info"):
            area_names = []
            for area in _xml_children(info, "area"):
                desc = _xml_text(area, "areaDesc")
                if desc:
                    area_names.append(desc)
            msg["info"].append({
                "event": _xml_text(info, "event") or "Veðurviðvörun",
                "headline": _xml_text(info, "headline") or _xml_text(info, "event") or "Veðurviðvörun",
                "description": _xml_text(info, "description"),
                "instruction": _xml_text(info, "instruction"),
                "severity": _xml_text(info, "severity") or "Unknown",
                "urgency": _xml_text(info, "urgency"),
                "certainty": _xml_text(info, "certainty"),
                "category": _xml_text(info, "category"),
                "area": ", ".join(area_names),
                "effective": _xml_text(info, "effective"),
                "onset": _xml_text(info, "onset"),
                "expires": _xml_text(info, "expires"),
            })
        rows.extend(_normalize_cap_alerts(msg))

    if rows:
        return rows

    # 2) Ef þjónustan skilar RSS/Atom yfirliti í stað CAP XML, lesum titla og lýsingar.
    for item in [el for el in root.iter() if el.tag.split("}")[-1] in ("item", "entry")]:
        title = _xml_text(item, "title") or "Veðurviðvörun"
        summary = _xml_text(item, "summary") or _xml_text(item, "description") or ""
        updated = _xml_text(item, "updated") or _xml_text(item, "pubDate") or _xml_text(item, "published")
        combined = f"{title} {summary}"
        sev = "Unknown"
        low = combined.lower()
        if any(x in low for x in ["red", "rauð", "raudur"]):
            sev = "Extreme"
        elif any(x in low for x in ["orange", "appelsínugul"]):
            sev = "Severe"
        elif any(x in low for x in ["yellow", "gul"]):
            sev = "Moderate"
        rows.append({
            "identifier": title,
            "sent": updated,
            "sender": "Veðurstofa Íslands",
            "event": title,
            "headline": title,
            "description": summary,
            "instruction": "Skoðið nánari upplýsingar á vedur.is áður en ákvörðun er tekin.",
            "severity": sev,
            "severity_is": SEVERITY_ICELANDIC.get(sev, sev),
            "severity_score": SEVERITY_ORDER.get(sev, 0),
            "urgency": "",
            "certainty": "",
            "category": "Met",
            "area": "Sjá nánar á vedur.is",
            "effective": updated,
            "onset": updated,
            "expires": "",
            "snertir_sudurland": _text_contains_south(combined),
        })
    return rows


def _load_cap_from_url(url):
    headers = {
        "Accept": "application/json, application/xml;q=0.9, text/xml;q=0.9, */*;q=0.5",
        "User-Agent": "Vallaskoli-Vedurvefur/2.6.1 (+https://streamlit.app)",
    }
    r = requests.get(url, timeout=20, headers=headers)
    status = r.status_code
    ctype = (r.headers.get("content-type") or "").lower()
    text = r.text or ""
    if status in (204, 404) or not text.strip():
        return {"ok": True, "rows": [], "source": url, "note": f"Tómt svar eða engar virkar viðvaranir. HTTP {status}"}
    r.raise_for_status()

    # Prófum JSON fyrst þegar það lítur út eins og JSON.
    stripped = text.lstrip()
    if "json" in ctype or stripped.startswith(("{", "[")):
        payload = r.json()
        return {"ok": True, "rows": _normalize_cap_alerts(payload), "source": url, "note": "JSON"}

    # Annars prófum XML/RSS/Atom.
    if "xml" in ctype or stripped.startswith("<"):
        rows = _normalize_cap_xml(text)
        return {"ok": True, "rows": rows, "source": url, "note": "XML/RSS"}

    raise ValueError(f"Óþekkt svar frá CAP þjónustu. HTTP {status}, content-type={ctype}, byrjun={text[:80]!r}")


@st.cache_data(ttl=300, show_spinner=False)
def load_vedur_cap_alerts():
    """Sækir virkar CAP-viðvaranir frá Veðurstofu Íslands.

    API-ið hefur verið að skila mismunandi formum eftir endpointi og stöðu viðvarana,
    svo við reynum bæði /cap/v1 og /cap, JSON og RSS/XML áður en við gefumst upp.
    """
    errors = []
    for url in CAP_SOURCE_URLS:
        try:
            result = _load_cap_from_url(url)
            result.setdefault("rows", [])
            result.setdefault("error", "")
            result["ok"] = True
            return result
        except Exception as e:
            errors.append(f"{url} -> {type(e).__name__}: {e}")
    return {"ok": False, "rows": [], "error": "\n".join(errors), "source": ""}


def highest_cap_status(rows):
    if not rows:
        return "Engar virkar viðvaranir", "good", "✅", 0
    high = max([int(r.get("severity_score", 0) or 0) for r in rows])
    if high >= 4:
        return "Rauð viðvörun / mjög alvarlegt", "danger", "🔴", high
    if high >= 3:
        return "Appelsínugul viðvörun / alvarlegt", "danger", "🟠", high
    if high >= 2:
        return "Gul viðvörun / varúð", "warn", "🟡", high
    return "Viðvörun til skoðunar", "warn", "⚠️", high


def render_cap_alert_cards(rows, show_empty=True):
    if not rows:
        if show_empty:
            st.success("Engar virkar CAP-viðvaranir fundust í þessum flokki núna.")
        return
    for r in sorted(rows, key=lambda x: (x.get("severity_score", 0), str(x.get("onset") or x.get("effective") or "")), reverse=True):
        label = r.get("severity_is") or r.get("severity") or "Óþekkt"
        title = r.get("headline") or r.get("event") or "Veðurviðvörun"
        south = " · Suðurland tengt" if r.get("snertir_sudurland") else ""
        with st.expander(f"⚠️ {title} — {label}{south}", expanded=bool(r.get("snertir_sudurland"))):
            c1, c2, c3 = st.columns(3)
            c1.metric("Alvarleiki", label)
            c2.metric("Svæði", str(r.get("area") or "—")[:42])
            c3.metric("Gildir til", _format_cap_time(r.get("expires")))
            st.write(f"**Atburður:** {r.get('event') or '—'}")
            st.write(f"**Gildir frá:** {_format_cap_time(r.get('onset') or r.get('effective'))}")
            if r.get("description"):
                st.markdown("**Lýsing:**")
                st.write(r.get("description"))
            if r.get("instruction"):
                st.markdown("**Leiðbeiningar:**")
                st.write(r.get("instruction"))
            st.caption(f"Auðkenni: {r.get('identifier') or '—'} · Sent: {_format_cap_time(r.get('sent'))}")


def render_vedur_alert_summary(place=None, selected_route=None, compact=True):
    data = load_vedur_cap_alerts()
    if not data.get("ok"):
        if not compact:
            st.warning("Náði ekki að sækja viðvaranir frá Veðurstofu Íslands í augnablikinu.")
            st.caption(data.get("error", ""))
        return []
    rows = data.get("rows", [])
    south_rows = [r for r in rows if r.get("snertir_sudurland")]
    target_rows = south_rows or rows
    status, klass, emoji, _ = highest_cap_status(target_rows)
    if compact:
        if south_rows:
            st.warning(f"{emoji} Virkar viðvaranir sem gætu snert Suðurland: {len(south_rows)} · {status}")
        elif rows:
            st.info(f"⚠️ Virkar viðvaranir á landinu: {len(rows)}. Engin greinileg Suðurlandsviðvörun fannst í texta skilaboða.")
        else:
            st.success("✅ Engar virkar CAP-viðvaranir frá Veðurstofu Íslands fundust núna.")
    return rows


def render_vedur_alerts_page(place, current, hourly, selected_route):
    st.markdown("## ⚠️ Viðvaranir Veðurstofu Íslands")
    st.caption("Sækir virkar CAP-viðvaranir frá Veðurstofu Íslands og tengir þær við skóla-, ferðalaga- og kennslunotkun. Gögnin eru opinber viðvörunarskilaboð, en vefurinn okkar túlkar þau aðeins sem kennslu- og yfirlitstæki.")

    data = load_vedur_cap_alerts()
    if not data.get("ok"):
        st.error("Náði ekki að sækja viðvaranir frá Veðurstofu Íslands.")
        st.code(data.get("error", "Óþekkt villa"))
        st.link_button("Opna viðvaranir á vedur.is", "https://www.vedur.is/vidvaranir/")
        return

    rows = data.get("rows", [])
    south_rows = [r for r in rows if r.get("snertir_sudurland")]
    status_all, klass_all, emoji_all, high_all = highest_cap_status(rows)
    status_south, klass_south, emoji_south, high_south = highest_cap_status(south_rows)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Virkar viðvaranir", len(rows))
    c2.metric("Tengdar Suðurlandi", len(south_rows))
    c3.metric("Hæsta mat", status_south if south_rows else status_all)
    c4.metric("Valinn staður", place)

    if south_rows:
        st.markdown(f"""
        <div class="weather-hero" style="background:linear-gradient(135deg,#7c2d12,#f97316);">
          <div style="display:flex;justify-content:space-between;gap:18px;align-items:center;flex-wrap:wrap;">
            <div>
              <div style="opacity:.85;font-weight:800;">Viðvaranir · Suðurland</div>
              <h1 style="margin:.3rem 0;font-size:2.2rem;">{emoji_south} {status_south}</h1>
              <p style="margin:0;opacity:.9;">Skoðaðu áhrif á útikennslu, frímínútur, umferð og skólaferðir áður en ákvörðun er tekin.</p>
            </div>
            <div style="font-size:3rem;font-weight:900;">{len(south_rows)}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    elif rows:
        st.info("Það eru virkar viðvaranir á landinu, en engin fannst sem textinn tengir beint við Suðurland. Skoðaðu samt listann ef ferð er fyrirhuguð út fyrir Suðurland.")
    else:
        st.success("Engar virkar CAP-viðvaranir fundust núna.")

    tabs = st.tabs(["🌍 Suðurland", "🇮🇸 Allar viðvaranir", "🛡️ Áhrif á skóla/ferðir", "🧑‍🏫 Kennsluverkefni", "🔗 Gögn"])
    with tabs[0]:
        st.markdown("### Viðvaranir sem gætu snert Suðurland")
        render_cap_alert_cards(south_rows)
    with tabs[1]:
        st.markdown("### Allar virkar CAP-viðvaranir")
        render_cap_alert_cards(rows)
    with tabs[2]:
        st.markdown("### Hvernig hefur þetta áhrif á ákvarðanir?")
        target = south_rows or rows
        if not target:
            st.success("Engin virk viðvörun fannst. Venjulegt veðurmat vefsins gildir áfram.")
        else:
            _, _, _, high = highest_cap_status(target)
            if high >= 4:
                st.error("🔴 **Rauð eða mjög alvarleg viðvörun:** Ekki skipuleggja útikennslu eða skólaferðir nema stjórnendur meti aðstæður sérstaklega og fylgi opinberum leiðbeiningum.")
            elif high >= 3:
                st.warning("🟠 **Appelsínugul/alvarleg viðvörun:** Endurmeta skólaferðir, útikennslu og langa útiveru. Skoða þarf Umferðina, Veðurstofu og Vegagerð áður en farið er af stað.")
            elif high >= 2:
                st.warning("🟡 **Gul viðvörun:** Góð ástæða til að stytta útiveru, velja skjól, fylgjast með vindi/úrkomu og undirbúa foreldratilkynningu ef farið er í ferð.")
            else:
                st.info("⚠️ Viðvörun eða skilaboð eru til skoðunar. Lesið lýsingu og svæði áður en ákvörðun er tekin.")

            msg = f"""Stutt tilkynning:
Veðurstofa Íslands er með virka viðvörun sem gæti haft áhrif á skólastarf eða ferðir. Við fylgjumst með stöðu mála og metum útiveru/ferðir út frá veðri, færð og opinberum leiðbeiningum.

Valinn staður: {place}
Ferðaleið: {selected_route}
Viðvörunarstaða: {highest_cap_status(target)[0]}
"""
            st.text_area("Afritanleg tilkynning", msg, height=170)
            c1, c2, c3 = st.columns(3)
            c1.link_button("Veðurstofan — viðvaranir", "https://www.vedur.is/vidvaranir/")
            c2.link_button("Umferðin.is", "https://umferdin.is/")
            c3.link_button("Vegagerðin", "https://www.vegagerdin.is/")
    with tabs[3]:
        assignment = f"""Verkefni: Veðurviðvaranir Veðurstofu Íslands

1. Opnaðu flipann Viðvaranir.
2. Finndu hvort einhver viðvörun tengist Suðurlandi.
3. Skráðu: lit/stig viðvörunar, svæði, tíma og helstu hættu.
4. Útskýrðu með eigin orðum hvað viðvörunin þýðir fyrir:
   a) frímínútur
   b) útikennslu
   c) ferð frá Selfossi til Reykjavíkur eða Víkur
5. Berðu saman við vind, úrkomu og hitastig í Veðurvefnum.
6. Skrifaðu 3 ráð til nemenda eða foreldra.

Aukaverkefni: Finndu á korti hvaða svæði viðvörunin nær yfir og útskýrðu af hverju veður getur verið verra á fjallvegum en í byggð.
"""
        st.text_area("Afritanlegt verkefni", assignment, height=310)
        st.download_button("⬇️ Sækja verkefni sem TXT", assignment, file_name="vedurvidvaranir_verkefni.txt", mime="text/plain")
        st.info("Kennslutenging: náttúrufræði, landafræði, upplýsinga- og miðlalæsi, samfélagsfræði og lífsleikni.")
    with tabs[4]:
        st.markdown("### API-tenging")
        st.code("\n".join(CAP_SOURCE_URLS))
        st.write("Vefurinn reynir fyrst JSON frá CAP API og fellur svo yfir í XML/RSS ef þjónustan skilar ekki JSON. Þetta kemur í veg fyrir villuna `Expecting value: line 1 column 1` þegar þjónustan skilar tómu eða XML-svari.")
        st.link_button("Opna CAP API skjöl", "https://api.vedur.is/")
        st.link_button("Opna viðvaranir á vedur.is", "https://www.vedur.is/vidvaranir/")

def render_alerts(alerts):
    st.subheader("⚠️ Viðvaranir")
    render_vedur_alert_summary(compact=True)
    if not alerts:
        st.caption("OpenWeather skilaði engum sérviðvörunum með þessu kalli. CAP-viðvaranir Veðurstofu Íslands eru birtar hér að ofan og í sér flipanum Viðvaranir.")
        st.link_button("Opna viðvaranir Veðurstofu Íslands", "https://www.vedur.is/vidvaranir/")
        return
    st.markdown("#### OpenWeather-viðvaranir")
    for a in alerts:
        with st.expander(a.get("event", "Viðvörun"), expanded=True):
            start = fmt_time(a.get("start"))
            end = fmt_time(a.get("end"))
            st.write(f"**Frá:** {start}  **Til:** {end}")
            st.write(a.get("description", ""))

def render_education():
    st.subheader("📚 Veðurfróðleikur, loftslag og jöklar")
    cols = st.columns(2)
    for i, fact in enumerate(FACTS):
        with cols[i % 2]:
            st.markdown(f"""
            <div class="edu-card">
              <h3>{fact['title']}</h3>
              <p>{fact['text']}</p>
              <p class="small-muted"><b>Í kennslu:</b> {fact['classroom']}</p>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("#### Verkefnahugmyndir fyrir nemendur")
    st.write("""
    - Veldu tvo staði, t.d. Selfoss og Hellisheiði. Berðu saman hita, vind og úrkomu.
    - Fylgstu með loftþrýstingi í 5 daga. Hvað gerist þegar þrýstingur lækkar?
    - Búðu til veðurfrétt fyrir Suðurland með 60 sekúndna myndbandi.
    - Teiknaðu ferðaleið og merktu inn hvar veðrið breytist mest.
    - Ræddu: Hvernig geta hlýnandi vetur haft áhrif á snjó, jökla, ár og útivist?
    """)

def render_sources():
    st.subheader("🔗 Gögn og næstu tengingar")
    st.write("""
    Fyrsta útgáfan notar OpenWeather sem aðalveðurspá. Næsta skref er að tengja betur við íslensk gögn:
    Veðurstofu Íslands fyrir opinbera íslenska spá og viðvaranir, og Vegagerðina/Umferðina fyrir færð, vegaveður og myndavélar.
    """)
    st.link_button("OpenWeather One Call API", "https://openweathermap.org/api/one-call-3")
    st.link_button("Veðurstofa Íslands API", "https://api.vedur.is/")
    st.link_button("CAP viðvaranir Veðurstofu", "https://api.vedur.is/")
    st.link_button("Viðvaranir á vedur.is", "https://www.vedur.is/vidvaranir/")
    st.link_button("Umferðin.is", "https://umferdin.is/")
    st.link_button("Gagnaveita Vegagerðarinnar", "https://gagnaveita.vegagerdin.is/")
    st.link_button("Zoom Earth vindkort Selfoss", "https://zoom.earth/places/iceland/selfoss/#map=wind-speed/model=icon")


def status_from_score(score):
    if score >= 80:
        return "Frábært", "good", "✅"
    if score >= 60:
        return "Gott", "good", "✅"
    if score >= 40:
        return "Varúð", "warn", "⚠️"
    return "Ekki mælt með", "danger", "⛔"

def evaluate_school_decisions(current, hourly):
    temp = current.get("temp")
    wind = current.get("wind_speed") or 0
    rain = (current.get("rain_1h") or 0) + (current.get("snow_1h") or 0)
    now_score, now_reasons = school_weather_score(temp, wind, rain, current.get("main"))

    next_24 = hourly.head(24).copy() if not hourly.empty else pd.DataFrame()
    avg_score = now_score
    max_wind = wind
    max_rain = rain
    min_temp = temp if temp is not None else 0
    best_times = "—"
    if not next_24.empty:
        scores = []
        for _, r in next_24.iterrows():
            sc, _ = school_weather_score(r.get("temp"), r.get("wind"), r.get("rain"), r.get("main"))
            scores.append(sc)
        next_24["score"] = scores
        avg_score = round(sum(scores[:8]) / max(1, len(scores[:8])))
        max_wind = float(next_24["wind"].max()) if "wind" in next_24 else wind
        max_rain = float(next_24["rain"].max()) if "rain" in next_24 else rain
        min_temp = float(next_24["temp"].min()) if "temp" in next_24 else (temp or 0)
        # Veljum aðeins raunhæfa skólatíma, ekki miðnætti.
        school_best = next_24[(next_24["time"].dt.hour >= 8) & (next_24["time"].dt.hour <= 16)].copy()
        if school_best.empty:
            school_best = next_24.copy()
        best = school_best.sort_values(["score", "time"], ascending=[False, True]).head(3)
        best_times = " · ".join([_friendly_time_label(t) for t in best["time"].tolist()])

    # Sérhæfð ákvörðunarkort
    frimin_score = max(0, min(100, now_score + (5 if rain < .5 else -10)))
    outdoor_score = max(0, min(100, avg_score))
    sports_score = max(0, min(100, avg_score - (12 if max_wind >= 10 else 0)))
    trip_score = max(0, min(100, avg_score - (10 if max_wind >= 12 else 0) - (8 if min_temp < 0 else 0)))

    return {
        "overall": round((frimin_score + outdoor_score + sports_score + trip_score) / 4),
        "best_times": best_times,
        "now_reasons": now_reasons,
        "max_wind": max_wind,
        "max_rain": max_rain,
        "min_temp": min_temp,
        "cards": [
            {"title":"Frímínútur", "emoji":"🛝", "score":frimin_score, "text":"Hentar til stuttrar útiveru ef nemendur eru rétt klæddir."},
            {"title":"Útikennsla", "emoji":"🌿", "score":outdoor_score, "text":"Veldu besta tímagluggann og hafðu skýr fyrirmæli áður en farið er út."},
            {"title":"Íþróttir úti", "emoji":"⚽", "score":sports_score, "text":"Skoðaðu sérstaklega vind, hviður og hálku/kulda í fingrum."},
            {"title":"Ferð með bekk", "emoji":"🚌", "score":trip_score, "text":"Fyrir ferðir þarf alltaf að skoða Veðurstofu og Umferðina líka."},
        ]
    }

def render_clothing_icons(temp, wind, rain):
    tips = []
    wc = wind_chill(temp, wind) if temp is not None and wind is not None else temp
    if wc is not None and wc < 0:
        tips += [("🧥", "Hlý úlpa"), ("🧤", "Vettlingar"), ("🧢", "Húfa")]
    elif wc is not None and wc < 7:
        tips += [("🧥", "Jakki"), ("🧶", "Peysa")]
    else:
        tips += [("🧥", "Léttur jakki"), ("👟", "Góðir skór")]
    if rain and rain > 0.5:
        tips += [("🌧️", "Regnföt"), ("🥾", "Vatnsheldir skór")]
    if wind and wind >= 10:
        tips += [("💨", "Vindheldur fatnaður")]
    if not tips:
        tips = [("👟", "Góðir skór"), ("🧥", "Léttur jakki")]
    cols = st.columns(min(4, len(tips)))
    for col, (emoji, label) in zip(cols, tips[:4]):
        with col:
            st.markdown(f"""
            <div class="decision-card" style="text-align:center; min-height:115px;">
                <div style="font-size:2.3rem;">{emoji}</div>
                <div class="action-title">{label}</div>
            </div>
            """, unsafe_allow_html=True)

def weather_question_of_day():
    questions = [
        ("Af hverju getur verið kaldara á Hellisheiði en á Selfossi?", "Hæð yfir sjó, vindur og minni skjól geta gert fjallvegi kaldari og varasamari."),
        ("Hvað segir vindhraði okkur sem hitatala segir ekki?", "Vindur eykur varmatap frá líkamanum og getur gert útiveru mun kaldari."),
        ("Af hverju skiptir loftþrýstingur máli?", "Lækkandi loftþrýstingur getur bent til lægðar, vinds og úrkomu."),
        ("Hvað er betra fyrir útikennslu: 4°C og logn eða 8°C og 14 m/s?", "Oft er lognið þægilegra, því vindkæling og hviður skipta miklu máli."),
        ("Hvernig getur hlýnandi loftslag haft áhrif á jökla?", "Meðalhiti hefur áhrif á bráðnun, snjósöfnun og vatnsrennsli frá jöklum."),
    ]
    idx = datetime.now(TZ).timetuple().tm_yday % len(questions)
    return questions[idx]

def render_sudurland_meter(place, current, hourly, selected_route):
    st.subheader("🌍 Suðurlandsmælirinn")
    st.caption("v1.2: eitt skýrt stöðumat fyrir skóla, útiveru og ferðir á Suðurlandi — hannað fyrir tölvur, síma og iPad.")
    assessment = evaluate_school_decisions(current, hourly)
    overall = assessment["overall"]
    label, klass, emoji = status_from_score(overall)
    temp = current.get("temp")
    wind = current.get("wind_speed") or 0
    rain = (current.get("rain_1h") or 0) + (current.get("snow_1h") or 0)

    st.markdown(f"""
    <div class="sudurland-score">
      <div style="display:flex; justify-content:space-between; gap:18px; flex-wrap:wrap; align-items:center;">
        <div>
          <div style="opacity:.88; font-weight:800;">Staðan núna · {place}</div>
          <h1 style="font-size:2.45rem; margin:.2rem 0 .55rem 0;">{emoji} {label} fyrir skóla og útiveru</h1>
          <div>
            <span class="pill {klass}">Heildarmat {overall}%</span>
            <span class="pill">Bestu tímar: {assessment['best_times']}</span>
            <span class="pill">Vindur mest næstu klst.: {assessment['max_wind']:.1f} m/s</span>
          </div>
        </div>
        <div style="text-align:right; min-width:170px;">
          <div style="opacity:.82;">Suðurlandsmælir</div>
          <div class="big-score">{overall}%</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="mobile-only-note">📱 Á síma og iPad raðast kortin sjálfkrafa niður svo auðvelt sé að lesa þau.</div>', unsafe_allow_html=True)

    st.markdown("#### Skólaákvarðanir")
    cols = st.columns(4)
    for col, card in zip(cols, assessment["cards"]):
        lab, cls, emo = status_from_score(card["score"])
        with col:
            st.markdown(f"""
            <div class="decision-card">
              <div class="action-title">{card['emoji']} {card['title']}</div>
              <div class="action-status" style="color:{'#166534' if cls=='good' else '#92400e' if cls=='warn' else '#991b1b'};">{lab}</div>
              <span class="pill {cls}">{card['score']}%</span>
              <p class="small-muted" style="margin-top:.65rem;">{card['text']}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("#### Klæðnaðarráð fyrir nemendur")
    render_clothing_icons(temp, wind, rain)

    st.markdown("#### Hellisheiðar- og ferðamælir")
    st.write("Fyrst metum við ferðaleiðina út frá OpenWeather punktum. Í næstu útgáfu má tengja þetta beint við Vegagerðina/Umferðina.")
    points = ROUTES[selected_route]
    rows = []
    for p in points:
        c, h, d, a, src = load_weather(p, show_messages=False)
        rows.append({
            "place": p,
            "temp": c.get("temp"),
            "wind": c.get("wind_speed"),
            "gust": c.get("wind_gust"),
            "rain": (c.get("rain_1h") or 0) + (c.get("snow_1h") or 0),
            "desc": c.get("description", "—"),
            "main": c.get("main"),
        })
    tscore, tlabel, reasons = travel_score(rows)
    tlab, tcls, temo = status_from_score(tscore)
    st.markdown(f"""
    <div class="decision-card">
      <div class="action-title">{temo} {selected_route}</div>
      <div class="action-status">{tlabel}</div>
      <span class="pill {tcls}">Ferðamat {tscore}%</span>
      <p class="small-muted">{' · '.join(reasons) if reasons else 'Engin stór veðurmerki komu upp í einföldu mati.'}</p>
    </div>
    """, unsafe_allow_html=True)

    route_cols = st.columns(len(rows))
    for col, r in zip(route_cols, rows):
        with col:
            st.markdown(f"""
            <div class="metric-card">
              <div class="metric-label">{r['place']}</div>
              <div class="metric-value">{weather_icon(r['main'])} {r['temp']:.1f}°C</div>
              <div class="small-muted">Vindur {r['wind'] or 0:.1f} m/s · úrkoma {r['rain']:.1f} mm</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("#### Veðurspurning dagsins")
    q, ans = weather_question_of_day()
    with st.expander("Opna spurningu og stutta útskýringu", expanded=True):
        st.markdown(f"**{q}**")
        st.write(ans)
        st.info("Kennsluverkefni: láttu nemendur bera saman tvo staði í vefnum og skrifa eina setningu um muninn.")

    st.markdown("#### Flýtitenglar")
    c1, c2, c3 = st.columns(3)
    c1.link_button("Veðurstofa Íslands", "https://www.vedur.is/")
    c2.link_button("Umferðin.is", "https://umferdin.is/")
    c3.link_button("Vegagerðin", "https://www.vegagerdin.is/ferdaupplysingar")


def status_word(score):
    if score >= 80:
        return "grænt", "Mjög gott"
    if score >= 60:
        return "ljósgrænt", "Gott"
    if score >= 40:
        return "gult", "Varúð"
    return "rautt", "Frekar inni / fresta"

def get_weather_summary_sentence(place, current):
    temp = current.get("temp")
    wind = current.get("wind_speed") or 0
    rain = (current.get("rain_1h") or 0) + (current.get("snow_1h") or 0)
    desc = (current.get("description") or "veður").lower()
    wc = wind_chill(temp, wind)
    if rain >= 1:
        rain_text = "úrkoma er í gangi eða líkleg"
    else:
        rain_text = "úrkoma er lítil sem stendur"
    chill_text = f"Vindkæling er um {wc:.1f}°C" if wc is not None else "Vindkæling liggur ekki fyrir"
    return f"Á {place} er nú {temp:.1f}°C, {desc}, vindur um {wind:.1f} m/s og {rain_text}. {chill_text}."

def get_best_window_text(hourly):
    best = pick_best_windows(hourly, 3)
    if best.empty:
        return "Ekki næg gögn til að velja besta tímann."
    first = best.iloc[0]
    return f"Besti tíminn næstu 24 klst. virðist vera um kl. {first['Tími']} ({int(first['Mat'])}%). Aðrir góðir gluggar: {', '.join(best['Tími'].tolist())}."

def build_school_announcement(place, current, hourly):
    temp = current.get("temp")
    wind = current.get("wind_speed") or 0
    rain = (current.get("rain_1h") or 0) + (current.get("snow_1h") or 0)
    score, reasons = school_weather_score(temp, wind, rain, current.get("main"))
    color, label = status_word(score)
    clothing = clothing_tip(temp, wind, rain)
    best = get_best_window_text(hourly)
    if score >= 75:
        advice = "Það er gott veður fyrir frímínútur og stutta útikennslu, ef nemendur eru rétt klæddir."
    elif score >= 45:
        advice = "Mælt er með styttri útiveru og að kennarar fylgist sérstaklega með vindi, kulda og úrkomu."
    else:
        advice = "Betra er að halda útiveru stuttri eða færa verkefni inn, nema aðstæður batni."
    return (
        f"Góðan dag. {get_weather_summary_sentence(place, current)}\n\n"
        f"Skólaveður er {label.lower()} ({score}%). {advice}\n"
        f"Klæðnaðarráð: {clothing}.\n"
        f"{best}\n\n"
        f"Ástæður mats: {', '.join(reasons)}."
    )

def lesson_idea_by_weather(current):
    temp = current.get("temp") or 0
    wind = current.get("wind_speed") or 0
    rain = (current.get("rain_1h") or 0) + (current.get("snow_1h") or 0)
    if rain >= 1:
        return {
            "title": "Úrkomurannsókn",
            "task": "Nemendur mæla eða áætla úrkomu, skoða pollamyndun og ræða hvert vatnið fer eftir rigningu.",
            "question": "Af hverju safnast vatn á sumum stöðum en rennur burt annars staðar?"
        }
    if wind >= 8:
        return {
            "title": "Vindrannsókn",
            "task": "Nemendur búa til einfalda vindvísa úr pappír eða borðum og skrá vindátt á skólalóð.",
            "question": "Hvar á skólalóðinni finnur maður mest skjól og af hverju?"
        }
    if temp <= 2:
        return {
            "title": "Kuldi og vindkæling",
            "task": "Nemendur bera saman hvernig hitinn finnst í skjóli og á opnu svæði og skrifa þrjár athuganir.",
            "question": "Af hverju segir hitatalan ekki alltaf alla söguna?"
        }
    return {
        "title": "Ský, hiti og staðbundið veður",
        "task": "Nemendur teikna himininn, meta skýjahulu í prósentum og bera saman við töluna í veðurvefnum.",
        "question": "Hversu nákvæm var okkar eigin veðurathugun miðað við spána?"
    }

def build_recess_blocks(hourly):
    if hourly.empty:
        return []
    blocks = [("Morgunfrímínútur", 9, 11), ("Hádegisfrímínútur", 11, 13), ("Eftir hádegi", 13, 16)]
    out = []
    h = hourly.copy()
    h["hour"] = h["time"].dt.hour
    for label, start, end in blocks:
        part = h[(h["hour"] >= start) & (h["hour"] < end)]
        if part.empty:
            part = h.head(1)
        scores = []
        reasons_all = []
        for _, r in part.iterrows():
            sc, rs = school_weather_score(r.get("temp"), r.get("wind"), r.get("rain"), r.get("main"))
            scores.append(sc)
            reasons_all += rs
        avg = int(sum(scores)/max(1,len(scores)))
        lab, cls, emo = status_from_score(avg)
        out.append({"label": label, "score": avg, "status": lab, "class": cls, "emoji": emo, "reasons": sorted(set(reasons_all))[:3]})
    return out

def render_school_master(place, current, hourly, selected_route):
    st.subheader("🎒 Veðurstjóri skólans")
    st.caption("v1.3: daglegt ákvörðunartól fyrir kennara, stjórnendur og nemendur — með texta sem má afrita beint í tilkynningar.")

    temp = current.get("temp")
    wind = current.get("wind_speed") or 0
    rain = (current.get("rain_1h") or 0) + (current.get("snow_1h") or 0)
    score, reasons = school_weather_score(temp, wind, rain, current.get("main"))
    lab, cls, emo = status_from_score(score)
    announcement = build_school_announcement(place, current, hourly)
    best_text = get_best_window_text(hourly)
    idea = lesson_idea_by_weather(current)

    st.markdown(f"""
    <div class="sudurland-score" style="background:linear-gradient(135deg,#111827 0%,#1d4ed8 50%,#0891b2 100%);">
      <div style="display:flex; justify-content:space-between; gap:18px; flex-wrap:wrap; align-items:center;">
        <div>
          <div style="opacity:.88; font-weight:800;">Daglegt skólastjórnborð · {place}</div>
          <h1 style="font-size:2.35rem; margin:.2rem 0 .55rem 0;">{emo} {lab} fyrir skóladaginn</h1>
          <div>
            <span class="pill {cls}">Skólaveður {score}%</span>
            <span class="pill">Hiti {temp:.1f}°C</span>
            <span class="pill">Vindur {wind:.1f} m/s</span>
            <span class="pill">Úrkoma {rain:.1f} mm</span>
          </div>
        </div>
        <div style="text-align:right; min-width:170px;">
          <div style="opacity:.82;">Veðurstjóri</div>
          <div class="big-score">{score}%</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### 📣 Dagleg skólatilkynning")
    st.write("Þessi texti er tilbúinn til að afrita í Mentor, tölvupóst, upplýsingaskjá eða á skjávarpa í stofu.")
    st.text_area("Afritaðu tilkynninguna héðan", announcement, height=190)

    st.markdown("#### 🕒 Útikennslu-áætlun dagsins")
    c1, c2 = st.columns([1.15, .85])
    with c1:
        st.markdown(f"""
        <div class="decision-card">
          <div class="action-title">🌿 Besti glugginn</div>
          <div class="action-status">{best_text}</div>
          <p class="small-muted">Notaðu þetta sem fyrsta mat. Skoðaðu alltaf raunveður og aðstæður á skólalóð áður en farið er út.</p>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="decision-card">
          <div class="action-title">🧥 Klæðnaðarráð</div>
          <div class="action-status" style="font-size:1.15rem;">{clothing_tip(temp, wind, rain)}</div>
          <p class="small-muted">Sérstaklega mikilvægt fyrir yngri nemendur og lengri útiveru.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("#### 🛝 Frímínútu-mælir")
    blocks = build_recess_blocks(hourly)
    cols = st.columns(3)
    for col, b in zip(cols, blocks):
        with col:
            st.markdown(f"""
            <div class="decision-card">
              <div class="action-title">{b['emoji']} {b['label']}</div>
              <div class="action-status" style="color:{'#166534' if b['class']=='good' else '#92400e' if b['class']=='warn' else '#991b1b'};">{b['status']}</div>
              <span class="pill {b['class']}">{b['score']}%</span>
              <p class="small-muted">{', '.join(b['reasons'])}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("#### 🚌 Ferð með bekk")
    points = ROUTES[selected_route]
    rows = []
    for p in points:
        c, h, d, a, src = load_weather(p, show_messages=False)
        rows.append({
            "place": p,
            "temp": c.get("temp"),
            "wind": c.get("wind_speed"),
            "gust": c.get("wind_gust"),
            "rain": (c.get("rain_1h") or 0) + (c.get("snow_1h") or 0),
            "desc": c.get("description", "—"),
            "main": c.get("main"),
        })
    tscore, tlabel, treasons = travel_score(rows)
    tlab, tcls, temo = status_from_score(tscore)
    st.markdown(f"""
    <div class="decision-card">
      <div class="action-title">{temo} {selected_route}</div>
      <div class="action-status">{tlabel}</div>
      <span class="pill {tcls}">Ferðamat {tscore}%</span>
      <p class="small-muted">{('Athuga sérstaklega: ' + ' · '.join(treasons)) if treasons else 'Engin stór veðurmerki komu upp í einföldu mati. Skoðaðu samt alltaf Umferðina áður en lagt er af stað.'}</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### 🔬 Veðurverkefni dagsins")
    c3, c4 = st.columns([.9, 1.1])
    with c3:
        st.markdown(f"""
        <div class="edu-card">
          <h3 style="margin-top:0;">{idea['title']}</h3>
          <p>{idea['task']}</p>
          <p><b>Spurning:</b> {idea['question']}</p>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown("**Útgáfur fyrir aldursstig:**")
        st.info("**Yngsta stig:** teikna veðurtákn og segja eina setningu um veðrið.")
        st.success("**Miðstig:** mæla/skrá hita, vind, skýjahulu og bera saman við spá.")
        st.warning("**Unglingastig:** ræða áreiðanleika spáa, staðbundið veður og áhrif loftslagsbreytinga.")

    st.markdown("#### ✅ Gátlisti fyrir kennara")
    checklist = [
        "Skoða vind og hviður, ekki bara hitastig.",
        "Velja styttri fyrirmæli inni áður en farið er út.",
        "Hafa varaáætlun ef úrkoma eða vindur eykst.",
        "Fyrir ferðir: opna Veðurstofu og Umferðina áður en lagt er af stað.",
    ]
    for item in checklist:
        st.checkbox(item, value=False)


def _journal_path():
    path = Path("data") / "weather_journal.csv"
    path.parent.mkdir(exist_ok=True)
    return path

def load_journal_df():
    path = _journal_path()
    if path.exists():
        try:
            df = pd.read_csv(path)
        except Exception:
            df = pd.DataFrame()
    else:
        df = pd.DataFrame()
    session_rows = st.session_state.get("weather_journal_rows", [])
    if session_rows:
        df = pd.concat([df, pd.DataFrame(session_rows)], ignore_index=True)
        df = df.drop_duplicates(subset=["id"], keep="last") if "id" in df.columns else df
    return df

def save_journal_entry(row):
    if "weather_journal_rows" not in st.session_state:
        st.session_state.weather_journal_rows = []
    st.session_state.weather_journal_rows.append(row)
    path = _journal_path()
    df = pd.DataFrame([row])
    df.to_csv(path, mode="a", header=not path.exists(), index=False, encoding="utf-8-sig")

def temp_accuracy_label(diff):
    if diff is None or pd.isna(diff):
        return "Skráning vistuð"
    if diff <= 0.5:
        return "🏅 Veðurvísindamaður! Mjög nákvæm mæling."
    if diff <= 1.5:
        return "🌟 Flott mæling — mjög nálægt spánni."
    if diff <= 3:
        return "👍 Góð athugun — ræðum af hverju munurinn getur orðið."
    return "🔍 Mikill munur — gott rannsóknartækifæri!"

def render_weather_diary(place, current, hourly):
    st.subheader("📘 Veðurdagbók nemenda")
    st.caption("v1.5: nemendur skrá eigin veðurathuganir, bera saman við spána og æfa náttúrufræði, stærðfræði, íslensku og gagnalæsi.")

    temp = current.get("temp")
    wind = current.get("wind_speed") or 0
    rain = (current.get("rain_1h") or 0) + (current.get("snow_1h") or 0)
    desc = current.get("description", "—")

    st.markdown(f"""
    <div class="diary-hero">
      <div style="display:flex; justify-content:space-between; gap:18px; flex-wrap:wrap; align-items:center;">
        <div>
          <div style="opacity:.88; font-weight:800;">Veðurdagbók · {place}</div>
          <h1 style="font-size:2.25rem; margin:.2rem 0 .55rem 0;">🔬 Farðu út, mældu og berðu saman</h1>
          <div class="badge-row">
            <span class="pill">Spá: {temp:.1f}°C</span>
            <span class="pill">Vindur {wind:.1f} m/s</span>
            <span class="pill">Úrkoma {rain:.1f} mm</span>
            <span class="pill">{desc}</span>
          </div>
        </div>
        <div style="text-align:right; min-width:180px;">
          <div style="opacity:.82;">Markmið</div>
          <div class="big-score" style="font-size:3.4rem;">Rannsaka</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["✍️ Skrá athugun", "📊 Bekkjarsamantekt", "🖨️ Verkefni / prent"])

    with tab1:
        st.markdown("#### Skrá nýja veðurathugun")
        st.info("Ábending: Láttu nemendur fara út í 2–5 mínútur, mæla hitastig ef hitamælir er til, lýsa vindi, skýjum og úrkomu og bera síðan saman við vefinn.")
        with st.form("weather_diary_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                student = st.text_input("Nafn nemanda eða hóps", placeholder="t.d. Hópur 1")
                class_group = st.text_input("Bekkur / hópur", placeholder="t.d. 5. bekkur")
                obs_place = st.selectbox("Staður", list(PLACES.keys()), index=list(PLACES.keys()).index(place) if place in PLACES else 0)
                measured_temp = st.number_input("Hitastig sem við mældum úti °C", min_value=-40.0, max_value=40.0, value=float(round(temp if temp is not None else 0, 1)), step=0.5)
            with c2:
                wind_words = st.selectbox("Vindur", ["Logn", "Gola", "Vindur", "Hvasst", "Mjög hvasst"])
                clouds = st.selectbox("Skýjahula", ["Heiðskírt", "Léttskýjað", "Skýjað", "Alskýjað", "Þoka/mistur"])
                precipitation = st.selectbox("Úrkoma", ["Engin", "Súld", "Rigning", "Slydda", "Snjór", "Hagl"])
                feeling = st.select_slider("Hvernig fannst veðrið?", options=["Mjög kalt", "Kalt", "Svalt", "Þægilegt", "Hlýtt"])
            tomorrow = st.text_area("Spá okkar fyrir morgundaginn", placeholder="Við höldum að á morgun verði...")
            note = st.text_area("Lýsing / athugasemd", placeholder="Skrifaðu 1–3 setningar um veðrið.")
            submitted = st.form_submit_button("💾 Vista veðurathugun", use_container_width=True)

        if submitted:
            diff = abs(float(measured_temp) - float(temp)) if temp is not None else None
            row = {
                "id": datetime.now(TZ).strftime("%Y%m%d%H%M%S%f"),
                "timestamp": datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"),
                "student_group": student or "Óskráð",
                "class_group": class_group or "Óskráður hópur",
                "place": obs_place,
                "measured_temp": round(float(measured_temp), 1),
                "forecast_temp": round(float(temp), 1) if temp is not None else None,
                "temp_diff": round(diff, 1) if diff is not None else None,
                "forecast_wind_ms": round(float(wind), 1),
                "wind_words": wind_words,
                "clouds": clouds,
                "precipitation": precipitation,
                "feeling": feeling,
                "tomorrow_prediction": tomorrow,
                "note": note,
            }
            save_journal_entry(row)
            st.success(temp_accuracy_label(diff))
            st.balloons()

        st.markdown("#### Samanburður núna")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Spáin segir", f"{temp:.1f}°C" if temp is not None else "—")
        with col_b:
            st.metric("Vindur í spá", f"{wind:.1f} m/s")
        with col_c:
            st.metric("Lýsing", desc)

    with tab2:
        st.markdown("#### Samantekt úr veðurdagbók")
        df = load_journal_df()
        if df.empty:
            st.warning("Engar skráningar enn. Skráðu fyrstu veðurathugunina í flipanum 'Skrá athugun'.")
        else:
            for col in ["measured_temp", "forecast_temp", "temp_diff", "forecast_wind_ms"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Skráningar", len(df))
            with m2:
                st.metric("Meðalhiti mældur", f"{df['measured_temp'].mean():.1f}°C" if "measured_temp" in df else "—")
            with m3:
                st.metric("Meðalmunur", f"{df['temp_diff'].mean():.1f}°C" if "temp_diff" in df else "—")
            with m4:
                common = df["wind_words"].mode().iloc[0] if "wind_words" in df and not df["wind_words"].mode().empty else "—"
                st.metric("Algengasti vindur", common)

            show_cols = [c for c in ["timestamp", "student_group", "class_group", "place", "measured_temp", "forecast_temp", "temp_diff", "wind_words", "clouds", "precipitation", "feeling", "tomorrow_prediction", "note"] if c in df.columns]
            st.dataframe(df[show_cols].tail(30), use_container_width=True, hide_index=True)

            chart_df = df.dropna(subset=["measured_temp", "forecast_temp"]).tail(30).copy()
            if not chart_df.empty:
                chart_df["nr"] = range(1, len(chart_df)+1)
                long = chart_df.melt(id_vars=["nr", "student_group"], value_vars=["measured_temp", "forecast_temp"], var_name="Tegund", value_name="Hiti")
                fig = px.line(long, x="nr", y="Hiti", color="Tegund", markers=True, hover_data=["student_group"], title="Mældur hiti vs. spá")
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("#### 🏅 Veðurvísindamenn vikunnar")
            award_cols = st.columns(3)
            clean = df.dropna(subset=["temp_diff"]).copy() if "temp_diff" in df else pd.DataFrame()
            with award_cols[0]:
                if not clean.empty:
                    r = clean.sort_values("temp_diff").iloc[0]
                    st.success(f"🏅 Nákvæmasta hitamælingin: **{r.get('student_group','—')}** ({r.get('temp_diff',0):.1f}°C munur)")
                else:
                    st.info("Skráðu mælingar til að fá verðlaun.")
            with award_cols[1]:
                if "note" in df and df["note"].fillna("").str.len().max() > 0:
                    r = df.loc[df["note"].fillna("").str.len().idxmax()]
                    st.success(f"📝 Besta veðurlýsingin: **{r.get('student_group','—')}**")
                else:
                    st.info("Skráðu lýsingu til að fá verðlaun.")
            with award_cols[2]:
                if "tomorrow_prediction" in df and df["tomorrow_prediction"].fillna("").str.len().max() > 0:
                    r = df.loc[df["tomorrow_prediction"].fillna("").str.len().idxmax()]
                    st.success(f"🔮 Spámaður dagsins: **{r.get('student_group','—')}**")
                else:
                    st.info("Skráðu spá fyrir morgundaginn.")

            csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇️ Sækja veðurdagbók sem CSV", data=csv_bytes, file_name="vedurdagbok.csv", mime="text/csv", use_container_width=True)

    with tab3:
        st.markdown("#### Útprentanlegt verkefni dagsins")
        task = f"""VEÐURDAGBÓK — {datetime.now(TZ).strftime('%d.%m.%Y')}

Staður: _______________________________
Nafn / hópur: __________________________

1. Farðu út og vertu kyrr í 2 mínútur. Hvernig finnst þér veðrið?
   ________________________________________________________________

2. Mældu eða mettu hitastigið úti: ________ °C

3. Lýstu vindinum:  ☐ logn  ☐ gola  ☐ vindur  ☐ hvasst

4. Lýstu skýjunum: ☐ heiðskírt ☐ léttskýjað ☐ skýjað ☐ alskýjað

5. Er úrkoma? ☐ engin ☐ súld ☐ rigning ☐ slydda ☐ snjór

6. Spáin í veðurvefnum segir núna fyrir {place}:
   Hiti: {temp:.1f}°C    Vindur: {wind:.1f} m/s    Lýsing: {desc}

7. Hver er munurinn á mælingunni þinni og spánni?
   ________________________________________________________________

8. Spáðu fyrir morgundaginn. Hvernig heldur þú að veðrið verði?
   ________________________________________________________________

9. Teiknaðu veðurtákn dagsins eða lítið veðurkort á blaðið.
"""
        st.text_area("Afritaðu verkefnið eða prentaðu úr vafranum", task, height=430)
        st.download_button("⬇️ Sækja verkefnið sem .txt", data=task.encode("utf-8"), file_name="vedurdagbok_verkefni.txt", mime="text/plain", use_container_width=True)
        st.markdown("#### Hugmynd að kennslulotu")
        st.markdown("""
        1. Kennari opnar **Veðurstjóri skólans** og ræðir stöðuna.
        2. Nemendur fara út í litlum hópum og gera athugun.
        3. Hópar skrá niðurstöður í **Veðurdagbók**.
        4. Bekkurinn ber saman mælingar og spá.
        5. Nemendur skrifa 3–5 setningar: *Veðrið í dag var...*
        """)


# -----------------------------
# v1.6 Vegalengdir á Suðurlandi
# -----------------------------
ROAD_PLACES = {
    **PLACES,
    "Kerið": {"lat": 64.0413, "lon": -20.8851, "kind": "gígur"},
    "Reykholt": {"lat": 64.1760, "lon": -20.4470, "kind": "sveit"},
    "Geysir": {"lat": 64.3138, "lon": -20.2996, "kind": "hverasvæði"},
    "Gullfoss": {"lat": 64.3271, "lon": -20.1199, "kind": "foss"},
    "Seljalandsfoss": {"lat": 63.6156, "lon": -19.9886, "kind": "foss"},
    "Skógar": {"lat": 63.5321, "lon": -19.5114, "kind": "foss/safn"},
    "Sólheimajökull": {"lat": 63.5308, "lon": -19.3693, "kind": "jökull"},
    "Landeyjahöfn": {"lat": 63.5307, "lon": -20.1154, "kind": "höfn"},
}

# Vegalengdir eru áætlaðar akstursvegalengdir í km milli næstu punkta.
# Hugmyndin er kennsluleg: nemendur sjá leið, leggja saman kafla og bera saman við beina loftlínu.
ROAD_SEGMENTS = [
    ("Selfoss", "Hveragerði", 13),
    ("Hveragerði", "Hellisheiði", 19),
    ("Hellisheiði", "Reykjavík", 33),
    ("Selfoss", "Eyrarbakki", 12),
    ("Eyrarbakki", "Stokkseyri", 6),
    ("Stokkseyri", "Þorlákshöfn", 23),
    ("Selfoss", "Kerið", 15),
    ("Kerið", "Laugarvatn", 25),
    ("Laugarvatn", "Þingvellir", 31),
    ("Kerið", "Flúðir", 36),
    ("Selfoss", "Reykholt", 42),
    ("Reykholt", "Flúðir", 15),
    ("Reykholt", "Geysir", 25),
    ("Flúðir", "Geysir", 30),
    ("Geysir", "Gullfoss", 10),
    ("Selfoss", "Hella", 35),
    ("Hella", "Hvolsvöllur", 14),
    ("Hvolsvöllur", "Seljalandsfoss", 21),
    ("Seljalandsfoss", "Skógar", 30),
    ("Skógar", "Sólheimajökull", 12),
    ("Skógar", "Vík í Mýrdal", 34),
    ("Hvolsvöllur", "Landeyjahöfn", 30),
    ("Landeyjahöfn", "Vestmannaeyjar", 13),  # ferja/sjóleið, ekki akstursvegur
    ("Þorlákshöfn", "Hveragerði", 29),
]

def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2-lat1)
    dl = math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*r*math.atan2(math.sqrt(a), math.sqrt(1-a))

def build_road_graph():
    graph = {p: [] for p in ROAD_PLACES}
    for a,b,km in ROAD_SEGMENTS:
        graph.setdefault(a, []).append((b, km))
        graph.setdefault(b, []).append((a, km))
    return graph

def shortest_route(start, end):
    import heapq
    graph = build_road_graph()
    q = [(0, start, [])]
    seen = set()
    while q:
        dist, node, path = heapq.heappop(q)
        if node in seen:
            continue
        seen.add(node)
        path = path + [node]
        if node == end:
            return dist, path
        for nxt, km in graph.get(node, []):
            if nxt not in seen:
                heapq.heappush(q, (dist + km, nxt, path))
    return None, []

def route_segments_for_path(path):
    if len(path) < 2:
        return []
    lookup = {}
    for a,b,km in ROAD_SEGMENTS:
        lookup[(a,b)] = km
        lookup[(b,a)] = km
    return [(a, b, lookup.get((a,b), 0)) for a,b in zip(path[:-1], path[1:])]

def estimate_drive_time(distance_km):
    # Varfærin kennsluáætlun: meðalhraði 70 km/klst. á blönduðum leiðum.
    minutes = max(1, round(distance_km / 70 * 60))
    h, m = divmod(minutes, 60)
    if h:
        return f"um {h} klst. {m} mín."
    return f"um {m} mín."

def map_is_url(place):
    # map.is tekur ekki stöðugt við einföldum route-parameterum í þessu verkefni.
    # Við opnum því map.is sjálft og notandi getur slegið staðinn eða leiðina inn þar.
    return "https://map.is/"

def google_directions_url(start, end):
    a = ROAD_PLACES[start]
    b = ROAD_PLACES[end]
    return f"https://www.google.com/maps/dir/?api=1&origin={a['lat']},{a['lon']}&destination={b['lat']},{b['lon']}&travelmode=driving"

def render_distance_map(path):
    if not path:
        return
    coords = [ROAD_PLACES[p] for p in path]
    fig = go.Figure()
    fig.add_trace(go.Scattermapbox(
        lat=[c["lat"] for c in coords],
        lon=[c["lon"] for c in coords],
        mode="lines+markers+text",
        text=path,
        textposition="top center",
        marker=dict(size=12),
        line=dict(width=4),
        hoverinfo="text",
        hovertext=path,
    ))
    center_lat = sum(c["lat"] for c in coords)/len(coords)
    center_lon = sum(c["lon"] for c in coords)/len(coords)
    fig.update_layout(
        mapbox=dict(style="open-street-map", center=dict(lat=center_lat, lon=center_lon), zoom=7),
        margin=dict(l=0, r=0, t=0, b=0),
        height=430,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

def render_distance_center(default_start="Selfoss"):
    st.subheader("📏 Vegalengdir á Suðurlandi")
    st.caption("v1.6: Nemendur velja tvo staði, sjá áætlaða vegalengd, leiðarkafla, loftlínu og kort. Vegalengdir eru kennslulegar nálganir og geta breyst eftir leiðavali, færð og vegalokunum.")

    st.markdown("""
    <div class="distance-hero">
      <div style="display:flex; justify-content:space-between; gap:18px; flex-wrap:wrap; align-items:center;">
        <div>
          <div style="opacity:.88; font-weight:800;">Suðurland · vegalengdir · kortalæsi</div>
          <h1 style="font-size:2.25rem; margin:.25rem 0 .55rem 0;">🧭 Hvað eru margir km á milli staða?</h1>
          <div><span class="pill good">Stærðfræði</span><span class="pill">Landafræði</span><span class="pill">Ferðaveður</span><span class="pill">Kortalæsi</span></div>
        </div>
        <div style="text-align:right; min-width:230px;">
          <div style="opacity:.82;">Verkefni dagsins</div>
          <div style="font-size:1.55rem; font-weight:950;">Veldu tvo staði</div>
          <div style="opacity:.9;">berðu saman veg og loftlínu</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    names = list(ROAD_PLACES.keys())
    default_idx = names.index(default_start) if default_start in names else 0
    c1, c2 = st.columns(2)
    with c1:
        start = st.selectbox("Frá", names, index=default_idx)
    with c2:
        end_default = "Reykjavík" if "Reykjavík" in names else names[1]
        end = st.selectbox("Til", names, index=names.index(end_default))

    if start == end:
        st.info("Veldu tvo ólíka staði til að reikna vegalengd.")
        return

    distance, path = shortest_route(start, end)
    if distance is None:
        st.error("Ég fann ekki leið milli þessara staða í innbyggða Suðurlandsnetinu.")
        return

    a, b = ROAD_PLACES[start], ROAD_PLACES[end]
    straight = haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
    extra = distance - straight
    ratio = distance / straight if straight else 1
    time_text = estimate_drive_time(distance)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""<div class="distance-card"><div class="metric-label">Vegalengd eftir leið</div><div class="metric-value">{distance:.0f} km</div><div class="small-muted">áætluð aksturs-/ferðaleið</div></div>""", unsafe_allow_html=True)
    with m2:
        st.markdown(f"""<div class="distance-card"><div class="metric-label">Áætlaður tími</div><div class="metric-value">{time_text}</div><div class="small-muted">miðað við rólegan meðalhraða</div></div>""", unsafe_allow_html=True)
    with m3:
        st.markdown(f"""<div class="distance-card"><div class="metric-label">Bein loftlína</div><div class="metric-value">{straight:.0f} km</div><div class="small-muted">GPS punktur til GPS punkts</div></div>""", unsafe_allow_html=True)
    with m4:
        st.markdown(f"""<div class="distance-card"><div class="metric-label">Vegur vs loftlína</div><div class="metric-value">{ratio:.1f}×</div><div class="small-muted">vegurinn er {extra:.0f} km lengri</div></div>""", unsafe_allow_html=True)

    st.markdown("#### Leiðin sem kerfið valdi")
    st.success(" → ".join(path))
    segs = route_segments_for_path(path)
    for a, b, km in segs:
        note = " — ferja/sjóleið" if {a,b} == {"Landeyjahöfn", "Vestmannaeyjar"} else ""
        st.markdown(f"<div class='route-step'>📍 <b>{a}</b> → <b>{b}</b>: {km:.0f} km{note}</div>", unsafe_allow_html=True)

    st.markdown("#### Kort af leiðinni")
    render_distance_map(path)

    c3, c4 = st.columns(2)
    with c3:
        st.link_button("🗺️ Opna map.is", map_is_url(start), use_container_width=True)
    with c4:
        st.link_button("🧭 Opna leið í Google Maps", google_directions_url(start, end), use_container_width=True)

    with st.expander("🧑‍🏫 Kennsluhugmyndir með vegalengdum"):
        st.markdown(f"""
        - **Samlagning:** Leggðu saman leiðarkaflana hér að ofan. Fæst sama heildartala og {distance:.0f} km?
        - **Mismunur:** Hvað munar á vegalengd og loftlínu? Hér er munurinn um **{extra:.0f} km**.
        - **Tími:** Ef bíll keyrir 70 km/klst., hvað tekur ferðin langan tíma?
        - **Veður + vegalengd:** Opnaðu Kortamiðstöð og skoðaðu vind/úrkomu á leiðinni.
        - **Rökstuðningur:** Af hverju er vegurinn oft lengri en bein lína á korti?
        """)

    st.warning("Athugið: Þetta er kennslunálgun, ekki opinbert leiðsögukerfi. Fyrir raunferðir þarf að skoða map.is, Umferðina, Veðurstofu og Vegagerðina.")



# v1.7 Veðurleiðangrar og tákn
WEATHER_SYMBOL_EXPLANATIONS = [
    {"emoji":"☀️", "name":"Heiðskírt", "meaning":"Himinn er að mestu skýr og sólin sést vel.", "watch":"Gott útiveður, en muna sólarvörn á björtum dögum."},
    {"emoji":"🌤️", "name":"Léttskýjað", "meaning":"Nokkur ský eru á himni en sólin nær oft í gegn.", "watch":"Oft gott veður fyrir frímínútur og útikennslu."},
    {"emoji":"⛅", "name":"Hálfskýjað", "meaning":"Ský og sól skiptast á. Veðrið getur verið breytilegt.", "watch":"Fylgist með vindi og hitastigi áður en farið er út."},
    {"emoji":"☁️", "name":"Skýjað", "meaning":"Mikið af skýjum og lítil eða engin sól.", "watch":"Getur verið svalt þó hitatalan sé ágæt."},
    {"emoji":"🌧️", "name":"Rigning", "meaning":"Úrkoma fellur sem regn.", "watch":"Regnföt, góðir skór og styttri útivera geta verið skynsamleg."},
    {"emoji":"🌦️", "name":"Skúrir", "meaning":"Rigning kemur í köflum, oft með þurrum bilum á milli.", "watch":"Gott að skoða úrkomukort áður en farið er í útikennslu."},
    {"emoji":"❄️", "name":"Snjór", "meaning":"Úrkoma fellur sem snjór eða él.", "watch":"Athuga hálku, sýnileika og klæðnað."},
    {"emoji":"🌫️", "name":"Þoka", "meaning":"Vatnsdropar í loftinu minnka skyggni.", "watch":"Varúð í umferð og á gönguleiðum."},
    {"emoji":"💨", "name":"Vindasamt", "meaning":"Vindur hefur mikil áhrif á hvernig veðrið finnst.", "watch":"Vindkæling getur gert daginn mun kaldari."},
    {"emoji":"⛈️", "name":"Þrumuveður", "meaning":"Skúrir eða él með þrumum og mögulegum eldingum.", "watch":"Fresta útiveru og fylgjast með viðvörunum."},
    {"emoji":"🌡️", "name":"Hiti", "meaning":"Hitastig segir hversu heitt eða kalt loftið er.", "watch":"Berið saman hitastig og vindkælingu."},
    {"emoji":"🧭", "name":"Vindátt", "meaning":"Segir hvaðan vindurinn blæs, t.d. norðan eða suðaustan.", "watch":"Vindátt getur ráðið miklu um úrkomu og kulda á Íslandi."},
]

ADVENTURE_BANK = [
    {
        "title":"Finndu besta staðinn fyrir útikennslu",
        "level":"Miðstig",
        "subject":"Náttúrufræði + gagnalæsi",
        "goal":"Velja stað og tíma fyrir útikennslu út frá hita, vindi og úrkomu.",
        "steps":["Veldu Selfoss og tvo aðra staði á Suðurlandi.", "Skoðaðu hita, vind og úrkomu í dag.", "Veldu besta staðinn og rökstyddu með þremur gögnum."],
        "product":"Stutt ráðlegging til kennara: Við ættum að fara út kl. __ vegna þess að __.",
    },
    {
        "title":"Hellisheiðar-rannsóknin",
        "level":"Miðstig / unglingastig",
        "subject":"Landafræði + ferðaveður",
        "goal":"Meta hvort veður á leiðinni Selfoss → Reykjavík sé gott, varúð eða slæmt.",
        "steps":["Berðu saman Selfoss, Hveragerði, Hellisheiði og Reykjavík.", "Skoðaðu sérstaklega vind og úrkomu.", "Opnaðu Kortamiðstöð og skoðaðu vindkort."],
        "product":"Ferðamat með niðurstöðu: grænt, gult eða rautt.",
    },
    {
        "title":"Vegalengd vs. loftlína",
        "level":"Miðstig",
        "subject":"Stærðfræði + kortalæsi",
        "goal":"Skilja muninn á vegalengd og beinni loftlínu.",
        "steps":["Opnaðu Vegalengdir.", "Veldu tvo staði á Suðurlandi.", "Reiknaðu hversu mörgum km vegurinn er lengri en loftlínan."],
        "product":"Setning: Vegurinn er __ km lengri en loftlínan, líklega vegna __.",
    },
    {
        "title":"Veðurfréttamaður Suðurlands",
        "level":"Yngsta stig / miðstig",
        "subject":"Íslenska + náttúrufræði",
        "goal":"Búa til stutta veðurfrétt með réttum veðurtáknum og íslenskum orðum.",
        "steps":["Skoðaðu veðrið í vefnum.", "Veldu þrjú veðurtákn sem passa við daginn.", "Skrifaðu eða taktu upp 30–60 sekúndna veðurfrétt."],
        "product":"Veðurfrétt: Góðan dag, í dag er __ á Suðurlandi...",
    },
    {
        "title":"Spáðu og sannreyndu",
        "level":"Allir aldurshópar",
        "subject":"Vísindaleg vinnubrögð",
        "goal":"Nemendur spá fyrir um veðrið á morgun og bera saman við raunveður.",
        "steps":["Skráðu spá fyrir morgundaginn í Veðurdagbók.", "Daginn eftir skráir þú raunveður.", "Berðu saman: hvað var rétt og hvað kom á óvart?"],
        "product":"Lítil niðurstaða: Spáin mín var __ vegna þess að __.",
    },
    {
        "title":"Úrkoma á korti",
        "level":"Miðstig / unglingastig",
        "subject":"Kort + náttúrufræði",
        "goal":"Nota úrkomukort til að spá hvort rigni á næstu klukkustundum.",
        "steps":["Opnaðu Kortamiðstöð.", "Veldu úrkomukort.", "Skrifaðu spá fyrir Selfoss og einn annan stað."],
        "product":"Kortaskýring með örvum: úrkoman virðist færast __.",
    },
]


def render_weather_symbols():
    st.subheader("🌦️ Veðurtákn og útskýringar á íslensku")
    st.caption("Nemendur geta notað þennan hluta til að læra veðurorð og túlka táknin sem birtast í veðurspám.")
    cols = st.columns(3)
    for i, item in enumerate(WEATHER_SYMBOL_EXPLANATIONS):
        with cols[i % 3]:
            st.markdown(f"""
            <div class="symbol-card">
              <div class="symbol-emoji">{item['emoji']}</div>
              <div class="challenge-title">{item['name']}</div>
              <div>{item['meaning']}</div>
              <div class="small-muted" style="margin-top:.55rem;"><b>Passa að:</b> {item['watch']}</div>
            </div>
            """, unsafe_allow_html=True)
    with st.expander("🧑‍🏫 Hugmynd að verkefni með táknunum"):
        st.markdown("""
        **Veðurorð dagsins:** Nemendur velja þrjú tákn sem passa við veðrið í dag og skrifa eina málsgrein með orðunum.

        Dæmi: *Í dag er skýjað og svolítil gola. Það er ekki mikil úrkoma, en gott er að vera í jakka.*
        """)


def render_weather_adventures(place, current, hourly, selected_route):
    st.subheader("🧭 Veðurleiðangrar og áskoranir")
    st.caption("v1.7: verkefni sem tengja veður, kort, vegalengdir, stærðfræði, íslensku, náttúrufræði og ferðaskipulag.")

    temp = current.get("temp")
    wind = current.get("wind_speed") or 0
    rain = (current.get("rain_1h") or 0) + (current.get("snow_1h") or 0)
    score, reasons = school_weather_score(temp, wind, rain, current.get("main"))
    label, klass, emoji = status_from_score(score)
    best = pick_best_windows(hourly, 1)
    best_time = best.iloc[0]["Tími"] if not best.empty else "óljóst"

    st.markdown(f"""
    <div class="challenge-hero">
      <div style="display:flex; justify-content:space-between; gap:18px; flex-wrap:wrap; align-items:center;">
        <div>
          <div style="opacity:.88; font-weight:800;">Leiðangursstjórn · {place}</div>
          <h1 style="font-size:2.3rem; margin:.25rem 0 .55rem 0;">{emoji} Verkefni dagsins út frá raunveðri</h1>
          <div>
            <span class="pill {klass}">Veðurmat {score}% · {label}</span>
            <span class="pill">Besti útigluggi: {best_time}</span>
            <span class="pill">Ferðaleið: {selected_route}</span>
          </div>
        </div>
        <div style="text-align:right; min-width:210px;">
          <div style="opacity:.82;">Áskorunarstig dagsins</div>
          <div class="big-score">{score}%</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    level = st.selectbox("Veldu aldursstig", ["Allt", "Yngsta stig", "Miðstig", "Unglingastig", "Miðstig / unglingastig", "Allir aldurshópar"], index=0)
    subject = st.selectbox("Veldu áherslu", ["Allt", "Náttúrufræði", "Stærðfræði", "Landafræði", "Íslenska", "Kort", "ferðaveður", "gagnalæsi"], index=0)

    filtered = []
    for item in ADVENTURE_BANK:
        ok_level = level == "Allt" or level in item["level"]
        ok_subject = subject == "Allt" or subject.lower() in (item["subject"] + " " + item["goal"]).lower()
        if ok_level and ok_subject:
            filtered.append(item)
    if not filtered:
        filtered = ADVENTURE_BANK

    st.markdown("#### Veldu leiðangur")
    cols = st.columns(2)
    for i, item in enumerate(filtered):
        with cols[i % 2]:
            st.markdown(f"""
            <div class="challenge-card">
              <div class="challenge-title">🧩 {item['title']}</div>
              <div><span class="pill">{item['level']}</span><span class="pill">{item['subject']}</span></div>
              <p><b>Markmið:</b> {item['goal']}</p>
              <p class="small-muted"><b>Afurð:</b> {item['product']}</p>
            </div>
            """, unsafe_allow_html=True)
            with st.expander(f"Skref fyrir skref: {item['title']}"):
                for n, step in enumerate(item["steps"], start=1):
                    st.write(f"{n}. {step}")
                st.success(item["product"])

    st.divider()
    st.markdown("#### 🎲 Slembiáskorun fyrir kennara")
    import random
    seed = datetime.now(TZ).strftime("%Y-%m-%d") + place
    random.seed(seed)
    daily = random.choice(ADVENTURE_BANK)
    st.info(f"**Áskorun dagsins:** {daily['title']} — {daily['goal']}")

    st.markdown("#### Afritanleg fyrirmæli")
    instruction = f"""Veðurleiðangur dagsins: {daily['title']}
Staður: {place}
Veðurmat vefsins: {score}% ({label})
Verkefni: {daily['goal']}
Skref:
1. {daily['steps'][0]}
2. {daily['steps'][1]}
3. {daily['steps'][2]}
Skila: {daily['product']}"""
    st.text_area("Texti fyrir Classroom/Mentor", instruction, height=190)

    st.divider()
    render_weather_symbols()



# v1.8 Veðurstofa bekkjarins
WEATHER_ROLES = [
    {"role":"Veðurfræðingur", "emoji":"🌡️", "task":"Skoðar tölur: hita, vind, úrkomu og loftþrýsting.", "output":"Segir hvaða þrjár tölur skipta mestu máli í dag."},
    {"role":"Kortasérfræðingur", "emoji":"🗺️", "task":"Opnar Kortamiðstöð/Zoom Earth og skoðar vind, úrkomu eða ský.", "output":"Segir hvað kortin sýna og hvert veðrið virðist færast."},
    {"role":"Fréttamaður", "emoji":"🎙️", "task":"Skrifar eða flytur veðurfrétt dagsins fyrir bekkinn.", "output":"30–60 sekúndna veðurfrétt með skýrum inngangi og niðurstöðu."},
    {"role":"Ráðgjafi", "emoji":"🧥", "task":"Gefur klæðnaðar- og útiveruráð miðað við veður.", "output":"Segir hvað nemendur ættu að klæðast og hvort gott sé að vera úti."},
    {"role":"Ferðasérfræðingur", "emoji":"🚌", "task":"Metur ferðaveður og leiðir, t.d. Hellisheiði eða Landeyjahöfn.", "output":"Gefur grænt/gult/rautt ferðamat og rökstyður það."},
]

WEATHER_WORD_BANK = [
    ("lægð", "Svæði þar sem loftþrýstingur er lægri. Lægðir tengjast oft vindi, skýjum og úrkomu."),
    ("hæð", "Svæði þar sem loftþrýstingur er hærri. Hæðir tengjast oft stöðugra og þurrara veðri."),
    ("úrkoma", "Vatn sem fellur úr lofti, til dæmis rigning, slydda, snjór eða hagl."),
    ("skúrir", "Rigning sem kemur í köflum. Stundum rignir, stundum styttir upp."),
    ("slydda", "Blanda af regni og snjó. Slydda kemur oft þegar hitinn er nálægt frostmarki."),
    ("hviður", "Þegar vindur verður skyndilega sterkari í stuttan tíma."),
    ("loftþrýstingur", "Þyngd loftsins yfir okkur. Breytingar á þrýstingi geta sagt til um veðurbreytingar."),
    ("vindkæling", "Þegar vindur gerir það að verkum að okkur finnst kaldara en hitamælirinn segir."),
    ("skýjahula", "Hversu stór hluti himinsins er þakinn skýjum, oft sýnt í prósentum."),
    ("þíða", "Þegar snjór eða ís bráðnar vegna hlýinda."),
    ("frost", "Þegar hitastig er undir 0°C."),
    ("skyggni", "Hversu langt við sjáum. Þoka, snjókoma og mikil rigning minnka skyggni."),
]

WEATHER_QUIZ = [
    {"q":"Hvað merkir 100% skýjahula?", "options":["Heiðskírt", "Alskýjað", "Mikill hiti", "Þrumuveður"], "answer":"Alskýjað", "why":"100% skýjahula þýðir að himinninn er nánast alveg þakinn skýjum."},
    {"q":"Af hverju getur 3°C og mikill vindur fundist kaldara en 3°C og logn?", "options":["Vegna vindkælingar", "Vegna sólarupprásar", "Vegna loftþrýstings eingöngu", "Vegna skýjahulu eingöngu"], "answer":"Vegna vindkælingar", "why":"Vindur kælir líkamann hraðar og því finnst okkur kaldara."},
    {"q":"Hvað eru hviður?", "options":["Stuttar vindaukningar", "Snjór á fjöllum", "Mikil skýjahula", "Sólarglampa"], "answer":"Stuttar vindaukningar", "why":"Hviður eru þegar vindurinn verður skyndilega sterkari í stuttan tíma."},
    {"q":"Hvaða gögn skipta miklu máli fyrir útikennslu?", "options":["Hiti, vindur og úrkoma", "Aðeins sólarupprás", "Aðeins loftþrýstingur", "Aðeins vikudagur"], "answer":"Hiti, vindur og úrkoma", "why":"Þessi þrjú atriði ráða miklu um hvort þægilegt og öruggt sé að vera úti."},
    {"q":"Hvað er best að skoða áður en farið er yfir Hellisheiði?", "options":["Vind, úrkomu, færð og viðvaranir", "Aðeins hitann á Selfossi", "Aðeins skýjahulu", "Aðeins sólsetur"], "answer":"Vind, úrkomu, færð og viðvaranir", "why":"Fjallvegir geta verið öðruvísi en bæirnir sitt hvoru megin."},
]

def _class_station_path():
    path = Path("data") / "class_weather_station.csv"
    path.parent.mkdir(exist_ok=True)
    return path

def save_class_forecast(row):
    if "class_station_rows" not in st.session_state:
        st.session_state.class_station_rows = []
    st.session_state.class_station_rows.append(row)
    path = _class_station_path()
    pd.DataFrame([row]).to_csv(path, mode="a", header=not path.exists(), index=False, encoding="utf-8-sig")

def load_class_forecast_df():
    path = _class_station_path()
    if path.exists():
        try:
            df = pd.read_csv(path)
        except Exception:
            df = pd.DataFrame()
    else:
        df = pd.DataFrame()
    session_rows = st.session_state.get("class_station_rows", [])
    if session_rows:
        df = pd.concat([df, pd.DataFrame(session_rows)], ignore_index=True)
        if "id" in df.columns:
            df = df.drop_duplicates(subset=["id"], keep="last")
    return df

def tomorrow_guess_from_hourly(hourly):
    if hourly is None or hourly.empty or "time" not in hourly:
        return None
    tmp = hourly.copy()
    tomorrow = datetime.now(TZ).date() + pd.Timedelta(days=1)
    tmp["date"] = tmp["time"].dt.date
    rows = tmp[tmp["date"] == tomorrow]
    if rows.empty:
        rows = tmp.tail(8)
    return {
        "temp": round(rows["temp"].mean(), 1) if "temp" in rows else None,
        "wind": round(rows["wind"].mean(), 1) if "wind" in rows else None,
        "rain": round(rows["rain"].sum(), 1) if "rain" in rows else None,
        "desc": rows["description"].mode().iloc[0] if "description" in rows and not rows["description"].mode().empty else "—",
    }

def render_class_weather_station(place, current, hourly, selected_route):
    st.subheader("🎙️ Veðurstofa bekkjarins")
    st.caption("v1.8: nemendur búa til eigin veðurfrétt, skipta með sér hlutverkum, spá fyrir morgundaginn og læra veðurorð.")

    temp = current.get("temp")
    wind = current.get("wind_speed") or 0
    rain = (current.get("rain_1h") or 0) + (current.get("snow_1h") or 0)
    desc = current.get("description", "—")
    main_weather = current.get("main")
    score, reasons = school_weather_score(temp, wind, rain, main_weather)
    label, klass, emoji = status_from_score(score)
    clothing = clothing_tip(temp, wind, rain)
    tomorrow = tomorrow_guess_from_hourly(hourly) or {"temp": None, "wind": None, "rain": None, "desc": "—"}

    st.markdown(f"""
    <div class="challenge-hero">
      <div style="display:flex; justify-content:space-between; gap:18px; flex-wrap:wrap; align-items:center;">
        <div>
          <div style="opacity:.88; font-weight:800;">Nemendarekin veðurstofa · {place}</div>
          <h1 style="font-size:2.25rem; margin:.25rem 0 .55rem 0;">{weather_icon(main_weather)} Veðurfrétt dagsins</h1>
          <div>
            <span class="pill {klass}">Skólaveður {score}% · {label}</span>
            <span class="pill">{temp:.1f}°C</span>
            <span class="pill">Vindur {wind:.1f} m/s</span>
            <span class="pill">{selected_route}</span>
          </div>
        </div>
        <div style="text-align:right; min-width:210px;">
          <div style="opacity:.82;">Veðurstjóri bekkjar</div>
          <div class="big-score">LIVE</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### 📣 Búðu til veðurfrétt")
    col_a, col_b = st.columns([1.05, .95])
    with col_a:
        reporter = st.text_input("Nafn fréttamanns / hóps", value="5. bekkur")
        audience = st.selectbox("Fyrir hvern er fréttin?", ["bekkinn", "foreldra", "skólastjórnendur", "upplýsingaskjá skólans", "útvarp bekkjarins"])
        tone = st.selectbox("Tónn", ["stutt og skýrt", "skemmtilegt og barnvænt", "formlegt", "eins og sjónvarpsveðurfrétt"])
        include_trip = st.checkbox("Taka með ferðaráð", value=True)
    with col_b:
        st.markdown("**Gögn dagsins**")
        st.info(f"{place}: {temp:.1f}°C, {desc}, vindur {wind:.1f} m/s, úrkoma {rain:.1f} mm. Klæðnaðarráð: {clothing}")
        st.success(f"Spá fyrir morgundaginn í kerfinu: um {tomorrow.get('temp', '—')}°C, vindur {tomorrow.get('wind', '—')} m/s, úrkoma {tomorrow.get('rain', '—')} mm.")

    trip_sentence = f" Fyrir ferðaleiðina {selected_route} er skynsamlegt að skoða Kortamiðstöð og Umferðina áður en lagt er af stað." if include_trip else ""
    news_text = f"""Góðan dag. Þetta er veðurfrétt frá {reporter} fyrir {audience}.

Í dag er veðrið í {place}: {desc}, hitinn er {temp:.1f}°C og vindur er um {wind:.1f} m/s. Úrkoma síðustu klukkustund eða núna er um {rain:.1f} mm.

Skólaveðurmælirinn gefur {score}% og matið er: {label}. Ráð dagsins: {clothing}.{trip_sentence}

Á morgun gæti veðrið orðið um {tomorrow.get('temp', '—')}°C með vindi um {tomorrow.get('wind', '—')} m/s. Við munum bera spána saman við raunveðrið á morgun.

Þetta var veðurfrétt dagsins."""
    st.text_area("Afritaðu veðurfréttina héðan", news_text, height=260)

    st.markdown("#### 👥 Hlutverk í veðurstofunni")
    role_cols = st.columns(5)
    for col, r in zip(role_cols, WEATHER_ROLES):
        with col:
            st.markdown(f"""
            <div class="symbol-card">
              <div class="symbol-emoji">{r['emoji']}</div>
              <div class="challenge-title">{r['role']}</div>
              <div>{r['task']}</div>
              <div class="small-muted" style="margin-top:.55rem;"><b>Skilar:</b> {r['output']}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("#### 🔮 Spáðu fyrir morgundaginn")
    with st.form("class_forecast_form"):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            group = st.text_input("Hópur / nemandi", value=reporter)
            forecast_temp = st.number_input("Ég spái hita °C", min_value=-30.0, max_value=35.0, value=float(round((temp or 5),1)), step=0.5)
        with c2:
            forecast_wind = st.number_input("Ég spái vindi m/s", min_value=0.0, max_value=40.0, value=float(round(wind,1)), step=0.5)
            forecast_rain = st.selectbox("Úrkoma á morgun", ["engin", "smá", "nokkur", "mikil", "snjór/slydda"])
        with c3:
            forecast_sky = st.selectbox("Skýjahula", ["heiðskírt", "léttskýjað", "skýjað", "alskýjað", "þoka"])
            confidence = st.slider("Hversu viss er spáin?", 0, 100, 60)
        with c4:
            reason = st.text_area("Af hverju heldurðu þetta?", height=110, placeholder="Ég skoðaði vind, ský og hitaspá...")
        submitted = st.form_submit_button("Vista spá bekkjarins")
        if submitted:
            row = {
                "id": datetime.now(TZ).isoformat(),
                "timestamp": datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"),
                "place": place,
                "group": group,
                "forecast_temp": forecast_temp,
                "forecast_wind": forecast_wind,
                "forecast_rain": forecast_rain,
                "forecast_sky": forecast_sky,
                "confidence": confidence,
                "reason": reason,
                "model_tomorrow_temp": tomorrow.get("temp"),
                "model_tomorrow_wind": tomorrow.get("wind"),
                "model_tomorrow_rain": tomorrow.get("rain"),
            }
            save_class_forecast(row)
            st.success("Spá vistuð! Á morgun getið þið borið hana saman við raunveðrið.")

    df = load_class_forecast_df()
    if not df.empty:
        st.markdown("#### 📊 Spár bekkjarins")
        recent = df.tail(12).copy()
        st.dataframe(recent[[c for c in ["timestamp", "place", "group", "forecast_temp", "forecast_wind", "forecast_rain", "forecast_sky", "confidence"] if c in recent.columns]], use_container_width=True, hide_index=True)
        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Sækja spár bekkjarins sem CSV", csv, "vedurstofa_bekkjarins.csv", "text/csv", use_container_width=True)

    st.markdown("#### 📚 Veðurorðabanki")
    q = st.text_input("Leita í veðurorðabanka", placeholder="t.d. hviður, úrkoma, lægð...")
    terms = [(w, d) for w, d in WEATHER_WORD_BANK if not q or q.lower() in w.lower() or q.lower() in d.lower()]
    word_cols = st.columns(3)
    for i, (word, definition) in enumerate(terms):
        with word_cols[i % 3]:
            st.markdown(f"""
            <div class="edu-card">
              <h3 style="margin-top:0;">{word}</h3>
              <p>{definition}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("#### 🎯 Veðurpróf bekkjarins")
    st.caption("Smá æfingaleikur. Nemendur svara og ræða af hverju rétt svar er rétt.")
    quiz_score = 0
    for i, item in enumerate(WEATHER_QUIZ, start=1):
        ans = st.radio(f"{i}. {item['q']}", item["options"], key=f"weather_quiz_{i}", horizontal=False)
        if ans == item["answer"]:
            quiz_score += 1
            st.success("Rétt! " + item["why"])
        else:
            st.info("Veldu svar og ræðið: " + item["why"])
    st.markdown(f"### Einkunn í veðurprófi: {quiz_score}/{len(WEATHER_QUIZ)}")

    with st.expander("🧑‍🏫 Kennaraleiðbeining: 20 mínútna veðurstofa"):
        st.markdown("""
        **1. 3 mín:** Skoðið veður dagsins á forsíðu.  
        **2. 5 mín:** Skiptið í hlutverk: veðurfræðingur, kortasérfræðingur, fréttamaður, ráðgjafi og ferðasérfræðingur.  
        **3. 7 mín:** Hópurinn býr til veðurfrétt og spá fyrir morgundaginn.  
        **4. 3 mín:** Einn hópur flytur veðurfrétt.  
        **5. 2 mín:** Skráið eitt nýtt veðurorð í orðabankann í vinnubók eða Classroom.
        """)



def board_status(score):
    if score >= 75:
        return "🟢 Grænt", "Gott úti", "good"
    if score >= 45:
        return "🟡 Gult", "Fara varlega", "warn"
    return "🔴 Rautt", "Betra inni / stutt útivera", "danger"


def school_board_message(place, current, hourly, selected_route):
    temp = current.get("temp")
    wind = current.get("wind_speed") or 0
    rain = (current.get("rain_1h") or 0) + (current.get("snow_1h") or 0)
    score, reasons = school_weather_score(temp, wind, rain, current.get("main"))
    status, label, _ = board_status(score)
    best = pick_best_windows(hourly, 2)
    best_text = " og ".join(best["Tími"].tolist()) if not best.empty else "næstu upplýsingar vantar"
    clothing = clothing_tip(temp, wind, rain)
    desc = (current.get("description") or "veður").lower()
    return (
        f"Góðan dag. Í dag er veðrið á {place} {desc}, hitinn er {temp:.1f}°C "
        f"og vindur um {wind:.1f} m/s. Staðan fyrir útiveru er {status} — {label.lower()}. "
        f"Bestu gluggarnir fyrir útikennslu næstu klukkustundir eru um {best_text}. "
        f"Mælt er með: {clothing}. Ferðaleið dagsins í kerfinu er {selected_route}; skoðið Umferðina og Veðurstofu fyrir alvöru ferðir."
    )


def render_school_board(place, current, hourly, selected_route):
    st.subheader("📺 Veðurborð skólans / Upplýsingaskjár")
    st.caption("Hannað fyrir skjávarpa, upplýsingaskjá, iPad og síma. Gott að setja vafrann í full screen með F11 á Windows.")

    temp = current.get("temp")
    wind = current.get("wind_speed") or 0
    gust = current.get("wind_gust") or 0
    rain = (current.get("rain_1h") or 0) + (current.get("snow_1h") or 0)
    score, reasons = school_weather_score(temp, wind, rain, current.get("main"))
    status, label, klass = board_status(score)
    wc = wind_chill(temp, wind)
    now = datetime.now(TZ).strftime("%A %d.%m. kl. %H:%M")
    desc = (current.get("description") or "—").capitalize()
    icon = weather_icon(current.get("main"))
    clothing = clothing_tip(temp, wind, rain)
    best = pick_best_windows(hourly, 3)
    best_text = " · ".join(best["Tími"].tolist()) if not best.empty else "—"

    st.markdown(f"""
    <div class="school-board-hero">
      <div style="display:flex; justify-content:space-between; align-items:center; gap:24px; flex-wrap:wrap;">
        <div>
          <div class="board-sub">{APP_TITLE} · Upplýsingaskjár · {now}</div>
          <div class="board-place">{icon} {place}</div>
          <div style="font-size:1.45rem; opacity:.92; margin-top:.35rem;">{desc}</div>
        </div>
        <div style="text-align:right;">
          <div class="board-temp">{temp:.1f}°</div>
          <div class="board-sub">Tilfinning {current.get('feels_like', temp):.1f}°C · vindkæling {wc:.1f}°C</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    cards = [
        ("Frímínútur", status, label, f"{score}% · {', '.join(reasons)}"),
        ("Útikennsla", status if score >= 55 else "🟡 Gult" if score >= 40 else "🔴 Rautt", "Bestu tímar", best_text),
        ("Klæðnaður", "🧥 Ráð", "Muna eftir", clothing),
        ("Ferðaveður", "🚗 Skoða", selected_route, "Opna Umferðina/Veðurstofu fyrir lengri ferðir"),
    ]
    for col, (title, big, sub, note) in zip([c1,c2,c3,c4], cards):
        with col:
            st.markdown(f"""
            <div class="board-card">
              <div class="metric-label">{title}</div>
              <div class="board-status">{big}</div>
              <div style="font-weight:850; color:#0f172a; margin-bottom:.25rem;">{sub}</div>
              <div class="small-muted">{note}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("### 🟢🟡🔴 Ákvörðun dagsins")
    d1, d2, d3 = st.columns(3)
    decisions = [
        ("Frímínútur", "Gott úti" if score >= 60 else "Styttri útivera" if score >= 40 else "Halda inni eða mjög stutt", score),
        ("Íþróttir úti", "Í lagi" if score >= 70 else "Meta aðstæður" if score >= 45 else "Betra inni", max(0, score - (10 if wind >= 8 else 0))),
        ("Ferð með bekk", "Í lagi með gátlista" if score >= 70 else "Skoða vel færð" if score >= 45 else "Fresta/endurmeta", max(0, score - (15 if selected_route and "Hellisheiði" in selected_route else 0))),
    ]
    for col, (title, text, sc) in zip([d1,d2,d3], decisions):
        s, lab, cl = board_status(sc)
        with col:
            st.markdown(f"""
            <div class="board-card-dark">
              <div style="opacity:.78;">{title}</div>
              <div class="board-status">{s}</div>
              <div style="font-size:1.15rem; font-weight:850;">{text}</div>
              <div style="opacity:.82; margin-top:.4rem;">Mat: {sc}%</div>
            </div>
            """, unsafe_allow_html=True)

    message = school_board_message(place, current, hourly, selected_route)
    st.markdown("### 📣 Dagleg skilaboð")
    st.markdown(f'<div class="board-message">{message}</div>', unsafe_allow_html=True)
    st.text_area("Afritanleg skilaboð fyrir upplýsingaskjá, Mentor eða Classroom", value=message, height=130)

    st.markdown("### 📚 Veðurorð og verkefni dagsins")
    idx = datetime.now(TZ).timetuple().tm_yday % len(WEATHER_WORD_BANK)
    word, definition = WEATHER_WORD_BANK[idx]
    tasks = [
        "Farðu út í 2 mínútur og lýstu skýjunum með þremur lýsingarorðum.",
        "Berðu saman hitann á Selfossi og Hellisheiði. Af hverju gæti verið munur?",
        "Skoðaðu vindáttina. Úr hvaða átt blæs og hvað gæti það þýtt fyrir veðrið?",
        "Finndu besta tímann fyrir útikennslu í dag og rökstuddu valið.",
        "Skrifaðu 4 setninga veðurfrétt út frá upplýsingunum á skjánum.",
    ]
    task = tasks[datetime.now(TZ).timetuple().tm_yday % len(tasks)]
    w1, w2 = st.columns(2)
    with w1:
        st.markdown(f"""
        <div class="board-card">
          <div class="metric-label">Veðurorð dagsins</div>
          <div class="board-status">{word}</div>
          <div class="small-muted">{definition}</div>
        </div>
        """, unsafe_allow_html=True)
    with w2:
        st.markdown(f"""
        <div class="board-card">
          <div class="metric-label">Verkefni dagsins</div>
          <div class="board-status">🧪 5 mín.</div>
          <div class="small-muted">{task}</div>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("⚙️ Ráð fyrir upplýsingaskjá"):
        st.markdown("""
        - Opnaðu þennan flipa á tölvu tengdri skjávarpa eða upplýsingaskjá.
        - Ýttu á **F11** í Chrome/Edge til að fara í full screen.
        - Veldu **Selfoss** eða þann stað sem á að birtast á skjánum.
        - Endurhlaðið síðuna reglulega eða þegar nýr skóladagur byrjar.
        - Fyrir langvarandi skjá er gott að hafa tölvuna tengda við rafmagn og slökkva á sleep-stillingu.
        """)



def build_teacher_assignment(place, current, hourly, grade_band, subject, duration, lesson_type, focus, difficulty):
    """Býr til kennsluverkefni út frá veðri dagsins og vali kennara."""
    temp = current.get("temp")
    wind = current.get("wind_speed") or 0
    rain = (current.get("rain_1h") or 0) + (current.get("snow_1h") or 0)
    clouds = current.get("clouds")
    desc = str(current.get("description", "veður")).capitalize()
    score, reasons = school_weather_score(temp, wind, rain, current.get("main"))
    best = pick_best_windows(hourly, 3)
    best_times = ", ".join(best["Tími"].tolist()) if not best.empty else "skoðið spána saman"
    today = datetime.now(TZ).strftime("%d.%m.%Y")

    focus_tasks = {
        "Hiti": [
            "Skráið hitastigið á vefnum og berið saman við mælingu úti ef hitamælir er til.",
            "Reiknið muninn á hitanum núna og tilfinningunni úti ef vindkæling kemur fram.",
            "Ræðið af hverju sama hitatala getur fundist mismunandi eftir vindi, sól og raka."
        ],
        "Vindur": [
            "Finnið vindhraða, vindátt og hviður á vefnum.",
            "Skoðið Zoom Earth vindkort í Kortamiðstöð og berið saman Selfoss og Hellisheiði.",
            "Útskýrið með eigin orðum hvenær vindur verður varasamur fyrir útikennslu eða ferð."
        ],
        "Úrkoma": [
            "Skoðið úrkomu núna og næstu klukkustundir.",
            "Finnið hvort úrkoma sé líklegri síðar í dag og veljið besta tímann fyrir útiveru.",
            "Teiknið einfalt úrkomukort eða skrifið stutta veðurviðvörun ef þörf er á."
        ],
        "Kort og leiðir": [
            "Veljið tvo staði í Vegalengdir og skráið vegalengd, loftlínu og áætlaðan tíma.",
            "Opnið map.is eða Google Maps hnappinn og skoðið hvernig leiðin liggur.",
            "Rökstyðjið hvort veður og vegalengd henti fyrir skólaferð."
        ],
        "Veðurfrétt": [
            "Skrifið 5–7 setninga veðurfrétt fyrir Suðurland.",
            "Notið að minnsta kosti fjögur veðurorð: hiti, vindur, úrkoma, skýjahula, loftþrýstingur eða hviður.",
            "Kynnið fréttina munnlega fyrir hóp eða takið hana upp sem stutt myndband."
        ],
        "Loftslag og jöklar": [
            "Útskýrið muninn á veðri dagsins og loftslagi yfir langan tíma.",
            "Ræðið hvernig hlýnandi loftslag getur haft áhrif á jökla, ár og náttúru á Suðurlandi.",
            "Búið til þrjár spurningar sem þið mynduð vilja rannsaka nánar."
        ],
        "Umferð og veður": [
            "Opnið flipann Umferðarteljarar og finnið tvo teljara á Suðurlandi.",
            "Berið saman veður dagsins og umferðarmagn. Hvaða veðurþættir gætu haft áhrif á ferðalög?",
            "Skrifið stutta niðurstöðu: Hvenær gæti umferð verið meiri eða minni og af hverju?"
        ],
        "Öryggismat ferða": [
            "Veljið ferðaleið og skoðið Öryggismæli ferða.",
            "Skráið þrjá áhættuþætti: vind, úrkomu, vegalengd, fjallveg, ferju eða umferð.",
            "Gefið ferðinni grænt, gult eða rautt mat og rökstyðjið ákvörðunina."
        ],
        "Vegalengdir": [
            "Veljið tvo staði í Vegalengdir og skráið vegalengd, loftlínu og áætlaðan aksturstíma.",
            "Reiknið hvað vegalengdin er mörgum kílómetrum lengri en loftlínan.",
            "Útskýrið af hverju vegir liggja ekki alltaf beina leið milli staða."
        ],
        "Veðurtákn og orðaforði": [
            "Opnið Veðurtákn og veljið fimm tákn sem passa við veður dagsins eða spána.",
            "Skrifið eina útskýringu á hverju tákni með eigin orðum.",
            "Búið til smá veðurorðabók með að minnsta kosti tíu hugtökum."
        ],
        "Veðurdagbók": [
            "Skráið eigin veðurathugun í Veðurdagbók.",
            "Berið saman ykkar mælingu við spána á vefnum og reiknið muninn.",
            "Skrifið ígrundun: Hvað var auðvelt að mæla og hvað var erfiðast?"
        ],
        "Blanda af öllu": [
            "Skráið hiti, vind, úrkomu og skýjahulu fyrir valinn stað.",
            "Berið saman tvo staði á Suðurlandi og finnið mikilvægasta muninn.",
            "Veljið hvort dagurinn henti fyrir frímínútur, útikennslu eða ferð með bekk og rökstyðjið."
        ],
    }

    subject_angle = {
        "Náttúrufræði": "Nemendur æfa að lesa náttúruleg gögn, tengja þau við upplifun úti og nota vísindaleg hugtök.",
        "Stærðfræði": "Nemendur vinna með tölur úr raunveruleikanum: hitamun, vegalengd, tíma, meðaltöl og samanburð.",
        "Íslenska": "Nemendur þjálfa lýsandi mál, rökstuðning, orðaforða og stutta kynningu eða fréttatexta.",
        "Landafræði": "Nemendur tengja staði, leiðir, kortalæsi, landslag og veðurfar á Suðurlandi.",
        "Lífsleikni": "Nemendur þjálfa ákvarðanatöku, samvinnu, öryggishugsun og rökstuðning út frá raunverulegum aðstæðum.",
        "Upplýsinga- og tæknimennt": "Nemendur lesa gögn af vef, nota kort, bera saman heimildir og setja niðurstöður fram stafrænt.",
        "Samþætt verkefni": "Nemendur tengja saman veðurfræði, kortalæsi, stærðfræði, íslensku og stafræna framsetningu.",
    }

    level_tip = {
        "1.–2. bekkur": "Hafið fyrirmæli stutt, notið myndir/tákn og látið nemendur segja frá munnlega eða teikna.",
        "3.–4. bekkur": "Látið nemendur skrá fáar tölur, teikna veðurtákn og útskýra með einföldum setningum.",
        "5.–6. bekkur": "Látið nemendur bera saman tvo staði, reikna mun og skrifa stutta rökstudda niðurstöðu.",
        "7.–8. bekkur": "Bætið við kortarýni, gagnasamanburði og umræðu um áreiðanleika spáa.",
        "9.–10. bekkur": "Látið nemendur vinna sjálfstæðari rannsókn, setja fram gögn og tengja við loftslag eða samfélag."
    }

    if duration == "10 mínútur":
        structure = ["1. Opnið vefinn og finnið helstu tölur dagsins.", "2. Svarið tveimur stuttum spurningum.", "3. Deilið einni niðurstöðu með hópnum."]
    elif duration == "20 mínútur":
        structure = ["1. Lesið veðurgögnin saman.", "2. Vinnið verkefnin í pörum eða litlum hópum.", "3. Skrifið 3–5 setninga niðurstöðu.", "4. Tveir hópar deila niðurstöðum."]
    elif duration == "40 mínútur":
        structure = ["1. Byrjið á 5 mínútna sameiginlegri yfirferð.", "2. Nemendur safna gögnum úr veðurvef, kortum og/eða útiveru.", "3. Hópar vinna niðurstöðu með tölum, korti og rökstuðningi.", "4. Kynning eða skil á stuttu verkefnablaði."]
    else:
        structure = ["1. Kveikja: skoðið veður dagsins og setjið rannsóknarspurningu.", "2. Gagnaöflun: veðurvefur, kort, vegalengdir og eigin athuganir.", "3. Úrvinnsla: tafla, myndrit, texti eða veðurfrétt.", "4. Kynning: hópar sýna niðurstöður og svara spurningum.", "5. Ígrundun: hvað lærðum við og hvað kom á óvart?"]

    tasks = focus_tasks.get(focus, focus_tasks["Blanda af öllu"])
    if difficulty == "Einfalt":
        questions = [
            f"Hvernig er veðrið í {place} núna?",
            "Er gott að fara út? Af hverju eða af hverju ekki?",
            "Hvaða veðurtákn passar best við daginn?"
        ]
    elif difficulty == "Miðlungs":
        questions = [
            f"Hver er hitinn í {place} og hvernig finnst hann líklega miðað við vind?",
            "Hvaða þáttur hefur mest áhrif á útiverumat dagsins: hiti, vindur eða úrkoma? Rökstuddu.",
            "Hvaða tími dagsins hentar best fyrir útikennslu og af hverju?"
        ]
    else:
        questions = [
            f"Berðu saman veðurgögnin fyrir {place} við annan stað á Suðurlandi. Hver er mikilvægasti munurinn?",
            "Hvernig geta vindur, hiti og úrkoma haft áhrif á ákvörðun um skólaferð?",
            "Hvaða gögn myndir þú vilja bæta við til að taka enn betri ákvörðun?"
        ]

    printable = f"""VEÐURVERKEFNI — {subject.upper()} — {grade_band}\nDagsetning: {today}\nStaður: {place}\n\nVeður núna: {desc}, hiti {temp:.1f}°C, vindur {wind:.1f} m/s, úrkoma {rain:.1f} mm, skýjahula {clouds if clouds is not None else '—'}%.\nÚtiverumat: {score}% ({score_label(score)}) — {', '.join(reasons)}.\nBestu tímar til útiveru: {best_times}.\n\nMarkmið:\n- Ég get lesið helstu veðurgögn og útskýrt hvað þau þýða.\n- Ég get notað veðurgögn til að rökstyðja ákvörðun.\n- Ég get sett niðurstöðu fram með texta, töflu, korti eða munnlegri kynningu.\n\nFyrirmæli:\n"""
    for line in structure:
        printable += f"{line}\n"
    printable += "\nVerkefni:\n"
    for i, task in enumerate(tasks, 1):
        printable += f"{i}. {task}\n"
    printable += "\nSpurningar:\n"
    for i, question in enumerate(questions, 1):
        printable += f"{i}. {question}\n"
    printable += f"\nSkil:\n{lesson_type}. Skrifið niðurstöðu eða kynnið fyrir hópnum.\n\nKennaraathugasemd:\n{subject_angle.get(subject, '')}\n{level_tip.get(grade_band, '')}\n"
    return printable


def render_teacher_admin(place, current, hourly, selected_route):
    st.markdown("## 🧑‍🏫 Kennaraumsjón og verkefnasmiður")
    st.caption("Búðu til verkefni út frá veðri dagsins, staðnum sem er valinn og því sem hentar bekknum þínum.")

    temp = current.get("temp")
    wind = current.get("wind_speed") or 0
    rain = (current.get("rain_1h") or 0) + (current.get("snow_1h") or 0)
    score, reasons = school_weather_score(temp, wind, rain, current.get("main"))
    best = pick_best_windows(hourly, 3)
    best_text = ", ".join(best["Tími"].tolist()) if not best.empty else "—"

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Staður", place, f"{temp:.1f}°C")
    with k2:
        st.metric("Vindur", f"{wind:.1f} m/s", deg_to_compass(current.get("wind_deg")))
    with k3:
        st.metric("Útiverumat", f"{score}%", score_label(score))
    with k4:
        st.metric("Bestu tímar", best_text)

    st.markdown("### ⚙️ Veldu stillingar")
    c1, c2, c3 = st.columns(3)
    with c1:
        grade_band = st.selectbox("Bekkur / aldursstig", ["1.–2. bekkur", "3.–4. bekkur", "5.–6. bekkur", "7.–8. bekkur", "9.–10. bekkur"], index=2)
        subject = st.selectbox("Námsgrein", ["Náttúrufræði", "Stærðfræði", "Íslenska", "Landafræði", "Lífsleikni", "Upplýsinga- og tæknimennt", "Samþætt verkefni"])
    with c2:
        duration = st.selectbox("Lengd", ["10 mínútur", "20 mínútur", "40 mínútur", "80 mínútur"], index=1)
        lesson_type = st.selectbox("Kennsluform", ["Einstaklingsverkefni", "Paravinna", "Hópavinna", "Útikennsla", "Stöðvavinna", "Kynningarverkefni"], index=2)
    with c3:
        focus = st.selectbox("Áhersla", ["Blanda af öllu", "Hiti", "Vindur", "Úrkoma", "Kort og leiðir", "Vegalengdir", "Umferð og veður", "Öryggismat ferða", "Veðurtákn og orðaforði", "Veðurdagbók", "Veðurfrétt", "Loftslag og jöklar"])
        difficulty = st.selectbox("Erfiðleikastig", ["Einfalt", "Miðlungs", "Krefjandi"], index=1)

    assignment = build_teacher_assignment(place, current, hourly, grade_band, subject, duration, lesson_type, focus, difficulty)

    st.markdown("### 📄 Tilbúið verkefni")
    st.text_area("Afritaðu verkefnið í Google Classroom, Mentor, Word eða tölvupóst", value=assignment, height=520)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.download_button("⬇️ Sækja sem .txt", data=assignment.encode("utf-8"), file_name=f"vedurverkefni_{datetime.now(TZ).strftime('%Y%m%d')}.txt", mime="text/plain", use_container_width=True)
    with col_b:
        if st.button("💾 Vista í verkefnabanka", use_container_width=True):
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            row = {
                "created": datetime.now(TZ).isoformat(timespec="seconds"),
                "place": place,
                "grade_band": grade_band,
                "subject": subject,
                "duration": duration,
                "lesson_type": lesson_type,
                "focus": focus,
                "difficulty": difficulty,
                "temperature": temp,
                "wind": wind,
                "score": score,
                "assignment": assignment,
            }
            file = data_dir / "teacher_assignments.csv"
            df = pd.DataFrame([row])
            if file.exists():
                df.to_csv(file, mode="a", index=False, header=False, encoding="utf-8")
            else:
                df.to_csv(file, index=False, encoding="utf-8")
            st.success("Verkefnið var vistað í data/teacher_assignments.csv")
    with col_c:
        classroom_message = f"Verkefni dagsins: Opnið Veðurvef Árborgar og Suðurlands, veljið {place} og vinnið verkefnið um {focus.lower()}. Skilið niðurstöðu samkvæmt fyrirmælum kennara."
        st.text_area("Stutt Classroom/Mentor skilaboð", value=classroom_message, height=120)

    st.markdown("### 🧰 Fljótleg verkefni úr verkefnabanka")
    banks = [
        ("🌡️ Hitamunur", "Berið saman hitastig á tveimur stöðum og reiknið muninn. Skrifið af hverju munurinn gæti verið til staðar."),
        ("🌬️ Vindrýni", "Skoðið vindhraða og vindátt. Útskýrið hvort vindurinn hafi áhrif á útiveru eða ferðalag."),
        ("🗺️ Kortalæsi", "Veljið leið á Suðurlandi. Finnið vegalengd, loftlínu og áætlaðan tíma."),
        ("🎙️ Veðurfrétt", "Búið til 30 sekúndna veðurfrétt með tölum, veðurtákni og ráðleggingu."),
        ("📊 Gögn", "Setjið hiti, vind og úrkomu í töflu og skrifið þrjár niðurstöður úr gögnunum."),
        ("🧊 Loftslag", "Útskýrið muninn á veðri dagsins og loftslagi. Tengið við jökla eða ár á Íslandi."),
        ("🚗 Umferð", "Skoðið umferðarteljara og finnið hvar umferðin er mest. Ræðið hvaða áhrif veður gæti haft."),
        ("🛡️ Öryggismat", "Veljið ferðaleið og gefið henni grænt, gult eða rautt mat með rökstuðningi."),
        ("📘 Veðurdagbók", "Skráið mælingu, berið saman við spá og skrifið eina niðurstöðu úr athuguninni."),
        ("🌦️ Veðurtákn", "Veljið fimm veðurtákn, útskýrið þau og tengið við veðrið í dag."),
        ("📏 Vegalengdir", "Reiknið mun á loftlínu og vegalengd og útskýrið af hverju munurinn verður til."),
        ("🧑‍🤝‍🧑 Hópahlutverk", "Skiptið hlutverkum: gagnasafnari, kortasérfræðingur, reiknimeistari, fréttamaður og ritari."),
    ]
    cols = st.columns(3)
    for i, (title, desc) in enumerate(banks):
        with cols[i % 3]:
            st.markdown(f"""
            <div class="metric-card">
              <div class="metric-label">{title}</div>
              <div class="small-muted">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("### 🧩 Tilbúnir kennslupakkar")
    st.caption("Veldu pakka og fáðu skýra kennsluáætlun sem hægt er að afrita beint í Classroom, Mentor eða prenta.")
    package = st.selectbox(
        "Veldu kennslupakka",
        [
            "20 mín — Veðurhraðferð",
            "40 mín — Veður + stærðfræði",
            "40 mín — Veðurfréttastofa",
            "60 mín — Öryggismat skólaferðar",
            "80 mín — Suðurlandsrannsókn",
            "Vikupakki — Veðurdagbók og spár"
        ]
    )

    package_texts = {
        "20 mín — Veðurhraðferð": f"""KENNSLUPAKKI: Veðurhraðferð
Tími: 20 mínútur
Staður: {place}

Markmið:
- Nemendur lesa helstu veðurtölur dagsins.
- Nemendur rökstyðja hvort hentar að fara út.

Framkvæmd:
1. Kennari sýnir Yfirlit fyrir {place}.
2. Nemendur skrá hiti, vind, úrkomu og skýjahulu.
3. Nemendur velja eitt veðurtákn og útskýra það.
4. Parið svarar: Er gott útiveður? Af hverju?

Skil:
3 setningar eða stutt munnleg niðurstaða.
""",
        "40 mín — Veður + stærðfræði": f"""KENNSLUPAKKI: Veður + stærðfræði
Tími: 40 mínútur

Markmið:
- Reikna mun á hitastigi, vindhraða, vegalengd og loftlínu.
- Setja tölur úr raunheimi í töflu.

Framkvæmd:
1. Veljið tvo til fjóra staði á Suðurlandi.
2. Skráið hitastig, vind og skýjahulu.
3. Reiknið muninn á hæstu og lægstu tölu.
4. Opnið Vegalengdir og berið saman vegalengd og loftlínu.
5. Skrifið þrjár stærðfræðilegar niðurstöður.

Aukaverkefni:
Gerið súlurit eða línurit í Google Sheets.
""",
        "40 mín — Veðurfréttastofa": f"""KENNSLUPAKKI: Veðurfréttastofa
Tími: 40 mínútur

Hlutverk:
- Veðurfræðingur: finnur tölur dagsins.
- Kortasérfræðingur: skoðar Kortamiðstöð.
- Ráðgjafi: gefur klæðnaðarráð.
- Fréttamaður: skrifar og flytur frétt.

Verkefni:
Búið til 45–60 sekúndna veðurfrétt fyrir Suðurland. Notið að minnsta kosti fimm veðurorð og rökstyðjið hvort dagurinn henti fyrir útikennslu.
""",
        "60 mín — Öryggismat skólaferðar": f"""KENNSLUPAKKI: Öryggismat skólaferðar
Tími: 60 mínútur
Leið: {selected_route}

Markmið:
- Nemendur nota veður, umferð og vegalengd til að taka upplýsta ákvörðun.

Framkvæmd:
1. Opnið Öryggismæli ferða og veljið leið.
2. Skráið vegalengd, aksturstíma, vind, úrkomu og helstu áhættuþætti.
3. Skoðið Umferðarteljara og Kortamiðstöð.
4. Gefið ferðinni grænt, gult eða rautt mat.
5. Skrifið skilaboð til foreldra með klæðnaðarráðum og ferðamati.
""",
        "80 mín — Suðurlandsrannsókn": f"""KENNSLUPAKKI: Suðurlandsrannsókn
Tími: 80 mínútur

Rannsóknarspurning:
Hvar á Suðurlandi er best að vera úti í dag — og af hverju?

Framkvæmd:
1. Hópar velja 3–4 staði.
2. Safna gögnum: hiti, vindur, úrkoma, skýjahula, vegalengd og umferð.
3. Setja gögn í töflu.
4. Velja besta staðinn fyrir útikennslu eða stutta ferð.
5. Kynna niðurstöður með korti, tölum og rökstuðningi.
""",
        "Vikupakki — Veðurdagbók og spár": f"""KENNSLUPAKKI: Veðurdagbók og spár
Tími: 5–10 mínútur á dag í eina viku

Daglega:
1. Skráið veðurathugun í Veðurdagbók.
2. Spáið fyrir morgundeginum: hiti, vindur, úrkoma og ský.
3. Daginn eftir: berið spána saman við raunveður.

Í lok vikunnar:
- Finnið meðalhita.
- Finnið vindasamasta daginn.
- Veljið nákvæmustu spána.
- Skrifið 5 setninga samantekt: Hvað lærðum við um veður?
"""
    }

    selected_package_text = package_texts[package]
    st.text_area("Afritanlegur kennslupakki", selected_package_text, height=360)
    st.download_button("⬇️ Sækja kennslupakka sem .txt", selected_package_text.encode("utf-8"), file_name=f"kennslupakki_{datetime.now(TZ).strftime('%Y%m%d')}.txt", mime="text/plain", use_container_width=True)

    st.markdown("### 🖨️ Útprentanleg verkefnaspjöld")
    cards = [
        f"1. Skráðu veðrið í {place}: hiti, vindur, úrkoma og skýjahula.",
        "2. Veldu tvo staði og reiknaðu hitamuninn.",
        "3. Opnaðu Vegalengdir og finndu mun á vegalengd og loftlínu.",
        "4. Skoðaðu Umferðarteljara. Hvar er mest umferð og hvað gæti skýrt það?",
        "5. Gefðu ferð grænt/gult/rautt öryggismat og rökstuddu.",
        "6. Búðu til stutta veðurfrétt með að minnsta kosti 5 veðurorðum."
    ]
    st.text_area("Prentvæn verkefnaspjöld — klipptu út eða settu í Classroom", "\n\n".join(cards), height=260)

    with st.expander("📌 Kennararáð fyrir notkun"):
        st.markdown(f"""
        - Byrjaðu á að velja staðinn í vinstri valmynd, t.d. **{place}**.
        - Veldu síðan aldursstig, námsgrein og áherslu.
        - Notaðu textareitinn sem prentvænt verkefni eða afritaðu hann beint í Classroom/Mentor.
        - Fyrir útiverkefni: skoðaðu fyrst útiverumatið. Núverandi mat er **{score}%** ({', '.join(reasons)}).
        - Fyrir ferðaverkefni: notaðu líka flipana **Vegalengdir**, **Kortamiðstöð** og **Ferðaveður**.
        - Vistað verkefni fer í `data/teacher_assignments.csv` svo þú getir byggt upp eigin verkefnabanka.
        """)



@st.cache_data(ttl=900, show_spinner=False)
def load_traffic_counters():
    """Sækir umferðarteljara Vegagerðarinnar sem GeoJSON.

    Þjónustan getur skilað dálkum með mismunandi nöfnum eftir uppfærslum, þannig að
    úrvinnslan er viljandi sveigjanleg: hún finnur heiti, auðkenni, hnit og talnadálka
    án þess að treysta á eitt fast dálkanafn.
    """
    url = "https://gagnaveita.vegagerdin.is/geoserver/gis/ows"
    params = {
        "service": "WFS",
        "version": "1.0.0",
        "request": "GetFeature",
        "typeName": "gis:umferdvika_2021_1",
        "srsName": "EPSG:4326",
        "outputFormat": "application/json",
    }
    r = requests.get(url, params=params, timeout=25)
    r.raise_for_status()
    data = r.json()
    rows = []

    def first_lon_lat(coords):
        if not coords:
            return None, None
        if isinstance(coords, (list, tuple)) and len(coords) >= 2 and all(isinstance(x, (int, float)) for x in coords[:2]):
            return float(coords[0]), float(coords[1])
        if isinstance(coords, (list, tuple)):
            for item in coords:
                lon, lat = first_lon_lat(item)
                if lon is not None and lat is not None:
                    return lon, lat
        return None, None

    for feature in data.get("features", []):
        props = feature.get("properties", {}) or {}
        geom = feature.get("geometry") or {}
        lon, lat = first_lon_lat(geom.get("coordinates"))
        row = dict(props)
        row["lon"] = lon
        row["lat"] = lat
        rows.append(row)

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Finna möguleg heiti og auðkenni.
    upper = {c.upper(): c for c in df.columns}
    name_col = upper.get("NAFN") or upper.get("HEITI") or upper.get("NAME")
    id_col = upper.get("IDSTOD") or upper.get("ID") or upper.get("OBJECTID")
    if name_col and name_col != "nafn":
        df["nafn"] = df[name_col].astype(str)
    elif "nafn" not in df.columns:
        df["nafn"] = "Ónefndur teljari"
    if id_col and id_col != "idstod":
        df["idstod"] = df[id_col].astype(str)
    elif "idstod" not in df.columns:
        df["idstod"] = df.index.astype(str)

    # Reyna að breyta líklegum talnadálkum í tölur án þess að valda FutureWarning.
    for col in df.columns:
        if col not in ["nafn", "idstod"]:
            converted = pd.to_numeric(df[col], errors="coerce")
            # Ef dálkurinn inniheldur einhver talnagildi notum við tölvuútgáfuna, annars höldum við textanum.
            if converted.notna().any():
                df[col] = converted
    return df


def south_iceland_traffic(df):
    """Gróft Suðurlandsfilter út frá WGS84 hnitum."""
    if df.empty or "lat" not in df.columns or "lon" not in df.columns:
        return df
    # Selfoss, Suðurlandsvegur, Þorlákshöfn, Hella, Hvolsvöllur, Vík og nágrenni.
    mask = (
        df["lat"].between(63.25, 64.45, inclusive="both")
        & df["lon"].between(-22.5, -18.0, inclusive="both")
    )
    south = df.loc[mask].copy()
    return south if not south.empty else df.copy()


def render_traffic_counters():
    st.markdown("## 🚗 Umferðarteljarar Vegagerðarinnar")
    st.caption("Nemendur geta skoðað hvernig umferð dreifist um Suðurland, borið saman staði og tengt gögnin við veður, vegalengdir og ferðaveður.")

    with st.expander("ℹ️ Hvað eru þessi gögn?", expanded=False):
        st.markdown("""
        Vegagerðin rekur umferðarteljara víða um land. Þjónustan `gis:umferdvika_2021_1`
        skilar staðsetningu teljara og talningum, meðal annars fjölda ökutækja síðustu 15 mínútur,
        frá miðnætti og fyrir síðustu daga þegar gögn eru tiltæk.

        Vefurinn sækir gögnin sem **GeoJSON** með `outputFormat=application/json` og `srsName=EPSG:4326`,
        svo hægt sé að birta þau á korti í vefnum.
        """)

    try:
        df_all = load_traffic_counters()
    except Exception as e:
        st.error("Náði ekki að sækja umferðarteljara frá Vegagerðinni.")
        with st.expander("Sjá tæknivillu"):
            st.code(str(e))
        st.link_button("Opna hráa WFS þjónustu", "https://gagnaveita.vegagerdin.is/geoserver/gis/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=gis:umferdvika_2021_1")
        return

    if df_all.empty:
        st.warning("Engin gögn bárust frá þjónustunni að þessu sinni.")
        return

    df_south = south_iceland_traffic(df_all)
    numeric_cols = []
    for col in df_south.columns:
        if col not in ["lat", "lon"] and pd.api.types.is_numeric_dtype(df_south[col]):
            numeric_cols.append(col)

    # Velja sjálfgefið talnagildi sem lítur út eins og umferð/talning.
    preferred = None
    for key in ["MIDN", "MIDNAETTI", "SOLAR", "DAG", "UMFERD", "FJOLDI", "15"]:
        for col in numeric_cols:
            if key in col.upper():
                preferred = col
                break
        if preferred:
            break
    metric = st.selectbox("Veldu talnadálk til að lita kortið", numeric_cols, index=(numeric_cols.index(preferred) if preferred in numeric_cols else 0)) if numeric_cols else None

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Teljarar á landinu", len(df_all))
    with col2:
        st.metric("Teljarar í Suðurlandsglugga", len(df_south))
    with col3:
        if metric:
            st.metric(f"Samtals / meðaltal: {metric}", f"{df_south[metric].sum(skipna=True):,.0f}".replace(",", "."))
        else:
            st.metric("Talnadálkar", "finnast ekki")

    search = st.text_input("Leita að teljara eða stað", placeholder="t.d. Selfoss, Hella, Vík, Hellisheiði...")
    view = df_south.copy()
    if search:
        view = view[view["nafn"].str.contains(search, case=False, na=False)]

    st.markdown("### 🗺️ Kort yfir umferðarteljara")
    if {"lat", "lon"}.issubset(view.columns) and not view.empty:
        map_df = view.dropna(subset=["lat", "lon"]).copy()
        hover_cols = [c for c in ["nafn", "idstod", metric] if c and c in map_df.columns]

        # Plotly má ekki fá NaN eða neikvæð gildi í `size`.
        # Sumir teljarar í WFS-gögnunum skila auðum gildum í völdum talnadálki,
        # þannig að við búum til hreinan kortadálk sem virkar alltaf.
        size_col = None
        color_col = None
        if metric and metric in map_df.columns:
            safe_metric = pd.to_numeric(map_df[metric], errors="coerce")
            color_col = "_kort_gildi"
            size_col = "_kort_staerd"
            map_df[color_col] = safe_metric
            # Stærðin þarf að vera jákvæð tala. Litun má samt sýna NaN sem tómt.
            positive = safe_metric.fillna(0).clip(lower=0)
            if positive.max() > 0:
                map_df[size_col] = positive
            else:
                size_col = None

        fig = px.scatter_mapbox(
            map_df,
            lat="lat",
            lon="lon",
            color=color_col,
            size=size_col,
            hover_name="nafn" if "nafn" in map_df.columns else None,
            hover_data=hover_cols,
            zoom=6.2,
            height=560,
            mapbox_style="open-street-map",
        )
        fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Engin kortahniti fundust fyrir valið úrtak.")

    st.markdown("### 📊 Samanburður teljara")
    if metric and metric in view.columns:
        top = view[["nafn", "idstod", metric]].dropna().sort_values(metric, ascending=False).head(15)
        if not top.empty:
            fig_bar = px.bar(top.sort_values(metric), x=metric, y="nafn", orientation="h", title=f"Mestu gildi í Suðurlandsúrtaki: {metric}")
            fig_bar.update_layout(height=520, margin={"r":20,"t":55,"l":20,"b":20})
            st.plotly_chart(fig_bar, use_container_width=True)

    show_cols = [c for c in ["nafn", "idstod", "lat", "lon", metric] if c and c in view.columns]
    extra_cols = [c for c in numeric_cols if c not in show_cols][:8]
    st.dataframe(view[show_cols + extra_cols].head(200), use_container_width=True, hide_index=True)

    st.markdown("### 🧑‍🏫 Kennsluhugmyndir")
    st.markdown("""
    - **Stærðfræði:** Finnið þrjá umferðarmestu teljarana og reiknið muninn á þeim.
    - **Landafræði:** Af hverju er meiri umferð á sumum leiðum en öðrum?
    - **Veður og samfélag:** Berið saman umferð og veður. Heldur fólk sig meira heima þegar veður er slæmt?
    - **Ferðaskipulag:** Veljið leið á Suðurlandi og rökstyðjið hvar væri best að setja nýjan teljara.
    - **Gagnalæsi:** Hvað þarf að passa þegar gögn eru sjálfvirk og geta verið gömul, ófullkomin eða tímabundið óaðgengileg?
    """)

    col_a, col_b = st.columns(2)
    with col_a:
        st.link_button("Opna WFS þjónustu Vegagerðarinnar", "https://gagnaveita.vegagerdin.is/geoserver/gis/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=gis:umferdvika_2021_1")
    with col_b:
        st.link_button("Opna Gagnaveitu Vegagerðarinnar", "https://gagnaveita.vegagerdin.is/")


def get_numeric_traffic_columns(df):
    """Finnur talnadálka í umferðargögnum á öruggan hátt."""
    if df is None or df.empty:
        return []
    skip = {"lat", "lon"}
    cols = []
    for col in df.columns:
        if col in skip:
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            cols.append(col)
    return cols


def choose_default_traffic_metric(numeric_cols):
    """Velur líklegasta umferðardálkinn sjálfkrafa."""
    for key in ["MIDN", "MIDNAETTI", "SÓLAR", "SOLAR", "DAG", "UMFERD", "UMF", "FJOLDI", "15"]:
        for col in numeric_cols:
            if key in col.upper():
                return col
    return numeric_cols[0] if numeric_cols else None


def traffic_level_label(value):
    if value is None or pd.isna(value):
        return "óþekkt", "⚪", "Engin eða ófullkomin talnagögn bárust frá teljara."
    try:
        value = float(value)
    except Exception:
        return "óþekkt", "⚪", "Ekki tókst að lesa talnagildi."
    if value >= 2500:
        return "mikil umferð", "🔴", "Mikil umferð miðað við kennslumatið — gott að ræða álag, öryggi og tíma dags."
    if value >= 900:
        return "nokkur umferð", "🟡", "Nokkur umferð — hentar vel til samanburðar milli staða."
    return "lítil umferð", "🟢", "Lítil umferð — skoðið hvort staðsetning, tími eða veður geti skýrt það."


def nearest_traffic_counters(df, lat, lon, n=8):
    if df is None or df.empty or "lat" not in df.columns or "lon" not in df.columns:
        return pd.DataFrame()
    out = df.dropna(subset=["lat", "lon"]).copy()
    if out.empty:
        return out
    out["fjarlægð_km"] = out.apply(lambda r: haversine_km(lat, lon, r["lat"], r["lon"]), axis=1)
    return out.sort_values("fjarlægð_km").head(n)


def route_weather_rows(route_points, api_key):
    rows = []
    for rp in route_points:
        if rp not in PLACES:
            continue
        try:
            data = load_weather(rp)
            current = data[0]
            if current:
                rows.append({
                    "staður": rp,
                    "hiti": current.get("temp"),
                    "vindur": current.get("wind"),
                    "úrkoma": current.get("rain", 0),
                    "ský": current.get("clouds"),
                    "veður": current.get("desc", ""),
                })
        except Exception:
            rows.append({"staður": rp, "hiti": None, "vindur": None, "úrkoma": None, "ský": None, "veður": "gögn vantar"})
    return pd.DataFrame(rows)


def render_weather_traffic_comparison(place, current, hourly, selected_route):
    st.markdown("## 🌦️🚗 Veður + umferð samanburður")
    st.caption("Hér skoða nemendur hvort umferð og veður geti tengst saman: vindur, úrkoma, hitastig, ferðaleiðir og umferðarteljarar á Suðurlandi.")

    st.markdown("""
    <div class="feature-card">
      <h3>Rannsóknarspurning dagsins</h3>
      <p>Hefur veður áhrif á það hvernig fólk ferðast? Skoðum núverandi veður og nálæga umferðarteljara og búum til tilgátu.</p>
    </div>
    """, unsafe_allow_html=True)

    api_key = get_api_key()
    try:
        df_all = load_traffic_counters()
        df_south = south_iceland_traffic(df_all)
    except Exception as e:
        st.error("Náði ekki að sækja umferðargögn frá Vegagerðinni.")
        with st.expander("Sjá tæknivillu"):
            st.code(str(e))
        return

    if df_south.empty:
        st.warning("Engin umferðargögn fundust fyrir Suðurlandsglugga.")
        return

    numeric_cols = get_numeric_traffic_columns(df_south)
    default_metric = choose_default_traffic_metric(numeric_cols)
    metric = st.selectbox(
        "Veldu umferðartölu til samanburðar",
        numeric_cols,
        index=(numeric_cols.index(default_metric) if default_metric in numeric_cols else 0),
        key="weather_traffic_metric"
    ) if numeric_cols else None

    analysis_mode = st.radio(
        "Hvað viltu bera saman?",
        ["Nálægir teljarar við valinn stað", "Ferðaleiðin í hliðarvalmynd", "Topp 10 umferð á Suðurlandi"],
        horizontal=True,
        key="weather_traffic_mode"
    )

    place_info = PLACES.get(place, PLACES["Selfoss"])
    weather_score, weather_reasons = school_weather_score(
        current.get("temp") if current else None,
        current.get("wind") if current else None,
        current.get("rain") if current else 0,
        current.get("main") if current else None,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Staður", place)
    c2.metric("Veðurmat", f"{weather_score}%", score_label(weather_score))
    c3.metric("Vindur", f"{current.get('wind', 0):.1f} m/s" if current else "—")
    c4.metric("Úrkoma", f"{current.get('rain', 0):.1f} mm" if current else "—")

    if analysis_mode == "Nálægir teljarar við valinn stað":
        view = nearest_traffic_counters(df_south, place_info["lat"], place_info["lon"], n=12)
        title = f"Næstu umferðarteljarar við {place}"
    elif analysis_mode == "Ferðaleiðin í hliðarvalmynd":
        route_points = ROUTES.get(selected_route, [])
        frames = []
        for rp in route_points:
            info = PLACES.get(rp)
            if info:
                near = nearest_traffic_counters(df_south, info["lat"], info["lon"], n=4)
                if not near.empty:
                    near = near.copy()
                    near["leiðarpunktur"] = rp
                    frames.append(near)
        view = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["idstod"], keep="first") if frames else pd.DataFrame()
        title = f"Teljarar nálægt ferðaleið: {selected_route}"
    else:
        view = df_south.copy()
        if metric and metric in view.columns:
            view["_metric_clean"] = pd.to_numeric(view[metric], errors="coerce")
            view = view.sort_values("_metric_clean", ascending=False).head(10)
        title = "Umferðarmestu teljarar í Suðurlandsglugga"

    st.markdown(f"### {title}")
    if view.empty:
        st.info("Engir teljarar fundust fyrir valið úrtak.")
        return

    if metric and metric in view.columns:
        clean_metric = pd.to_numeric(view[metric], errors="coerce")
        total = clean_metric.sum(skipna=True)
        avg = clean_metric.mean(skipna=True)
        top_val = clean_metric.max(skipna=True)
        label, emoji, level_text = traffic_level_label(avg)
        m1, m2, m3 = st.columns(3)
        m1.metric("Samtals í úrtaki", f"{total:,.0f}".replace(",", "."))
        m2.metric("Meðaltal á teljara", f"{avg:,.0f}".replace(",", "."))
        m3.metric("Umferðarmat", f"{emoji} {label}")
        st.info(level_text)
    else:
        clean_metric = None
        st.info("Enginn talnadálkur fannst til samanburðar.")

    map_df = view.dropna(subset=["lat", "lon"]).copy()
    if not map_df.empty:
        color_col = None
        size_col = None
        if metric and metric in map_df.columns:
            vals = pd.to_numeric(map_df[metric], errors="coerce")
            map_df["_umferd_litur"] = vals
            positive = vals.fillna(0).clip(lower=0)
            if positive.max() > 0:
                map_df["_umferd_staerd"] = positive
                size_col = "_umferd_staerd"
            color_col = "_umferd_litur"
        hover_cols = [c for c in ["nafn", "idstod", metric, "fjarlægð_km", "leiðarpunktur"] if c and c in map_df.columns]
        fig = px.scatter_mapbox(
            map_df,
            lat="lat",
            lon="lon",
            color=color_col,
            size=size_col,
            hover_name="nafn" if "nafn" in map_df.columns else None,
            hover_data=hover_cols,
            zoom=6.4,
            height=520,
            mapbox_style="open-street-map",
        )
        fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        st.plotly_chart(fig, use_container_width=True)

    if metric and metric in view.columns:
        bar_df = view.copy()
        bar_df["_metric_clean"] = pd.to_numeric(bar_df[metric], errors="coerce")
        bar_df = bar_df.dropna(subset=["_metric_clean"]).sort_values("_metric_clean", ascending=False).head(12)
        if not bar_df.empty:
            fig_bar = px.bar(
                bar_df.sort_values("_metric_clean"),
                x="_metric_clean",
                y="nafn",
                orientation="h",
                title=f"Samanburður á umferðargildi: {metric}",
            )
            fig_bar.update_layout(height=470, margin={"r":20,"t":55,"l":20,"b":20}, xaxis_title=metric, yaxis_title="Teljari")
            st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("### 🧠 Sjálfvirk túlkun fyrir nemendur")
    temp = current.get("temp") if current else None
    wind = current.get("wind") if current else None
    rain = current.get("rain") if current else 0
    weather_words = []
    if rain and rain >= 1:
        weather_words.append("úrkoma gæti haft áhrif á akstur og útiveru")
    if wind and wind >= 10:
        weather_words.append("vindur er orðinn það mikill að hann skiptir máli fyrir ferðalög")
    if temp is not None and temp <= 0:
        weather_words.append("frost getur aukið líkur á hálku")
    if not weather_words:
        weather_words.append("veðrið virðist ekki setja miklar skorður á ferðalög samkvæmt einföldu mati")

    st.markdown(f"""
    - **Veðurstaða:** {', '.join(weather_reasons)}.
    - **Hugsanleg áhrif:** {', '.join(weather_words)}.
    - **Tilgáta:** Ef veður versnar, gæti umferð minnkað á sumum leiðum eða færst til á tíma dags. Þetta þarf að sannreyna með fleiri mælingum.
    - **Varúð:** Ein mæling sýnir ekki orsök. Til að finna samband þarf að skoða marga daga og bera saman við veður á sama tíma.
    """)

    with st.expander("🧑‍🏫 Verkefni: Veður og umferð", expanded=True):
        assignment = f"""Verkefni: Veður + umferð á Suðurlandi

1. Veldu stað eða ferðaleið í Veðurvefnum.
2. Skráðu veðrið: hiti, vindur, úrkoma og skýjahula.
3. Skoðaðu umferðarteljara nálægt staðnum eða leiðinni.
4. Finndu hæsta og lægsta umferðargildið í úrtakinu.
5. Settu fram tilgátu: Hefur veðrið áhrif á umferðina? Af hverju / af hverju ekki?
6. Skrifaðu 5–7 línur þar sem þú notar bæði tölur og orð.

Valinn staður: {place}
Valin leið: {selected_route}
Veðurmat: {weather_score}% ({', '.join(weather_reasons)})
Umferðardálkur: {metric or 'engin talnagögn'}
"""
        st.text_area("Afritanlegt verkefni", assignment, height=260)
        st.download_button("⬇️ Sækja verkefni sem TXT", assignment, file_name="vedur_umferd_verkefni.txt", mime="text/plain")

    if analysis_mode == "Ferðaleiðin í hliðarvalmynd":
        st.markdown("### 🌦️ Veður á leiðarpunktum")
        route_points = ROUTES.get(selected_route, [])
        weather_df = route_weather_rows(route_points, api_key)
        if not weather_df.empty:
            st.dataframe(weather_df, use_container_width=True, hide_index=True)

    show_cols = [c for c in ["nafn", "idstod", "lat", "lon", "fjarlægð_km", "leiðarpunktur", metric] if c and c in view.columns]
    st.markdown("### 🔎 Gögnin sem eru notuð")
    st.dataframe(view[show_cols].head(100), use_container_width=True, hide_index=True)

    st.markdown("### 💡 Snilldarhugmyndir fyrir næstu útgáfu")
    st.markdown("""
    - **Tímaraðir:** safna veðri og umferð daglega í CSV/Google Sheets og skoða þróun yfir vikur.
    - **Spálíkan nemenda:** nemendur reyna að spá hvort umferð verði meiri eða minni á morgun út frá veðurspá.
    - **Öryggismælir ferða:** sameina vind, úrkomu, vegalengd og umferð í eitt ferðamat.
    - **Kortaleikur:** hver finnur leiðina þar sem veður er best en umferð minnst?
    - **Samfélagsrýni:** ræða hvernig veður, skólar, vinna, frídagar og ferðamennska hafa áhrif á umferð.
    """)



def _risk_label(score):
    if score >= 72:
        return "Rautt", "🔴", "Há áhætta / bíða eða endurmeta", "Mælt er með að skoða Veðurstofu, Umferðina og Vegagerð áður en farið er. Fyrir skólaferð væri skynsamlegt að ræða við stjórnendur."
    if score >= 42:
        return "Gult", "🟡", "Varúð / undirbúa vel", "Ferðin getur gengið, en gott er að hafa varaáætlun, fylgjast með breytingum og senda skýr skilaboð um klæðnað."
    return "Grænt", "🟢", "Gott ferðaveður miðað við kennslumat", "Engin stór veðurmerki sjást í þessu einfalda mati, en alltaf þarf að skoða opinberar upplýsingar áður en lagt er af stað."


def _safe_float(value, default=0.0):
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _score_weather_point(row):
    temp = _safe_float(row.get("hiti"), 0)
    wind = _safe_float(row.get("vindur"), 0)
    rain = _safe_float(row.get("úrkoma"), 0)
    clouds = _safe_float(row.get("ský"), 0)
    score = 0
    reasons = []
    if wind >= 18:
        score += 35; reasons.append(f"mjög hvasst við {row.get('staður', 'leiðarpunkt')} ({wind:.1f} m/s)")
    elif wind >= 12:
        score += 24; reasons.append(f"nokkuð hvasst við {row.get('staður', 'leiðarpunkt')} ({wind:.1f} m/s)")
    elif wind >= 8:
        score += 10; reasons.append(f"vindur getur haft áhrif við {row.get('staður', 'leiðarpunkt')} ({wind:.1f} m/s)")
    if rain >= 5:
        score += 22; reasons.append(f"talsverð úrkoma við {row.get('staður', 'leiðarpunkt')} ({rain:.1f} mm)")
    elif rain >= 1:
        score += 10; reasons.append(f"einhver úrkoma við {row.get('staður', 'leiðarpunkt')} ({rain:.1f} mm)")
    if temp <= -3:
        score += 22; reasons.append(f"frost við {row.get('staður', 'leiðarpunkt')} ({temp:.1f}°C)")
    elif temp <= 1:
        score += 10; reasons.append(f"kalt nálægt frostmarki við {row.get('staður', 'leiðarpunkt')} ({temp:.1f}°C)")
    if clouds >= 95:
        score += 4
    return score, reasons


def render_travel_safety_meter(place, current, hourly, selected_route):
    st.markdown("## 🛡️ Öryggismælir ferða")
    st.caption("Kennslumælir sem sameinar veður, vegalengd, leiðarpunkta, umferðargögn og CAP-viðvaranir Veðurstofu Íslands. Þetta er ekki opinbert öryggismat heldur hjálpartæki fyrir nemendur og kennara til að ræða ferðaskipulag.")
    render_vedur_alert_summary(place, selected_route, compact=True)

    route_names = list(ROUTES.keys())
    default_index = route_names.index(selected_route) if selected_route in route_names else 0
    route = st.selectbox("Veldu ferðaleið til að meta", route_names, index=default_index, key="safety_route")
    route_points = ROUTES.get(route, [])
    start = route_points[0] if route_points else place
    end = route_points[-1] if route_points else place

    distance, path = shortest_route(start, end) if start in ROAD_PLACES and end in ROAD_PLACES else (None, [])
    route_distance_score = 0
    distance_reason = None
    if distance is not None:
        if distance >= 120:
            route_distance_score = 18; distance_reason = f"löng leið ({distance:.0f} km)"
        elif distance >= 70:
            route_distance_score = 10; distance_reason = f"miðlungs löng leið ({distance:.0f} km)"
        else:
            route_distance_score = 4; distance_reason = f"stutt/miðlungs leið ({distance:.0f} km)"

    weather_df = route_weather_rows(route_points, get_api_key())
    weather_score = 0
    weather_reasons = []
    if not weather_df.empty:
        for _, row in weather_df.iterrows():
            sc, reasons = _score_weather_point(row)
            weather_score = max(weather_score, sc)
            weather_reasons.extend(reasons)
    else:
        # fallback: nota núverandi stað ef leiðarveður fæst ekki
        temp = _safe_float(current.get("temp") if current else None, 0)
        wind = _safe_float(current.get("wind") if current else None, 0)
        rain = _safe_float(current.get("rain") if current else None, 0)
        fake = {"staður": place, "hiti": temp, "vindur": wind, "úrkoma": rain, "ský": current.get("clouds") if current else 0}
        weather_score, weather_reasons = _score_weather_point(fake)

    traffic_score = 0
    traffic_reason = "umferðargögn ekki notuð"
    traffic_view = pd.DataFrame()
    metric = None
    try:
        df_all = load_traffic_counters()
        df_south = south_iceland_traffic(df_all)
        numeric_cols = get_numeric_traffic_columns(df_south)
        metric = choose_default_traffic_metric(numeric_cols)
        if metric and route_points:
            chunks = []
            for rp in route_points:
                info = PLACES.get(rp) or ROAD_PLACES.get(rp)
                if not info:
                    continue
                near = nearest_traffic_counters(df_south, info["lat"], info["lon"], n=4)
                if not near.empty:
                    near = near.copy()
                    near["leiðarpunktur"] = rp
                    chunks.append(near)
            if chunks:
                traffic_view = pd.concat(chunks, ignore_index=True).drop_duplicates(subset=["idstod"] if "idstod" in chunks[0].columns else None)
                vals = pd.to_numeric(traffic_view[metric], errors="coerce").dropna() if metric in traffic_view.columns else pd.Series(dtype=float)
                if not vals.empty:
                    high = float(vals.max())
                    avg = float(vals.mean())
                    if high >= 2500:
                        traffic_score = 18; traffic_reason = f"mikil umferð á einhverjum teljara ({high:.0f})"
                    elif high >= 900:
                        traffic_score = 10; traffic_reason = f"nokkur umferð á leiðinni (hæsta gildi {high:.0f})"
                    else:
                        traffic_score = 4; traffic_reason = f"lítil/meðal umferð í nálægum teljurum (meðaltal {avg:.0f})"
    except Exception as e:
        traffic_reason = f"náði ekki að sækja umferðargögn: {e}"

    special_score = 0
    special_reasons = []
    if "Hellisheiði" in route_points:
        special_score += 10
        special_reasons.append("leiðin fer um Hellisheiði/fjallveg")
    if "Vestmannaeyjar" in route_points or "Landeyjahöfn" in route_points:
        special_score += 10
        special_reasons.append("leiðin tengist ferju/sjóleið")
    if "Vík í Mýrdal" in route_points or "Skógar" in route_points or "Sólheimajökull" in route_points:
        special_score += 6
        special_reasons.append("leiðin nær lengra austur þar sem veður getur breyst hratt")

    total_score = min(100, weather_score + route_distance_score + traffic_score + special_score)
    color, icon, label, advice = _risk_label(total_score)

    st.markdown(f"""
    <div class="hero">
      <div>
        <div class="small">Öryggismælir ferða · {route}</div>
        <h1>{icon} {label}</h1>
        <p>Heildarmat: <b>{total_score:.0f}/100</b> · staða: <b>{color}</b></p>
      </div>
      <div style="text-align:right">
        <div class="big-metric">{total_score:.0f}%</div>
        <div class="small">varúðarmælir</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Veðuráhætta", f"{weather_score:.0f}/60")
    c2.metric("Vegalengd", f"{distance:.0f} km" if distance is not None else "—")
    c3.metric("Umferð", traffic_reason.split("(")[0].strip())
    c4.metric("Leið", " → ".join(route_points[:2]) + ("..." if len(route_points) > 2 else ""))

    st.info(advice)

    st.markdown("### 🔎 Af hverju er matið svona?")
    reasons = []
    if weather_reasons:
        reasons.extend(weather_reasons[:6])
    if distance_reason:
        reasons.append(distance_reason)
    if traffic_reason:
        reasons.append(traffic_reason)
    reasons.extend(special_reasons)
    if not reasons:
        reasons = ["Engin sérstök áhættumerki fundust í kennslumatinu."]
    for r in reasons:
        st.markdown(f"- {r}")

    st.markdown("### ✅ Gátlisti fyrir kennara")
    checklist_items = [
        "Skoða Veðurstofu Íslands áður en lagt er af stað.",
        "Skoða Umferðina/Vegagerðina, sérstaklega ef farið er um fjallveg.",
        "Athuga vind og hviður, ekki bara hitastig.",
        "Meta klæðnað: jakki, regnföt, húfa/vettlingar, góðir skór.",
        "Hafa varaáætlun ef veður eða færð breytist.",
        "Senda skýr skilaboð til foreldra/nemenda um klæðnað og tímasetningu.",
    ]
    for item in checklist_items:
        st.checkbox(item, value=False, key="safe_" + item[:18])

    st.markdown("### 🌦️ Veður á leiðarpunktum")
    if not weather_df.empty:
        st.dataframe(weather_df, use_container_width=True, hide_index=True)
    else:
        st.warning("Náði ekki að sækja leiðarveður að þessu sinni.")

    if path:
        st.markdown("### 🗺️ Leið og vegalengd")
        st.write(f"Áætluð leið: **{' → '.join(path)}**")
        st.write(f"Áætlaður aksturstími: **{estimate_drive_time(distance)}**")
        render_distance_map(path)

    if not traffic_view.empty and metric:
        st.markdown("### 🚗 Nálægir umferðarteljarar")
        cols = [c for c in ["leiðarpunktur", "nafn", "idstod", "fjarlægð_km", metric] if c in traffic_view.columns]
        st.dataframe(traffic_view[cols].head(30), use_container_width=True, hide_index=True)

    st.markdown("### 🧑‍🏫 Verkefni fyrir nemendur")
    assignment = f"""Verkefni: Öryggismælir ferða

Leið: {route}
Mat vefsins: {icon} {label} ({total_score:.0f}/100)

1. Skráðu þrjár tölur úr veðurspánni á leiðinni: hiti, vindur og úrkoma.
2. Skráðu áætlaða vegalengd og aksturstíma.
3. Skoðaðu einn umferðarteljara nálægt leiðinni. Hvað segir hann?
4. Nefndu tvö atriði sem gætu gert ferð öruggari.
5. Ertu sammála mati vefsins? Rökstuddu svarið með gögnum.

Mundu: Þetta er kennslumat. Fyrir alvöru ferðir þarf að skoða opinberar upplýsingar frá Veðurstofu Íslands, Umferðinni og Vegagerðinni.
"""
    st.text_area("Afritanlegt verkefni", assignment, height=260)
    st.download_button("⬇️ Sækja verkefni sem TXT", assignment, file_name="oryggismaelir_ferda.txt", mime="text/plain")

    st.markdown("### 🔗 Opna opinberar upplýsingar")
    b1, b2, b3, b4 = st.columns(4)
    b1.link_button("Veðurstofan", "https://www.vedur.is/")
    b2.link_button("Umferðin", "https://umferdin.is/")
    b3.link_button("Vegagerðin", "https://www.vegagerdin.is/")
    b4.link_button("Map.is", "https://map.is/")


def main():
    render_header()

    with st.sidebar:
        st.title("🌦️ Veðurvefur")
        if "selected_place" not in st.session_state or st.session_state["selected_place"] not in PLACES:
            st.session_state["selected_place"] = "Selfoss"
        place_options = list(PLACES.keys())
        place_index = place_options.index(st.session_state["selected_place"])
        place = st.selectbox("Veldu stað", place_options, index=place_index)
        st.session_state["selected_place"] = place
        page = st.radio(
            "Veldu síðu",
            ["Yfirlit", "Viðvaranir", "Veðurborð skólans", "Kennaraumsjón", "Umferðarteljarar", "Veður + umferð", "Öryggismælir ferða", "Suðurlandsmælir", "Veðurstjóri skólans", "Veðurstofa bekkjarins", "Veðurleiðangrar", "Veðurdagbók", "Vegalengdir", "Veðurtákn", "Kortamiðstöð", "Spá", "Skólaveður", "Ferðaveður", "Kort", "Fróðleikur", "Gögn og tengingar"],
        )
        selected_route = st.selectbox("Ferðaleið", list(ROUTES.keys()), index=0)
        st.caption("Ferðaleiðin er notuð í Ferðaveður/Kortamiðstöð. Fyrir frjálst val á tveimur stöðum: opnaðu flipann 📏 Vegalengdir.")
        try:
            route_points = ROUTES.get(selected_route, [])
            if len(route_points) >= 2:
                route_distance, route_path = shortest_route(route_points[0], route_points[-1])
                if route_distance is not None:
                    st.info(f"Áætluð vegalengd: {route_distance:.0f} km · {' → '.join(route_path)}")
        except Exception:
            pass
        st.divider()
        st.caption("API lykill er lesinn úr OPENWEATHER_API_KEY í .env eða Streamlit secrets.")
        if get_api_key():
            st.success("API lykill fannst ✅")
        else:
            st.error("OPENWEATHER_API_KEY vantar.")

    current, hourly, daily, alerts, source = load_weather(place)

    if page == "Yfirlit":
        render_current(place, current, source)
        render_place_tiles(place)
        st.divider()
        render_daily_weather_card(place, current, hourly)
        st.divider()
        render_alerts(alerts)
        st.divider()
        render_forecast(hourly, daily)
    elif page == "Viðvaranir":
        render_vedur_alerts_page(place, current, hourly, selected_route)
    elif page == "Veðurborð skólans":
        render_school_board(place, current, hourly, selected_route)
    elif page == "Kennaraumsjón":
        render_teacher_admin(place, current, hourly, selected_route)
    elif page == "Umferðarteljarar":
        render_traffic_counters()
    elif page == "Veður + umferð":
        render_weather_traffic_comparison(place, current, hourly, selected_route)
    elif page == "Öryggismælir ferða":
        render_travel_safety_meter(place, current, hourly, selected_route)
    elif page == "Suðurlandsmælir":
        render_sudurland_meter(place, current, hourly, selected_route)
    elif page == "Veðurstjóri skólans":
        render_school_master(place, current, hourly, selected_route)
    elif page == "Veðurstofa bekkjarins":
        render_class_weather_station(place, current, hourly, selected_route)
    elif page == "Veðurleiðangrar":
        render_weather_adventures(place, current, hourly, selected_route)
    elif page == "Veðurdagbók":
        render_weather_diary(place, current, hourly)
    elif page == "Vegalengdir":
        render_distance_center(place)
    elif page == "Veðurtákn":
        render_weather_symbols()
    elif page == "Kortamiðstöð":
        render_map_center(place, current, hourly, selected_route)
    elif page == "Spá":
        render_forecast(hourly, daily)
    elif page == "Skólaveður":
        render_school(hourly)
    elif page == "Ferðaveður":
        render_travel(selected_route)
    elif page == "Kort":
        render_map(place)
    elif page == "Fróðleikur":
        render_education()
    elif page == "Gögn og tengingar":
        render_sources()

if __name__ == "__main__":
    main()