# ФАЙЛ: репозиторій кабінету / dashboard.py
"""
АЛЬТАВІСТА — Кабінет спостереження v2 (SaaS-рівень).
Для автора методології: спостерігати, як працює методологія вживу.

Вкладки: Огляд · Діалоги (з фільтрами, чат-вид) · Воронка · Якість
"""

import os
import json
import psycopg2
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

# ============ ПІДКЛЮЧЕННЯ ============
def get_conn():
    dsn = os.environ.get("DATABASE_URL") or st.secrets.get("DATABASE_URL", "")
    if dsn.startswith("postgres://"):
        dsn = dsn.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(dsn, sslmode="require")

@st.cache_data(ttl=30)
def q(sql, params=None):
    conn = get_conn()
    try:
        return pd.read_sql(sql, conn, params=params)
    finally:
        conn.close()

st.set_page_config(page_title="Альтавіста · Кабінет", page_icon="🔥", layout="wide")

# ============ ФІРМОВИЙ СТИЛЬ КАБІНЕТУ (єдиний для всіх вкладок) ============
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600&display=swap');

  :root {
    --cal-cream:#F7F2EA; --cal-clay:#C4642A; --cal-gold:#DBA431;
    --cal-ink:#1E2930; --cal-slate:#3A3F3D; --cal-earth:#7A5A2C;
    --cal-line:#E9E0D2;
  }

  html, body, [class*="css"], .stMarkdown, .stText, p, li, label, span, div {
    font-family:'Inter',-apple-system,'Segoe UI',sans-serif;
  }

  /* заголовки — характерна антиква, стримано */
  h1, h2, h3 {
    font-family:'Fraunces',Georgia,serif !important;
    color:var(--cal-ink) !important;
    letter-spacing:-.01em;
    font-weight:600 !important;
  }
  h1 {font-size:32px !important;}
  h2 {font-size:25px !important;}
  h3 {font-size:19px !important;}

  /* вкладки: спокійні, з теплим підкресленням активної */
  .stTabs [data-baseweb="tab-list"] {
    gap:2px; border-bottom:1px solid var(--cal-line); padding-bottom:0;
  }
  .stTabs [data-baseweb="tab"] {
    font-family:'Inter',sans-serif !important; font-size:15px !important; font-weight:500;
    color:#6C737B; padding:11px 16px; border-radius:10px 10px 0 0;
  }
  .stTabs [data-baseweb="tab"] p,
  .stTabs [data-baseweb="tab"] div {font-size:15px !important;}

  .stTabs [data-baseweb="tab"]:hover {color:var(--cal-ink); background:#FBF8F3;}

  /* активна вкладка — теплою заливкою, щоб одразу читалась */
  .stTabs [aria-selected="true"] {
    color:var(--cal-clay) !important; font-weight:600 !important;
    background:#FBEFE3 !important;
    box-shadow:inset 0 -2px 0 var(--cal-clay);
  }
  .stTabs [data-baseweb="tab-highlight"] {background:var(--cal-clay);}

  /* метрики — цифра антиквою, підпис дрібним капітелем */
  [data-testid="stMetricValue"] {
    font-family:'Fraunces',Georgia,serif; font-weight:700;
    color:var(--cal-ink); font-size:29px;
  }
  [data-testid="stMetricLabel"] {
    font-size:11px !important; letter-spacing:.13em; text-transform:uppercase;
    color:var(--cal-earth) !important; font-weight:600;
  }

  /* кнопки */
  .stButton > button {
    font-family:'Inter',sans-serif; font-weight:500; font-size:14px;
    border-radius:9px; border:1px solid var(--cal-line);
    color:var(--cal-ink); transition:.16s;
  }
  .stButton > button:hover {
    border-color:var(--cal-clay); color:var(--cal-clay); background:#FDF7F1;
  }
  .stButton > button[kind="primary"] {
    background:var(--cal-clay); border-color:var(--cal-clay); color:#fff;
  }
  .stButton > button[kind="primary"]:hover {background:#A9531F; color:#fff;}

  /* поля вводу */
  .stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"] > div {
    border-radius:9px !important; border-color:var(--cal-line) !important;
    font-family:'Inter',sans-serif;
  }
  .stTextInput input:focus, .stTextArea textarea:focus {
    border-color:var(--cal-clay) !important; box-shadow:0 0 0 2px rgba(196,100,42,.10) !important;
  }

  /* розгортайки */
  .streamlit-expanderHeader, [data-testid="stExpander"] summary {
    font-family:'Inter',sans-serif; font-weight:500; font-size:14px;
    color:var(--cal-ink); border-radius:9px;
  }
  [data-testid="stExpander"] {border:1px solid var(--cal-line); border-radius:10px;}

  /* таблиці */
  [data-testid="stDataFrame"] {border:1px solid var(--cal-line); border-radius:10px;}

  /* підписи і розділювачі */
  [data-testid="stCaptionContainer"] {color:#8A9096; font-size:13px;}
  hr {border-color:var(--cal-line); margin:1.1rem 0;}

  /* бокова панель */
  section[data-testid="stSidebar"] {background:var(--cal-cream); border-right:1px solid var(--cal-line);}


  /* сповіщення */
  .stAlert {border-radius:10px; border-width:1px;}

  /* службові елементи Streamlit Cloud — команді проєкту не потрібні */
  [data-testid="stToolbar"]{display:none !important;}
  [data-testid="stToolbarActions"]{display:none !important;}
  [data-testid="stActionButtonIcon"]{display:none !important;}
  [data-testid="stAppDeployButton"]{display:none !important;}
  [data-testid="stMainMenu"]{display:none !important;}
  [data-testid="manage-app-button"]{display:none !important;}
  [data-testid="stStatusWidget"]{visibility:hidden;}
  header{background:transparent !important;}
  footer{visibility:hidden !important;}
</style>
""", unsafe_allow_html=True)

# логотип проєкту (в кутку кабінету); не падаємо, якщо файла нема
try:
    st.logo("logo.png")
except Exception:
    pass

# ============ ВХІД (email + пароль, користувачі в базі) ============
import hashlib

def _hash_pw(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()

def _check_login(email: str, password: str):
    """Повертає роль користувача або None."""
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute("SELECT pw_salt, pw_hash, role FROM dashboard_users WHERE email=%s",
                    (email.strip().lower(),))
        row = cur.fetchone(); conn.close()
        if not row:
            return None
        salt, pw_hash, role = row
        if _hash_pw(password, salt) == pw_hash:
            return role
        return None
    except Exception:
        return None

# ---- довга сесія: токен у посиланні + запис у базі (30 днів) ----
import secrets as _secrets
from datetime import datetime as _dt, timedelta as _td

SESSION_DAYS = 30

def _session_create(email, role):
    """Створює токен сесії, повертає його."""
    token = _secrets.token_urlsafe(32)
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute("""INSERT INTO dashboard_sessions (token, email, role, expires_at)
                       VALUES (%s,%s,%s,%s)""",
                    (token, email, role, _dt.utcnow() + _td(days=SESSION_DAYS)))
        conn.commit(); conn.close()
        return token
    except Exception:
        return None

def _session_check(token):
    """Повертає (email, role) якщо токен живий, інакше None."""
    if not token:
        return None
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute("""SELECT email, role FROM dashboard_sessions
                        WHERE token=%s AND expires_at > now()""", (token,))
        row = cur.fetchone(); conn.close()
        return (row[0], row[1]) if row else None
    except Exception:
        return None

def _session_drop(token):
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute("DELETE FROM dashboard_sessions WHERE token=%s", (token,))
        conn.commit(); conn.close()
    except Exception:
        pass

if "auth_role" not in st.session_state:
    st.session_state.auth_role = None
    st.session_state.auth_email = None
    st.session_state.auth_token = None

# автовхід за токеном з посилання (переживає перезавантаження і обриви зв'язку)
if not st.session_state.auth_role:
    _t = st.query_params.get("t")
    if isinstance(_t, list):
        _t = _t[0] if _t else None
    _found = _session_check(_t)
    if _found:
        st.session_state.auth_email, st.session_state.auth_role = _found
        st.session_state.auth_token = _t

if not st.session_state.auth_role:
    # компактна картка входу по центру
    st.markdown("""
    <style>
      [data-testid="stForm"] {max-width: 420px; margin: 0 auto;
        border: 1px solid #e6e0d4; border-radius: 14px; padding: 26px 26px 18px;
        box-shadow: 0 8px 30px rgba(0,0,0,.06);}
      .login-logo {display:flex; justify-content:center; margin: 8px 0 6px;}
      .login-logo img {width: 170px; height: 170px; object-fit: cover;
        border-radius: 38px; box-shadow: 0 14px 40px rgba(160,40,90,.30);}
      .login-title {text-align:center; font-size: 30px; font-weight: 700; margin: 10px 0 2px;}
      .login-sub {text-align:center; color:#8a8f99; margin-bottom: 18px;}
    </style>
    """, unsafe_allow_html=True)

    import base64 as _b64, os as _os
    if _os.path.exists("logo.png"):
        _logo64 = _b64.b64encode(open("logo.png","rb").read()).decode()
        st.markdown(f'<div class="login-logo"><img src="data:image/png;base64,{_logo64}"></div>',
                    unsafe_allow_html=True)
    st.markdown('<div class="login-title">Альтавіста — Кабінет</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-sub">Вхід для команди проєкту</div>', unsafe_allow_html=True)

    with st.form("login"):
        email = st.text_input("Email")
        password = st.text_input("Пароль", type="password")
        ok = st.form_submit_button("Увійти", use_container_width=True)
    if ok:
        role = _check_login(email, password)
        if role:
            st.session_state.auth_role = role
            st.session_state.auth_email = email.strip().lower()
            _tok = _session_create(st.session_state.auth_email, role)
            if _tok:
                st.session_state.auth_token = _tok
                st.query_params["t"] = _tok
            st.rerun()
        else:
            st.error("Невірний email або пароль.")
    st.stop()

# кнопка виходу в сайдбарі
with st.sidebar:
    st.caption(f"👤 {st.session_state.auth_email} · {st.session_state.auth_role}")
    if st.button("🚪 Вийти"):
        _session_drop(st.session_state.get("auth_token"))
        st.session_state.auth_role = None
        st.session_state.auth_email = None
        st.session_state.auth_token = None
        try:
            del st.query_params["t"]
        except Exception:
            pass
        st.rerun()


# ----- тёмний стиль -----
st.markdown("""
<style>

  .bubble-child {
     background: rgba(88,166,255,0.12); border-radius:14px 14px 14px 4px;
     padding:10px 14px; margin:4px 0; max-width:75%;
     border:1px solid rgba(88,166,255,0.4);
  }
  .bubble-ai {
     background: rgba(163,113,247,0.16); border-radius:14px 14px 4px 14px;
     padding:10px 14px; margin:4px 0 4px auto; max-width:75%;
     border:1px solid rgba(163,113,247,0.45); text-align:left;
  }
  .meta { opacity:0.6; font-size:0.75rem; margin-bottom:2px; }
  .flag { display:inline-block; padding:1px 8px; border-radius:10px;
          font-size:0.7rem; margin-left:6px; }
  .flag-warn { background: rgba(224,160,96,0.2); color:#e0a060; }
  .flag-ok { background: rgba(96,208,144,0.2); color:#60d090; }
</style>
""", unsafe_allow_html=True)

st.title("🔥 Альтавіста — Кабінет спостереження та управління")
st.caption("Спостереження за діалогами · управління методологією та контентом")
st.markdown(
    "🤖 **Бот для тестування:** [@OwnLearningLab_bot](https://t.me/OwnLearningLab_bot) "
    "— натисніть, щоб відкрити в Telegram і написати `/start`."
)

# тема зафіксована тёмна — графіки в темному оформленні
PLOTLY_TEMPLATE = "plotly_white"

_is_manager = st.session_state.auth_role in ("admin", "owner")
if _is_manager:
    (tab_how, tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab_prof,
     tab_eval, tab8, tab9) = st.tabs(
        ["🧭 Як це працює", "📊 Огляд", "💬 Діалоги", "🎯 Воронка", "✅ Якість",
         "⚙️ Методологія", "📝 Контент", "👥 Учні", "🎭 Профілі",
         "🧪 Тести якості", "❓ Довідка", "🔐 Команда"])
else:
    (tab_how, tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab_prof,
     tab_eval, tab8) = st.tabs(
        ["🧭 Як це працює", "📊 Огляд", "💬 Діалоги", "🎯 Воронка", "✅ Якість",
         "⚙️ Методологія", "📝 Контент", "👥 Учні", "🎭 Профілі",
         "🧪 Тести якості", "❓ Довідка"])
    tab9 = None

# ============ ОГЛЯД ============
with tab1:
    users = int(q("SELECT count(*) n FROM users")["n"][0])
    sessions = int(q("SELECT count(*) n FROM sessions")["n"][0])
    messages = int(q("SELECT count(*) n FROM messages")["n"][0])
    child_msgs = int(q("SELECT count(*) n FROM messages WHERE role='child'")["n"][0])
    active_24h = int(q("""SELECT count(DISTINCT s.user_id) n FROM sessions s
        JOIN messages m ON m.session_id=s.id
        WHERE m.ts > now() - interval '24 hours'""")["n"][0])

    c = st.columns(5)
    c[0].metric("Дітей", users)
    c[1].metric("Активні (24г)", active_24h)
    c[2].metric("Сесій", sessions)
    c[3].metric("Повідомлень", messages)
    c[4].metric("Реплік/сесію", round(child_msgs/sessions,1) if sessions else 0)

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Етапи (FSM)")
        states = q("""SELECT current_state "Стан", count(*) "Дітей"
                      FROM sessions GROUP BY 1 ORDER BY 2 DESC""")
        if not states.empty:
            st.bar_chart(states.set_index("Стан"), height=240)
    with col2:
        st.subheader("Активність по днях")
        daily = q("""SELECT date_trunc('day',ts)::date "День", count(*) "Повідомлень"
                     FROM messages GROUP BY 1 ORDER BY 1""")
        if not daily.empty:
            st.line_chart(daily.set_index("День"), height=240)

    # ===== АНАЛІТИКА ЕФЕКТИВНОСТІ (4 графіки) =====
    st.divider()
    st.header("📈 Аналітика ефективності методології")
    with st.expander("ℹ️ Як читати ці графіки (натисніть)"):
        st.markdown("""
        - **🎯 Воронка утримання** — головний графік. Показує, до якої репліки доходять діти.
          Якщо крива різко падає на 3-й репліці — значить саме там методологія втрачає увагу.
          Це підказка, який стан/промпт треба підкрутити.
        - **📊 Розподіл глибини** — скільки діалогів були короткими (1-2) чи довгими (11+).
          Багато коротких = діти не чіпляються. Багато довгих = методологія тримає.
        - **📉 Довжина відповідей бота** — чи не скочується бот у короткі пусті фрази.
          Якщо лінія падає до нуля — бот «втомився», відповіді стали порожніми.
        - **🔥 Теплова карта** — коли діти заходять (година × день). Темніше = більше активності.
        """)

    PALETTE = ["#f0883e", "#a371f7", "#3fb950", "#58a6ff", "#db61a2"]

    # --- 1. ВОРОНКА УТРИМАННЯ ПО РЕПЛІКАХ ---
    st.subheader("🎯 Воронка утримання: до якої репліки доходять діти")
    st.caption("Скільки дітей написали хоча б N-ту репліку. Де крива падає — там методологія втрачає дитину.")
    retention = q("""
        WITH numbered AS (
          SELECT s.user_id,
                 row_number() OVER (PARTITION BY s.user_id ORDER BY m.ts) AS rn
          FROM messages m JOIN sessions s ON s.id=m.session_id
          WHERE m.role='child'
        )
        SELECT rn AS "Репліка", count(DISTINCT user_id) AS "Дітей"
        FROM numbered WHERE rn <= 15 GROUP BY rn ORDER BY rn
    """)
    if not retention.empty and len(retention) > 1:
        fig = go.Figure(go.Scatter(
            x=retention["Репліка"], y=retention["Дітей"],
            fill='tozeroy', mode='lines+markers',
            line=dict(color="#f0883e", width=3),
            marker=dict(size=8, color="#f0883e")))
        fig.update_layout(
            template=PLOTLY_TEMPLATE, height=320,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis_title="Номер репліки дитини", yaxis_title="Скільки дітей дійшло",
            margin=dict(l=40,r=20,t=20,b=40))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Замало даних для воронки — потрібно більше діалогів.")

    cc1, cc2 = st.columns(2)

    # --- 2. РОЗПОДІЛ ГЛИБИНИ ДІАЛОГІВ (гістограма) ---
    with cc1:
        st.subheader("📊 Розподіл глибини діалогів")
        depths = q("""SELECT count(*) c FROM messages WHERE role='child'
                      GROUP BY session_id""")
        if not depths.empty:
            bins = {"1-2":0,"3-5":0,"6-10":0,"11+":0}
            for c in depths["c"]:
                if c<=2: bins["1-2"]+=1
                elif c<=5: bins["3-5"]+=1
                elif c<=10: bins["6-10"]+=1
                else: bins["11+"]+=1
            dfb = pd.DataFrame({"Глибина":list(bins.keys()),"Діалогів":list(bins.values())})
            fig2 = px.bar(dfb, x="Глибина", y="Діалогів",
                          color="Глибина", color_discrete_sequence=PALETTE)
            fig2.update_layout(template=PLOTLY_TEMPLATE, height=280, showlegend=False,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=40,r=20,t=20,b=40))
            st.plotly_chart(fig2, use_container_width=True)
            st.caption("Багато коротких (1-2) = діти не чіпляються. Довгі = методологія тримає.")

    # --- 3. ДОВЖИНА ВІДПОВІДЕЙ БОТА В ЧАСІ ---
    with cc2:
        st.subheader("📉 Довжина відповідей бота")
        ailen = q("""SELECT row_number() OVER (ORDER BY ts) AS n,
                            length(text) AS len
                     FROM messages WHERE role='ai' ORDER BY ts""")
        if not ailen.empty and len(ailen) > 1:
            fig3 = go.Figure(go.Scatter(
                x=ailen["n"], y=ailen["len"], mode='lines',
                line=dict(color="#a371f7", width=2)))
            fig3.update_layout(template=PLOTLY_TEMPLATE, height=280,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis_title="Відповідь №", yaxis_title="Символів",
                margin=dict(l=40,r=20,t=20,b=40))
            st.plotly_chart(fig3, use_container_width=True)
            st.caption("Якщо падає до нуля — бот скочується в короткі пустушки (як Groq).")

    # --- 4. ТЕПЛОВА КАРТА АКТИВНОСТІ (година × день тижня) ---
    st.subheader("🔥 Коли діти заходять (теплова карта)")
    heat = q("""SELECT extract(dow from ts)::int AS dow,
                       extract(hour from ts)::int AS hr,
                       count(*) AS c
                FROM messages GROUP BY 1,2""")
    if not heat.empty:
        days_ua = ["Нд","Пн","Вт","Ср","Чт","Пт","Сб"]
        pivot = pd.DataFrame(0, index=days_ua, columns=list(range(24)))
        for _,r in heat.iterrows():
            pivot.iloc[int(r["dow"]), int(r["hr"])] = r["c"]
        fig4 = px.imshow(pivot, color_continuous_scale="Oranges", aspect="auto")
        fig4.update_layout(template=PLOTLY_TEMPLATE, height=260,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis_title="Година доби", yaxis_title="",
            margin=dict(l=40,r=20,t=20,b=40))
        st.plotly_chart(fig4, use_container_width=True)
        st.caption("Темніше = більше активності. Видно, коли діти користуються ботом.")

# ============ ДІАЛОГИ (фільтри + чат-вид) ============
with tab2:
    st.subheader("Читати діалоги")

    fc = st.columns([2,2,3])
    # фільтр по даті
    period = fc[0].selectbox("Період", ["Усі", "Сьогодні", "7 днів", "30 днів"])
    # фільтр по стану
    all_states = q("SELECT DISTINCT current_state s FROM sessions")["s"].dropna().tolist()
    state_f = fc[1].selectbox("Стан", ["Усі"] + all_states)
    # пошук по тексту
    search = fc[2].text_input("🔍 Пошук по тексту діалогу", "")

    # збираємо дітей з фільтрами
    where = ["1=1"]
    params = {}
    if period == "Сьогодні":
        where.append("m.ts::date = current_date")
    elif period == "7 днів":
        where.append("m.ts > now() - interval '7 days'")
    elif period == "30 днів":
        where.append("m.ts > now() - interval '30 days'")
    if state_f != "Усі":
        where.append("s.current_state = %(st)s"); params["st"] = state_f
    if search.strip():
        where.append("m.text ILIKE %(q)s"); params["q"] = f"%{search.strip()}%"

    # тягнемо ще ім'я/нік (з відкатом, якщо стара схема)
    try:
        kids = q(f"""
            SELECT u.id, u.tg_id,
                   COALESCE(u.first_name,'') AS name, u.username,
                   count(m.id) msgs, max(m.ts) last_ts
            FROM users u
            JOIN sessions s ON s.user_id=u.id
            JOIN messages m ON m.session_id=s.id
            WHERE {' AND '.join(where)}
            GROUP BY u.id, u.tg_id, u.first_name, u.username
            ORDER BY last_ts DESC
        """, params)
        has_names = True
    except Exception:
        kids = q(f"""
            SELECT u.id, u.tg_id, count(m.id) msgs, max(m.ts) last_ts
            FROM users u
            JOIN sessions s ON s.user_id=u.id
            JOIN messages m ON m.session_id=s.id
            WHERE {' AND '.join(where)}
            GROUP BY u.id, u.tg_id
            ORDER BY last_ts DESC
        """, params)
        has_names = False

    if kids.empty:
        st.info("Нічого не знайдено за фільтрами.")
    else:
        def make_label(r):
            name = str(r.get("name") or "").strip() if has_names else ""
            uname_raw = r.get("username") if has_names else None
            # username може бути None / NaN / число — приводимо надійно
            uname = ""
            if uname_raw is not None:
                try:
                    import pandas as _pd
                    if not _pd.isna(uname_raw):
                        uname = str(uname_raw).strip()
                except Exception:
                    uname = str(uname_raw).strip()
            who = name if name else f"Дитина #{r['id']}"
            tag = f" (@{uname})" if uname else ""
            return f"{who}{tag} · {r['msgs']} реплік"
        kids["label"] = kids.apply(make_label, axis=1)
        choice = st.selectbox(f"Знайдено дітей: {len(kids)}", kids["label"])
        sel_row = kids[kids["label"]==choice].iloc[0]
        uid = int(sel_row["id"])

        # клікабельне посилання на телеграм дитини (якщо є username)
        uname_sel = ""
        if has_names:
            raw = sel_row.get("username")
            if raw is not None:
                try:
                    import pandas as _pd
                    if not _pd.isna(raw):
                        uname_sel = str(raw).strip()
                except Exception:
                    uname_sel = str(raw).strip()
        if uname_sel:
            st.markdown(f"🔗 Написати в Telegram: [@{uname_sel}](https://t.me/{uname_sel})")
        else:
            st.caption(f"Прямого посилання немає (без @username). tg_id: {sel_row['tg_id']}")

        # ---- фільтри перегляду, щоб діалог не був суцільною стрічкою ----
        fc1, fc2, fc3 = st.columns([1.2, 1, 1])
        with fc1:
            _period = st.selectbox("Період:",
                ["Останні 7 днів", "Останні 30 днів", "Весь час"],
                index=0, key=f"dlg_period_{uid}")
        with fc2:
            _limit = st.selectbox("Показати реплік:", [30, 50, 100, 300],
                                  index=1, key=f"dlg_limit_{uid}")
        with fc3:
            _order = st.selectbox("Порядок:", ["Спочатку нові", "Спочатку старі"],
                                  index=0, key=f"dlg_order_{uid}")

        _days = {"Останні 7 днів": 7, "Останні 30 днів": 30, "Весь час": None}[_period]
        _where_period = "AND m.ts > now() - interval '%d days'" % _days if _days else ""

        dialog = q(f"""SELECT role, text, state, ts, markers, s.id AS sess
                        FROM messages m
                        JOIN sessions s ON s.id=m.session_id
                       WHERE s.user_id=%(uid)s {_where_period}
                       ORDER BY m.ts DESC
                       LIMIT {int(_limit)}""", {"uid": uid})
        # з бази прийшли останні N у зворотному порядку — розвертаємо за потреби
        if _order == "Спочатку старі":
            dialog = dialog.iloc[::-1]

        st.caption(f"Показано реплік: {len(dialog)}")

        # короткі назви моделей для підпису під реплікою
        _MODEL_SHORT = {
            "claude-sonnet-5": "Sonnet 5",
            "claude-opus-5": "Opus 5",
            "claude-fable-5": "Fable 5",
            "claude-haiku-4-5-20251001": "Haiku 4.5",
            "claude-sonnet-4-6": "Sonnet 4.6",
        }

        # детект зацикливания: ИИ повторяет начало фразы
        prev_ai_start = None
        _prev_sess = None
        for _, m in dialog.iterrows():
            # візуальний розрив між різними сесіями
            if _prev_sess is not None and m.get("sess") != _prev_sess:
                st.markdown("<hr style='border:none;border-top:1px dashed #E9E0D2;"
                            "margin:18px 0'>", unsafe_allow_html=True)
            _prev_sess = m.get("sess")
            t = m["text"]
            ts = pd.to_datetime(m["ts"]).strftime("%d.%m %H:%M")
            if m["role"] == "system":
                # службова позначка (напр. оцінка готовності до Вектора)
                st.markdown(
                    f"<div style='text-align:center;margin:10px 0;font-size:12px;"
                    f"color:#8A9096'>⋯ {t} · {ts} ⋯</div>", unsafe_allow_html=True)
            elif m["role"] == "child":
                st.markdown(f"<div class='meta'>🧒 {ts}</div>"
                            f"<div class='bubble-child'>{t}</div>", unsafe_allow_html=True)
            else:
                # прапорець зацикливания
                start = t[:15]
                flag = ""
                if prev_ai_start and start == prev_ai_start:
                    flag = "<span class='flag flag-warn'>повтор зачину</span>"
                prev_ai_start = start
                # яка модель відповідала (пишеться в markers при генерації)
                _mk = m.get("markers")
                if isinstance(_mk, str):
                    try: _mk = json.loads(_mk)
                    except Exception: _mk = {}
                _model = (_mk or {}).get("model", "")
                _label = _MODEL_SHORT.get(_model, _model)
                _model_tag = (f" · <span style='color:#8A9096'>модель ШІ:</span> "
                              f"<span style='color:#C4642A;font-weight:600'>"
                              f"{_label}</span>") if _label else ""
                st.markdown(f"<div class='meta' style='text-align:right'>"
                            f"🔥 Провідник · {m['state']} · {ts}{_model_tag}{flag}</div>"
                            f"<div class='bubble-ai'>{t}</div>", unsafe_allow_html=True)

# ============ ВОРОНКА ============
with tab3:
    st.subheader("Воронка методології: Іскра → Вектор")
    st.caption("Скільки дітей дійшло до кожного етапу")

    total = int(q("SELECT count(*) n FROM users")["n"][0])
    reached_iskra = int(q("""SELECT count(DISTINCT user_id) n FROM sessions
        WHERE current_state IN ('iskra','vektor')""")["n"][0])
    reached_vektor = int(q("""SELECT count(DISTINCT user_id) n FROM sessions
        WHERE current_state='vektor'""")["n"][0])

    funnel = pd.DataFrame({
        "Етап": ["Зайшли", "Іскра", "Вектор"],
        "Дітей": [total, reached_iskra, reached_vektor]
    })
    st.bar_chart(funnel.set_index("Етап"), height=260)

    c = st.columns(3)
    c[0].metric("Зайшли", total)
    c[1].metric("Дійшли до Іскри", reached_iskra,
                f"{round(100*reached_iskra/total)}%" if total else "—")
    c[2].metric("Дійшли до Вектора", reached_vektor,
                f"{round(100*reached_vektor/total)}%" if total else "—")
    st.info("**Вектор** — ключова мета MVP: дитина сама сформулювала ціль. "
            "Конверсія в Вектор = головний показник, чи працює методологія.")

# ============ ЯКІСТЬ ============
with tab4:
    st.subheader("Якість діалогів")

    # середня довжина діалогу
    avg_len = q("""SELECT avg(c) a FROM (
        SELECT session_id, count(*) c FROM messages WHERE role='child'
        GROUP BY session_id) t""")["a"][0]
    longest = q("""SELECT max(c) m FROM (
        SELECT session_id, count(*) c FROM messages WHERE role='child'
        GROUP BY session_id) t""")["m"][0]

    c = st.columns(3)
    c[0].metric("Середня глибина діалогу", round(float(avg_len),1) if avg_len else 0)
    c[1].metric("Найдовший діалог", int(longest) if longest else 0)
    stalled = int(q("""SELECT count(*) n FROM (
        SELECT session_id, count(*) c FROM messages WHERE role='child'
        GROUP BY session_id HAVING count(*) <= 2) t""")["n"][0])
    c[2].metric("Заглухли (≤2 реплік)", stalled,
                help="Діти що написали 1-2 рази і зникли — тривожний сигнал")

    st.divider()

    # ----- ТАБЛИЦЯ ПО КОЖНІЙ ДИТИНІ -----
    st.subheader("📋 Якість по кожній дитині")
    per_child = q("""
        SELECT
            u.id AS "Дитина",
            u.tg_id AS "tg",
            count(*) FILTER (WHERE m.role='child') AS "Реплік",
            count(*) FILTER (WHERE m.role='ai') AS "Відповідей",
            max(s.current_state) AS "Стан",
            round(avg(length(m.text)) FILTER (WHERE m.role='child')) AS "Сер.довжина repl",
            min(m.ts) AS "Початок",
            max(m.ts) AS "Останнє"
        FROM users u
        JOIN sessions s ON s.user_id=u.id
        JOIN messages m ON m.session_id=s.id
        GROUP BY u.id, u.tg_id
        ORDER BY count(*) FILTER (WHERE m.role='child') DESC
    """)
    if not per_child.empty:
        # маркер залученості: багато реплік = добре
        def engagement(n):
            if n >= 8: return "🟢 висока"
            if n >= 4: return "🟡 середня"
            return "🔴 низька"
        per_child["Залученість"] = per_child["Реплік"].map(engagement)
        # тривалість сесії в хвилинах
        per_child["Хвилин"] = (
            (pd.to_datetime(per_child["Останнє"]) - pd.to_datetime(per_child["Початок"]))
            .dt.total_seconds() / 60
        ).round().astype(int)
        show = per_child[["Дитина","tg","Реплік","Відповідей","Стан",
                          "Залученість","Хвилин","Сер.довжина repl"]]
        st.dataframe(show, use_container_width=True, hide_index=True)
        st.caption("Залученість: 🟢 8+ реплік · 🟡 4-7 · 🔴 ≤3. "
                   "Низька = дитина не зачепилась, методологія не спрацювала.")

    st.divider()

    # ----- ГРАФІК: глибина діалогу по дітях -----
    st.subheader("📊 Глибина діалогу по дітях")
    if not per_child.empty:
        chart_data = per_child.set_index("Дитина")[["Реплік"]]
        st.bar_chart(chart_data, height=240)

    st.divider()

    # ----- МАРКЕРИ ЯКОСТІ -----
    st.subheader("🚦 Маркери якості методології")

    # зацикливание: ИИ повторил начало фразы 2+ раз
    loops = q("""
        WITH ai AS (
          SELECT s.user_id, left(m.text,15) AS start, m.ts,
                 lag(left(m.text,15)) OVER (PARTITION BY s.user_id ORDER BY m.ts) AS prev
          FROM messages m JOIN sessions s ON s.id=m.session_id
          WHERE m.role='ai'
        )
        SELECT count(*) n FROM ai WHERE start = prev
    """)["n"][0]

    mc = st.columns(3)
    mc[0].metric("🔁 Повторів зачину ШІ", int(loops),
                 help="Скільки разів бот почав відповідь так само як попередню — ознака зацикленості (як Groq)")
    # дітей що дійшли далі 5 реплік (зачепились)
    hooked = int(q("""SELECT count(*) n FROM (
        SELECT session_id FROM messages WHERE role='child'
        GROUP BY session_id HAVING count(*) >= 5) t""")["n"][0])
    mc[1].metric("🎣 Зачепились (5+ реплік)", hooked,
                 help="Діти що написали 5+ разів — методологія втримала увагу")
    total_kids = int(q("SELECT count(*) n FROM users")["n"][0])
    rate = round(100*hooked/total_kids) if total_kids else 0
    mc[2].metric("Утримання", f"{rate}%",
                 help="Частка дітей що зачепились від усіх")

    st.divider()
    st.subheader("Розподіл реплік по станах")
    by_state = q("""SELECT state "Стан",
        count(*) FILTER (WHERE role='ai') "Відповідей Провідника",
        count(*) FILTER (WHERE role='child') "Реплік дитини"
        FROM messages WHERE state IS NOT NULL GROUP BY 1""")
    if not by_state.empty:
        st.dataframe(by_state, use_container_width=True, hide_index=True)

# ============ МЕТОДОЛОГІЯ (Ольга редагує промпти) ============
with tab5:
    st.subheader("⚙️ Лабораторія методології")
    st.caption("Тут ви редагуєте промпти Провідника. Зберегли → бот одразу "
               "відповідає по-новому. Тестуйте в Telegram без перезапуску.")

    def get_conn_w():
        dsn = os.environ.get("DATABASE_URL") or st.secrets.get("DATABASE_URL","")
        if dsn.startswith("postgres://"):
            dsn = dsn.replace("postgres://","postgresql://",1)
        return psycopg2.connect(dsn, sslmode="require")

    # перевірка чи є таблиця
    try:
        meth = q("SELECT state_key, title, system_prompt, sample_phrases, updated_at, updated_by FROM methodology ORDER BY state_key")
        has_table = True
    except Exception:
        has_table = False

    if not has_table:
        st.warning("Таблиця методології ще не створена. "
                   "Розробнику: запустити `python -m db.migrate_methodology`.")
    elif meth.empty:
        st.info("Методологія порожня. Запустіть міграцію з YAML.")
    else:
        # вибір що редагувати
        labels = {
            "iskra": "🔥 Іскра (промпт стану)",
            "vektor": "🎯 Вектор (промпт стану)",
            "__global__": "🚫 Глобальні заборони",
        }
        meth["nice"] = meth["state_key"].map(lambda k: labels.get(k, k))
        pick = st.selectbox("Що редагувати:", meth["nice"].tolist())
        row = meth[meth["nice"]==pick].iloc[0]
        key = row["state_key"]

        st.caption(f"Останнє редагування: {row['updated_at']} · ким: {row['updated_by']}")

        new_prompt = st.text_area(
            "Промпт (інструкція для Провідника):",
            value=row["system_prompt"], height=380, key=f"prompt_{key}")

        new_phrases = None
        if key not in ("__global__",):
            new_phrases = st.text_area(
                "Приклади фраз (по одній на рядок, опційно):",
                value=row["sample_phrases"] or "", height=120, key=f"phr_{key}")

        col_save, col_info = st.columns([1,3])
        if col_save.button("💾 Зберегти", type="primary"):
            try:
                conn = get_conn_w()
                cur = conn.cursor()
                if new_phrases is not None:
                    cur.execute("""UPDATE methodology
                        SET system_prompt=%s, sample_phrases=%s,
                            updated_at=now(), updated_by='olga'
                        WHERE state_key=%s""", (new_prompt, new_phrases, key))
                else:
                    cur.execute("""UPDATE methodology
                        SET system_prompt=%s, updated_at=now(), updated_by='olga'
                        WHERE state_key=%s""", (new_prompt, key))
                conn.commit(); conn.close()
                q.clear()  # скинути кеш
                st.success("✅ Збережено! Бот уже відповідає по-новому. "
                           "Перевірте в Telegram.")
            except Exception as e:
                st.error(f"Помилка збереження: {e}")
        col_info.caption("Після збереження напишіть боту в Telegram — "
                         "він візьме нову версію з першої ж відповіді.")

# ============ КОНТЕНТ (Ольга наповнює дерево входу) ============
with tab6:
    st.subheader("📝 Контент дерева входу")
    st.caption("Тут ви наповнюєте те, що бот показує дитині: питання діагностики, "
               "хаби, тексти входу, логіку аватара. Бот бере звідси.")

    def conn_w():
        dsn = os.environ.get("DATABASE_URL") or st.secrets.get("DATABASE_URL","")
        if dsn.startswith("postgres://"):
            dsn = dsn.replace("postgres://","postgresql://",1)
        return psycopg2.connect(dsn, sslmode="require")

    # перевірка таблиць
    try:
        _ = q("SELECT 1 FROM entry_texts LIMIT 1")
        ready = True
    except Exception:
        ready = False

    if not ready:
        st.warning("Таблиці контенту ще не створені. "
                   "Розробнику: `python -m db.init_content`")
    else:
        sub = st.radio("Розділ:", ["✍️ Тексти входу", "❓ Діагностика (16 питань)",
                                    "🗂 Хаби та підтеми", "🎭 Аватар"], horizontal=True)

        # ---- ТЕКСТИ ВХОДУ ----
        if sub == "✍️ Тексти входу":
            texts = q("SELECT key, text, note FROM entry_texts ORDER BY key")
            for _, row in texts.iterrows():
                st.markdown(f"**{row['note']}** `({row['key']})`")
                new = st.text_area("", value=row["text"], key=f"txt_{row['key']}",
                                   height=80, label_visibility="collapsed")
                if st.button("💾 Зберегти", key=f"savetxt_{row['key']}"):
                    cn=conn_w();cur=cn.cursor()
                    cur.execute("UPDATE entry_texts SET text=%s,updated_at=now() WHERE key=%s",
                                (new,row["key"]));cn.commit();cn.close();q.clear()
                    st.success("Збережено!")
                st.divider()

        # ---- ДІАГНОСТИКА ----
        elif sub == "❓ Діагностика (16 питань)":
            qs = q("SELECT id, ord, text, options FROM diag_questions ORDER BY ord")
            st.caption(f"Питань у базі: {len(qs)}. Варіанти: А=Аутсайдер, Б=Глядач, В=Гравець.")
            if qs.empty:
                st.info("Питань ще немає.")
            for _, row in qs.iterrows():
                with st.expander(f"Питання {row['ord']}: {row['text'][:50]}..."):
                    new_text = st.text_input("Текст питання", value=row["text"],
                                             key=f"q_{row['id']}")
                    opts = row["options"] if isinstance(row["options"],list) else json.loads(row["options"])
                    new_opts = []
                    for j,o in enumerate(opts):
                        scores = o.get("scores",{})
                        who = "А/outsider" if "outsider" in scores else ("Б/spectator" if "spectator" in scores else "В/player")
                        lbl = st.text_input(f"Варіант {who}", value=o["label"],
                                            key=f"q_{row['id']}_o{j}")
                        new_opts.append({"label":lbl,"scores":scores})
                    if st.button("💾 Зберегти питання", key=f"saveq_{row['id']}"):
                        cn=conn_w();cur=cn.cursor()
                        cur.execute("UPDATE diag_questions SET text=%s,options=%s,updated_at=now() WHERE id=%s",
                                    (new_text,json.dumps(new_opts,ensure_ascii=False),int(row["id"])))
                        cn.commit();cn.close();q.clear()
                        st.success("Збережено!")

        # ---- ХАБИ ----
        elif sub == "🗂 Хаби та підтеми":
            # trigger_phrase може ще не існувати в базі — читаємо з відкатом
            try:
                hubs = q("SELECT id, label, subtopics, COALESCE(trigger_phrase,'') AS trigger_phrase FROM hubs ORDER BY ord")
                has_trigger = True
            except Exception:
                hubs = q("SELECT id, label, subtopics FROM hubs ORDER BY ord")
                has_trigger = False
            st.caption("Для кожного хаба: підтеми (по одній на рядок) і тригерна фраза — "
                       "що бот каже ОДРАЗУ після вибору цього хаба (вхід-провокація).")
            if not has_trigger:
                st.warning("Поле тригерної фрази ще не додано в базу — попросіть @vitter запустити міграцію.")
            for _, row in hubs.iterrows():
                subs = row["subtopics"] if isinstance(row["subtopics"],list) else json.loads(row["subtopics"] or "[]")
                with st.expander(f"🗂 {row['label']} ({len(subs)} підтем)"):
                    if has_trigger:
                        trig = st.text_area(
                            "⚡ Тригерна фраза після вибору (вхід-провокація):",
                            value=row.get("trigger_phrase") or "",
                            key=f"trig_{row['id']}", height=90,
                            placeholder="Напр.: О, Майбутнє! Знаєш, є професія, якої ще не існує — але через 10 років вона буде головною. Хочеш дізнатись, яка?")
                    txt = st.text_area("Підтеми (рядок = підтема):",
                                       value="\n".join(subs), key=f"hub_{row['id']}", height=120)
                    if st.button("💾 Зберегти", key=f"savehub_{row['id']}"):
                        new_subs=[s.strip() for s in txt.split("\n") if s.strip()]
                        cn=conn_w();cur=cn.cursor()
                        if has_trigger:
                            cur.execute("UPDATE hubs SET subtopics=%s, trigger_phrase=%s WHERE id=%s",
                                        (json.dumps(new_subs,ensure_ascii=False), trig.strip(), row["id"]))
                        else:
                            cur.execute("UPDATE hubs SET subtopics=%s WHERE id=%s",
                                        (json.dumps(new_subs,ensure_ascii=False),row["id"]))
                        cn.commit();cn.close();q.clear()
                        st.success("Збережено!")

        # ---- АВАТАР ----
        elif sub == "🎭 Аватар":
            st.caption("Як домінанта профілю перетворюється на картку-аватар дитини.")
            am = q("SELECT profile_type, superpower, weakness, driver FROM avatar_map")
            names = {"player":"🟢 Гравець","spectator":"🟡 Глядач","outsider":"🔴 Аутсайдер"}
            for _, row in am.iterrows():
                st.markdown(f"### {names.get(row['profile_type'],row['profile_type'])}")
                sp = st.text_input("Суперсила", value=row["superpower"] or "", key=f"av_sp_{row['profile_type']}")
                wk = st.text_input("Зона росту", value=row["weakness"] or "", key=f"av_wk_{row['profile_type']}")
                dr = st.text_input("Що рухає (драйвер)", value=row["driver"] or "", key=f"av_dr_{row['profile_type']}")
                if st.button("💾 Зберегти", key=f"saveav_{row['profile_type']}"):
                    cn=conn_w();cur=cn.cursor()
                    cur.execute("""UPDATE avatar_map SET superpower=%s,weakness=%s,driver=%s,updated_at=now()
                        WHERE profile_type=%s""",(sp,wk,dr,row["profile_type"]))
                    cn.commit();cn.close();q.clear()
                    st.success("Збережено!")
                st.divider()

# ============ ДОВІДКА (інструкція всередині кабінету) ============
with tab8:
    st.subheader("❓ Як користуватись кабінетом")
    st.markdown("""
Вітаю, Ольго! Тут ви **спостерігаєте**, як діти спілкуються з ботом,
і **керуєте** методологією та контентом — без програміста.

Головне: ви працюєте переважно з двома вкладками —
**⚙️ Методологія** (як говорить бот) і **📝 Контент** (що показує бот).
Решта вкладок — щоб спостерігати.

---

#### ⚙️ Методологія — ви редагуєте промпти
1. Оберіть: 🔥 Іскра / 🎯 Вектор / 🚫 Глобальні заборони
2. Правте текст інструкції для бота
3. Натисніть **💾 Зберегти**
4. Напишіть боту в Telegram — він **одразу** відповідає по-новому

> Це жива лабораторія: крутите формулювання і відразу бачите результат.
> Якщо щось зламалось — поверніть назад текст і збережіть.

---

#### 📝 Контент — ви наповнюєте дерево входу
- **✍️ Тексти входу** — привітання, аватар, пропозиції
- **❓ Діагностика** — 16 питань (А=Аутсайдер, Б=Глядач, В=Гравець). Чернетка — правте під себе
- **🗂 Хаби** — впишіть підтеми для тем (по одній на рядок)
- **🎭 Аватар** — суперсила/зона росту/драйвер для кожного типу

---

#### 📊 Спостереження
- **Огляд** — загальні цифри + графіки (над ними є «ℹ️ Як читати»)
- **Діалоги** — читати реальні розмови, з фільтрами і пошуком
- **Воронка** — скільки дітей дійшло до Вектора (головна мета)
- **Якість** — таблиця по кожній дитині, хто зачепився (🟢/🟡/🔴)

---

#### Щоб бот запрацював повністю, від вас:
1. Затвердити/поправити **16 питань** діагностики
2. Заповнити **аватар** (суперсила/зона росту/драйвер × 3 типи)
3. Додати **підтеми** хоча б для одного хаба

Після цього бот вестиме дитину: знайомство → діагностика → аватар → тема → Іскра.

---

#### Як тестувати бота (у Telegram)
- Відкрийте [@OwnLearningLab_bot](https://t.me/OwnLearningLab_bot) і напишіть `/start` — він почне з знайомства (запитає ім'я).
- Далі пройдіть діагностику кнопками, побачите аватар і вибір теми.
- Щоб почати **заново** з чистого аркуша — просто напишіть `/start` ще раз.
- Усе, що ви напишете боту, одразу з'являється у вкладці **Діалоги**.

---

#### Словничок (що означають слова)
- **Іскра** — етап, де дитина знаходить, що їй цікаво.
- **Вектор** — дитина сама сформулювала ціль («хочу зробити Y»). Головна мета.
- **Залученість 🟢/🟡/🔴** — наскільки дитина зачепилась: 🟢 багато спілкувалась, 🔴 пішла швидко.
- **Профіль (Аутсайдер/Глядач/Гравець)** — тип ставлення дитини, який визначає діагностика.

---

#### Якщо щось пішло не так
- **Бот не відповідає** — напишіть у Telegram @vitter, можливо потрібен перезапуск.
- **Хочу скинути дитину на початок** — нехай напише `/start`, дерево почнеться заново.
- **Зберегла зміни, а бот не змінився** — напишіть боту нове повідомлення, він бере свіжу версію з наступної відповіді.
- **Бачу `[у дужках]`** — це незаповнений контент, впишіть свій текст у вкладці Контент.

---

*Якщо щось не зрозуміло — пишіть у Telegram @vitter.*
    """)

# ============ УЧНІ (управління учнями) ============
with tab7:
    st.subheader("👥 Управління учнями")

    def conn_uw():
        dsn = os.environ.get("DATABASE_URL") or st.secrets.get("DATABASE_URL","")
        if dsn.startswith("postgres://"):
            dsn = dsn.replace("postgres://","postgresql://",1)
        return psycopg2.connect(dsn, sslmode="require")

    # тягнемо учнів з ім'ям/ніком (best-effort на випадок старої схеми)
    try:
        pupils = q("""
            SELECT u.id, u.tg_id,
                   COALESCE(u.first_name,'—') AS name,
                   u.username,
                   COALESCE(u.status,'active') AS status,
                   COALESCE(u.note,'') AS note,
                   count(m.id) AS msgs,
                   max(m.ts) AS last_seen
            FROM users u
            LEFT JOIN sessions s ON s.user_id=u.id
            LEFT JOIN messages m ON m.session_id=s.id
            GROUP BY u.id, u.tg_id, u.first_name, u.username, u.status, u.note
            ORDER BY max(m.ts) DESC NULLS LAST
        """)
        new_schema = True
    except Exception:
        pupils = q("""SELECT u.id, u.tg_id, count(m.id) msgs, max(m.ts) last_seen
            FROM users u LEFT JOIN sessions s ON s.user_id=u.id
            LEFT JOIN messages m ON m.session_id=s.id
            GROUP BY u.id, u.tg_id ORDER BY max(m.ts) DESC NULLS LAST""")
        new_schema = False
        st.warning("Поля імені ще не додані. Розробнику: `python -m db.migrate_users`")

    if pupils.empty:
        st.info("Поки немає учнів.")
    else:
        st.caption(f"Усього учнів: {len(pupils)}")

        # таблиця-огляд
        if new_schema:
            disp = pupils.copy()
            disp["Telegram"] = disp["username"].map(
                lambda u: f"@{u}" if u else "—")
            disp["Статус"] = disp["status"].map(
                {"active":"🟢 активний","test":"🧪 тест","blocked":"⛔ заблок."})
            show = disp[["id","name","Telegram","tg_id","msgs","Статус","last_seen"]]
            show.columns = ["ID","Ім'я","Telegram","tg_id","Реплік","Статус","Останній раз"]
            st.dataframe(show, use_container_width=True, hide_index=True)
        else:
            st.dataframe(pupils, use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("#### Дії з учнем")
        pupils["pick"] = pupils.apply(
            lambda r: f"#{r['id']} · {r.get('name','—')} · tg {r['tg_id']} · {r['msgs']} реплік", axis=1)
        sel = st.selectbox("Оберіть учня:", pupils["pick"])
        prow = pupils[pupils["pick"]==sel].iloc[0]
        uid = int(prow["id"])

        # посилання на телеграм якщо є username
        if new_schema and prow.get("username"):
            st.markdown(f"🔗 Telegram: [@{prow['username']}](https://t.me/{prow['username']})")
        else:
            st.caption("Прямого посилання нема (учень без @username). "
                       f"tg_id: {prow['tg_id']}")

        ca, cb, cc = st.columns(3)

        # пометка статусу
        if new_schema:
            with ca:
                new_status = st.selectbox("Статус:",
                    ["active","test","blocked"],
                    index=["active","test","blocked"].index(prow["status"]))
                if st.button("Зберегти статус"):
                    cn=conn_uw();cur=cn.cursor()
                    cur.execute("UPDATE users SET status=%s WHERE id=%s",(new_status,uid))
                    cn.commit();cn.close();q.clear()
                    st.success(f"Статус: {new_status}")
            with cb:
                note = st.text_input("Нотатка:", value=prow.get("note",""))
                if st.button("Зберегти нотатку"):
                    cn=conn_uw();cur=cn.cursor()
                    cur.execute("UPDATE users SET note=%s WHERE id=%s",(note,uid))
                    cn.commit();cn.close();q.clear()
                    st.success("Нотатку збережено")

        # видалення з підтвердженням
        with cc:
            st.markdown("**🗑 Видалити назавжди**")
            confirm = st.checkbox("Я впевнена, видалити всі дані цього учня")
            if st.button("🗑 Видалити", type="secondary", disabled=not confirm):
                cn=conn_uw();cur=cn.cursor()
                cur.execute("DELETE FROM users WHERE id=%s",(uid,))  # каскад знесе сесії+повідомлення
                cn.commit();cn.close();q.clear()
                st.success("Учня видалено (разом з діалогами).")
                st.rerun()

# ============ 🔐 КОМАНДА (тільки admin/owner) ============
if tab9 is not None:
    with tab9:
        st.subheader("Команда кабінету")
        st.caption("Доступи до цього кабінету: хто може заходити, ролі, паролі. "
                   "Це користувачі КАБІНЕТУ (не діти — діти у вкладці Учні).")

        import secrets as _secrets

        team = q("SELECT id, email, role, created_at FROM dashboard_users ORDER BY id")
        st.dataframe(
            team.rename(columns={"email":"Email","role":"Роль","created_at":"Створений"}),
            use_container_width=True, hide_index=True,
            column_config={"id": None})

        st.markdown("---")
        colA, colB = st.columns(2)

        # ---- створити користувача ----
        with colA:
            st.markdown("#### Додати учасника")
            with st.form("add_team_user", clear_on_submit=True):
                new_email = st.text_input("Email (логін)")
                new_pw = st.text_input("Пароль", type="password",
                                       help="Мін. 8 символів. Передайте учаснику особисто.")
                new_role = st.selectbox("Роль", ["methodologist", "admin", "owner"],
                    format_func=lambda r: {"methodologist":"Методолог","admin":"Адмін","owner":"Власник"}[r])
                add_ok = st.form_submit_button("Створити")
            if add_ok:
                if not new_email.strip() or len(new_pw) < 8:
                    st.error("Вкажіть email і пароль від 8 символів.")
                else:
                    salt = _secrets.token_hex(16)
                    pw_hash = _hash_pw(new_pw, salt)
                    try:
                        cn = conn_w(); cur = cn.cursor()
                        cur.execute("""INSERT INTO dashboard_users (email, pw_salt, pw_hash, role)
                                       VALUES (%s,%s,%s,%s)""",
                                    (new_email.strip().lower(), salt, pw_hash, new_role))
                        cn.commit(); cn.close(); q.clear()
                        st.success(f"✅ {new_email.strip().lower()} доданий ({new_role})")
                        st.rerun()
                    except Exception as e:
                        st.error("Не вдалось (можливо, email вже існує).")

        # ---- змінити пароль / видалити ----
        with colB:
            st.markdown("#### Пароль і видалення")
            emails = team["email"].tolist()
            sel_email = st.selectbox("Учасник:", emails)
            with st.form("chpw_form"):
                pw2 = st.text_input("Новий пароль", type="password")
                ch_ok = st.form_submit_button("🔑 Змінити пароль")
            if ch_ok:
                if len(pw2) < 8:
                    st.error("Пароль від 8 символів.")
                else:
                    salt = _secrets.token_hex(16)
                    cn = conn_w(); cur = cn.cursor()
                    cur.execute("UPDATE dashboard_users SET pw_salt=%s, pw_hash=%s WHERE email=%s",
                                (salt, _hash_pw(pw2, salt), sel_email))
                    cn.commit(); cn.close(); q.clear()
                    st.success(f"✅ Пароль для {sel_email} змінено")

            st.markdown("")
            if sel_email == st.session_state.auth_email:
                st.caption("🙅 Себе видалити не можна.")
            else:
                confirm_del = st.checkbox(f"Підтверджую видалення {sel_email}")
                if st.button("🗑 Видалити учасника", disabled=not confirm_del):
                    cn = conn_w(); cur = cn.cursor()
                    cur.execute("DELETE FROM dashboard_users WHERE email=%s", (sel_email,))
                    cn.commit(); cn.close(); q.clear()
                    st.success(f"🗑 {sel_email} видалений")
                    st.rerun()

# ============ 🎭 ПРОФІЛІ (4 осі + згенеровані аватари) ============
with tab_prof:
    st.subheader("Профілі дітей та згенеровані аватари")
    st.caption("Що система визначила по кожній дитині: тип навчання, драйвер, "
               "рівень зрілості — і який аватар згенерував ШІ. "
               "Тут ви перевіряєте, чи діагностика влучає в реальність.")

    # --- дані (з відкатом, якщо міграція ще не пройшла) ---
    _prof_err = None
    try:
        prof = q("""
            SELECT u.id,
                   COALESCE(o.name, '') AS name,
                   p.learning_type, p.driver, p.maturity, p.axis_scores
              FROM users u
              LEFT JOIN profiles p ON p.user_id=u.id
              LEFT JOIN onboarding o ON o.user_id=u.id
             ORDER BY u.id
        """)
        # к-сть реплік окремо (щоб важкий підзапит не ламав основний)
        try:
            msgs = q("""SELECT s.user_id AS id, count(*) AS msgs
                          FROM messages m JOIN sessions s ON s.id=m.session_id
                         GROUP BY s.user_id""")
            prof = prof.merge(msgs, on="id", how="left")
        except Exception:
            prof["msgs"] = 0
        prof["msgs"] = prof["msgs"].fillna(0).astype(int)
        has4 = True
    except Exception as e:
        prof = None
        has4 = False
        _prof_err = str(e)

    if not has4 or prof is None or prof.empty:
        st.info("Профілі за 4 осями ще не заповнені. Вони з'являються після того, "
                "як дитина проходить діагностику (потрібна міграція add_profile_4axis).")
        if _prof_err:
            with st.expander("Технічна деталь (для розробника)"):
                st.code(_prof_err)
    else:
        # ---- зведення: розподіл типів навчання ----
        st.markdown("#### Розподіл типів навчання")
        dist = prof["learning_type"].fillna("— не визначено").value_counts().reset_index()
        dist.columns = ["Тип навчання", "Дітей"]
        c1, c2 = st.columns([1, 1])
        with c1:
            st.dataframe(dist, use_container_width=True, hide_index=True)
        with c2:
            drv = prof["driver"].fillna("— не визначено").value_counts().reset_index()
            drv.columns = ["Драйвер", "Дітей"]
            st.dataframe(drv, use_container_width=True, hide_index=True)

        # попередження про перекіс — головний сигнал якості діагностики
        determined = prof["learning_type"].dropna()
        if len(determined) >= 3 and determined.nunique() == 1:
            st.warning("⚠️ Усім дітям визначено ОДИН тип навчання. Схоже, питання "
                       "діагностики поки не розрізняють осі — варто переробити їх "
                       "під 4 осі (вкладка Контент → Діагностика).")

        st.markdown("---")
        st.markdown("#### Профіль по кожній дитині")
        table = prof.copy()
        table["Дитина"] = table.apply(
            lambda r: (str(r["name"]).strip() if r["name"] else f"Дитина #{r['id']}"), axis=1)
        show = table[["Дитина", "learning_type", "driver", "maturity", "msgs"]].rename(
            columns={"learning_type": "Тип навчання", "driver": "Драйвер",
                     "maturity": "Зрілість", "msgs": "Реплік"})
        st.dataframe(show, use_container_width=True, hide_index=True)

        # ---- детальна картка обраної дитини ----
        st.markdown("---")
        st.markdown("#### Детально: профіль і аватар")
        names = table["Дитина"].tolist()
        pick = st.selectbox("Оберіть дитину:", names, key="prof_pick")
        row = table[table["Дитина"] == pick].iloc[0]
        uid = int(row["id"])

        cA, cB, cC = st.columns(3)
        cA.metric("Тип навчання", row["learning_type"] or "—")
        cB.metric("Драйвер", row["driver"] or "—")
        cC.metric("Зрілість", row["maturity"] or "—")

        # як саме профіль впливає на розмову (ті самі правила, що у промпті бота)
        _LEARNING_STYLE = {
            "діяч": ("Діяч — осмислює через дію.\n"
                     "• Дія одразу, без довгих вступів\n"
                     "• Спочатку «спробуй», потім «що вийшло?»\n"
                     "• Мікровиклики працюють краще за пояснення"),
            "рефлектор": ("Рефлектор — вчиться на досвіді інших.\n"
                     "• Конкретні кейси реальних людей\n"
                     "• Не квапити до «пробуй», дати зважити\n"
                     "• Пауза — це його спосіб думати, не втрата інтересу\n"
                     "• Чесні шляхи з помилками, не глянець"),
            "мислитель": ("Мислитель — бачить світ через концепції.\n"
                     "• Спочатку структура: як влаштовано, за яким принципом\n"
                     "• Відповідати на «чому саме так»\n"
                     "• Дати побудувати модель ПЕРЕД діями\n"
                     "• Парадокси — найкраще паливо"),
            "сенсор": ("Сенсор — потребує тілесно-чуттєвого досвіду.\n"
                     "• Дати спробувати, помацати, прожити\n"
                     "• «Як тобі це відчувалось?» важливіше за «що вийшло?»\n"
                     "• Реальний матеріал і реальна дія, не абстракції"),
        }
        _DRIVER_HOOK = {
            "досягнення": "Драйвер досягнення — показувати видимий результат і прогрес.",
            "цікавість":  "Драйвер цікавість — тримати на недоказаному: «а що там далі».",
            "творчість":  "Драйвер творчість — залишати простір зробити по-своєму.",
            "виклик":     "Драйвер виклик — складність як паливо: «більшість тут здається».",
            "сенс":       "Драйвер сенс — пояснювати, навіщо це і на що впливає.",
            "разом":      "Драйвер разом — згадувати спільну дію: кому показати, з ким зробити.",
            "визнання":   "Драйвер визнання — підкреслювати, що результат помітять.",
        }
        _MATURITY = {
            "виконавець": "Рівень початківець — прості конкретні кроки, один за раз.",
            "проблемник": "Рівень проблемник — можна давати суперечності без єдиної відповіді.",
            "пошуковець": "Рівень пошуковець — витримує невизначеність, простір для гіпотез.",
            "архітектор": "Рівень архітектор — працює з системами, стратегічні питання.",
        }

        if row["learning_type"] or row["driver"]:
            with st.expander("Як Провідник адаптує розмову під цю дитину"):
                _blocks = []
                _lt = (row["learning_type"] or "").lower()
                _dr = (row["driver"] or "").lower()
                _mt = (row["maturity"] or "").lower()
                if _lt in _LEARNING_STYLE: _blocks.append(_LEARNING_STYLE[_lt])
                if _dr in _DRIVER_HOOK: _blocks.append(_DRIVER_HOOK[_dr])
                if _mt in _MATURITY: _blocks.append(_MATURITY[_mt])
                st.code("\n\n".join(_blocks) or "—", language=None)
                st.caption("Ці інструкції додаються до промпту Провідника при кожній "
                           "відповіді саме цій дитині — поверх правил етапу, не замість них.")

        # бали по осях — показують, наскільки впевнено визначився профіль
        ax = row["axis_scores"]
        if isinstance(ax, str):
            try: ax = json.loads(ax)
            except Exception: ax = {}
        if ax:
            # висновок ІІ-профайлера — головне для валідації методики
            ai_a = ax.get("ai_analysis") or {}
            if ai_a:
                conf = ai_a.get("confidence")
                st.markdown(f"**🤖 Висновок ШІ:** {ai_a.get('reasoning','—')}")
                if conf is not None:
                    try:
                        st.progress(float(conf), text=f"Впевненість визначення: {float(conf):.0%}")
                    except Exception:
                        pass
            with st.expander("Відповіді дитини на діагностику (сирі дані)"):
                for i, a in enumerate(ax.get("answers") or [], 1):
                    st.markdown(f"**{i}. {a.get('question','')}**  \n→ _{a.get('answer','')}_")
                if ax.get("weights"):
                    st.markdown("**Ваги від методолога:**")
                    st.json(ax["weights"])

        # згенеровані аватари цієї дитини
        try:
            av = q("""SELECT name, subtitle, superpower, weakness,
                             activation_phrase, maturity_at_generation, created_at
                        FROM generated_avatars WHERE user_id=%(uid)s
                       ORDER BY created_at DESC""", {"uid": uid})
        except Exception:
            av = None

        if av is None or av.empty:
            st.caption("Аватар ще не генерувався для цієї дитини.")
        else:
            for _, a in av.iterrows():
                st.markdown(
                    f"**🎭 {a['name']}**  \n"
                    f"_{a['subtitle']}_  \n\n"
                    f"⚡ **Суперсила:** {a['superpower']}  \n"
                    f"🌱 **Зона росту:** {a['weakness']}  \n\n"
                    f"«{a['activation_phrase']}»  \n"
                    f"<span style='color:#8a8f99;font-size:13px'>рівень: "
                    f"{a['maturity_at_generation']} · {a['created_at']:%d.%m.%Y %H:%M}</span>",
                    unsafe_allow_html=True)
                st.markdown("---")


# ============ ЯК ЦЕ ПРАЦЮЄ ============
with tab_how:
    def _safe_scalar(sql, default=0):
        try:
            df = q(sql)
            return int(df.iloc[0, 0]) if not df.empty else default
        except Exception:
            return default

    n_kids     = _safe_scalar("SELECT count(*) FROM users")
    n_msgs     = _safe_scalar("SELECT count(*) FROM messages")
    n_profiles = _safe_scalar("SELECT count(*) FROM profiles WHERE learning_type IS NOT NULL")
    n_avatars  = _safe_scalar("SELECT count(*) FROM generated_avatars")
    n_hubs     = _safe_scalar("SELECT count(*) FROM hubs WHERE active")

    # ---- фірмові знаки з айдентики CALABI (двері, компас, спіраль, куб) ----
    ICONS = {
        "door":    '<path d="M7 3h10v18H7z"/><path d="M7 3 4 5v16l3-2"/><circle cx="14" cy="12" r="1" fill="currentColor" stroke="none"/>',
        "compass": '<circle cx="12" cy="12" r="9"/><path d="m15.5 8.5-2 5-5 2 2-5z"/>',
        "spiral":  '<path d="M12 12a2 2 0 1 1 2.5 1.94A4.5 4.5 0 0 1 7.6 12 7 7 0 0 1 19 8.9"/>',
        "cube":    '<path d="M12 3 4 7.5v9L12 21l8-4.5v-9z"/><path d="M4 7.5 12 12l8-4.5M12 12v9"/>',
        "paths":   '<path d="M12 21V11"/><path d="M12 11 5 4M12 11l7-7"/><circle cx="5" cy="3.5" r="1.4"/><circle cx="19" cy="3.5" r="1.4"/>',
        "spark":   '<path d="M12 2.5 14 9l6.5 2-6.5 2-2 6.5-2-6.5L3.5 11 10 9z"/>',
        "vector":  '<path d="M4 20 20 4"/><path d="M13 4h7v7"/>',
        "veil":    '<path d="M3 12h7"/><path d="M14 12h7"/><circle cx="12" cy="12" r="1.6"/><path d="M12 4v3M12 17v3" stroke-dasharray="2 3"/>',
    }
    def ico(name, size=22):
        return (f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" '
                f'stroke="currentColor" stroke-width="1.4" stroke-linecap="round" '
                f'stroke-linejoin="round">{ICONS[name]}</svg>')

    st.markdown("""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Inter:wght@400;500;600&display=swap');
      .cal {
        --cream:#F4EDE4; --clay:#C4642A; --gold:#DBA431;
        --ink:#1E2930; --slate:#3A3F3D; --earth:#7A5A2C;
        font-family:'Inter',-apple-system,sans-serif;
      }
      .cal h2.t {font-family:'Fraunces',Georgia,serif; font-size:30px; font-weight:700;
        color:var(--ink); letter-spacing:-.01em; margin:2px 0 6px;}
      .cal .lead {font-size:16.5px; color:var(--slate); max-width:70ch; line-height:1.6;}
      .cal .eyebrow {font-size:11px; letter-spacing:.22em; text-transform:uppercase;
        color:var(--earth); font-weight:600; margin-bottom:10px;}

      /* струна: лінія, на якій сидять вузли — відсилання до простору Калабі-Яу */
      .string {position:relative; margin:26px 0 10px;}
      .string::before {content:""; position:absolute; left:2%; right:2%; top:34px; height:1px;
        background:linear-gradient(90deg,transparent,var(--gold) 12%,var(--gold) 88%,transparent);}
      .row {display:flex; gap:12px; position:relative; z-index:1;}
      .n {flex:1 1 0; min-width:132px; background:#fff; border:1px solid #E6DCCB;
        border-radius:12px; padding:16px 14px 14px; transition:.18s;}
      .n:hover {transform:translateY(-2px); box-shadow:0 6px 20px rgba(30,41,48,.07);}
      .n .ic {color:var(--earth); height:24px; margin-bottom:9px;}
      .n.ai {border-color:var(--clay); background:linear-gradient(180deg,#fff,#FDF6EF);}
      .n.ai .ic {color:var(--clay);}
      .n.next {border-style:dashed; background:transparent; opacity:.7;}
      .n .h {font-family:'Fraunces',Georgia,serif; font-size:16px; font-weight:600;
        color:var(--ink); margin-bottom:3px;}
      .n .d {font-size:12.5px; color:#767B82; line-height:1.45;}
      .n .v {font-family:'Fraunces',Georgia,serif; font-size:22px; font-weight:700;
        color:var(--clay); margin-top:8px; line-height:1;}
      .n .vl {font-size:11px; color:#9AA0A6; letter-spacing:.04em;}
      .note {font-size:12.5px; color:#8A9096; margin-top:14px;}
      .note b {color:var(--clay); font-weight:600;}

      /* кроки */
      .stp {display:flex; gap:16px; padding:16px 0; border-top:1px solid #EDE5D8;}
      .stp:first-of-type {border-top:none;}
      .stp .mk {flex:0 0 34px; height:34px; border-radius:10px; background:var(--cream);
        color:var(--earth); display:flex; align-items:center; justify-content:center;}
      .stp .hd {font-family:'Fraunces',Georgia,serif; font-size:17px; font-weight:600;
        color:var(--ink); display:flex; align-items:center; gap:9px; margin-bottom:3px;}
      .tag {font-family:'Inter',sans-serif; font-size:10.5px; font-weight:600; letter-spacing:.06em;
        text-transform:uppercase; padding:3px 9px; border-radius:20px;}
      .tag.hum {background:#E9F1EC; color:#3F7D5C;}
      .tag.sys {background:#FBF0E2; color:var(--earth);}
      .stp .tx {font-size:14.5px; color:var(--slate); line-height:1.6; max-width:76ch;}
      .stp .tx b {color:var(--ink); font-weight:600;}
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="cal">
      <div class="eyebrow">Calabi · як розгортається система</div>
      <h2 class="t">Від згорнутого інтересу — до власного вектора</h2>
      <p class="lead">У просторі Калабі-Яу виміри згорнуті: побачити їх напряму неможливо,
      але саме вони формують властивості світу. Так само в дитині — таланти, спосіб мислення,
      те, що по-справжньому чіпляє. Система розгортає ці виміри крок за кроком.</p>

      <div class="string">
        <div class="row">
          <div class="n"><div class="ic">{ico('door')}</div>
            <div class="h">Знайомство</div><div class="d">Дитина заходить у бот, називає ім'я</div>
            <div class="v">{n_kids}</div><div class="vl">дітей у системі</div></div>
          <div class="n"><div class="ic">{ico('compass')}</div>
            <div class="h">Діагностика</div><div class="d">16 питань, у яких немає правильних відповідей</div>
            <div class="v">{n_profiles}</div><div class="vl">профілів визначено</div></div>
          <div class="n ai"><div class="ic">{ico('spiral')}</div>
            <div class="h">Профайлер</div><div class="d">ШІ читає зміст відповідей: тип навчання, драйвер, зрілість</div></div>
          <div class="n ai"><div class="ic">{ico('cube')}</div>
            <div class="h">Аватар</div><div class="d">Персонаж, зібраний під конкретний профіль</div>
            <div class="v">{n_avatars}</div><div class="vl">згенеровано</div></div>
        </div>
      </div>

      <div class="string">
        <div class="row">
          <div class="n"><div class="ic">{ico('paths')}</div>
            <div class="h">Напрям</div><div class="d">Хаби, підтеми і ваші тригерні фрази</div>
            <div class="v">{n_hubs}</div><div class="vl">напрямків</div></div>
          <div class="n ai"><div class="ic">{ico('spark')}</div>
            <div class="h">Іскра</div><div class="d">Живий діалог: парадокс, факт, питання вглиб</div>
            <div class="v">{n_msgs}</div><div class="vl">реплік</div></div>
          <div class="n next"><div class="ic">{ico('vector')}</div>
            <div class="h">Вектор</div><div class="d">Кристалізація мети — у розробці</div></div>
          <div class="n next"><div class="ic">{ico('veil')}</div>
            <div class="h">Таємниця</div><div class="d">Глибинне дослідження — наступний крок</div></div>
        </div>
      </div>

      <p class="note">Блоки з <b>теплою рамкою</b> — там працює ШІ. Пунктирні — етапи,
      які ще будуються. Цифри читаються з бази щоразу, коли ви відкриваєте цю сторінку.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")
    st.markdown(f"""
    <div class="cal">
      <div class="eyebrow">Порядок роботи</div>

      <div class="stp">
        <div class="mk">{ico('door', 20)}</div>
        <div><div class="hd">Наповнюєте зміст <span class="tag hum">методолог</span></div>
        <div class="tx">У вкладці <b>Контент</b> — питання діагностики, хаби з підтемами,
        тригерні фрази, тексти входу. У вкладці <b>Методологія</b> — промпти Провідника:
        як саме ШІ говорить з дитиною. Зберегли — бот відповідає по-новому одразу.</div></div>
      </div>

      <div class="stp">
        <div class="mk">{ico('compass', 20)}</div>
        <div><div class="hd">Дитина проходить вхід <span class="tag sys">система</span></div>
        <div class="tx">Знайомство, 16 питань, аналіз змісту відповідей, генерація аватара.
        Профіль будується не з галочок, а з того, <b>що саме</b> дитина обрала і як це
        поєднується між питаннями.</div></div>
      </div>

      <div class="stp">
        <div class="mk">{ico('paths', 20)}</div>
        <div><div class="hd">Дитина обирає напрям <span class="tag sys">система</span></div>
        <div class="tx">Або одразу пише свою тему, або дивиться напрямки. Після вибору хаба
        бот показує вашу тригерну фразу і підтеми — і веде розмову по темі,
        а не перепитує «що тобі цікаво».</div></div>
      </div>

      <div class="stp">
        <div class="mk">{ico('spiral', 20)}</div>
        <div><div class="hd">Ви звіряєте з реальністю <span class="tag hum">методолог</span></div>
        <div class="tx">Вкладка <b>Профілі</b>: що система визначила по кожній дитині,
        <b>чому</b> саме так і наскільки впевнено — разом з усіма відповідями.
        <b>Діалоги</b> — реальні розмови. <b>Якість</b> і <b>Воронка</b> — хто зачепився і хто пішов далі.</div></div>
      </div>

      <div class="stp">
        <div class="mk">{ico('cube', 20)}</div>
        <div><div class="hd">Система стає точнішою <span class="tag hum">разом</span></div>
        <div class="tx">Бачите промах діагностики або місце, де діти застрягають — правите
        питання і промпти тут же. Накопичується зв'язка «профіль → який прийом спрацював →
        де зачепилось». Це той актив, який неможливо скопіювати ззовні.</div></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Модель**  \nClaude Sonnet 5 з кешуванням промптів — витрати "
                    "тримаються в межах кількох доларів на місяць.")
    with c2:
        st.markdown("**Дані**  \nPostgreSQL: діти, сесії, репліки, профілі, аватари. "
                    "Зміст відділений від коду — методолог змінює все сам.")
    with c3:
        st.markdown("**Доступ**  \nБот працює цілодобово, кабінет — під паролем, "
                    "з ролями. Дані дітей закриті від сторонніх.")

# ============ ВИБІР МОДЕЛІ ШІ (у вкладці Методологія) ============
with tab5:
    st.markdown("---")
    st.markdown("#### Модель ШІ")
    st.caption("Який «мозок» використовує Провідник. Зміна діє одразу, без перезапуску.")

    _MODELS = {
        "": "За замовчуванням (Sonnet 5)",
        "claude-sonnet-5": "Sonnet 5 — щоденна робота · 2/10 USD за 1М токенів",
        "claude-opus-5": "Opus 5 — складніші задачі, вдвічі дорожча · 5/25 USD",
        "claude-fable-5": "Fable 5 — найпотужніша, у 5 разів дорожча · 10/50 USD",
        "claude-haiku-4-5-20251001": "Haiku 4.5 — найшвидша і найдешевша · 1/5 USD",
    }

    try:
        _cur = q("SELECT value FROM app_settings WHERE key='ai_model'")
        _current = _cur.iloc[0, 0] if not _cur.empty else ""
        _current = _current or ""
        _has_settings = True
    except Exception:
        _current, _has_settings = "", False

    if not _has_settings:
        st.info("Таблиця налаштувань ще не створена — попросіть запустити міграцію add_settings.")
    else:
        _keys = list(_MODELS.keys())
        _idx = _keys.index(_current) if _current in _keys else 0
        _pick = st.selectbox("Модель:", _keys, index=_idx,
                             format_func=lambda k: _MODELS[k], key="ai_model_pick")
        if st.button("Зберегти модель"):
            cn = conn_w(); cur = cn.cursor()
            cur.execute("""INSERT INTO app_settings (key, value, updated_at)
                           VALUES ('ai_model', %s, now())
                           ON CONFLICT (key) DO UPDATE
                             SET value=EXCLUDED.value, updated_at=now()""", (_pick,))
            cn.commit(); cn.close(); q.clear()
            st.success(f"Збережено: {_MODELS[_pick]}")

        st.caption("Ціни за 1 млн токенів (вхід/вихід). Для звичайних діалогів з дітьми "
                   "Sonnet 5 достатньо: різниця з дорожчими моделями майже непомітна, "
                   "а рахунок відрізняється в рази. Fable має сенс для складних "
                   "експериментів, не для щоденної роботи.")

# ============ ПРАВИЛА АДАПТАЦІЇ ТОНУ (вкладка Методологія) ============
with tab5:
    st.markdown("---")
    st.markdown("#### Як Провідник підлаштовується під дитину")
    st.caption("Ці правила додаються до промпту при кожній відповіді — залежно від того, "
               "що система визначила про дитину. Змінюєте тут — бот говорить інакше одразу.")

    _AXIS_TITLE = {
        "learning_type": "Тип навчання",
        "driver": "Драйвер мотивації",
        "maturity": "Рівень зрілості",
        "age": "Вік",
    }

    try:
        _rules = q("SELECT id, axis, key, label, rule, ord FROM tone_rules "
                   "WHERE active ORDER BY axis, ord")
        _has_rules = True
    except Exception:
        _rules, _has_rules = None, False

    if not _has_rules or _rules is None or _rules.empty:
        st.info("Правила ще не перенесені в базу — попросіть запустити міграцію add_tone_rules.")
    else:
        _axis_pick = st.radio("Розділ:", list(_AXIS_TITLE.keys()),
                              format_func=lambda a: _AXIS_TITLE[a],
                              horizontal=True, key="tone_axis")
        _sub = _rules[_rules["axis"] == _axis_pick]

        for _, r in _sub.iterrows():
            with st.expander(r["label"]):
                _txt = st.text_area("Правило:", value=r["rule"],
                                    key=f"tone_{r['id']}", height=160)
                if st.button("Зберегти", key=f"tone_save_{r['id']}"):
                    cn = conn_w(); cur = cn.cursor()
                    cur.execute("UPDATE tone_rules SET rule=%s, updated_at=now() "
                                "WHERE id=%s", (_txt.strip(), int(r["id"])))
                    cn.commit(); cn.close(); q.clear()
                    st.success("Збережено — бот вже говорить по-новому")

# ============ ТЕСТИ ЯКОСТІ ============
with tab_eval:
    st.subheader("Тести якості відповідей")
    st.caption("Набір типових ситуацій, які проганяються через Провідника. "
               "Показує цифрами, чи стало краще після зміни моделі або промпту — "
               "замість «прочитаю і відчую різницю».")

    try:
        _cases = q("SELECT id, title, note, child_text, state FROM eval_cases "
                   "WHERE active ORDER BY id")
        _runs = q("""SELECT id, model, started_at, cases_n, score
                       FROM eval_runs ORDER BY started_at DESC LIMIT 20""")
        _has_eval = True
    except Exception:
        _cases, _runs, _has_eval = None, None, False

    if not _has_eval:
        st.info("Таблиці ще не створені — попросіть запустити міграцію add_quality_eval.")
    else:
        # ---- історія прогонів ----
        if _runs is not None and not _runs.empty:
            st.markdown("#### Історія прогонів")
            _show = _runs.copy()
            _show["Бал"] = (_show["score"].astype(float) * 100).round(0).astype(int).astype(str) + "%"
            _show = _show.rename(columns={"model": "Модель", "started_at": "Коли",
                                          "cases_n": "Випадків"})
            st.dataframe(_show[["Коли", "Модель", "Випадків", "Бал"]],
                         use_container_width=True, hide_index=True)

            # порівняння двох останніх
            if len(_runs) >= 2:
                a, b = _runs.iloc[0], _runs.iloc[1]
                delta = (float(a["score"]) - float(b["score"])) * 100
                c1, c2, c3 = st.columns(3)
                c1.metric("Останній прогін", f"{float(a['score'])*100:.0f}%", f"{delta:+.0f}%")
                c2.metric("Модель", a["model"] or "—")
                c3.metric("Попередній", f"{float(b['score'])*100:.0f}%")

        # ---- деталі обраного прогону ----
        if _runs is not None and not _runs.empty:
            st.markdown("---")
            st.markdown("#### Деталі прогону")
            _opts = {int(r["id"]): f"{r['started_at']:%d.%m %H:%M} · {r['model']} · "
                                   f"{float(r['score'])*100:.0f}%"
                     for _, r in _runs.iterrows()}
            _pick = st.selectbox("Прогін:", list(_opts.keys()),
                                 format_func=lambda i: _opts[i], key="eval_run_pick")
            _res = q("""SELECT c.title, r.answer, r.checks, r.score, r.verdict
                          FROM eval_results r JOIN eval_cases c ON c.id=r.case_id
                         WHERE r.run_id=%(rid)s ORDER BY c.id""", {"rid": _pick})
            for _, row in _res.iterrows():
                _sc = float(row["score"])
                _icon = "🟢" if _sc >= 0.8 else ("🟡" if _sc >= 0.5 else "🔴")
                with st.expander(f"{_icon} {row['title']} · {_sc*100:.0f}%"):
                    st.markdown(f"**Відповідь Провідника:**  \n{row['answer']}")
                    _ch = row["checks"]
                    if isinstance(_ch, str):
                        try: _ch = json.loads(_ch)
                        except Exception: _ch = {}
                    if _ch:
                        _ok = [k.replace("_", " ") for k, v in _ch.items() if v]
                        _bad = [k.replace("_", " ") for k, v in _ch.items() if not v]
                        if _ok:
                            st.markdown("✅ " + " · ".join(_ok))
                        if _bad:
                            st.markdown("❌ " + " · ".join(_bad))
                    if row["verdict"]:
                        st.caption(f"Суддя: {row['verdict']}")

        # ---- набір випадків ----
        st.markdown("---")
        st.markdown("#### Набір тестових ситуацій")
        st.caption("Побачили в діалогах проблемну ситуацію — додайте її сюди, "
                   "щоб вона перевірялась при кожній зміні.")
        if _cases is not None and not _cases.empty:
            _t = _cases.rename(columns={"title": "Ситуація", "note": "Що перевіряємо",
                                        "child_text": "Репліка дитини"})
            st.dataframe(_t[["Ситуація", "Що перевіряємо", "Репліка дитини"]],
                         use_container_width=True, hide_index=True)

        with st.form("add_eval_case", clear_on_submit=True):
            st.markdown("**Додати ситуацію**")
            _title = st.text_input("Назва (коротко)")
            _note = st.text_input("Що саме перевіряємо")
            _ctx = st.text_area("Контекст розмови (необов'язково)", height=80)
            _child = st.text_area("Репліка дитини", height=80)
            if st.form_submit_button("Додати"):
                if _title.strip() and _child.strip():
                    cn = conn_w(); cur = cn.cursor()
                    cur.execute("""INSERT INTO eval_cases (title, note, context, child_text)
                                   VALUES (%s,%s,%s,%s)""",
                                (_title.strip(), _note.strip(), _ctx.strip(), _child.strip()))
                    cn.commit(); cn.close(); q.clear()
                    st.success("Додано")
                    st.rerun()
                else:
                    st.error("Потрібні назва і репліка дитини.")

        st.markdown("---")
        st.markdown("#### Запустити прогін")

        # перевіряємо, чи вже щось виконується
        try:
            _qrows = q("""SELECT id, status, requested_at, finished_at, message
                            FROM eval_queue ORDER BY requested_at DESC LIMIT 3""")
            _has_queue = True
        except Exception:
            _qrows, _has_queue = None, False

        if not _has_queue:
            st.caption("Черга ще не створена — попросіть запустити міграцію add_eval_queue.")
        else:
            _busy = (_qrows is not None and not _qrows.empty
                     and _qrows.iloc[0]["status"] in ("pending", "running"))

            if _busy:
                st.info("Прогін виконується — оновіть сторінку за хвилину.")
            else:
                st.caption("Прогін робить 2 виклики моделі на кожну ситуацію "
                           "(8 ситуацій ≈ 16 викликів). Запускайте після зміни моделі "
                           "чи промптів, а не після кожної дрібної правки.")
                if st.button("Запустити прогін", type="primary"):
                    cn = conn_w(); cur = cn.cursor()
                    cur.execute("INSERT INTO eval_queue (requested_by) VALUES (%s)",
                                (st.session_state.get("auth_email", "—"),))
                    cn.commit(); cn.close(); q.clear()
                    st.success("Поставлено в чергу — результат з'явиться за 1-2 хвилини")
                    st.rerun()

            if _qrows is not None and not _qrows.empty:
                _last = _qrows.iloc[0]
                _st_map = {"pending": "очікує", "running": "виконується",
                           "done": "завершено", "error": "помилка"}
                st.caption(f"Останній запит: {_st_map.get(_last['status'], _last['status'])}"
                           + (f" · {_last['message']}" if _last.get("message") else ""))
