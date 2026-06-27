# Альтавіста — Кабінет спостереження

Streamlit-дашборд для автора методології: читати діалоги дітей + метрики.
Підключається до тієї ж бази PostgreSQL, що й бот.

## Вкладки
- **Огляд** — метрики (діти, сесії, повідомлення, етапи FSM, активність)
- **Діалоги** — читати повний діалог обраної дитини
- **Якість** — розподіл по станах, скільки дійшло до «Вектора»

## Запуск локально
```
pip install -r requirements.txt
export DATABASE_URL="postgres://..."
streamlit run dashboard.py
```

## Деплой на Streamlit Cloud
1. Залити цей репозиторій на GitHub
2. share.streamlit.io → New app → обрати репо → dashboard.py
3. Settings → Secrets → вставити DATABASE_URL (з Heroku Config Vars)
4. Deploy

⚠️ Доступ закрити: Streamlit Cloud → Settings → зробити app приватним
   або обмежити по email (там логи діалогів реальних дітей).
