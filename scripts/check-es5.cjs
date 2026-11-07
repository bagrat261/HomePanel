const fs = require('node:fs');
const path = require('node:path');
const acorn = require('acorn');
const directory = path.join(__dirname, '..', 'homepanel', 'frontend');
const files = fs.readdirSync(directory).filter(file => file.endsWith('.js'));
for (const file of files) {
    acorn.parse(fs.readFileSync(path.join(directory, file), 'utf8'), { ecmaVersion: 5 });
    console.log('ES5 PASS:', file);
}
