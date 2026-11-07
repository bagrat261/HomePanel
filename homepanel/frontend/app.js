(function (P) {
    'use strict';
    var timer, lastData = '', failures = 0;
    function clock() {
        var now = new Date(), days = ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'];
        var months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];
        P.el('clock').textContent = ('0' + now.getHours()).slice(-2) + ':' + ('0' + now.getMinutes()).slice(-2);
        P.el('date').textContent = days[now.getDay()] + ', ' + now.getDate() + ' ' + months[now.getMonth()];
        if (P.data && P.view === 'music') { P.updateProgress(); }
    }
    function applyScreen() {
        var theme = P.store('theme') === 'light' ? 'light' : 'dark';
        var night = P.store('night') === 'true', brightness = parseInt(P.store('brightness'), 10) || 65;
        brightness = Math.max(30, Math.min(100, brightness));
        document.body.className = theme === 'light' ? 'light' : '';
        P.el('theme').value = theme; P.el('brightness').value = brightness;
        P.el('night-shade').style.opacity = night ? (100 - brightness) / 100 : 0;
        P.el('night').setAttribute('aria-pressed', String(night));
        P.el('night-setting').checked = night;
    }
    function schedule() {
        clearTimeout(timer);
        timer = setTimeout(function () { P.refresh(false); }, document.hidden ? 30000 : Math.min(60000, (P.data ? P.data.poll_seconds : 5) * 1000 * Math.pow(2, failures)));
    }
    P.refresh = function (force) {
        P.request('GET', '/api/dashboard', null, function (error, data, status) {
            var fingerprint, active = document.activeElement;
            if (error) {
                lastData = '';
                failures = Math.min(failures + 1, 4); P.online = false;
                P.el('connection').textContent = 'Нет связи'; P.el('connection').className = 'offline';
                if (status !== 401) { P.message(error); }
                if (P.data && (!active || !/INPUT|SELECT/.test(active.tagName))) { P.renderDevices(); P.renderMusic(); }
                if (status !== 401) { schedule(); } else { bootstrap(); }
                return;
            }
            failures = 0; P.data = data; P.online = data.connection === 'online';
            P.el('login').hidden = true;
            P.el('home-title').textContent = data.title; P.el('demo-badge').hidden = !data.demo;
            P.el('connection').textContent = P.online ? (data.demo ? 'Демо подключено' : 'Подключено') : 'HA недоступен';
            P.el('connection').className = P.online ? 'online' : 'offline';
            if (!P.online) { P.message('Home Assistant недоступен. Показаны последние данные. Повторное подключение автоматически.'); }
            else if (P.el('notice').textContent.indexOf('недоступен') >= 0 || P.el('notice').textContent.indexOf('Wi-Fi') >= 0) { P.message(''); }
            fingerprint = JSON.stringify(data);
            if ((force || fingerprint !== lastData) && (!active || !/INPUT|SELECT/.test(active.tagName))) {
                P.renderDevices(); P.renderMusic(); lastData = fingerprint;
            }
            schedule();
        });
    };
    function bootstrap() {
        P.request('GET', '/api/session', null, function (error, data, status) {
            if (error) { if (status !== 401) { P.message(error); timer = setTimeout(bootstrap, 10000); } return; }
            P.csrf = data.csrf; P.el('login').hidden = true; P.refresh(true);
        });
    }
    document.addEventListener('click', function (event) {
        var node = event.target, entity, step, target;
        while (node && node !== document) {
            if (node.disabled) { return; }
            if (node.getAttribute && node.hasAttribute('data-view')) { P.setView(node.getAttribute('data-view')); return; }
            if (node.getAttribute && node.hasAttribute('data-room')) {
                P.room = node.getAttribute('data-room'); P.renderDevices(); return;
            }
            if (node.getAttribute && node.hasAttribute('data-mode')) { P.command('/api/modes/' + node.getAttribute('data-mode'), null); return; }
            if (node.getAttribute && node.hasAttribute('data-action')) {
                P.action(node.getAttribute('data-entity'), node.getAttribute('data-action')); return;
            }
            if (node.getAttribute && node.hasAttribute('data-step')) {
                entity = P.find(node.getAttribute('data-entity'));
                if (entity && typeof entity.attributes.temperature === 'number') {
                    step = entity.attributes.target_temp_step || 0.5;
                    target = entity.attributes.temperature + parseInt(node.getAttribute('data-step'), 10) * step;
                    target = Math.max(entity.attributes.min_temp, Math.min(entity.attributes.max_temp, target));
                    P.action(entity.entity_id, 'temperature', Math.round(target * 100) / 100);
                }
                return;
            }
            node = node.parentNode;
        }
    }, false);
    document.addEventListener('change', function (event) {
        var node = event.target, action = node.getAttribute('data-range');
        if (action) { P.action(node.getAttribute('data-entity'), action, parseFloat(node.value) / (action === 'volume' ? 100 : 1)); }
        if (node.hasAttribute('data-player')) { P.player = node.value; P.store('player', node.value); P.renderMusic(); }
        if (node.id === 'theme' || node.id === 'brightness') { P.store(node.id, node.value); applyScreen(); }
        if (node.id === 'night-setting') { P.store('night', String(node.checked)); applyScreen(); }
    }, false);
    P.el('night').onclick = function () { P.store('night', String(P.store('night') !== 'true')); applyScreen(); };
    P.el('fullscreen').onclick = function () {
        var root = document.documentElement;
        if (document.fullscreenElement && document.exitFullscreen) { document.exitFullscreen(); }
        else if (root.requestFullscreen) { root.requestFullscreen(); }
        else if (root.webkitRequestFullscreen) { root.webkitRequestFullscreen(); }
        else { P.message('На этом устройстве: «Поделиться» → «На экран Домой». Для постоянного экрана отключите автоблокировку iOS.'); }
    };
    P.el('login-form').onsubmit = function (event) {
        event.preventDefault();
        var button = this.querySelector('button'); button.disabled = true;
        P.request('POST', '/api/login', { password: P.el('password').value }, function (error, data) {
            button.disabled = false;
            P.el('login-error').textContent = error || '';
            if (!error) { P.csrf = data.csrf; P.el('password').value = ''; P.el('login').hidden = true; P.refresh(true); }
        });
    };
    P.el('logout').onclick = function () {
        var anonymousDemo = P.data && P.data.demo;
        P.request('POST', '/api/logout', null, function (error) {
            if (error) { P.message(error); return; }
            clearTimeout(timer); P.csrf = ''; P.data = null; P.online = false; lastData = '';
            P.el('devices').innerHTML = ''; P.el('player').innerHTML = '';
            P.el('login').hidden = false;
            if (anonymousDemo) { bootstrap(); }
        });
    };
    window.addEventListener('hashchange', function () { P.setView(window.location.hash.slice(1) || 'home'); }, false);
    document.addEventListener('visibilitychange', function () { if (!document.hidden && P.csrf) { P.refresh(true); } }, false);
    window.addEventListener('online', function () { if (P.csrf) { P.refresh(true); } else { bootstrap(); } }, false);
    P.player = P.store('player') || ''; applyScreen(); clock(); setInterval(clock, 1000);
    P.setView(window.location.hash.slice(1) || 'home'); bootstrap();
}(window.Panel));
