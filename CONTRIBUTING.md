# Участие в разработке Локсо

## Issues

Задачи ведутся в [GitHub Issues](https://github.com/abuhtoyarov/lokso-app/issues).
Перед созданием новой — поискать среди существующих.

Заголовок по формату:

- баг: `🐛 Баг: краткое описание`
- фича: `🚀 Фича: краткое описание`
- улучшение: `🛠️ Улучшение: краткое описание`
- документация: `📘 Доки: краткое описание`

Для бага нужен воспроизводимый сценарий: что сделали, что ожидали, что
получилось, версии окружения.

## Локальная разработка

Требования и пошаговая инструкция — в [ЛОКАЛЬНАЯ-РАЗРАБОТКА.md](ЛОКАЛЬНАЯ-РАЗРАБОТКА.md).

Коротко:

```bash
./setup.sh
docker compose -f docker-compose-local.yml up -d plane-db plane-redis plane-mq plane-minio
pnpm install
pnpm turbo run build --filter='web^...'
pnpm --filter web dev
```

Команды монорепозитория и код-стайл — в [AGENTS.md](AGENTS.md).

## Ветки и коммиты

Базовая ветка — `main`. Изменения попадают в неё только через pull request из feature-ветки — прямые коммиты в `main` не делаем.

Имя ветки: `<тип>/<номер-issue>-<краткое-описание>`, например
`feat/42-telegram-bot`. Типы: `feat`, `fix`, `chore`, `refactor`, `docs`, `perf`.

Сообщения коммитов — по conventional commits: `feat(api): краткое описание`.

## Pull request

Перед PR прогнать проверки:

```bash
pnpm check:types
pnpm check:lint
```

Тесты бэкенда:

```bash
docker compose -f docker-compose-test.yml up --build --abort-on-container-exit --exit-code-from api-tests
```

Заполнить шаблон `.github/pull_request_template.md` и связать PR с задачей
строкой `Closes #<номер>` в описании.

## Лицензия

Проект распространяется под AGPL-3.0. Отправляя pull request, вы соглашаетесь,
что ваш вклад публикуется на условиях этой лицензии.
