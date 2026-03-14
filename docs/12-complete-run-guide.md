# Бағдарламаны Іске Қосу Толық Нұсқаулық

Бұл құжат PhishGuard жобасын нөлден бастап толық іске қосу үшін жазылды.
Нұсқаулық Windows PowerShell ортасына бейімделген.

## 1. Не орнатылады

Жоба мына бөліктерден тұрады:

- ML модель дайындау
- Gmail хаттарын оқу
- Email-ды талдау
- Нәтижені деректер базасына жазу
- Dashboard арқылы көрсету

## 2. Алдын ала талаптар

Компьютеріңізде мыналар болуы керек:

- `Python 3.10+`
- `pip`
- `git`

Қосымша:

- Gmail real интеграция керек болса: Google Cloud Console аккаунты
- PostgreSQL керек болса: PostgreSQL Server
- BERT үйрету керек болса: CUDA бар GPU ұсынылады

Python нұсқасын тексеру:

```powershell
python --version
```

## 3. Жобаны ашу

Егер репо әлі көшірілмесе:

```powershell
git clone https://github.com/Azamaperdeev05/akhmetzhan.git
cd akhmetzhan
```

Егер жоба компьютерде бар болса:

```powershell
cd "C:\Users\Acer\Desktop\Ахметжан"
```

## 4. Виртуалды орта жасау

```powershell
python -m venv venv
```

Іске қосу:

```powershell
venv\Scripts\Activate.ps1
```

Егер PowerShell execution policy қате берсе:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
venv\Scripts\Activate.ps1
```

## 5. Тәуелділіктерді орнату

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 6. `.env` файлын жасау

Үлгіден көшіріңіз:

```powershell
Copy-Item .env.example .env
```

## 7. Ең қарапайым жұмыс істейтін нұсқа

Егер алдымен жобаны тез көргіңіз келсе, осы режимді қолданыңыз:

- Database: `SQLite`
- Gmail: міндетті емес
- Sample fallback: уақытша қосуға болады

`.env` ішінде мына мәндер бар екенін тексеріңіз:

```env
DATABASE_URL=sqlite:///phishguard.db
PHISHING_THRESHOLD=0.75
SCAN_INTERVAL_MINUTES=5
AUTO_SCAN_ENABLED=0
ALLOW_SAMPLE_FALLBACK=1
FLASK_SECRET_KEY=change-me
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=admin12345
MODEL_DIR=model/saved_model
```

Ескерту:

- `ALLOW_SAMPLE_FALLBACK=1` тек offline demo үшін
- Нақты Gmail қолдансаңыз, оны `0` қылыңыз

## 8. Деректер базасын дайындау

### 8.1. SQLite

SQLite local demo үшін ең жеңіл нұсқа.

Бұл режимде жоба `phishguard.db` файлын өзі жасай алады.
Егер ескі legacy база болса, migration скриптімен жаңартыңыз:

```powershell
python scripts/db_upgrade.py
```

### 8.2. PostgreSQL

Егер диплом қорғауда дұрыс архитектура көрсеткіңіз келсе, PostgreSQL қолданған дұрыс.

`.env` мысалы:

```env
DATABASE_URL=postgresql+psycopg://phishguard:phishguard@localhost:5432/phishguard
```

Одан кейін migration жүргізіңіз:

```powershell
python scripts/db_upgrade.py
```

Немесе:

```powershell
alembic upgrade head
```

## 9. Gmail real интеграциясын баптау

Егер нақты Gmail inbox оқу керек болса, мына қадамдарды орындаңыз.

### 9.1. Google Cloud Console

1. [Google Cloud Console](https://console.cloud.google.com/) ашыңыз
2. Жаңа project жасаңыз
3. `Gmail API` қосыңыз
4. `Google Auth Platform` бөліміне кіріңіз
5. `OAuth consent screen` баптаңыз
6. `Audience` бөлімінде өз Gmail адресіңізді `Test users` қатарына қосыңыз
7. `Clients` бөлімінде `Desktop app` типімен OAuth Client жасаңыз
8. Жүктелген файлды жоба түбіріне `credentials.json` деп қойыңыз

### 9.2. `.env` тексеру

Мына жолдар болсын:

```env
GMAIL_CREDENTIALS_PATH=credentials.json
GMAIL_TOKEN_PATH=token.json
GMAIL_LABEL_NAME=PHISHING
GMAIL_QUERY=in:inbox newer_than:1d
ALLOW_SAMPLE_FALLBACK=0
```

### 9.3. Алғашқы авторизация

Scanner алғаш real Gmail-мен іске қосылғанда браузер ашылады.
Сіз рұқсат бересіз, содан кейін `token.json` жасалады.

## 10. Датасет дайындау

Егер тек dashboard/demo керек болса, бұл қадамды өткізіп жіберуге болады.

```powershell
python data/preprocess.py
```

Нәтижелер:

- `data/processed/train.csv`
- `data/processed/val.csv`
- `data/processed/test.csv`

## 11. Модельді үйрету

### 11.1. Baseline

Бұл ең жеңіл және тез нұсқа:

```powershell
python model/train.py --mode baseline
```

### 11.2. BERT

GPU бар болса:

```powershell
python model/train.py --mode bert --epochs 4 --batch-size 16 --use-gpu
```

Қысқа smoke run:

```powershell
python model/train.py --mode bert --epochs 1 --batch-size 4 --use-gpu
```

## 12. Модельді бағалау

Baseline:

```powershell
python model/evaluate.py --mode baseline
```

BERT:

```powershell
python model/evaluate.py --mode bert --use-gpu
```

Нәтиже:

- `model/saved_model/evaluation_report.json`

## 13. Scanner іске қосу

### 13.1. Бір рет қана сканерлеу

```powershell
python main.py --once
```

### 13.2. Үздіксіз режим

```powershell
python main.py
```

### 13.3. Offline sample режим

```powershell
python main.py --once --allow-sample-fallback --offline-samples data/raw/sample_inbox.json
```

## 14. Dashboard іске қосу

```powershell
python dashboard/app.py
```

Ашылатын адрес:

- `http://127.0.0.1:5000`
- `http://127.0.0.1:5000/login`

Әдепкі логин:

- Логин: `admin`
- Пароль: `admin12345`

Өзгерту үшін `.env` ішіне:

```env
DASHBOARD_USERNAME=your_login
DASHBOARD_PASSWORD=your_password
FLASK_SECRET_KEY=your_secret_key
```

## 15. Dashboard ішінде не істеуге болады

- Жүйе статистикасын көру
- Соңғы хаттарды көру
- Қолмен `Қазір сканерлеу` батырмасын басу
- `Авто-сканерді қосу/өшіру`
- Threshold пен scan interval өзгерту

## 16. Жобаны толық демонстрация үшін іске қосу реті

Ең дұрыс реттік схема:

1. Виртуалды орта қосу
2. `python -m pip install -r requirements.txt`
3. `Copy-Item .env.example .env`
4. `.env` ішін баптау
5. PostgreSQL қолдансаңыз: `python scripts/db_upgrade.py`
6. Нақты Gmail керек болса: `credentials.json` қою
7. Модель керек болса: `python data/preprocess.py`
8. `python model/train.py --mode baseline`
9. `python model/evaluate.py --mode baseline`
10. `python dashboard/app.py`
11. Қажет болса бөлек терезеде `python main.py --once`

## 17. Жылдам demo сценарийі

Егер қазір тек интерфейсті көрсету керек болса:

1. `.env` ішінде `ALLOW_SAMPLE_FALLBACK=1`
2. `python dashboard/app.py`
3. Браузерден `http://127.0.0.1:5000/login`
4. `admin / admin12345` арқылы кіру
5. `Қазір сканерлеу` батырмасын басу
6. Нәтижені `Шолу`, `Хаттар`, `Статистика` беттерінен көрсету

## 18. Жиі кездесетін қателер

### `TemplateNotFound: login.html`

Соңғы версияда бұл түзетілген.
Ескі файлмен іске қосылып тұрмағанын тексеріңіз.

### `access_denied 403` Gmail авторизациясында

Себептері:

- аккаунт `Test users` тізімінде жоқ
- `OAuth consent screen` дұрыс аяқталмаған
- басқа Google аккаунтпен кіріп кеткенсіз

### `credentials.json not found`

Шешімі:

- `credentials.json` файл жоба түбірінде болуы керек
- `.env` ішіндегі `GMAIL_CREDENTIALS_PATH` дұрыс болсын

### `token.json` ескі болып қалды

Шешімі:

```powershell
Remove-Item token.json
```

Сосын scanner-ді қайта іске қосыңыз.

### PostgreSQL migration қатесі

Мыналарды тексеріңіз:

- PostgreSQL service қосулы ма
- `DATABASE_URL` дұрыс па
- бос база жасалған ба
- `python scripts/db_upgrade.py` орындалды ма

## 19. Тесттер

Барлық тест:

```powershell
python -m pytest -q tests
```

## 20. Қандай режимді таңдау керек

Егер тез көрсету керек болса:

- `SQLite`
- `ALLOW_SAMPLE_FALLBACK=1`
- `dashboard/app.py`

Егер нақты жұмысын көрсету керек болса:

- `SQLite` немесе `PostgreSQL`
- `ALLOW_SAMPLE_FALLBACK=0`
- `credentials.json`
- `token.json`
- `main.py`

Егер диплом қорғауда архитектураны дұрыс көрсету керек болса:

- `PostgreSQL`
- `Alembic migration`
- `Gmail real mode`
- `dashboard + scanner`

## 21. Ұсынылатын `.env` конфигтері

### 21.1. Demo режим

```env
DATABASE_URL=sqlite:///phishguard.db
PHISHING_THRESHOLD=0.75
SCAN_INTERVAL_MINUTES=5
AUTO_SCAN_ENABLED=0
ALLOW_SAMPLE_FALLBACK=1
FLASK_SECRET_KEY=change-me
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=admin12345
MODEL_DIR=model/saved_model
```

### 21.2. Real Gmail режим

```env
DATABASE_URL=sqlite:///phishguard.db
PHISHING_THRESHOLD=0.75
SCAN_INTERVAL_MINUTES=5
AUTO_SCAN_ENABLED=0
ALLOW_SAMPLE_FALLBACK=0
FLASK_SECRET_KEY=change-me
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=admin12345
GMAIL_CREDENTIALS_PATH=credentials.json
GMAIL_TOKEN_PATH=token.json
GMAIL_LABEL_NAME=PHISHING
GMAIL_QUERY=in:inbox newer_than:1d
MODEL_DIR=model/saved_model
```

### 21.3. PostgreSQL режим

```env
DATABASE_URL=postgresql+psycopg://phishguard:phishguard@localhost:5432/phishguard
PHISHING_THRESHOLD=0.75
SCAN_INTERVAL_MINUTES=5
AUTO_SCAN_ENABLED=0
ALLOW_SAMPLE_FALLBACK=0
FLASK_SECRET_KEY=change-me
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=admin12345
GMAIL_CREDENTIALS_PATH=credentials.json
GMAIL_TOKEN_PATH=token.json
MODEL_DIR=model/saved_model
```

## 22. Қысқа қорытынды

Ең жеңіл бастау:

```powershell
cd "C:\Users\Acer\Desktop\Ахметжан"
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python dashboard/app.py
```

Ең дұрыс толық іске қосу:

```powershell
cd "C:\Users\Acer\Desktop\Ахметжан"
venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/db_upgrade.py
python main.py --once
python dashboard/app.py
```
