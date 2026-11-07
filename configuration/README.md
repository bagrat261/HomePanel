# Серверная конфигурация

Скопируйте config.example.yaml в config.yaml. Замените пустой список `entities`
на сущности своего HA, например (это только образец синтаксиса):

```yaml
entities:
  - entity_id: light.your_light
    name: Свет
    room: Гостиная
  - entity_id: media_player.your_music_assistant_player
    name: Акустика
    room: Гостиная
  - entity_id: weather.your_weather
    name: За окном
    role: weather
  - entity_id: binary_sensor.your_pc_online
    name: Рабочий компьютер
    room: Кабинет
    role: computer
```

Все имена замените настоящими. `role` может быть device, weather, computer.
Плееры в списке доступны в селекторе. Никакие сущности не обнаруживаются и не
разрешаются автоматически. `modes[].entity_id` допускает только script/scene.
Режим без entity_id отключён. Токен и пароль задаются только в `.env`.
Для пути конфигурации используйте HOMEPANEL_CONFIG. Для LAN добавьте адрес
панели (не адрес HA) в allowed_hosts. Нельзя использовать wildcard для публичного доступа.
