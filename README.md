# Digital Garden

Автономно растущая коллекция арт-артефактов, создаваемых AI-агентом. Один артефакт каждые 6 часов. Температура 0.92. Без цензуры.

Агент выбирает случайную тему из 8 категорий (наука, искусство, инженерия, изобретения, литература, социум, мода, поп-культура), переосмысляет её как современный художник и создаёт HTML-артефакт.

## Быстрый старт

```bash
pip install -r requirements.txt

# DeepSeek (рекомендуется, 10M токенов бесплатно)
set DEEPSEEK_API_KEY=sk-ваш_ключ
python src/curator.py

# или OpenRouter
set OPENROUTER_API_KEY=sk-or-v1-ваш_ключ
python src/curator.py
```

Ключи:
- DeepSeek: https://platform.deepseek.com (free 10M tokens, без оплаты)
- OpenRouter: https://openrouter.ai/keys (free tier)

## GitHub Actions (автономный рост)

1. Создать репозиторий на GitHub
2. Залить проект в корень
3. В Settings → Secrets → Actions добавить `DEEPSEEK_API_KEY` (или `OPENROUTER_API_KEY`)
4. Агент будет запускаться каждые 6 часов автоматически

Артефакты собираются в `artifacts/`, галерея — `index.html`. Включить GitHub Pages в настройках репозитория (source: main, папка: /).

## Структура

```
garden/
├── src/
│   ├── curator.py       # ядро агента
│   └── sources.py       # банк тем (80 топиков)
├── artifacts/           # сгенерированные артефакты
├── index.html           # галерея (обновляется автоматически)
├── requirements.txt
└── .github/workflows/garden.yml
```
