# Проверка HomePanel MVP — 7 ноября 2026

## Проверка Mac перед нативной сборкой

Xcode 27.0 / SDK 27.0: создание ARMv7 object-файла прошло, линковка с UIKit,
Foundation и libSystem не прошла: SDK не содержит ARMv7 slices. Настоящий IPA
не собран. Команды, ограничения и повторяемая проверка:
[MAC-TOOLCHAIN.md](MAC-TOOLCHAIN.md). Это не проверка работы приложения на iPad
и не измерение производительности. Результаты Windows ниже относятся к исходному MVP.

## Выполнено

Среда: Windows, Python 3.12.10, Node.js 22.23.2, современный Microsoft Edge
в отдельном временном профиле. Реальный HA не использовался.

| Проверка | Результат | Доказательство |
|---|---|---|
| Серверные API и HA REST adapter | PASS, 42 теста | `uv run --extra dev pytest` |
| Python lint | PASS | `uv run --extra dev ruff check homepanel tests` |
| Python format | PASS | `uv run --extra dev ruff format --check homepanel tests` |
| Синтаксис Dashboard | PASS, все 4 JS-файла ES5 | `npm run check:es5`, Acorn ecmaVersion=5 |
| Python sdist/wheel | PASS | `uv build`, файлы в dist |
| HAOS source preparation | PASS, PowerShell | `scripts/prepare-ha-app.ps1` |
| Dashboard в Edge | PASS | scripts/browser-qa.mjs, artifacts/browser-evidence.json |
| Восстановление online после offline при неизменных данных | PASS | Браузерный регрессионный сценарий; до исправления тест падал |
| Stateless button/scene с unknown до первого использования | PASS | tests/test_stateless_entities.py; до исправления оба теста падали |

Pytest выдаёт одно предупреждение Starlette о будущем переходе TestClient с
httpx на httpx2. Это deprecation warning, не ошибка; для текущего MVP httpx
выбран явно и зафиксирован в диапазоне 0.28. CI для Windows/Linux и Python
3.11–3.13 подготовлен, но удалённый GitHub Actions запуск здесь не выполнялся.

## Браузерные сценарии

Успешно выполнены: загрузка demo, переключение света, комнаты, Movie Mode,
play/pause, next, выбор плеера с синхронизацией большого и мини-плеера,
тёмная/светлая темы, ночной режим через touch-доступную настройку.
Регрессия offline имитирует сетевую ошибку на границе XHR callback; физический
обрыв Wi-Fi не проверялся. Первоначальные desktop-снимки ошибочно были 1440px;
они заменены захватами с проверкой фактического innerWidth=1024.

Снимки: `artifacts/dashboard-1024-dark.png`, `dashboard-1024-light.png`,
`music-1024-dark.png`, `settings-1024-light.png`, `dashboard-390-dark.png`,
`dashboard-390-light.png`, `dashboard-320-dark.png`,
`dashboard-320-text-spacing.png`, `focus-320.png`.

Вертикальная прокрутка предусмотрена: при большом количестве карточек сценарии
и дополнительные устройства доступны ниже. Мини-плеер остаётся закреплённым.

## Доступность — частичная проверка WCAG 2.2 AA

Полная сертификация WCAG не заявляется. В таблице PASS относится только к
указанной измеренной проверке; N/A означает, что полная проверка не выполнялась.

| Критерий | Статус | Что проверено |
|---|---|---|
| Контраст основных цветов | PASS | Основные пары текста в обеих темах: 5.61–15.15:1; текст активной кнопки 11.28:1. Все состояния всех компонентов не аудированы |
| Focus | PASS частично | Видимая outline после Tab, снимок focus-320; полный обход всех состояний отдельно не выполнен |
| Размер цели | PASS | Все видимые button/a/input/select в восьми захватах не меньше 44×44 CSS px, измерения в browser-evidence.json |
| Keyboard | PASS частично | Native controls и Tab; полного ручного обхода с screen reader нет |
| Reflow/text spacing | PASS | Нет горизонтального overflow страницы при 1024, 390 и 320px; при 320px проверены line-height 1.5, letter-spacing .12em, word-spacing .16em, paragraph spacing 2em |
| Drag/auth/help | PASS частично | Нативные range реагируют на касание/клавиши; пароль допускает paste/password manager, без CAPTCHA; hardware touch не проверен |
| Размеры во всех состояниях | N/A | Базовые размеры измерены; автоматической матрицы каждого hover/loading/disabled нет |
| Цвета и поверхности | PASS | DESIGN.md, обычные CSS fallback-значения, без CSS Grid, blur, CSS variables |

Вспомогательный draft-guard из локального OMO не запустился под Node из-за
отсутствующего разрешения extensionless TypeScript import; это не проверка
продукта и не засчитано как PASS. Панель просмотрена вручную по снимкам.

## Не проверено / не реализовано

- Настоящий iPad 2 с iOS 9.3.5/9.3.6: совместимость остаётся неподтверждённой,
  несмотря на ES5/XHR и CSS fallback. Нужны touch, SVG, сон/пробуждение, cookie,
  Home Screen mode, память и CPU на реальном устройстве.
- Реальный Home Assistant и Music Assistant: только MockTransport и demo.
- Docker build/run: Docker CLI в окружении отсутствует.
- HAOS install/run: подготовлен локальный app build context; установка не выполнялась.
- Music Assistant search и просмотр/редактирование очереди: отложены за MVP.
- Нет редактора серверных разрешений в браузере, ingress, Screen Wake Lock и DRM-плеера.

Никаких реальных действий HA, установки apps или изменений домашней системы
при этих проверках не было.
