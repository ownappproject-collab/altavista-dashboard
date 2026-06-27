"""
АЛЬТАВІСТА — Кабінет спостереження (Streamlit).
Для автора методології: читати діалоги дітей + метрики.

Запуск локально:
    pip install streamlit psycopg2-binary pandas
    export DATABASE_URL="postgres://..."
    streamlit run dashboard.py

Деплой: окремий репозиторій на Streamlit Cloud,
DATABASE_URL — у Secrets (та сама база, що й бот).
"""

import os
import psycopg2
import pandas as pd
import streamlit as st

# ----- підключення до тієї ж бази, що й бот -----
def get_conn():
    dsn = os.environ.get("DATABASE_URL") or st.secrets.get("DATABASE_URL", "")
    if dsn.startswith("postgres://"):
        dsn = dsn.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(dsn, sslmode="require")


def q(sql, params=None):
    conn = get_conn()
    try:
        return pd.read_sql(sql, conn, params=params)
    finally:
        conn.close()


st.set_page_config(page_title="Альтавіста · Кабінет", page_icon="🔥", layout="wide")
st.title("🔥 Альтавіста — Кабінет спостереження")

tab_overview, tab_dialogs, tab_quality = st.tabs(
    ["📊 Огляд", "💬 Діалоги", "✅ Якість"]
)

# ============ ВКЛАДКА 1: ОГЛЯД ============
with tab_overview:
    st.subheader("Загальні метрики")

    users = q("SELECT count(*) AS n FROM users")["n"][0]
    sessions = q("SELECT count(*) AS n FROM sessions")["n"][0]
    messages = q("SELECT count(*) AS n FROM messages")["n"][0]
    child_msgs = q("SELECT count(*) AS n FROM messages WHERE role='child'")["n"][0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Дітей", int(users))
    c2.metric("Сесій", int(sessions))
    c3.metric("Повідомлень", int(messages))
    avg = round(child_msgs / sessions, 1) if sessions else 0
    c4.metric("Реплік дитини / сесію", avg)

    st.divider()

    # розподіл по станах FSM
    st.subheader("На якому етапі діти")
    states = q("""
        SELECT current_state AS "Стан", count(*) AS "Дітей"
        FROM sessions GROUP BY current_state ORDER BY count(*) DESC
    """)
    if not states.empty:
        st.bar_chart(states.set_index("Стан"))
    else:
        st.info("Поки немає сесій.")

    # активність по днях
    st.subheader("Активність по днях")
    daily = q("""
        SELECT date_trunc('day', ts)::date AS "День", count(*) AS "Повідомлень"
        FROM messages GROUP BY 1 ORDER BY 1
    """)
    if not daily.empty:
        st.line_chart(daily.set_index("День"))

# ============ ВКЛАДКА 2: ДІАЛОГИ ============
with tab_dialogs:
    st.subheader("Читати діалоги дітей")

    kids = q("""
        SELECT u.id, u.tg_id, u.age, u.created_at,
               count(m.id) AS msgs
        FROM users u
        LEFT JOIN sessions s ON s.user_id = u.id
        LEFT JOIN messages m ON m.session_id = s.id
        GROUP BY u.id, u.tg_id, u.age, u.created_at
        ORDER BY u.created_at DESC
    """)

    if kids.empty:
        st.info("Поки немає дітей у базі.")
    else:
        # вибір дитини
        kids["label"] = kids.apply(
            lambda r: f"Дитина #{r['id']} (tg {r['tg_id']}, {r['msgs']} реплік)", axis=1
        )
        choice = st.selectbox("Оберіть дитину:", kids["label"])
        uid = int(kids[kids["label"] == choice]["id"].values[0])

        # весь діалог цієї дитини
        dialog = q("""
            SELECT m.role, m.text, m.state, m.ts
            FROM messages m
            JOIN sessions s ON s.id = m.session_id
            WHERE s.user_id = %(uid)s
            ORDER BY m.ts
        """, {"uid": uid})

        st.caption(f"Всього реплік: {len(dialog)}")
        for _, m in dialog.iterrows():
            if m["role"] == "child":
                st.markdown(f"🧒 **Дитина:** {m['text']}")
            else:
                st.markdown(f"🔥 **Провідник** *(стан: {m['state']})*: {m['text']}")
        st.divider()

# ============ ВКЛАДКА 3: ЯКІСТЬ ============
with tab_quality:
    st.subheader("Якість роботи методології")

    by_state = q("""
        SELECT state AS "Стан",
               count(*) FILTER (WHERE role='ai') AS "Відповідей ІІ",
               count(*) FILTER (WHERE role='child') AS "Реплік дитини"
        FROM messages
        WHERE state IS NOT NULL
        GROUP BY state
    """)
    if not by_state.empty:
        st.dataframe(by_state, use_container_width=True, hide_index=True)
    else:
        st.info("Поки немає даних.")

    st.divider()
    st.subheader("Скільки дітей дійшло до Вектора")
    reached = q("""
        SELECT count(DISTINCT user_id) AS n
        FROM sessions WHERE current_state = 'vektor'
    """)["n"][0]
    total = q("SELECT count(*) AS n FROM users")["n"][0]
    st.metric("Дійшли до «Вектора»", f"{int(reached)} з {int(total)}")
    st.caption(
        "Ключова метрика MVP: чи доводить методологія дитину "
        "до самостійного формулювання цілі (стан «Вектор»)."
    )
