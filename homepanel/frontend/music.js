(function (P) {
    'use strict';
    var escape = P.escape;
    P.currentPlayer = function () {
        var entities = P.data ? P.data.entities : [], i, players = [];
        for (i = 0; i < entities.length; i += 1) {
            if (entities[i].entity_id.indexOf('media_player.') === 0) { players.push(entities[i]); }
        }
        for (i = 0; i < players.length; i += 1) { if (players[i].entity_id === P.player) { return players[i]; } }
        if (players.length) { P.player = players[0].entity_id; return players[0]; }
        return null;
    };
    function transport(entity) {
        var playing = entity.state === 'playing';
        return '<div class="transport">' + P.button(entity, 'previous', 'previous', 'Предыдущая композиция') + P.button(entity, playing ? 'pause' : 'play', playing ? 'pause' : 'play', playing ? 'Пауза' : 'Воспроизвести') + P.button(entity, 'next', 'next', 'Следующая композиция') + '</div>';
    }
    function selector(entity, location) {
        var html = '<select class="player-select" data-player="true" aria-label="Выбрать плеер: ' + location + '">', entities = P.data.entities, i;
        for (i = 0; i < entities.length; i += 1) {
            if (entities[i].entity_id.indexOf('media_player.') === 0) {
                html += '<option value="' + escape(entities[i].entity_id) + '"' + (entity.entity_id === entities[i].entity_id ? ' selected' : '') + '>' + escape(entities[i].name) + '</option>';
            }
        }
        return html + '</select>';
    }
    function volume(entity, location) {
        var level = typeof entity.attributes.volume_level === 'number' ? entity.attributes.volume_level : 0;
        return '<label class="volume-line">' + P.icon('volume') + '<input type="range" min="0" max="100" value="' + Math.round(level * 100) + '" data-entity="' + escape(entity.entity_id) + '" data-range="volume" aria-label="Громкость: ' + location + '"' + (P.can(entity, 'volume') && typeof entity.attributes.volume_level === 'number' ? '' : ' disabled') + '></label>';
    }
    P.time = function (seconds) {
        var value = Math.max(0, Math.floor(seconds || 0));
        return Math.floor(value / 60) + ':' + ('0' + value % 60).slice(-2);
    };
    P.position = function (entity) {
        var a = entity.attributes, position = a.media_position || 0, timestamp;
        if (entity.state === 'playing' && a.media_position_updated_at && !P.data.demo && P.online) {
            timestamp = Date.parse(a.media_position_updated_at);
            if (isFinite(timestamp)) { position += Math.max(0, (Date.now() - timestamp) / 1000); }
        }
        return Math.max(0, Math.min(a.media_duration || 0, position));
    };
    P.updateProgress = function () {
        var e = P.currentPlayer(), input = P.el('seek'), text = P.el('elapsed');
        if (e && input && document.activeElement !== input) { input.value = P.position(e); }
        if (e && text) { text.textContent = P.time(P.position(e)); }
    };
    P.renderMusic = function () {
        var entity = P.currentPlayer(), cover, title, artist, attrs, unavailable, detail;
        if (!entity) {
            P.el('player').innerHTML = '<p class="muted">Нет выбранных плееров · добавьте media_player в YAML.</p>';
            P.el('music-detail').innerHTML = '<div class="empty">Выберите плееры в configuration/config.yaml.<p class="muted">Для Music Assistant используйте его media_player сущности в Home Assistant.</p></div>';
            return;
        }
        attrs = entity.attributes;
        cover = P.data.demo ? '/static/cover.svg' : (entity.artwork || '/static/home.svg');
        unavailable = entity.state === 'unavailable' || entity.state === 'unknown';
        title = escape(unavailable ? 'Плеер недоступен' : attrs.media_title || 'Пока ничего не играет');
        artist = escape(attrs.media_artist || entity.name);
        P.el('player').innerHTML = '<div class="track-info"><a href="#music" aria-label="Открыть музыкальный экран"><img class="cover-small" src="' + escape(cover) + '" alt=""><div class="track-text"><strong>' + title + '</strong><small>' + artist + '</small></div></a></div>' + transport(entity) + '<div class="player-side">' + selector(entity, 'мини-плеер') + volume(entity, 'мини-плеер') + '</div>';
        detail = '<div class="music-stage"><img class="cover-large" src="' + escape(cover) + '" alt="Обложка альбома"><h2>' + title + '</h2><p class="muted">' + artist + (attrs.media_album_name ? ' · ' + escape(attrs.media_album_name) : '') + '</p>' + selector(entity, 'музыкальный экран');
        if (typeof attrs.media_duration === 'number' && attrs.media_duration > 0 && typeof attrs.media_position === 'number') {
            detail += '<div class="progress-row"><input id="seek" type="range" min="0" max="' + attrs.media_duration + '" value="' + P.position(entity) + '" data-entity="' + escape(entity.entity_id) + '" data-range="seek" aria-label="Позиция композиции"' + (P.can(entity, 'seek') ? '' : ' disabled') + '><div class="time-labels"><span id="elapsed">' + P.time(P.position(entity)) + '</span><span>' + P.time(attrs.media_duration) + '</span></div></div>';
        }
        detail += transport(entity) + volume(entity, 'музыкальный экран') + '<p class="muted">' + (P.data.demo ? 'Демонстрационный плеер · звук не воспроизводится' : 'Управление через Home Assistant') + '</p></div>';
        P.el('music-detail').innerHTML = detail;
        var images = document.querySelectorAll('.cover-small,.cover-large'), i;
        for (i = 0; i < images.length; i += 1) {
            images[i].onerror = function () { this.onerror = null; this.src = '/static/home.svg'; };
        }
    };
}(window.Panel));
