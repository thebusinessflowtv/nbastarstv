from pathlib import Path

path = Path('.github/workflows/daily-production.yml')
text = path.read_text(encoding='utf-8')
old = "          print(f'- Topic: {topic} / " + "$" + "{{ steps.setup.outputs.topic_name }}')\n"
new = (
    "          topic_name = " + "$" + "{{ toJSON(steps.setup.outputs.topic_name) }}\n"
    "          print(f'- Topic: {topic} / {topic_name}')\n"
)
if old in text:
    path.write_text(text.replace(old, new, 1), encoding='utf-8')
elif 'topic_name = ${{ toJSON(steps.setup.outputs.topic_name) }}' not in text:
    raise SystemExit('Cost summary topic line not found')
print('NBA daily-production cost summary is apostrophe-safe.')
