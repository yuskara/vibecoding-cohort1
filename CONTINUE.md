# CONTINUE.md

This file provides guidance to CONTINUE Code (CONTINUE.ai/code) when working with code in this repository.

## ZORUNLU KURAL: Bu Dosyaları Her Zaman Güncelle

**Her kod değişikliğinin ardından, commit yapmadan önce `CONTINUE.md` ve `AGENTS.md` dosyalarını güncellemelisin.**

Güncelleme gerektiren durumlar:
- Yeni dosya veya modül eklenmesi
- Yeni API endpoint'i eklenmesi veya kaldırılması
- Yeni frontend sayfası eklenmesi
- Mevcut bir modülün sorumluluğunun değişmesi
- Yeni bağımlılık veya ortam değişkeni eklenmesi

Güncelleme yapmazsan mimari bilgisi eskir ve gelecekteki CONTINUE oturumları yanlış varsayımlarla çalışır.

---

## Geliştirme Ortamı

```bash
# Sanal ortamı aktifleştir
source .venv/bin/activate

# Bağımlılıkları yükle
pip install -r requirements.txt

# Uygulamayı çalıştır (http://localhost:5000)
flask --app app run --debug
```

`.env` dosyasında `OPENAI_API_KEY` veya yerel Ollama için `OLLAMA_API_BASE=http://127.0.0.1:11434/v1` tanımlı olmalıdır.

---

## Mimari

Flask backend + vanilla JS frontend. Üç ayrı sayfa sunar:

| Sayfa | URL | Açıklama |
|---|---|---|
| LLM Arayüzü | `/` | Tek seferlik, hafızasız LLM çağrısı |
| Asistan | `/asistan` | Conversation history tutan sohbet arayüzü |
| Kodlama Agenti | `/agent` | Tool-calling agentic loop arayüzü |

### Dosya Sorumlulukları

- **`app.py`** — Flask uygulaması. Routing, model doğrulaması, asistan ve agent oturum yönetimi. Currently uses `qwen2.5-coder:3b` model from local Ollama.
- **`llm.py`** — OpenAI istemcisi kurulumu ve `stream_llm()` fonksiyonu. Tek seferlik, history'siz.
- **`asistan.py`** — `Asistan` sınıfı. Conversation history tutan, `sohbet()` ve `stream_sohbet()` metodları.
- **`agent.py`** — `Agent` sınıfı. Tool-calling agentic loop; `calistir()` generator'ı her adımda event dict'i yield eder. Tool'lar: `terminal`, `dosya_oku`, `dosya_yaz`, `search_supabase`.
- **`frontend/index.html`** — LLM arayüzü. Tek prompt → tek yanıt.
- **`frontend/asistan.html`** — Sohbet arayüzü. Baloncuklu, çok turlu, session tabanlı.
- **`frontend/agent.html`** — Agent arayüzü. Her adımı, tool call'ları, sonuçlarını ve thinking text'ini görsel olarak gösterir.

### LLM Arayüzü Veri Akışı

1. `frontend/index.html` → `POST /api/chat` (model, system_instructions, user_prompt)
2. `app.py` → `stream_llm()` çağrısı
3. `llm.py` → OpenAI Streaming API → chunk'lar `text/plain` olarak istemciye aktarılır
4. Frontend `ReadableStream` ile chunk'ları okur, `#response` div'ine ekler

### Asistan Veri Akışı

1. `frontend/asistan.html` → `POST /api/asistan/yeni` (model, system_instructions) → `session_id` döner
2. `frontend/asistan.html` → `POST /api/asistan/sohbet` (session_id, user_prompt)
3. `app.py` → `_asistanlar[session_id].stream_sohbet()` çağrısı
4. `asistan.py` → OpenAI Streaming API → chunk yield eder, bitince history'ye ekler
5. Frontend chunk'ları asistan balonuna akıtır

### Agent Veri Akışı

1. `frontend/agent.html` → `POST /api/agent/yeni` (model, system_instructions) → `session_id` döner
2. `frontend/agent.html` → `POST /api/agent/calistir` (session_id, user_prompt)
3. `app.py` → `_agentlar[session_id].calistir()` generator'ını iter eder
4. `agent.py` → OpenAI tool-calling API → her event için JSON satırı yield eder (NDJSON)
5. Frontend NDJSON satırlarını parse eder; event tipine göre (`step_start`, `thinking`, `tool_call`, `tool_result`, `text`, `done`) görsel bloklar oluşturur

### API Endpoint'leri

| Method | Path | Açıklama |
|---|---|---|
| POST | `/api/chat` | Tek seferlik LLM çağrısı (streaming, text/plain) |
| POST | `/api/asistan/yeni` | Yeni asistan oturumu oluştur |
| POST | `/api/asistan/sohbet` | Asistana mesaj gönder (streaming, text/plain) |
| POST | `/api/agent/yeni` | Yeni agent oturumu oluştur |
| POST | `/api/agent/calistir` | Agent'ı çalıştır (NDJSON stream) |

### Kritik Noktalar

- Model doğrulaması `app.py`'deki `ALLOWED_MODELS` set'i üzerinden yapılır. Currently set to `{"qwen2.5-coder:3b"}` for local Ollama usage. When models are changed, update both backend `ALLOWED_MODELS` and all frontend `<select>` elements in `index.html`, `asistan.html`, and `agent.html`.
- `llm.py` modül yüklendiğinde `client = OpenAI()` oluşturulur; `OPENAI_API_KEY` `.env`'de yoksa uygulama başlamaz.
- `_asistanlar` ve `_agentlar` dict'leri sunucu hafızasındadır; sunucu yeniden başlatılınca tüm oturumlar sıfırlanır.
- Asistan yanıtları `text/plain`, agent yanıtları `application/x-ndjson` olarak stream edilir.
- Agent terminal tool'u `/tmp/agent_workspace` dizininde çalışır; `shell=True` ile arbitrary komut çalıştırır (eğitim ortamı, localhost).
- Agent `thinking` event'i: model tool çağrısından önce metin üretirse bu `thinking` olarak işaretlenir; son yanıt `text` olarak işaretlenir.
