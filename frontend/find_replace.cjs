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
          if (t.name.includes('replace_file_content') && t.args && t.args.TargetFile && t.args.TargetFile.endsWith('HomePage.jsx')) {
            console.log('Found replace on line', i);
            console.log(JSON.stringify(t.args, null, 2));
            recovered = true;
          }
        }
      }
    } catch(e) {}
  }
}
