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

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(
    ["📊 Огляд", "💬 Діалоги", "🎯 Воронка", "✅ Якість",
     "⚙️ Методологія", "📝 Контент", "👥 Учні", "❓ Довідка"])

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
            name = (r.get("name") or "").strip() if has_names else ""
            uname = r.get("username") if has_names else None
            who = name if name else f"Дитина #{r['id']}"
            tag = f" ({'@'+uname})" if uname else ""
            return f"{who}{tag} · {r['msgs']} реплік"
        kids["label"] = kids.apply(make_label, axis=1)
        choice = st.selectbox(f"Знайдено дітей: {len(kids)}", kids["label"])
        sel_row = kids[kids["label"]==choice].iloc[0]
        uid = int(sel_row["id"])

        # клікабельне посилання на телеграм дитини (якщо є username)
        if has_names and sel_row.get("username"):
            uname = sel_row["username"]
            st.markdown(f"🔗 Написати в Telegram: [@{uname}](https://t.me/{uname})")
        else:
            st.caption(f"Прямого посилання немає (без @username). tg_id: {sel_row['tg_id']}")

        dialog = q("""SELECT role, text, state, ts FROM messages m
                      JOIN sessions s ON s.id=m.session_id
                      WHERE s.user_id=%(uid)s ORDER BY m.ts""", {"uid": uid})

        # детект зацикливания: ИИ повторяет начало фразы
        prev_ai_start = None
        for _, m in dialog.iterrows():
            t = m["text"]
            ts = pd.to_datetime(m["ts"]).strftime("%d.%m %H:%M")
            if m["role"] == "child":
                st.markdown(f"<div class='meta'>🧒 {ts}</div>"
                            f"<div class='bubble-child'>{t}</div>", unsafe_allow_html=True)
            else:
                # прапорець зацикливания
                start = t[:15]
                flag = ""
                if prev_ai_start and start == prev_ai_start:
                    flag = "<span class='flag flag-warn'>повтор зачину</span>"
                prev_ai_start = start
                st.markdown(f"<div class='meta' style='text-align:right'>"
                            f"🔥 Провідник · {m['state']} · {ts}{flag}</div>"
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
            hubs = q("SELECT id, label, subtopics FROM hubs ORDER BY ord")
            st.caption("Для кожного хаба впишіть підтеми (по одній на рядок).")
            for _, row in hubs.iterrows():
                subs = row["subtopics"] if isinstance(row["subtopics"],list) else json.loads(row["subtopics"] or "[]")
                with st.expander(f"🗂 {row['label']} ({len(subs)} підтем)"):
                    txt = st.text_area("Підтеми (рядок = підтема):",
                                       value="\n".join(subs), key=f"hub_{row['id']}", height=120)
                    if st.button("💾 Зберегти підтеми", key=f"savehub_{row['id']}"):
                        new_subs=[s.strip() for s in txt.split("\n") if s.strip()]
                        cn=conn_w();cur=cn.cursor()
                        cur.execute("UPDATE hubs SET subtopics=%s WHERE id=%s",
                                    (json.dumps(new_subs,ensure_ascii=False),row["id"]))
                        cn.commit();cn.close();q.clear()
                        st.success(f"Збережено {len(new_subs)} підтем!")

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
