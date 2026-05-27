# Digital Garden

Автономно растущий арт-проект, создаваемый AI-агентом. Один артефакт каждые 4 часа. Температура — 14-дневная синусоида от 0.1 до 1.8, с редкими скачками. Без архива: каждый новый артефакт замещает предыдущий.

Агент выбирает тему, переосмысляет её как современный художник и создаёт HTML-артефакт. После генерации из текста извлекаются ключевые темы, образы и тональность — они формируют свою почво-душу (souil.json), которая влияет на следующие генерации. Сад медленно эволюционирует, не накапливая артефакты.

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
4. Агент будет запускаться каждые 4 часа автоматически

Артефакты собираются в `artifacts/`, галерея — `index.html`. Включить GitHub Pages в настройках репозитория (source: main, папка: /).

## Структура

```
garden/
├── src/
│   ├── curator.py       # ядро агента
│   └── sources.py       # банк тем (80 топиков)
├── artifacts/           # сгенерированные артефакты
├── index.html           # корневой артефакт (обновляется каждый цикл)
├── souil.json           # внутреннее состояние сада (почва, настроение)
├── requirements.txt
└── .github/workflows/garden.yml
```
