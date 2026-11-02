<div align="center">

# ⚡️ V2RAY CONFIGS POOL
### پایگاه هوشمند و خودکار کانفیگ‌های تست‌شده و پرسرعت

[![Pipeline](https://github.com/alireza786786/V2RAYCONFIGSPOOL/actions/workflows/pipeline.yml/badge.svg)](https://github.com/alireza786786/V2RAYCONFIGSPOOL/actions)
![Update Cycle](https://img.shields.io/badge/Update-Every%2045%20Mins-blue?style=flat&logo=clock)
![Dual Engine](https://img.shields.io/badge/Engines-Xray%20%7C%20Sing--box-success?style=flat&logo=buffer)
![Routing](https://img.shields.io/badge/Iran%20Traffic-DIRECT-brightgreen?style=flat)

<p align="center">
  <b>غربالگری ۴ مرحله‌ای • تست ترافیک واقعی (HTTP 204) • هدایت مستقیم ترافیک داخلی ایران</b>
</p>

---

</div>

## 📌 لینک‌های اشتراک (Subscription Links)

تمامی لینک‌ها به‌صورت خودکار هر **۴۵ دقیقه** با تست ترافیک واقعی لایه انتقال (Dual Engine) بروزرسانی و منتشر می‌شوند.

### 🔗 اشتراک‌های مستقیم (Plain Text & Base64)

| رده | نوع محتوا | لینک اشتراک متن خام (Text) | لینک اشتراک Base64 |
| :--- | :--- | :--- | :--- |
| 🥇 **رده طلا (Gold)** | پرسرعت‌ترین و پایدارترین کانفیگ‌ها | [لینک اشتراک](https://raw.githubusercontent.com/alireza786786/V2RAYCONFIGSPOOL/main/gold.txt) | [لینک اشتراک](https://raw.githubusercontent.com/alireza786786/V2RAYCONFIGSPOOL/main/gold.b64) |
| ✅ **تأییدشده (Validated)** | تمام گره‌های سالم تست‌شده با ترافیک واقعی | [لینک اشتراک](https://raw.githubusercontent.com/alireza786786/V2RAYCONFIGSPOOL/main/validated.txt) | [لینک اشتراک](https://raw.githubusercontent.com/alireza786786/V2RAYCONFIGSPOOL/main/validated.b64) |
| 🌐 **کل مخزن (All Unique)** | کل کانفیگ‌های نرمال‌سازی و یکتاسازی‌شده | [لینک اشتراک](https://raw.githubusercontent.com/alireza786786/V2RAYCONFIGSPOOL/main/all.txt) | [لینک اشتراک](https://raw.githubusercontent.com/alireza786786/V2RAYCONFIGSPOOL/main/all.b64) |

---

### 📱 کانفیگ‌های آماده کلاینت‌ها (Client Profiles)

این فایل‌ها دارای **قوانین داخلی مسیریابی ایران (DIRECT)** هستند؛ ترافیک سایت‌های بانکی و دامنه‌های `.ir` بدون عبور از پروکسی و با سرعت حداکثری باز می‌شوند.

* 🔹 **کلش متا / میهومو (Clash Verge / Mihomo):**
  https://raw.githubusercontent.com/alireza786786/V2RAYCONFIGSPOOL/main/clash.yaml

* 🔹 **سینگ‌باکس (Sing-box / SFA / SFI):**
  https://raw.githubusercontent.com/alireza786786/V2RAYCONFIGSPOOL/main/singbox.json

---

## ⚙️ ویژگی‌های برجسته فنی (Architecture)

1. **اعتبارسنجی ترافیک واقعی (L3 Real Traffic Validation):**  
   برخلاف سیستم‌های سنتی که صرفاً پینگ TCP یا ICMP جعلی می‌گیرند، این خط لوله تمامی کانفیگ‌ها را از طریق پورت لوکال با هسته‌های رسمی **Xray-core** و **Sing-box** بوت کرده و دریافت پاسخ قطعی `HTTP 204` را بررسی می‌کند.

2. **تفکیک صحیح لایه شبکه (Fix VMess Net/Type):**  
   با برطرف کردن خطای منطقی خواندن هدرها، لایه‌های انتقال پیشرفته مانند WebSocket و gRPC بدون خطا شناسایی و به کلاینت منتقل می‌شوند.

3. **دروازه عقلانی (Sanity Gate):**  
   سیستم مجهز به سپر دفاعی پایداری است؛ در صورت اختلال در سرور رانر گیت‌هاب، خروجی‌های سالم قبلی پاک نمی‌شوند و اشتراک کاربران هرگز خالی نخواهد شد.

4. **پروتکل‌های تحت پوشش:**  
   `VLESS (Reality / TLS)` • `VMess (WS / gRPC)` • `Trojan` • `Hysteria2` • `TUIC` • `Shadowsocks`

---

## 📖 راهنمای اتصال سریع در نرم‌افزارها

1. لینک اشتراک مورد نظر (پیشنهاد: **رده طلا**) را کپی کنید.
2. در نرم‌افزار خود وارد بخش اشتراک‌ها (Subscriptions) شوید:
   * **v2rayNG / Streisand / NekoBox:** دکمه `+` ➔ گزینه `Import from Clipboard` یا `Add Subscription`.
   * **Hiddify:** دکمه `New Profile` ➔ جای‌گذاری لینک اشتراک.
   * **Clash Verge Rev:** بخش `Profiles` ➔ جای‌گذاری لینک `clash.yaml` و کلیک روی `Import`.
3. اشتراک را بروزرسانی کرده و متصل شوید.

---

<div align="center">

**توسعه‌یافته بر پایه استاندارد جهانی Goodbaye**  
*هدف این پروژه تسهیل دسترسی آزاد به جریان اطلاعات و اینترنت آزاد است.*

</div>
