# ⚡ برنامه تحت ترمینال API TEST CLI

<p align="center">
  <img src="docs/screenshot.png" alt="تصویر برنامه API TEST CLI" width="850"/>
</p>

<p align="center">
  <strong>محیط ترمینال پیشرفته جهت بنچمارک آماری، مقایسه رو‌در‌روی مدل‌ها (Arena)، تست استرس، تله‌متری TTFT و خط لوله‌های CI/CD مدل‌های هوش مصنوعی</strong>
</p>

<p align="center">
  <a href="#-قابلیت‌های-کلیدی">قابلیت‌ها</a> •
  <a href="#-نصب-و-اجرا">نصب و اجرا</a> •
  <a href="#-اجرا-در-حالت-اتوماسیون-و-cicd">حالت CI/CD</a> •
  <a href="#-جدول-دستورات-اسلش-slash-commands">دستورات اسلش</a> •
  <a href="#-گزارش-تله‌متری-و-خروجی‌ها">گزارش و خروجی</a> •
  <a href="README.md">English Documentation 🇬🇧</a>
</p>

---

## 🌟 قابلیت‌های کلیدی

- 🌈 **بنر متنی ASCII با گرادیانت رنگی RGB**: نمایش تایپوگرافی سه‌بعدی رنگی با پشتیبانی امن و بدون خطا از اینکودینگ UTF-8 در کنسول‌های مختلف ویندوز و لینوکس.
- 🥊 **مسابقه مقایسه رو‌در‌روی مدل‌ها (Model Arena)**:
  - بنچمارک همزمان دو یا چند مدل (`/compare` یا `--compare --models "model1,model2"`) روی پرامپت یکسان.
  - اعطای مدال‌های جدول افتخارات به برترین‌ها:
    - 🏆 **سریع‌ترین TTFT** (کمترین زمان تا شروع تولید اولین توکن)
    - 🚀 **بیشترین نرخ تولید توکن (TPS)** (قهرمان سرعت پردازش و Throughput)
    - ⏱ **سریع‌ترین پاسخ کل** (کمترین زمان کلی تا تکمیل پاسخ)
- 🌪 **تست استرس و بار همزمان (Concurrency & Load Stress Test)**:
  - شبیه‌سازی درخواست‌های همزمان کاربران (`/stress` یا `--stress`) با تعیین تعداد رشته‌ها و حجم درخواست‌ها.
  - سنجش دقیق خطاهای Rate Limit (HTTP 429)، افت ظرفیت سرور (HTTP 503)، نرخ کل توکن بر ثانیه و تاخیر صدک P95 زیر بار.
- 📈 **بنچمارک آماری چندمرحله‌ای و نمره پایداری (Stability Score)**:
  - امکان اجرای تکراری تست از ۱ تا ۲۰ دور (`/bench` با تنظیم تعداد دور).
  - محاسبه آماری **حداقل، حداکثر، میانگین، میانه، صدک P95 و انحراف معیار**.
  - تفکیک تاخیر اتصال اولیه (Cold-Start TTFT) از اتصالات گرم (Warm TTFT) و محاسبه **درصد پایداری** از روی واریانس سرعت.
- 🧠 **تحلیل و تفکیک توکن‌های تفکر (Reasoning Tokens)**:
  - استخراج خودکار و تمایز بخش تفکر (`<think>` یا `reasoning_content`) در مدل‌هایی نظیر DeepSeek-R1 و OpenAI o1/o3.
  - باکس تله‌متری مجزا برای زمان و تعداد توکن‌های تفکر و پاسخ نهایی.
- 📊 **خروجی چندگانه تله‌متری و بنچمارک (`/export` یا `--output`)**:
  - 🌐 **داشبورد تعاملی HTML با تم تاریک**: گزارش فوق‌العاده مدرن و زیبا، ریسپانسیو با کارت‌های آماری که ۱۰۰٪ بدون نیاز به اینترنت (بدون وابستگی CDN خارجی) در هر مرورگری باز می‌شود.
  - 📄 **فرمت مارک‌داون گیت‌هاب (Markdown)**: جدول‌های تمیز آماده برای کپی در PRها یا Issues گیت‌هاب.
  - 📊 **فرمت اکسل / CSV**: دیتاست ساخت‌یافته مناسب برای تحلیل در اکسل، Google Sheets یا پانداس پایتون.
  - 💾 **فرمت ساخت‌یافته JSON**: داده‌های خام کامل تله‌متری، هدرها، صدک‌ها و تک‌تک دورها.
- 🤖 **حالت بدون رابط گرافیکی جهت اتوماسیون و پایپ‌لاین‌های CI/CD**:
  - قابلیت اجرا در GitHub Actions، GitLab CI یا اسکریپت‌های سیستمی بدون باز کردن TUI.
  - شرط‌های اعتبارسنجی کیفیتی (`--max-ttft 250`، `--min-tps 40`، `--min-success-rate 95`) همراه با کدهای خروج استانداردی (`0` برای موفقیت و `1` برای رد شدن تست).
  - خروجی خالص `--json` جهت پردازش خودکار با ابزارهایی مثل `jq`.
- ⚡ **پیش‌نمایش انیمیشنی دستورات اسلش (`/`)**:
  - باز شدن پاپ‌آپ خاکستری با تایپ کاراکتر `/` و بسته شدن آن با پاک شدن کاراکتر.
  - فیلتر آنی، کلیدهای جهت‌نما و تکمیل خودکار با کلید Tab.
- 🎯 **انتخاب مدل با کلیدهای جهت‌نما (Arrow-Key Model Picker)**:
  - دریافت خودکار کاتالوگ مدل‌ها، جستجوی زنده با تایپ کلمه و ناوبری با کلیدهای **[↑ / ↓]**.
- 🔎 **صفحه اختصاصی وضعیت و سلامت مدل‌ها (Model Discovery Board)**:
  - تست سلامت موازی تمامی مدل‌ها با نوار پیشرفت زنده و گزارش شفاف علت خطاها.
- 💾 **مدیریت پروفایل و تاریخچه عملکرد**:
  - تنظیمات از پیش آماده (Presets) برای **OpenAI، سربراس (Cerebras با سرعت فوق‌العاده ۱۰۰۰+ توکن/ثانیه)، Groq Cloud، OpenRouter، DeepSeek، Mistral، Together AI، Fireworks AI، xAI (Grok)، Ollama و vLLM**.
  - مشاهده و مرور تاریخچه تست‌های قبلی با امکان پاکسازی یا خروجی گرفتن.

---

## 🚀 نصب و اجرا

### ۱. نصب

مخزن را کلون کرده و وابستگی‌ها را نصب کنید:

```bash
git clone https://github.com/Aporis3674/apitestllm.git
cd apitestllm
uv sync
```

یا اگر uv ندارید، از فایل requirements استفاده کنید:

```bash
pip install -r requirements.txt
```

### ۲. اجرای تعاملی در ترمینال
```bash
uv run apitestllm
# یا اگر uv ندارید:
python api_test.py
```
*در ویندوز می‌توانید مستقیماً فایل `run.bat` را با دو بار کلیک اجرا کنید.*

---

## 🤖 اجرا در حالت اتوماسیون و CI/CD

ابزار API TEST CLI می‌تواند بدون باز کردن منو، مستقیماً در خط فرمان و اسکریپت‌های اتوماسیون اجرا شود:

### ۱. اسکن سریع سلامت مدل‌ها
```bash
uv run apitestllm --scan --base-url "https://api.openai.com/v1" --api-key "sk-..."
```

### ۲. بنچمارک سرعت با شروط کیفی CI/CD
```bash
uv run apitestllm --benchmark --model "gpt-4o-mini" --runs 3 --max-ttft 300 --min-tps 50 --output "benchmark.html"
```
*اگر تاخیر TTFT بیش از ۳۰۰ میلی‌ثانیه شود یا سرعت تولید به زیر ۵۰ توکن بر ثانیه بیفتد، با کد خطای `1` خارج می‌شود.*

### ۳. مقایسه رو‌در‌روی چند مدل در مسابقه Arena
```bash
uv run apitestllm --compare --models "gpt-4o,gpt-4o-mini" --prompt "Explain photosynthesis" --output "comparison.md"
```

### ۴. تست استرس و تحمل همزمانی
```bash
uv run apitestllm --stress --model "gpt-4o-mini" --concurrency 10 --requests 30 --min-success-rate 95 --output "stress.json"
```

### ۵. خروجی JSON برای ابزار `jq`
```bash
uv run apitestllm --benchmark --model "gpt-4o-mini" --json | jq .ttft_ms
```

---

## 🛠 نمونه ورک‌فلو GitHub Actions

این بررسی خودکار سلامت اندپوینت را به `.github/workflows/ai-benchmark.yml` اضافه کنید:

```yaml
name: AI Endpoint SLA Check

on:
  schedule:
    - cron: '0 */6 * * *' # هر ۶ ساعت یک‌بار
  workflow_dispatch:

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Setup uv
        uses: astral-sh/setup-uv@bec219d24cd3e171d82865faccec33120bb574f4 # v10.1.0

      - name: Run Benchmark & Assert SLAs
        env:
          API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          uv run apitestllm \
            --benchmark \
            --base-url "https://api.openai.com/v1" \
            --api-key "$API_KEY" \
            --model "gpt-4o-mini" \
            --runs 3 \
            --max-ttft 350 \
            --min-tps 45 \
            --output "benchmark_report.html"

      - name: Upload Telemetry Artifact
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: benchmark-report
          path: benchmark_report.html
```

---

## 🧭 جدول دستورات اسلش (Slash Commands)

| دستور | میانبر | توضیحات |
|---|---|---|
| `/compare` | `/cmp`, `/arena` | **میدان مقایسه**: مقایسه رو‌در‌روی دو یا چند مدل با جدول قهرمانان سرعت |
| `/stress` | `/load`, `/concurrency` | **تست استرس**: آزمون لود همزمان، لیمیت نرخ و محاسبه ظرفیت کل |
| `/export` | `/exp` | **خروجی تله‌متری**: ذخیره به فرمت‌های HTML داشبورد، Markdown، CSV یا JSON |
| `/history` | `/h` | **تاریخچه**: مرور دورهای بنچمارک قبلی و گزارش‌های ذخیره‌شده |
| `/presets` | `/pre` | **پریست‌های آماده**: اتصال سریع به Groq، Cerebras، OpenRouter، DeepSeek و غیره |
| `/quick` | `/scan`, `/fetch` | **اسکن سریع**: ورود مستقیم اندپوینت و بررسی آنی سلامت مدل‌ها |
| `/test` | `/eval`, `/qbench` | **بنچمارک سریع**: انتخاب مدل با کلیدهای جهت‌نما و تست سرعت |
| `/start` | `1` | باز کردن منوی اصلی ابزار برای پروفایل فعال فعلی |
| `/models` | `m` | واکشی کاتالوگ مدل‌ها و نمایش جدول وضعیت سلامت |
| `/bench` | `b` | اجرای بنچمارک آماری با محاسبه صدک‌ها و نمره پایداری |
| `/stream` | `s` | تست تعاملی چت و نمایش زنده استریم توکن‌ها و توکن‌های تفکر |
| `/config` | `c` | پیکربندی یا تغییر اندپوینت، کلید API و مشخصات پروفایل |
| `/profiles` | `p` | جابجایی و مدیریت پروفایل‌های ذخیره‌شده |
| `/clear` | `cls` | پاک کردن صفحه ترمینال |
| `/back` | `0, ..` | بازگشت به منوی قبلی |
| `/exit` | `2, q` | خروج از برنامه |

---

## 📊 گزارش تله‌متری و خروجی‌ها

### نمونه کارت تله‌متری در ترمینال
```
┌────────────────────────────────── ⚡ Benchmark Telemetry: gpt-4o ⚡ ──────────────────────────────────┐
│                                                                                                       │
│  ┌───────────────────────────────────┬───────────────────────┬─────────────────────────────────────┐  │
│  │ Metric                            │ Measurement           │ Evaluation / Rating                 │  │
│  ├───────────────────────────────────┼───────────────────────┼─────────────────────────────────────┤  │
│  │ Target Model                      │ gpt-4o                │ ● Operational (HTTP 200)            │  │
│  │ TTFT (Time to First Token)        │ 185.4 ms              │ ⚡ Ultra-Fast (<250ms)              │  │
│  │ Total Response Latency            │ 580.2 ms              │ Streamed in 394.8 ms                │  │
│  │ Token Generation Speed            │ 128.5 tokens/sec      │ ⚡ High Throughput (>80 T/s)        │  │
│  │ Generated Tokens Count            │ 48 tokens             │ ~210 characters                     │  │
│  │ Stability Score                   │ 96.4%                 │ Based on throughput variance        │  │
│  │ Cold Start TTFT                   │ 210.0 ms              │ Initial request latency             │  │
│  │ Warm Avg TTFT                     │ 173.1 ms              │ Warmed connection latency           │  │
│  └───────────────────────────────────┴───────────────────────┴─────────────────────────────────────┘  │
│                                                                                                       │
└───────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### خروجی داشبورد مدرن HTML
با انتخاب خروجی `.html`، یک فایل وب کامل با طراحی تم تاریک، کارت‌های آماری، جداول مقایسه و نشانگرهای رنگی ساخته می‌شود که به‌صورت آفلاین و مستقل در هر سیستمی قابل مشاهده است.

---

## 📁 ساختار فایل‌های پروژه

```
api-test-cli/
├── src/apitestllm/
│   ├── __init__.py
│   ├── __main__.py      # نقطه ورود `python -m apitestllm`
│   ├── _compat.py       # UTF-8 هلپر مشترک
│   ├── cli.py           # حلقه تعاملی REPL، منوها و موتور اجرای غیرتعاملی
│   ├── client.py        # موتور HTTP، تحلیل SSE، بنچمارک آماری، مقایسه و تست استرس
│   ├── config.py        # مدیریت ماندگار پروفایل‌ها، تاریخچه و پریست‌های ابری و محلی
│   ├── exporter.py      # صادرکننده گزارش به فرمت‌های HTML، JSON، CSV و Markdown
│   ├── ui.py            # رابط کاربری با بنر رنگی RGB، جدول مسابقه، کارت‌های تله‌متری
│   ├── palette.py       # موتور انیمیشنی پیش‌نمایش دستورات اسلش و Autocomplete
│   └── picker.py        # انتخاب تعاملی مدل با کلیدهای جهت‌نما و فیلتر زنده
├── tests/
│   └── test_suite.py    # ۲۴ آزمون خودکار واحد و یکپارچه‌سازی آفلاین
├── scripts/
│   ├── export-requirements.sh  # requirements.txt تبدیه pyproject.toml تبدیل
│   └── export_requirements.py  # requirements.txt تبدیه pyproject.toml تبدیل
├── api_test.py          # uv اجرای مستقیم برای سیستم‌های بدون (در صورت وجود uv از `uv run apitestllm` استفاده کنید)
├── run.bat              # لانچر تک‌کلیکه برای سیستم‌عامل ویندوز
├── pyproject.toml
├── uv.lock              # درخت وابستگی قفل‌شده
└── requirements.txt     # وابستگی‌های پروژه
```

---

## 🧪 اجرای آزمون‌ها (Unit Tests)

آزمون‌های خودکار پروژه کاملاً آفلاین بوده و بدون نیاز به کلید یا دسترسی اینترنت اجرا می‌شوند:

```bash
uv sync --group dev
uv run pytest .
```
 هر ۲۴ تست، پیکربندی، محاسبات آماری، پارس SSE، صادرکننده‌ها، رندرهای UI، پارس آرگومان‌ها و آستانه‌های خطای CI را پوشش می‌دهند:

```
24 passed in 0.44s
```

---

## 📄 مجوز (License)

توسعه‌یافته و منتشرشده تحت مجوز GNU General Public License v3.0.
