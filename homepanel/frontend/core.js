(function () {
    'use strict';
    var P = window.Panel = { csrf: '', data: null, player: '', room: 'Все', view: 'home', busy: false, online: false };
    P.el = function (id) { return document.getElementById(id); };
    P.escape = function (value) {
        return String(value === null || typeof value === 'undefined' ? '' : value).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    };
    P.icon = function (name) { return '<svg class="icon" aria-hidden="true"><use xlink:href="#i-' + name + '"/></svg>'; };
    P.store = function (key, value) {
        try {
            if (typeof value === 'undefined') { return window.localStorage.getItem('homepanel-' + key); }
            window.localStorage.setItem('homepanel-' + key, value);
        } catch (error) {
            if (error.name !== 'SecurityError' && error.name !== 'QuotaExceededError') { throw error; }
        }
        return null;
    };
    P.message = function (text) { P.el('notice').textContent = text; P.el('notice').hidden = !text; };
    P.request = function (method, path, body, done) {
        var xhr = new XMLHttpRequest(), finished = false;
        function finish(error, data, status) {
            if (finished) { return; }
            finished = true;
            done(error, data, status);
        }
        xhr.open(method, path, true);
        xhr.timeout = 15000;
        if (method !== 'GET') {
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.setRequestHeader('X-CSRF-Token', P.csrf);
        }
        xhr.onreadystatechange = function () {
            var data;
            if (xhr.readyState !== 4 || xhr.status === 0) { return; }
            try { data = JSON.parse(xhr.responseText); }
            catch (error) {
                if (!(error instanceof SyntaxError)) { throw error; }
                finish('Сервер вернул неверный ответ.'); return;
            }
            if (xhr.status === 401) { P.el('login').hidden = false; }
            finish(xhr.status >= 200 && xhr.status < 300 ? null : (typeof data.detail === 'string' ? data.detail : 'Запрос отклонён сервером.'), data, xhr.status);
        };
        xhr.onerror = function () { finish('Нет связи с сервером. Проверьте Wi-Fi.'); };
        xhr.ontimeout = function () { finish('Сервер не ответил вовремя.'); };
        xhr.send(body ? JSON.stringify(body) : null);
    };
    P.find = function (id) {
        var list = P.data ? P.data.entities : [], i;
        for (i = 0; i < list.length; i += 1) { if (list[i].entity_id === id) { return list[i]; } }
        return null;
    };
    P.can = function (entity, action) { return P.online && entity && entity.actions.indexOf(action) !== -1; };
    P.command = function (path, body) {
        if (P.busy || !P.online) { return; }
        P.busy = true;
        P.request('POST', path, body, function (error, data, status) {
            P.busy = false;
            if (error) {
                P.message(error + (status ? '' : ' Команда могла выполниться. Проверьте состояние перед повтором.'));
            } else { P.message(path.indexOf('/modes/') >= 0 ? 'Сценарий запущен.' : ''); }
            P.refresh(true);
        });
    };
    P.action = function (id, action, value) {
        var body = { entity_id: id, action: action };
        if (typeof value === 'number') { body.value = value; }
        P.command('/api/action', body);
    };
    P.button = function (entity, action, icon, label) {
        return '<button class="' + (action === 'play' || action === 'pause' ? 'play-button' : 'icon-button') + '" data-entity="' + P.escape(entity.entity_id) + '" data-action="' + action + '" aria-label="' + label + '" title="' + label + '"' + (P.can(entity, action) ? '' : ' disabled') + '>' + P.icon(icon) + '</button>';
    };
    P.setView = function (name) {
        var views = ['home', 'music', 'settings'], i, buttons = document.querySelectorAll('[data-view]');
        if (views.indexOf(name) < 0) { return; }
        P.view = name;
        for (i = 0; i < views.length; i += 1) { P.el('view-' + views[i]).hidden = views[i] !== name; }
        for (i = 0; i < buttons.length; i += 1) { buttons[i].className = 'nav' + (buttons[i].getAttribute('data-view') === name ? ' active' : ''); }
        if (name === 'music' && P.data) { P.renderMusic(); }
    };
}());
