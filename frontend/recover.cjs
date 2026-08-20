const fs = require('fs');
const path = 'C:\\Users\\Acer\\.gemini\\antigravity\\brain\\07d98a3a-4741-42e4-a3f2-9d7147850b3c\\.system_generated\\logs\\transcript_full.jsonl';
const data = fs.readFileSync(path, 'utf8');
const lines = data.split('\n');
let recovered = false;
for (let i = lines.length - 1; i >= 0; i--) {
  if (lines[i].includes('"type":"PLANNER_RESPONSE"')) {
    try {
      const step = JSON.parse(lines[i]);
      if (step.tool_calls) {
        for (const t of step.tool_calls) {
          if ((t.name === 'write_to_file' || t.name === 'default_api:write_to_file') && t.args && t.args.TargetFile && t.args.TargetFile.endsWith('HomePage.jsx')) {
            fs.writeFileSync('C:\\Final_outfitAR\\outfit-ar\\frontend\\src\\pages\\HomePage.jsx', t.args.CodeContent);
            console.log('Recovered HomePage.jsx actually!');
            recovered = true;
            break;
          }
        }
      }
    } catch(e) {}
  }
  if (recovered) break;
}
if (!recovered) console.log('Not found');
