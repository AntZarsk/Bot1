# Self-hosted n8n на Mac

## Варіант без Docker — найпростіший старт

### 1. Перевір Node.js
```bash
node -v
npm -v
```

Якщо Node.js немає — встанови через Homebrew:
```bash
brew install node
```

### 2. Запусти n8n локально
```bash
npx n8n
```

Після запуску n8n буде доступний тут:
```text
http://localhost:5678
```

### 3. Якщо хочеш, щоб n8n працював постійно
Запусти його в окремому вікні Terminal або через:
```bash
nohup npx n8n > n8n.log 2>&1 &
```

### 4. Імпортуй workflow
У n8n:
- натисни `Create workflow`
- вибери `Import from file`
- завантаж файл:
  `n8n/worldfacts_schedule_workflow.json`

### 5. Налаштуй cron
У workflow вже є cron:
```text
0 8,11,14,17,20 * * *
```

Це 5 запусків на день.

### 6. Важливо
У node `Execute Command` шлях має бути:
```bash
curl -sS -X POST http://127.0.0.1:8080/post
```

Це спрацює тільки якщо локальний Python endpoint запущений **на цьому ж Mac**.

### 7. Запусти окремий локальний HTTP endpoint
У ще одному Terminal:
```bash
python3 local_post_server.py
```

Після запуску endpoint буде доступний тут:
```text
http://127.0.0.1:8080/health
http://127.0.0.1:8080/post
```

## Якщо хочеш через Docker
```bash
brew install --cask docker
docker volume create n8n_data
docker run -d --name n8n -p 5678:5678 -v n8n_data:/home/node/.n8n n8nio/n8n
```

Потім відкрий:
```text
http://localhost:5678
