"""
АЛЬТАВІСТА — Кабінет спостереження v2 (SaaS-рівень).
Для автора методології: спостерігати, як працює методологія вживу.

Вкладки: Огляд · Діалоги (з фільтрами, чат-вид) · Воронка · Якість
"""

import os
import psycopg2
import pandas as pd
import streamlit as st
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

# ----- легкий стиль -----
st.markdown("""
<style>
  .stApp { background: #0f1117; }
  .bubble-child {
     background:#1e2330; border-radius:14px 14px 14px 4px;
     padding:10px 14px; margin:4px 0; max-width:75%;
     color:#e8eaf0; border:1px solid #2a3142;
  }
  .bubble-ai {
     background:#2b1f3a; border-radius:14px 14px 4px 14px;
     padding:10px 14px; margin:4px 0 4px auto; max-width:75%;
     color:#f0e8fa; border:1px solid #443055; text-align:left;
  }
  .meta { color:#7a8294; font-size:0.75rem; margin-bottom:2px; }
  .flag { display:inline-block; padding:1px 8px; border-radius:10px;
          font-size:0.7rem; margin-left:6px; }
  .flag-warn { background:#3a2a1a; color:#e0a060; }
  .flag-ok { background:#1a3a25; color:#60d090; }
</style>
""", unsafe_allow_html=True)

st.title("🔥 Альтавіста — Кабінет спостереження")
st.caption("Спостереження за методологією у живих діалогах")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📊 Огляд", "💬 Діалоги", "🎯 Воронка", "✅ Якість", "⚙️ Методологія"])

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

    kids = q(f"""
        SELECT u.id, u.tg_id, count(m.id) msgs, max(m.ts) last_ts
        FROM users u
        JOIN sessions s ON s.user_id=u.id
        JOIN messages m ON m.session_id=s.id
        WHERE {' AND '.join(where)}
        GROUP BY u.id, u.tg_id
        ORDER BY last_ts DESC
    """, params)

    if kids.empty:
        st.info("Нічого не знайдено за фільтрами.")
    else:
        kids["label"] = kids.apply(
            lambda r: f"Дитина #{r['id']} · tg {r['tg_id']} · {r['msgs']} реплік", axis=1)
        choice = st.selectbox(f"Знайдено дітей: {len(kids)}", kids["label"])
        uid = int(kids[kids["label"]==choice]["id"].values[0])

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
    # сесій що заглухли (1-2 репліки)
    stalled = int(q("""SELECT count(*) n FROM (
        SELECT session_id, count(*) c FROM messages WHERE role='child'
        GROUP BY session_id HAVING count(*) <= 2) t""")["n"][0])
    c[2].metric("Заглухли (≤2 реплік)", stalled,
                help="Діти що написали 1-2 рази і зникли — тривожний сигнал")

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
