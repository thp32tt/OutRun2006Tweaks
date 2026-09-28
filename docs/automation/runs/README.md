# Queue automation run records

The ChatGPT worker creates one durable JSON/Markdown record per controller TASK_ID in this directory.

A record must distinguish:
- `automation_validation`
- `runtime_validation`

CI success never implies HMD/in-game success. Runtime remains `UNTESTED` unless real runtime evidence exists.
