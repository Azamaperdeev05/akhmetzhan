# 🛡️ PhishGuard — Корпоративті Пошта Жүйесіндегі Фишинг Хабарламаларды Автоматты Анықтау Модулі

> **Дипломдық жоба** | Бағдарламалық қамтамасыз ету және ақпараттық жүйелер мамандығы

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![BERT](https://img.shields.io/badge/Model-BERT-orange?logo=huggingface)
![Gmail API](https://img.shields.io/badge/Gmail-API-red?logo=gmail)
![Flask](https://img.shields.io/badge/Dashboard-Flask-green?logo=flask)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## 📌 Жоба туралы

**PhishGuard** — корпоративті Gmail пошта жүйесіне келетін хаттарды нақты уақытта талдап, фишинг шабуылдарын автоматты түрде анықтайтын бағдарламалық модуль.

Жүйе **BERT (Bidirectional Encoder Representations from Transformers)** тілдік моделін fine-tuning арқылы үйретіп, Gmail API интеграциясы арқылы кіріс хаттарды сканерлейді және веб-dashboard арқылы нәтижелерді визуализациялайды.

### 🎯 Жобаның мақсаты

Корпоративті ортадағы фишинг шабуылдарын адам факторынсыз, автоматты түрде және жоғары дәлдікпен анықтайтын интеллектуалды жүйе жасау.

### 🔍 Шешілетін мәселелер

- Қызметкерлердің фишинг хаттарын ажырата алмауы
- Дәстүрлі спам-фильтрлердің жаңа шабуылдарға төзімсіздігі
- Корпоративті деректердің ағып кету қаупі
- Кибершабуылдарға жедел жауап беру мүмкіндігінің болмауы

---

## ✨ Функционалдық мүмкіндіктер

| Модуль | Сипаттама |
|--------|-----------|
| 📥 **Gmail интеграциясы** | OAuth2 арқылы қауіпсіз қосылу, хаттарды автоматты оқу |
| 🤖 **BERT классификаторы** | Фишинг/заңды хат анықтау, сенімділік деңгейі (%) |
| 🔗 **URL талдаушы** | Хаттардағы сілтемелерді тексеру, қысқартылған URL ашу |
| 📊 **Веб-dashboard** | Статистика, хаттар тарихы, визуализация |
| 🏷️ **Автоматты белгілеу** | Фишинг хаттарға Gmail label қою, оқшаулау |
| 📝 **Лог жүйесі** | Барлық анықталған қауіптердің тарихы |

---

## 🏗️ Жоба құрылымы

```
phishguard/
│
├── 📁 data/
│   ├── raw/
│   │   ├── phishing_emails.csv        # Фишинг датасеті (Kaggle)
│   │   └── legitimate_emails.csv      # Заңды хаттар датасеті
│   └── processed/
│       ├── train.csv                  # Үйрету деректері (80%)
│       ├── val.csv                    # Валидация деректері (10%)
│       └── test.csv                   # Тест деректері (10%)
│
├── 📁 model/
│   ├── train.py                       # BERT fine-tuning скрипті
│   ├── evaluate.py                    # Модельді бағалау
│   ├── predict.py                     # Болжам жасау функциялары
│   └── saved_model/
│       ├── config.json                # BERT конфигурациясы
│       └── pytorch_model.bin          # Үйретілген модель салмақтары
│
├── 📁 gmail/
│   ├── auth.py                        # Gmail OAuth2 аутентификация
│   ├── fetch_emails.py                # Хаттарды алу және парсинг
│   └── label_manager.py              # Gmail label басқару
│
├── 📁 analyzer/
│   ├── preprocessor.py                # Мәтін алдын-ала өңдеу
│   ├── url_checker.py                 # URL талдау модулі
│   ├── header_analyzer.py             # Email header тексеру (SPF/DKIM)
│   └── pipeline.py                    # Толық анализ pipeline
│
├── 📁 dashboard/
│   ├── app.py                         # Flask қосымшасы
│   ├── 📁 templates/
│   │   ├── index.html                 # Басты бет
│   │   ├── emails.html                # Хаттар тізімі
│   │   └── stats.html                 # Статистика беті
│   └── 📁 static/
│       ├── css/style.css
│       └── js/charts.js
│
├── 📁 utils/
│   ├── logger.py                      # Лог жүйесі
│   ├── database.py                    # SQLite операциялары
│   └── config.py                      # Конфигурация параметрлері
│
├── 📁 tests/
│   ├── test_model.py                  # Модель тесттері
│   ├── test_gmail.py                  # Gmail интеграция тесттері
│   └── test_analyzer.py               # Анализатор тесттері
│
├── requirements.txt                   # Python тәуелділіктері
├── .env.example                       # Орта айнымалылары үлгісі
├── main.py                            # Негізгі іске қосу файлы
└── README.md                          # Осы файл
```

---

## 🛠️ Технологиялар стегі

### 🤖 Машиналық оқыту және NLP
| Кітапхана | Нұсқа | Мақсаты |
|-----------|-------|---------|
| `transformers` | 4.35+ | HuggingFace BERT моделі |
| `torch` (PyTorch) | 2.0+ | Нейрондық желі framework |
| `scikit-learn` | 1.3+ | Метрикалар, preprocessing |
| `datasets` | 2.14+ | Датасет басқару |
| `tokenizers` | 0.14+ | BERT токенизациясы |

### 📧 Gmail интеграциясы
| Кітапхана | Мақсаты |
|-----------|---------|
| `google-api-python-client` | Gmail API клиенті |
| `google-auth-oauthlib` | OAuth2 аутентификация |
| `google-auth-httplib2` | HTTP транспорт |

### 🌐 Веб және деректер базасы
| Кітапхана | Мақсаты |
|-----------|---------|
| `Flask` | Веб-dashboard |
| `SQLAlchemy` | ORM, SQLite |
| `Chart.js` | Визуализация (frontend) |

### 🔧 Утилиттер
| Кітапхана | Мақсаты |
|-----------|---------|
| `pandas` | Деректерді өңдеу |
| `requests` | HTTP сұраулар |
| `python-dotenv` | .env конфигурация |
| `loguru` | Лог жүйесі |
| `beautifulsoup4` | HTML парсинг |

---

## 🧠 BERT Моделінің Архитектурасы

```
Кіріс (Email мәтіні)
        │
        ▼
┌───────────────────┐
│   Preprocessor    │  → HTML тазалау, нормализация
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ BERT Tokenizer    │  → [CLS] token1 token2 ... [SEP]
│ (max_length=512)  │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  bert-base-uncased│  → 12 layer, 768 hidden, 12 heads
│  (fine-tuned)     │  → 110M параметр
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  [CLS] embedding  │  → 768-өлшемді вектор
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  Dropout(0.3)     │
│  Linear(768→2)    │  → Бинарлы классификация
└───────────────────┘
        │
        ▼
   Softmax Output
  [Заңды, Фишинг]
  [0.05,  0.95  ]  → 95% фишинг ықтималдығы
```

### 📊 Модель гиперпараметрлері

```python
BERT_MODEL      = "bert-base-uncased"
MAX_LENGTH      = 512          # Токен саны
BATCH_SIZE      = 16
LEARNING_RATE   = 2e-5         # AdamW optimizer
EPOCHS          = 4
WARMUP_STEPS    = 500
WEIGHT_DECAY    = 0.01
DROPOUT         = 0.3
```

---

## 📊 Датасет

### Қолданылатын датасеттер (Kaggle)

| Датасет | Хат саны | Сілтеме |
|---------|----------|---------|
| Phishing Email Dataset | ~18,000 | [Kaggle](https://www.kaggle.com/datasets/naserabdullahalam/phishing-email-dataset) |
| Spam/Ham Email Dataset | ~5,700 | [Kaggle](https://www.kaggle.com/datasets/uciml/sms-spam-collection-dataset) |
| Nigerian Fraud Emails | ~3,000 | [Kaggle](https://www.kaggle.com/) |

### Деректер бөлінісі

```
Барлығы: ~25,000 хат
├── Үйрету (train):      80% → 20,000 хат
├── Валидация (val):     10% →  2,500 хат
└── Тест (test):         10% →  2,500 хат

Класс балансы:
├── Фишинг:  50% (12,500)
└── Заңды:   50% (12,500)
```

---

## ⚙️ Орнату және Іске Қосу

### 1. Репозиторийді клондау

```bash
git clone https://github.com/username/phishguard.git
cd phishguard
```

### 2. Виртуалды орта жасау

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Тәуелділіктерді орнату

```bash
pip install -r requirements.txt
```

### 4. Орта айнымалыларын орнату

```bash
cp .env.example .env
# .env файлын өзіңіздің мәліметтеріңізбен толтырыңыз
```

```env
# .env файлы
GMAIL_CLIENT_ID=your_client_id
GMAIL_CLIENT_SECRET=your_client_secret
GMAIL_REDIRECT_URI=http://localhost:8080/callback
FLASK_SECRET_KEY=your_secret_key
DATABASE_URL=sqlite:///phishguard.db
SCAN_INTERVAL_MINUTES=5
PHISHING_THRESHOLD=0.75
```

### 5. Gmail API баптау

1. [Google Cloud Console](https://console.cloud.google.com/) сайтына кіріңіз
2. Жаңа жоба жасаңыз → **Gmail API** қосыңыз
3. **OAuth 2.0 Client ID** жасаңыз
4. `credentials.json` файлын жобаның түбіріне орналастырыңыз

### 6. Модельді үйрету

```bash
# Деректерді дайындау
python data/preprocess.py

# BERT fine-tuning (GPU ұсынылады, Colab-та жасауға болады)
python model/train.py

# Модельді бағалау
python model/evaluate.py
```

### 7. Жүйені іске қосу

```bash
# Толық жүйені іске қосу (Gmail сканер + Dashboard)
python main.py

# Тек dashboard
python dashboard/app.py
```

Dashboard: `http://localhost:5000`

---

## 🔄 Жұмыс принципі (Pipeline)

```
Gmail Inbox
    │
    ▼ (OAuth2 + Gmail API)
Хатты оқу
    │
    ├── Subject
    ├── Body (HTML → Plain text)
    ├── Sender domain
    └── URLs тізімі
    │
    ▼
Preprocessor
    │  → HTML тегтерін алу
    │  → Арнайы символдарды тазалау
    │  → Мәтінді нормализациялау
    │
    ▼
BERT Tokenizer + Model
    │  → Токенизация (max 512)
    │  → Fine-tuned BERT inference
    │  → Softmax → P(фишинг)
    │
    ├── URL Checker (қосымша тексеру)
    │     → Доменді тексеру
    │     → Қысқартылған URL ашу
    │
    └── Header Analyzer
          → SPF/DKIM тексеру
          → Жіберуші домен анализі
    │
    ▼
Шешім қабылдау
    │
    ├── P > 0.75 → 🚨 ФИШИНГ
    │     → Gmail label: "PHISHING"
    │     → Базаға жазу
    │     └── Dashboard жаңарту
    │
    └── P ≤ 0.75 → ✅ ЗАҢДЫ
          → Dashboard статистика
```

---

## 📈 Күтілетін нәтижелер

| Метрика | Мақсатты мән |
|---------|-------------|
| **Accuracy** | ≥ 97% |
| **Precision** | ≥ 96% |
| **Recall** | ≥ 97% |
| **F1-Score** | ≥ 96.5% |
| **AUC-ROC** | ≥ 0.99 |
| **Inference уақыты** | < 500ms / хат |

---

## 🖥️ Dashboard Мүмкіндіктері

- 📊 **Статистика беті** — анықталған фишинг саны, сенімділік деңгейлері
- 📋 **Хаттар тізімі** — барлық сканерленген хаттар + олардың нәтижесі
- 🔴 **Қауіп деңгейі** — HIGH / MEDIUM / LOW индикаторлары
- 📅 **Тарих** — соңғы 30 күндік статистика графигі
- ⚙️ **Баптаулар** — сканерлеу жиілігі, шектік мән параметрлері

---

## 🧪 Тестілеу

```bash
# Барлық тесттерді іске қосу
python -m pytest tests/ -v

# Жекелеген модуль тесті
python -m pytest tests/test_model.py -v
python -m pytest tests/test_gmail.py -v

# Coverage есебі
python -m pytest tests/ --cov=. --cov-report=html
```

---

## 📚 Диплом Тараулары

### 1-тарау: Теориялық бөлім
- 1.1 Фишинг шабуылдарының түрлері мен классификациясы
- 1.2 Фишингті анықтаудың қолданыстағы әдістеріне шолу
- 1.3 BERT моделінің теориялық негіздері (Transformer архитектурасы)
- 1.4 Тапсырма қойылымы және шешу тәсілін таңдау негіздемесі

### 2-тарау: Жобалау бөлімі
- 2.1 Жүйенің жалпы архитектурасы
- 2.2 Gmail API интеграциясы жобалау
- 2.3 BERT классификаторын fine-tuning жобалау
- 2.4 Деректер базасы схемасы
- 2.5 Веб-интерфейс жобалау

### 3-тарау: Практикалық бөлім
- 3.1 Датасет жинау және алдын-ала өңдеу
- 3.2 BERT модельін үйрету және оңтайландыру
- 3.3 Gmail API интеграциясын іске асыру
- 3.4 Dashboard жасау
- 3.5 Жүйені тестілеу және нәтижелерді бағалау

---

## 🔮 Болашақ жоспарлар

- [ ] Multimodal анализ (хат ішіндегі суреттерді тексеру)
- [ ] Real-time Telegram бот ескертпелері
- [ ] GPT-4 негізіндегі хат мазмұны түсіндірмесі
- [ ] Outlook / Yandex Mail интеграциясы
- [ ] Docker контейнеризация
- [ ] REST API endpoint жасау

---

## 📄 Лицензия

MIT License — толық мәтін үшін [LICENSE](LICENSE) файлын қараңыз.

---

## 👤 Автор

**[Аты-жөніңіз]**
- 🎓 Мамандық: Бағдарламалық қамтамасыз ету және ақпараттық жүйелер
- 🏫 Университет: [Университет атауы]
- 📅 Жыл: 2024-2025
- 📧 Email: your.email@university.edu
- 🔗 GitHub: [@username](https://github.com/username)

**Ғылыми жетекші:** [Жетекші аты-жөні, ғылыми дәрежесі]

---

## 🙏 Алғыс

- [HuggingFace](https://huggingface.co/) — Transformers кітапханасы
- [Google](https://developers.google.com/gmail/api) — Gmail API документациясы
- [Kaggle](https://www.kaggle.com/) — Ашық датасеттер

---

<div align="center">

**⭐ Жобаны пайдалы деп тапсаңыз, star қоюды ұмытпаңыз!**

*Дипломдық жоба | 2024-2025 оқу жылы*

</div>
