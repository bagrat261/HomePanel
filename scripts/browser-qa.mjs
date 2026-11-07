import { mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import assert from 'node:assert/strict';

const { loadOmowright } = await import(process.env.HOMEPANEL_OMOWRIGHT_LOADER);

const { omowright } = await loadOmowright();
const profile = await mkdtemp(join(tmpdir(), 'homepanel-qa-'));
await mkdir('artifacts', { recursive: true });
const browser = await omowright.connectPipe({
    browserPath: process.env.HOMEPANEL_BROWSER_PATH,
    browserArgs: ['--headless', '--no-first-run', '--no-default-browser-check', '--window-size=1024,768', '--user-data-dir=' + profile],
    storageRoot: profile,
});
try {
    const page = await browser.newTab('http://127.0.0.1:8090');
    const evidence = [];
    async function until(predicate) {
        for (let i = 0; i < 60; i += 1) {
            if (await page.evaluate(predicate)) { return; }
            await new Promise(resolve => setTimeout(resolve, 100));
        }
        throw new Error('Browser state did not settle');
    }
    async function capture(name) {
        await writeFile('artifacts/' + name + '.png', await page.screenshot());
        const geometry = await page.evaluate(() => ({
            width: innerWidth, height: innerHeight,
            scroll: document.documentElement.scrollWidth,
            targets: Array.from(document.querySelectorAll('button,a,input,select')).filter(e => e.getBoundingClientRect().width > 0).map(e => {
                const r = e.getBoundingClientRect();
                return { name: e.getAttribute('aria-label') || e.textContent.trim(), width: r.width, height: r.height };
            }),
        }));
        assert.ok(geometry.scroll <= geometry.width, 'No horizontal overflow: ' + name);
        evidence.push({ name, ...geometry });
    }
    await until(() => document.querySelectorAll('.device').length === 6);
    console.log(omowright.compactSnapshot(await page.snapshot()));
    await omowright.repinViewport(page, { width: 1024, height: 768 });
    assert.equal(await page.evaluate(() => innerWidth), 1024);
    await capture('dashboard-1024-dark');
    await page.evaluate(() => {
        const original = window.Panel.request;
        window.Panel.request = function (method, path, body, done) { done('Нет связи с сервером. Проверьте Wi-Fi.'); };
        window.Panel.refresh(false);
        window.Panel.request = original;
    });
    assert.equal(await page.evaluate(() => document.querySelector('[data-entity="light.demo_lounge"][data-action]').disabled), true);
    await page.evaluate(() => window.Panel.refresh(false));
    await until(() => document.querySelector('[data-entity="light.demo_lounge"][data-action]').disabled === false);
    const before = await page.evaluate(() => document.querySelector('[data-entity="light.demo_lounge"][data-action]').getAttribute('aria-pressed'));
    await page.locator('[data-entity="light.demo_lounge"][data-action]').click();
    await until(() => document.querySelector('[data-entity="light.demo_lounge"][data-action]').getAttribute('aria-pressed') === 'false');
    assert.equal(before, 'true');
    await page.locator('[data-room="Спальня"]').click();
    assert.equal(await page.evaluate(() => document.querySelectorAll('.device').length), 3);
    await page.locator('[data-room="Все"]').click();
    await page.locator('[data-mode="movie"]').click();
    await until(() => document.getElementById('notice').textContent === 'Сценарий запущен.');
    await page.locator('[data-view="music"]').click();
    await page.locator('#music-detail [data-action="play"]').click();
    await until(() => !!document.querySelector('#music-detail [data-action="pause"]'));
    await page.locator('#music-detail [data-action="next"]').click();
    await until(() => document.querySelector('#music-detail h2').textContent === 'A little closer');
    await page.locator('#music-detail [data-player]').selectOption('media_player.demo_bedroom');
    assert.equal(await page.evaluate(() => document.querySelector('#player [data-player]').value), 'media_player.demo_bedroom');
    await capture('music-1024-dark');
    await page.locator('[data-view="settings"]').click();
    await page.locator('#theme').selectOption('light');
    await capture('settings-1024-light');
    await page.locator('[data-view="home"]').click();
    await capture('dashboard-1024-light');
    await omowright.repinViewport(page, { width: 390, height: 844 });
    await capture('dashboard-390-light');
    await page.locator('[data-view="settings"]').click();
    await page.locator('#theme').selectOption('dark');
    await page.locator('[data-view="home"]').click();
    await capture('dashboard-390-dark');
    await omowright.repinViewport(page, { width: 320, height: 740 });
    await capture('dashboard-320-dark');
    await page.locator('[data-view="settings"]').click();
    await page.locator('#night-setting').check();
    assert.equal(await page.evaluate(() => document.getElementById('night-shade').style.opacity), '0.35');
    await page.locator('#night-setting').uncheck();
    await page.locator('[data-view="home"]').click();
    await page.evaluate(() => {
        const style = document.createElement('style');
        style.textContent = '* { line-height:1.5!important;letter-spacing:.12em!important;word-spacing:.16em!important } p {margin-bottom:2em!important}';
        document.head.appendChild(style);
    });
    await capture('dashboard-320-text-spacing');
    await page.keyboard.press('Tab');
    const focused = await page.evaluate(() => ({ tag: document.activeElement.tagName, outline: getComputedStyle(document.activeElement).outlineStyle }));
    assert.notEqual(focused.outline, 'none');
    await writeFile('artifacts/focus-320.png', await page.screenshot());
    await writeFile('artifacts/browser-evidence.json', JSON.stringify(evidence, null, 2));
    console.log('PASS: switch, rooms, scenario, playback, next, player selection, themes and reflow.');
} finally {
    await browser.close();
    await rm(profile, { recursive: true, force: true });
}
