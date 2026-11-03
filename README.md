<div align="center">

# ⚡️ V2RAY CONFIGS POOL
### پایگاه هوشمند، خودکار و ۴ لایه‌ی کانفیگ‌های تست‌شده و پرسرعت

[![Pipeline](https://github.com/alireza786786/V2RAYCONFIGSPOOL/actions/workflows/pipeline.yml/badge.svg)](https://github.com/alireza786786/V2RAYCONFIGSPOOL/actions)
![Update Cycle](https://img.shields.io/badge/Update-Every%2045%20Mins-blue?style=flat&logo=clock)
![Dual Engine](https://img.shields.io/badge/Engines-Xray%20%7C%20Sing--box-success?style=flat&logo=buffer)
![Routing](https://img.shields.io/badge/Iran%20Traffic-DIRECT-brightgreen?style=flat)

<p align="center">
  <b>غربالگری ۴ مرحله‌ای • تست ترافیک واقعی (HTTP 204) • هدایت مستقیم ترافیک داخلی ایران</b>
</p>

---

</div>

## 📌 لینک‌های اشتراک مستقیم (Subscription Links)

تمامی لینک‌ها به‌صورت خودکار هر **۴۵ دقیقه** با آزمون ترافیک واقعی لایه انتقال (Dual Engine: Xray + Sing-box) بروزرسانی و منتشر می‌شوند. تمام لینک‌ها مجهز به الگوی نام‌گذاری تمیز برندینگ (`#V2Pool-...`) هستند.

### 🔗 جدول اشتراک‌ها (Plain Text & Base64)

| رده کیفی | نوع محتوا و ویژگی | لینک اشتراک متن خام (Text) | لینک اشتراک Base64 |
| :--- | :--- | :--- | :--- |
| 🥇 **رده طلا (Gold)** | کمترین تأخیر، پروتکل‌های پیشرفته و بالاترین پایداری | [لینک اشتراک طلا](https://raw.githubusercontent.com/alireza786786/V2RAYCONFIGSPOOL/main/gold.txt) | [لینک اشتراک Base64](https://raw.githubusercontent.com/alireza786786/V2RAYCONFIGSPOOL/main/gold.b64) |
| 🥈 **رده نقره (Silver)** | گره‌های پرسرعت، متعادل و باکیفیت بالا | [لینک اشتراک نقره](https://raw.githubusercontent.com/alireza786786/V2RAYCONFIGSPOOL/main/silver.txt) | [لینک اشتراک Base64](https://raw.githubusercontent.com/alireza786786/V2RAYCONFIGSPOOL/main/silver.b64) |
| 🔰 **پایدار (Validated)** | مجموع تمام کانفیگ‌های سالم با پاسخ قطعی HTTP 204 | [لینک اشتراک پایدار](https://raw.githubusercontent.com/alireza786786/V2RAYCONFIGSPOOL/main/validated.txt) | [لینک اشتراک Base64](https://raw.githubusercontent.com/alireza786786/V2RAYCONFIGSPOOL/main/validated.b64) |
| 🌐 **کل مخزن (All Unique)** | کل کانفیگ‌های نرمال‌سازی و یکتاسازی‌شده مخزن | [لینک اشتراک جامع](https://raw.githubusercontent.com/alireza786786/V2RAYCONFIGSPOOL/main/all.txt) | [لینک اشتراک Base64](https://raw.githubusercontent.com/alireza786786/V2RAYCONFIGSPOOL/main/all.b64) |

---

### 📱 کانفیگ‌های آماده کلاینت‌ها (Client Profiles)

این فایل‌ها دارای **قوانین داخلی مسیریابی ایران (DIRECT)** هستند؛ ترافیک سایت‌های بانکی و دامنه‌های `.ir` بدون عبور از فیلترشکن و با نهایت سرعت باز می‌شوند.

* 🔹 **کلش متا / میهومو (Clash Verge / Mihomo):**
  https://raw.githubusercontent.com/alireza786786/V2RAYCONFIGSPOOL/main/clash.yaml

* 🔹 **سینگ‌باکس (Sing-box / SFA / SFI):**
  https://raw.githubusercontent.com/alireza786786/V2RAYCONFIGSPOOL/main/singbox.json

---

## ⚙️ ویژگی‌های برجسته فنی (Architecture)

1. **اعتبارسنجی ترافیک واقعی (L3 Real Traffic Validation):**  
   برخلاف پینگ‌های جعلی مرسوم (TCP/ICMP Ping)، تمامی کانفیگ‌ها داخل پورت لوکال رانر به صورت تک‌به‌تک بوت شده و دریافت پاسخ قطعی `HTTP 204` سنجیده می‌شود.

2. **الگوی نام‌گذاری یکدست و ایزوله (Branded Remarks):**  
   تمام تگ‌های تبلیغاتی سورس‌ها حذف شده و برچسب‌های استاندارد با پینگ واقعی درج می‌شوند:
   `#V2Pool-GOLD-<ms>ms` • `#V2Pool-SILVER-<ms>ms` • `#V2Pool-<ms>ms`

3. **تفکیک صحیح لایه شبکه (Fix VMess Net/Type):**  
   رفع کامل باگ هم‌پوشانی متغیر هدر با نوع شبکه در VMess و فعال‌سازی صحیح بستر WebSocket و gRPC در تمامی خروجی‌ها.

4. **دروازه عقلانی (Sanity Gate):**  
   مخزن مجهز به سیستم دفاع در برابر نوسان شبکه رانر است؛ در صورت اختلال اینترنت سرور تست، فایل‌های خروجی هرگز خالی نخواهند شد.

5. **پروتکل‌های تحت پوشش:**  
   `VLESS (Reality / TLS)` • `VMess (WS / gRPC)` • `Trojan` • `Hysteria2` • `TUIC` • `Shadowsocks`

---

## 📖 راهنمای اتصال سریع در نرم‌افزارها

1. لینک اشتراک مورد نظر (پیشنهاد: **رده طلا یا نقره**) را کپی کنید.
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
