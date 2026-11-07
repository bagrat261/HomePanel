(function (P) {
    'use strict';
    var escape = P.escape;
    function stateLabel(entity) {
        if (!P.online) { return 'Нет связи'; }
        var state = entity.state, domain = entity.entity_id.split('.')[0];
        if (state === 'unavailable') { return 'Недоступно'; }
        if (state === 'unknown') { return 'Нет данных'; }
        if (domain === 'binary_sensor') { return state === 'on' ? 'Открыто / активно' : 'Закрыто / неактивно'; }
        return { 'on': 'Включено', 'off': 'Выключено', 'heat': 'Обогрев', 'cool': 'Охлаждение', 'idle': 'Ожидание' }[state] || state;
    }
    function card(entity) {
        var domain = entity.entity_id.split('.')[0], attrs = entity.attributes, id = escape(entity.entity_id);
        var icon = { light: 'light', switch: 'switch', climate: 'climate', sensor: 'sensor', binary_sensor: 'window', scene: 'check', script: 'check', button: 'switch' }[domain] || 'sensor';
        var active = entity.state === 'on' || entity.state === 'heat' || entity.state === 'cool';
        var controls = '', state = escape(stateLabel(entity)), toggle = '';
        if (domain === 'sensor') { state = '<span class="value">' + escape(entity.state) + ' <small>' + escape(attrs.unit_of_measurement || '') + '</small></span>'; }
        if (entity.actions.indexOf('toggle') >= 0) {
            toggle = '<button class="toggle" data-entity="' + id + '" data-action="toggle" aria-label="Переключить ' + escape(entity.name) + '" aria-pressed="' + (entity.state === 'on') + '"' + (P.online ? '' : ' disabled') + '>' + (entity.state === 'on' ? 'Вкл.' : 'Выкл.') + '</button>';
        }
        if (entity.actions.indexOf('activate') >= 0) {
            toggle = '<button class="toggle" data-entity="' + id + '" data-action="activate"' + (P.online ? '' : ' disabled') + '>Запуск</button>';
        }
        if (domain === 'climate') {
            state = 'Сейчас ' + escape(attrs.current_temperature === undefined ? '—' : attrs.current_temperature) + '°';
            controls = '<div class="temperature-row"><button data-entity="' + id + '" data-step="-1" aria-label="Понизить температуру"' + (P.can(entity, 'temperature') ? '' : ' disabled') + '>−</button><span>' + escape(attrs.temperature === undefined ? '—' : attrs.temperature) + '°</span><button data-entity="' + id + '" data-step="1" aria-label="Повысить температуру"' + (P.can(entity, 'temperature') ? '' : ' disabled') + '>+</button></div>';
        }
        if (entity.actions.indexOf('brightness') >= 0) {
            controls = '<input type="range" min="0" max="255" value="' + (attrs.brightness || 0) + '" data-entity="' + id + '" data-range="brightness" aria-label="Яркость: ' + escape(entity.name) + '"' + (P.online ? '' : ' disabled') + '>';
        }
        return '<article class="device' + (active ? ' on' : '') + '"><div class="device-body"><span class="device-icon">' + P.icon(icon) + '</span>' + toggle + '<h2 class="device-name">' + escape(entity.name) + '</h2><div class="device-state">' + state + '</div>' + controls + '</div></article>';
    }
    P.renderDevices = function () {
        var entities = P.data.entities, rooms = ['Все'], devices = '', computer = '', weather = '', modes = '', i, entity, domain, mode;
        for (i = 0; i < entities.length; i += 1) {
            entity = entities[i]; domain = entity.entity_id.split('.')[0];
            if (entity.role === 'computer') {
                computer += '<p>' + escape(entity.name) + '</p><small>' + (domain === 'binary_sensor' ? (entity.state === 'on' ? 'В сети' : entity.state === 'off' ? 'Выключен' : 'Недоступен') : escape(entity.state + ' ' + (entity.attributes.unit_of_measurement || ''))) + '</small>';
            } else if (entity.role === 'weather') {
                if (entity.state !== 'unavailable' && entity.state !== 'unknown') {
                    weather = P.icon('sun') + '<strong>' + escape(typeof entity.attributes.temperature === 'number' ? entity.attributes.temperature : entity.state) + '°</strong><small>' + escape({ sunny: 'Ясно', partlycloudy: 'Переменная облачность', cloudy: 'Облачно', rainy: 'Дождь', snowy: 'Снег', 'clear-night': 'Ясная ночь' }[entity.state] || entity.name) + (P.data.demo ? ' · пример' : '') + '</small>';
                }
            } else if (domain !== 'media_player') {
                if (rooms.indexOf(entity.room) < 0) { rooms.push(entity.room); }
                if (P.room === 'Все' || P.room === entity.room) { devices += card(entity); }
            }
        }
        if (rooms.indexOf(P.room) < 0) { P.room = 'Все'; }
        P.el('rooms').innerHTML = rooms.map(function (room) { return '<button class="room' + (P.room === room ? ' active' : '') + '" data-room="' + escape(room) + '" aria-pressed="' + (P.room === room) + '">' + escape(room) + '</button>'; }).join('');
        P.el('devices').innerHTML = devices || '<div class="empty">Здесь появятся ваши устройства.<p class="muted">Добавьте сущности в configuration/config.yaml на сервере.</p></div>';
        P.el('weather').hidden = !weather; P.el('weather').innerHTML = weather;
        P.el('computer').innerHTML = '<div class="pc-card">' + P.icon('pc') + (computer || '<p>Нет выбранных датчиков</p><small>Настройте role: computer в YAML</small>') + '</div>';
        for (i = 0; i < P.data.modes.length; i += 1) {
            mode = P.data.modes[i];
            modes += '<div class="mode-wrap"><button class="mode" data-mode="' + escape(mode.id) + '"' + (mode.enabled && P.online ? '' : ' disabled title="Настройте доступный script или scene в YAML"') + '>' + P.icon({ gaming: 'game', movie: 'movie', sleep: 'moon', study: 'study' }[mode.id]) + '<span>' + escape(mode.name) + '</span></button></div>';
        }
        P.el('modes').innerHTML = modes;
        P.el('active-count').textContent = P.data.demo ? 'Демонстрационный дом' : (P.online ? 'Home Assistant' : 'Последние данные · нет связи');
        P.el('settings-mode').textContent = P.data.demo ? 'Demo Mode. Все устройства и музыка вымышлены.' : 'Home Assistant · разрешения заданы на сервере.';
        P.el('configured-entities').innerHTML = entities.map(function (e) { return '<div class="entity-row">' + escape(e.name) + '<span>' + escape(e.entity_id + ' · ' + e.room) + '</span></div>'; }).join('');
    };
}(window.Panel));
