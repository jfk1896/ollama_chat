# Ollama chat

A single-page chat for the Ollama API on the same computer. Python's standard library serves the page and forwards `/api/` to Ollama. Nothing is installed with pip.

The page listens on `127.0.0.1:8080` only. Open it at http://127.0.0.1:8080/

It was used with Ollama 0.40.16 and the official tags `qwen3.5:4b` and `qwen3.5:2b`. Qwen3.5 needs Ollama 0.30 or newer.

## What the page does

- The model list comes from Ollama. It selects `qwen3.5:4b` when that tag is installed, otherwise `qwen3.5:2b`.
- Thinking is a checkbox. These two models accept only on or off, and they default to on. The page sends `think: true` or `think: false`.
- A gauge shows tokens used and tokens left against the context length Ollama reports for the loaded model. The numbers start at 8,192 until a model is loaded. The bar turns orange at 90%.
- A timer runs from Send until the reply finishes. A comparison line keeps the latest finished time for each model across New chat.
- New chat clears the conversation that will be sent with the next question. It leaves the comparison line as it is.
- The page follows the end of a reply while you are already there. Scrolling up leaves the view where you put it.

With Thinking unchecked, Ollama does not open a separate thinking trace. The model can still write a long step-by-step answer in the reply itself.

## Disk and memory

| Tag | Download | Memory while that model is answering |
|---|---|---|
| qwen3.5:4b | 3.3 GB | about 3.4 GB |
| qwen3.5:2b | 2.7 GB | about 2.5 GB |

Ollama keeps one model loaded. The other tag stays on disk until you select it. Pull the 4B tag if you want the stronger reasoner. Pull the 2B tag as well when you want the comparison line to cover both.

Leave a few extra gigabytes free for Ollama's own files. A machine with 8 GB of RAM can run the 4B tag if the desktop is light. 16 GB is an easy fit.

## 1. Install Ollama

Install the current official build:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Check the service:

```bash
ollama -v
systemctl status ollama
```

Ollama should answer on http://127.0.0.1:11434/

If this computer already has an Ollama package from the distribution, update that package instead of running the install script over it.

## 2. Set the context length

On a CPU-only machine Ollama otherwise uses a short default context. This page was used with 8,192. A full 8,192-token prompt is the slow part: the model reads the whole chat before the first new token.

```bash
sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo tee /etc/systemd/system/ollama.service.d/context.conf >/dev/null << 'EOF'
[Service]
Environment="OLLAMA_CONTEXT_LENGTH=8192"
EOF
sudo systemctl daemon-reload
sudo systemctl restart ollama
systemctl show ollama -p Environment
```

`Environment` should include `OLLAMA_CONTEXT_LENGTH=8192`. After a model loads, `ollama ps` shows that context length, and the gauge follows it.

## 3. Download the models

```bash
ollama pull qwen3.5:4b
ollama pull qwen3.5:2b
```

Skip the 2B pull if you only want the 4B model. Check them with:

```bash
ollama list
```

A short private check, with thinking off:

```bash
curl http://127.0.0.1:11434/api/chat -d '{
  "model": "qwen3.5:4b",
  "think": false,
  "stream": false,
  "messages": [{"role": "user", "content": "What is 2+2? Reply with the number only."}]
}'
```

The content should be a short answer, and the message should have no thinking text.

## 4. Run the chat page

From this directory:

```bash
python3 server.py
```

Then open http://127.0.0.1:8080/

The process prints `Ollama chat at http://127.0.0.1:8080/`. Stop it with Ctrl-C. The server reads `index.html` on every page load, so a reload picks up edits. Port 8080 is set near the top of `server.py`. If Ollama is not on port 11434, start the server with `OLLAMA_HOST_URL` set to its base URL.

## 5. Optional: start the page at login

The unit expects this directory at `~/git/ollama_chat`. Change `ExecStart` and `WorkingDirectory` if the checkout lives somewhere else.

```bash
mkdir -p ~/.config/systemd/user
cp ollama-chat.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now ollama-chat.service
systemctl --user status ollama-chat.service
```

## What you are comparing

Use the same question on each model, with Thinking in the same position, and start a new chat before the second run. The first reply after a model has been idle includes the time to read the weights from disk. Ask again while `ollama ps` still lists that model when you want the generation time on its own. The comparison line under the gauge keeps the latest finished time for each tag.

Generated tokens include a thinking trace when the box is checked. Those tokens also count against the context limit.
