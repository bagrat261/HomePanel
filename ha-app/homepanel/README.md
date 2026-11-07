# Local Home Assistant OS app (experimental)

Это исходная упаковка для локальной сборки, не опубликованный app repository.
Поддержаны amd64 и aarch64. Установка на реальном HAOS здесь не проверена.
Не использует Supervisor token, host network, Docker socket или привилегии.
HomePanel требует собственный пароль и отдельный HA long-lived token в live режиме.

1. В корне проекта выполните в PowerShell `./scripts/prepare-ha-app.ps1`.
2. Скопируйте **всю** папку `ha-app/homepanel`, включая `source`, в
   `/addons/homepanel` на вашем HAOS. Не копируйте `.env` и личный YAML.
3. Перезагрузите список локальных apps/add-ons в магазине HA и установите HomePanel.
4. В настройках app задайте allowed_hosts (IP/имя вашего HAOS для доступа с iPad),
   при необходимости пароль для Demo, затем включите порт 8090 в разделе Network.
   По умолчанию порт выключен, автозапуск тоже выключен.
5. Для реального HA: demo=false, ha_url, ha_token, panel_password (12+ символов).
   В panel_yaml вставьте YAML-конфигурацию с entities и modes, как в configuration/README.md.
   Это поле содержит настройки, но не секреты. Перезапустите app после изменений.

Интерфейс открывается напрямую по порту в доверенной LAN. Ingress не настроен:
он добавляет требования к старому Safari и маршрутизации абсолютных путей.
Для HTTPS используйте собственный доверенный proxy; secure_cookie в panel_yaml=true.
Бэкапы app options могут содержать секреты, храните их соответственно.
