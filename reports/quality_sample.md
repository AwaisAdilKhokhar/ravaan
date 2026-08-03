# Stage 5 quality filter — 200-sample manual validation

PRD §6.3.5 requires the quality rules to be validated against 200 manually inspected random samples. This is that sample.

- Filter: `quality` v1, config fingerprint `57790136526b`
- Documents: 200 (100 uniform, 100 rejection-stratified)

## How to mark this up

For each document, fill in `**verdict:**` with one of:

- `keep` — this is text worth training a language model on.
- `drop` — this is boilerplate, junk, the wrong language, or otherwise not worth it.
- `?` — genuinely cannot tell. Abstaining is a real answer; guessing is not.

Judge the **document**, not the filter. The filter's own verdict is shown so that disagreements can be found afterwards, but it is not a hint — the whole point is to catch the cases where it is wrong. `**note:**` is free text and is preserved.

The two strata are scored separately and must never be pooled: the `uniform` documents are a random sample of the source, the `rejected` ones are an oversample of what the filter drops so that each rule has enough documents to measure.

Then run `python scripts/quality_sample.py score <this file>`.

---

### 1 · urdu-wikipedia:1099574

- **filter:** REJECT — repetition:dup_5gram
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 857 chars, 161 words, 13 lines
- **script:** ratio 0.997 (arabic 0.997, latin 0.003)
- **repetition:** dup_line 0.000, top-ngram 0.106, dup-ngram 0.406
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=6
- **url:** https://ur.wikipedia.org/wiki/%D8%B3%D9%85%DB%8C%D8%B9%20%D8%A7%D9%84%D9%84%DB%81%20%D8%AE%D8%A7%D9%86%20%28%D8%B3%DB%8C%D8%A7%D8%B3%D8%AA%D8%AF%D8%A7%D9%86%29

```text
سمیع اللہ خان ،ایک پاکستانی سیاست دان ہیں جو اگست 2018 سے جنوری 2023 تک پنجاب کی صوبائی اسمبلی کے رکن رہے۔

ابتدائی زندگی اور تعلیم
سمیع اللہ خان 17 اکتوبر 1960 کو لاہور، پاکستان میں پیدا ہوئے۔ انہوں نے 1999 میں گریجویشن کیا اور پنجاب یونیورسٹی سے بیچلر آف آرٹس کی ڈگری حاصل کی۔

سیاسی کیریئر
سمیع اللہ خان 2002 کے پاکستانی عام انتخابات میں حلقہ پی پی 144 (لاہور-I) سے پاکستان پیپلز پارٹی کے امیدوار کے طور پر پنجاب کی صوبائی اسمبلی کے لیے منتخب ہوئے۔ وہ 2018 کے پاکستانی عام انتخابات میں حلقہ پی پی 144 (لاہور-I) سے پاکستان مسلم لیگ (ن) کے امیدوار کے طور پر پنجاب کی صوبائی اسمبلی کے لیے دوبارہ منتخب ہوئے۔

حوالہ جات

1960ء کی پیدائشیں
لاہور کے سیاست دان
پاکستان مسلم لیگ (ن) کے ارکان صوبائی اسمبلی (پنجاب)
پاکستان پیپلزپارٹی کے ارکان صوبائی اسمبلی (پنجاب)
پنجاب ارکان صوبائی اسمبلی 2018ء تا 2023ء
پنجاب ارکان صوبائی اسمبلی 2002ء تا 2007ء
بقید حیات شخصیات
```

**verdict:** keep
**note:** clean politician biography; repetition is the recurring name plus standard biographical formulae and the category footer

---

### 2 · fineweb2-urd_Arab:<urn:uuid:aa241bbe-c65c-40b6-858a-b44d70ccacb6>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 1776 chars, 358 words, 3 lines *(excerpt shows first 1500)*
- **script:** ratio 0.628 (arabic 0.628, latin 0.372)
- **repetition:** dup_line 0.000, top-ngram 0.043, dup-ngram 0.134
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://kfoods.com/daily-tips/bister-ki-chadar-ke-nechy-sabun-rakhne-ke-fayde_tid3742

```text
بستر کی چادر کے نیچے صابن رکھنے سے کیا ہوتا ہے؟ عام سی چیز کا ایسا فائدہ کے آپ بھی یہ کرنے پر مجبور ہوجائیں گےکیا آپ نے کبھی لیٹے لیٹے اپنے پاؤں ہلائے ہیں؟ اکثر لوگ اس عادت میں مبتلا ہوتے ہیں اور بستر پہ لیٹتے ہوئے غیر ارادی طور پت اپنے پیر ہلانے لگتے ہیں۔ یہ بات جتنی معمولی لگتی ہے اکثر اتنی معمولی نہیں ہوتی۔ آج کے آرٹیکل میں ہم جانیں گے کہ یہ کیفیت دراصل کیا ہوتی ہے۔ریسٹ لیس لیگ سینڈرومریسٹ لیس لیگ سینڈروم یعنی بے آرام ٹانگیں ایک ایسی بیماری ہے جس کا تعلق انسانی دماغ سے ہے جس میں اعصاب جسم کی حرکت کو قابو نہیں کرپاتے۔ یہ کیفیت 40 سال کی عمر کے بعد زیادہ لوگوں میں پائی جاتی ہے۔ ریسٹ لیس لیگ سینڈروم میں سونے سے پہلے، بیٹھئے بے چینی میں ٹانگیں ہلانا، پیروں میں بے چینی اور سنسناہت کا احساس ہوتا ہے۔بستر کی چادر کے نیچے صابنماہرین کے مطابق اس کیفیت سے نجات کا کوئی حتمی طریقہ تو موجود نہیں البتہ ورزش، چائے یا کافی سے پرہیز اور پیروں پر مالش سے اس سے کسی حد آرام مل جاتا ہے۔ اس کے علاوہ ایک اور طریقہ ہے جس سے انسانی اعصاب کو تقویت اور سکون ملتا ہے وہ یہ کہ لیونڈر صابن کو بستر کی چادر کے نیچے رکھ کر سویا جائے۔ اگرچہ یہ طریقہ سائنس سے تو ثابت شدہ نہیں لیکن لیونڈر کی خوشبو اعصاب کو پرسکون کرتی ہے اور نیند لانے میں مددگار ہوتی ہے۔
In Health Tips and Totkay section you can check Bister Ki Chadar Ke Nechy Sabun Rakhne Ke Fayde in most easiest way. Find Bister Ki Chadar Ke Nechy Sabun Rakhne Ke Fayde in urdu totkay only at kfoods. At this page you can find Bister Ki Chadar Ke Nechy Sabun Rakhne Ke Fayde totka in details also check the relevant totkay in Urdu of Bister Ki Chadar Ke Nechy Sa
```

**verdict:** keep
**note:** Urdu health article; the Latin is site furniture, not a language problem

---

### 3 · fineweb2-urd_Arab:<urn:uuid:ab7c4152-3697-4c73-87f7-7d70a4c178e5>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 533 chars, 109 words, 1 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.049, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** teh_marbuta=3
- **url:** https://quran.com/56:11/tafsirs/tafsir-bayan-ul-quran

```text
آیت 1 1{ اُولٰٓئِکَ الْمُقَرَّبُوْنَ۔ } ”وہی تو بہت مقرب ہوں گے۔“ یعنی تیسرا گروہ مقربین بارگاہ پر مشتمل ہوگا۔ اللہ تعالیٰ انسان کو اپنے قرب سے نوازنا چاہتا ہے اور اس کے لیے قرآن میں جابجا ترغیبی انداز اختیار کیا گیا ہے۔ سورہ المائدہ میں تو امر کے صیغے میں فرمایا گیا : { وَابْتَغُوْٓا اِلَیْہِ الْوَسِیْلَہَ وَجَاھِدُوْا فِیْ سَبِیْلِہٖ } آیت 35 کہ تم اس کا قرب تلاش کرو اور اس کے لیے اس کی راہ میں جہاد کرو۔ ظاہر ہے جو کوئی اللہ کی راہ میں جان و مال کے ساتھ جہاد کے لیے نکلے گا اللہ تعالیٰ اسے ضرور اپنے مقربین میں شامل فرمائیں گے۔
```

**verdict:** keep
**note:** 

---

### 4 · urdu-wikipedia:919701

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 48339 chars, 10299 words, 127 lines *(excerpt shows first 1500)*
- **script:** ratio 0.994 (arabic 0.994, latin 0.006)
- **repetition:** dup_line 0.000, top-ngram 0.007, dup-ngram 0.029
- **url** 0.001 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** teh_marbuta=1, whitespace=404
- **url:** https://ur.wikipedia.org/wiki/%D8%A2%D8%B1%DA%86%DA%88%DB%8C%D9%88%DA%A9%20%D9%81%D8%B1%D8%A7%D9%86%D8%B2%20%D9%81%D8%B1%DA%88%DB%8C%D9%86%DB%8C%D9%86%DA%88%20%DA%A9%D8%A7%20%D9%82%D8%AA%D9%84

```text
آسٹریا کے آرچڈیوک فرانز فرڈیننڈ کا قتل آسٹریا ہنگری کے تخت کے ممکنہ وارث ، اور فرانز فرڈیننڈ کی بیوی سوفی، ڈچیس آف ہوہنبرگ، 28 جون 1914 کو سرائیوومیں اس وقت پیش آیا جب وہ گیریلو پرنسپل کے ہاتھوں جان لیوا زخمی ہوئے تھے۔ پرنسیپ ان چھ قاتلوں کے گروہ میں سے ایک تھا جس میں محمد محمدباشیچ، واسو ابریلووی ، نیلجکو ابرینووی ، سیجیتکو پاپوویش اور ٹرائون گریبی (ایک بوسنیائی اور پانچ سرب ) شامل تھے جنہیں ایک بوسنیائی سرب اور سیاہ ہاتھ خفیہ تنظیم کے رکن دانیلو ایلیچ نے منظم کیا تھا۔ اس قتل کا سیاسی مقصد آسٹریا ہنگری کے جنوبی سلاو صوبوں کو توڑنا تھا تاکہ انہیں یوگوسلاویہ میں جوڑ دیا جاسکے۔ سازشیوں کے مقاصد اس تحریک کے مطابق تھے جو بعد میں ینگ بوسنیا کے نام سے مشہور ہوئے۔ یہ قتل پہلی جنگ عظیم سے براہ راست اس وقت ہوا جب آسٹریا ہنگری نے بعد میں سربیا کی بادشاہت کا الٹی میٹم جاری کیا ، جسے جزوی طور پر مسترد کردیا گیا۔ اس کے بعد آسٹریا-ہنگری نے سربیا کے خلاف جنگ کا اعلان کیا جس کی وجہ سے بیشتر یورپی ریاستوں کے مابین جنگ کا آغاز ہوا۔

سربیا کی فوجی سازش کا اہتمام میجر ووئیسلاو ٹانکوسیچ اور جاسوس راد مالوبابیچ کی مدد سے سربیا کی فوجی انٹلیجنس کے چیف ڈریگوتن دیمتریجیویچ نے کیا تھا۔ تنکوسیچ نے قاتلوں کو بموں اور پستولوں سے مسلح کیا اور انہیں تربیت دی۔ قاتلوں کو محفوظ مکانات اور ایجنٹوں کے اسی خفیہ نیٹ ورک تک رسائی دی گئی تھی جو مالوبابیچ نے آسٹریا ہنگری میں ہتھیاروں اور اس کے کارندوں کی دراندازی کے لئے استعمال کیا تھا۔

قاتلوں ، خفیہ نیٹ ورک کے کلیدی ممبران ، اور سربیا کے کلیدی فوجی سازشی جو ابھی تک زندہ تھے ، انھیں گرفتار کیا گیا ، ان پر مقدمہ چلایا گیا ، انہیں سزا سنائی گئی اور سزا دی گئی۔ جنھیں 
```

**verdict:** keep
**note:** 

---

### 5 · fineweb2-urd_Arab:<urn:uuid:b533d79c-73bb-48bc-8450-77a2dd6a01e0>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 1388 chars, 296 words, 10 lines
- **script:** ratio 0.941 (arabic 0.941, latin 0.059)
- **repetition:** dup_line 0.000, top-ngram 0.043, dup-ngram 0.185
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://www.apnapointtv.com/archives/3212

```text
فرانس کے مونٹ پیلیئر ہوائی اڈے پر ایک کارگو طیارہ لینڈنگ کے دوران پھسل کر جھیل میں جا گرا۔
تفصیلات کے مطابق جنوبی فرانس کے محکمہ ہیرالٹ نے اس واقعے پر ایک بیان جاری کرتے ہوئے کہا کہ طیارے میں سوار تینوں افراد کو کوئی نقصان نہیں پہنچا ہے۔
غیر ملکی میڈیا کے مطابق فرانس کے مونٹ پیلیئر سٹی کے ہوائی اڈے پر ایک بڑا حادثہ پیش آیا، لینڈنگ کے دوران ایک کارگو طیارہ رن وے سے باہر نکل گیا اور رن وے کے قریب جھیل میں آدھا ڈوب گیا۔
اس حادثے کے بعد ہوائی اڈے کو مسافروں اور کارگو پروازوں کے لیے بند کر دیا گیا۔ اس دوران طیارے کا اگلا حصہ تقریباً آدھا پانی میں چلا گیا۔
ریسکیو ذرائع کا کہنا ہے کہ کارگو جہاز کا ایک انجن بھی پانی میں ڈوب گیا۔ فی الحال اسے نکالنے کی کوشش ی جارہی ہے۔
بتایا جا رہا ہے کہ کارگو جہاز بوئنگ 737 نے پیرس کے چارلس ڈی گال ہوائی اڈے سے مونٹ پیلیئر کے لیے اڑان بھری تھی۔ اس دوران مونٹ پیلیئر ایئرپورٹ پر لینڈنگ کے دوران طیارہ رن وے سے آگے نکل گیا اور قریبی جھیل میں ڈوب گیا۔ طیارے میں سوار تینوں افراد کو بچا لیا گیا ہے۔
حادثہ کیوں اور کیسے ہوا ابھی تک معلوم نہیں ہو سکا، جنوبی فرانس کے محکمہ ہیرالٹ نے اس واقعے پر ایک بیان جاری کیا۔ اس میں کہا گیا ہے کہ طیارے میں سوار تینوں افراد کو کوئی نقصان نہیں پہنچا ہے۔
ہوائی اڈے کے بند ہونے سے متاثر ہونے والی ایئر لائنز ٹرانساویا فرانس، ایزی جیٹ، ایئر فرانس، لکسیر، کے ایل ایم اور وولوٹیا ہیں۔ اتوار کے دن بھی ہوائی اڈہ صبح 12 فلائٹس کو منسوخ کر دیا گیا تھا۔
How to Claim the Most Benefit Out of your Wibe Auto Insurance
Leave a Comment
```

**verdict:** keep
**note:** 

---

### 6 · urdu-wikipedia:903508

- **filter:** REJECT — too_short
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 198 chars, 36 words, 7 lines
- **script:** ratio 0.755 (arabic 0.755, latin 0.245)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://ur.wikipedia.org/wiki/%DB%8C%D9%88%D9%B9%DB%8C%D9%88%D8%A8%20%D9%BE%D8%B1%20%D8%B3%D8%A8%20%D8%B3%DB%92%20%D8%B2%DB%8C%D8%A7%D8%AF%DB%81%20%D8%AF%DB%8C%DA%A9%DA%BE%DB%8C%20%D8%AC%D8%A7%D9%86%DB%92%20%D9%88%D8%A7%D9%84%DB%8C%20%D9%88%DB%8C%DA%88%DB%8C%D9%88%D8%B2%20%DA%A9%DB%8C%20%D9%81%DB%81%D8%B1%D8%B3%D8%AA

```text
اس فہرست میں یوٹیوب پر سب سے زیادہ دیکھی جانے والی ویڈیوز کو شامل کیا گیا ہے۔

فہرست

حوالہ جات

اکیسویں صدی سے متعلقہ فہرستیں
صفحات مع گراف
یوٹیوب ویڈیو
Short description is different from Wikidata
```

**verdict:** drop
**note:** list stub: headers and a maintenance category, no body

---

### 7 · fineweb2-urd_Arab:<urn:uuid:92d84416-6901-4172-9f0b-ca6718d4602e>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 603 chars, 110 words, 9 lines
- **script:** ratio 0.712 (arabic 0.712, latin 0.187)
- **repetition:** dup_line 0.000, top-ngram 0.050, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** alef=1, teh_marbuta=1, yeh=1
- **url:** https://www.khaleejurdu.com/uae-news/abu-dhabi-170-motorists-fined-dh1000-each-for-littering/

```text
خلیج اردو
18 اگست 2021
ابوظبہی : ابوظبہی پولیس نے 170 ڈرائیوروں کو سڑک اور عوامی مقامات پر کچرا پھینکنے کے الزام میں ہر ایک کو 1000 درہم جرمانہ کیا ہے۔
متحدہ عرب امارات کے دارلحکومت کے ٹریفک قوانین کے مطابق گاڑی چلاتے ہوئے سڑک پر کچرا پھینکنے پر ایک ہزار درہم کا جرمانہ اور ڈرائونگ لائنسس میں چھ سیاہ پوائنٹس لگائے جائیں گے۔
Abu Dhabi Police fine 170 motorists for littering on roads
വാഹനത്തിൽ നിന്നും റോഡിൽ മാലിന്യം തള്ളിയതിന് 170 ഡ്രൈവർമാർക്ക് അബുദാബി പോലീസ് പിഴ ചുമത്തി
— شرطہ ابوظبی (@ADPoliceHQ) August 18, 2021
پولیس نے رہائشیوں سے اپیل کی ہے کہ وہ کچرا مختص جگہ پر پھینکیں۔
Source : Khaleej Times
```

**verdict:** keep
**note:** 

---

### 8 · fineweb2-urd_Arab:<urn:uuid:87fdec5d-78ee-44ba-872d-a997c51d3ef9>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 1174 chars, 230 words, 4 lines
- **script:** ratio 0.996 (arabic 0.996, latin 0.004)
- **repetition:** dup_line 0.000, top-ngram 0.044, dup-ngram 0.153
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://www.minhaj.org/urdu/tid/16757/%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD-%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD-%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD-%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD-%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD-%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD-%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD-%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD-%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD-%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD-%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD-%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD-%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD.html

```text
کالج آف شریعہ اینڈ اسلامک سائنسز کے زیر اہتمام محفل ذکر سرور کونین
کالج آف شریعہ اینڈ اسلامک سائنسز بی ایس VIII کے طلباء کے زیراہتمام 12 مارچ 2012 کو بعد ازنماز عشاء مرکزی صفہ ہال میں ’’محفل ذکر سرور کونین‘‘ منعقد ہوئی۔ جس کی صدارت وائس پرنسپل کالج آف شریعہ ڈاکٹر محمد اصغر جاوید الازہری نے کی۔ مہمانان گرامی میں رانا محمد اکرم قادری، محمد صابر نقشبندی، ظفر اقبال، مراد علی دانش، حامد الازہری، اشیاق الازہری اور صاحبزادہ مقصود احمد نوشاہی شامل تھے۔
پروگرام کا آغاز قاری اللہ بخش نقشبندی نے تلاوت کلام پاک سے کیا۔ اس کے بعد حافظ نعمان قادری، سید عبدالرؤف بخاری، سید بلال حسین اور محمد آصف چشتی نے نبی رحمت حضور صلی اللہ علیہ وآلہ وسلم کی بارگاہ اقدس میں اپنے لحن داؤدی سے گلہائے عقیدت نچھاور کیے۔ محفل میں نقابت کے فرائض ملک عرفان قادری نے سرانجام دیے۔
پروگرام کے اختتام پر صدر محفل وائس پرنسپل کالج آف شریعہ ڈاکٹر محمد اصغر جاوید الازہری نے تمام امت مسلمہ کی امن وآشتی اور شیخ الاسلام ڈاکٹر محمد طاہرالقادری کی صحت وسلامتی، ان کی درازی عمر اور طلباء کے علم و عمل میں برکتوں کے لیے خصوصی دعا کی۔ انہوں نے طلباء کے ذوق و محبت کو سراہتے ہوئے انہیں مبارکباد پیش کی جبکہ تمام مہمانان گرامی کا شکریہ ادا کیا اور بعدازاں جملہ طلباء اور مہمانان گرامی کے لئے ضیافت کا اہتمام کیا گیا۔
```

**verdict:** keep
**note:** 

---

### 9 · urdu-wikipedia:618016

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 503 chars, 79 words, 14 lines
- **script:** ratio 0.481 (arabic 0.481, latin 0.519)
- **repetition:** dup_line 0.000, top-ngram 0.024, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=5
- **url:** https://ur.wikipedia.org/wiki/%D9%84%D9%88%D9%BE%D8%A7%D9%86%DA%AF%20%DB%81%DB%8C%D9%86%DB%8C%D8%B1%D8%A7%D9%86%DA%AF

```text
لوپانگ ہینیرانگ (؛ انگریزی: Chosen Land؛ ہسپانوی: Patria Adorada)) فلپائن کا قومی ترانہ ہے۔

شاعری

تاریخی ترجمے

بیرونی روابط
The Philippines: Lupang Hinirang – Audio of the national anthem of the Philippines, with information and lyrics
Philippine studies – Historical notes: The Philippine National Anthem
Philippine–American war – Arnaldo Dumindin

حوالہ جات

ایشیائی ترانے
فلپائن کی قومی علامات
فلپائنی نغمے
قومی ترانے
کامنز زمرہ جس کا ربط ویکی ڈیٹا پر ہے
ویکی ڈیٹا سے مطابقت رکھنے والی مختصر تفصیل
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 10 · urdu-wikipedia:892083

- **filter:** REJECT — html_residue
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 1436 chars, 298 words, 8 lines
- **script:** ratio 0.903 (arabic 0.903, latin 0.097)
- **repetition:** dup_line 0.000, top-ngram 0.039, dup-ngram 0.089
- **url** 0.000 · **html** 0.070 · **U+FFFD** 0.00000
- **stage 4:** whitespace=3
- **url:** https://ur.wikipedia.org/wiki/%D8%AF%D8%B1%DB%8C%D8%A7%D8%A6%DB%92%20%D8%BA%D9%88%D8%B1%D8%A8%D9%86%D8%AF

```text
دریائے غوربند افغانستان کا ایک دریا ہے جو صوبہ پروان سے ہوتا ہوا گزرتا ہے ۔ یہ دریائے پنجشیر کی ایک معاون دریا ہے ، پھر دریائے سندھ کا ذیلی معاون ، پھر دریائے کابل کا ۔

غوربند مکمل طور پر صوبہ پروان میں بہتا ہے ، جہاں اس نے اپنا نام ضلع گوربند کو دیا۔ یہ مشرقی شببر پاس (جو پروان اور بامیان کے صوبوں یا غوربند اور دریائے قندوز کے آبی بہاوؤں کو جوڑتا ہے) میں پیدا ہوا ہے اور یہ مشرق کی سمت میں گزرتا ہے جو اسے اپنے بیشتر حصے میں برقرار رکھتا ہے۔ یہ جنوب کے ساتھ ساتھ بہتا ہے اور ہندوکش کے مسلط وسطی سلسلے کو ، سالنگ کے شببر پاس علاقے میں پگھلا ہوا ملتا ہے۔ یہ اس سے جنوب کی طرف ہندوکش (شمال) اور کوہ بابا کے اعلی سلسلے کے درمیان ایک لمبی وادی میں بہتا ہے۔ اس کے بعد یا اپنے دائیں کنارے پر مشرق میں چاریکر سے 10 کلومیٹر کے فاصلے پر دریائے پنج چیر ساتھ ملتا ہے۔ یہ شیخ علی ، چنواری ، غوربند اور سورکھ پارسا کے اضلاع میں بہتا ہے۔

گوربند میں بائیں اور دائیں دونوں طرف سے بہت سے معاون دریا ملتے ہیں ، یہ سب بنیادی طور پر موسم بہار اور گرمیوں میں برف پگھلنے سے بہتے ہیں۔ اس کا اہم معاون دریا ، دریائے ترکمان ہے لیکن دریائے سالانگ بائیں کنارے سے ملتا ہے اور اس کی وادی گزرنے اور ملک کے شمالی آدھے حصے تک جانے کا ایک اہم راستہ ہے۔ جبل سراج کے مقام پر دریائے سالانگ ، دریائے غوربند کے ساتھ ملتا ہے۔

حوالہ جات

بیرونی روابط

صوبہ پروان کا نقشہ [ <span title="Dead link since January 2017">مستقل مردہ لنک</span> ][ <span title="Dead link since January 2017">مستقل مردہ لنک</span> ]

افغانستان کے دریا
Short description is different from Wikidata
```

**verdict:** keep
**note:** 

---

### 11 · urdu-wikipedia:396832

- **filter:** REJECT — too_short, html_residue
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** code_switched
- **size:** 98 chars, 14 words, 6 lines
- **script:** ratio 1.000 (arabic 0.377, latin 0.623)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.112 · **U+FFFD** 0.00000
- **stage 4:** whitespace=3
- **url:** https://ur.wikipedia.org/wiki/2035%D8%A1

```text
دسمبر

<noinclude>

2035ء
مستقبل کے خط زمانی
ہزارسالہ
Short description is different from Wikidata
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 12 · urdu-wikipedia:16251

- **filter:** REJECT — repetition:top_4gram, repetition:dup_5gram, repetition:dup_6gram
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 1209 chars, 244 words, 33 lines
- **script:** ratio 0.953 (arabic 0.953, latin 0.048)
- **repetition:** dup_line 0.000, top-ngram 0.337, dup-ngram 0.512
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=31
- **url:** https://ur.wikipedia.org/wiki/18%20%28%D8%B6%D8%AF%20%D8%A7%D8%A8%DB%81%D8%A7%D9%85%29

```text
18 ق م، قبل مسیح کا سال
18ء، عیسوی تقویم کا سال
18ھ، ہجری تقویم کا سال
18 (عدد)، قدرتی عدد جو 17 سے بڑا اور 19 سے چھوٹا ہے۔
18 جنوری، پہلے شمسی مہینے کی 18 تاریخ
18 فروری، دوسرے شمسی مہینے کی 18 تاریخ
18 مارچ، تیسرے شمسی مہینے کی 18 تاریخ
18 اپریل، چوتھے شمسی مہینے کی 18 تاریخ
18 مئی، پانچویں شمسی مہینے کی 18 تاریخ
18 جون، چھٹے شمسی مہینے کی 18 تاریخ
18 جولائی، ساتویں شمسی مہینے کی 18 تاریخ
18 اگست، آٹھویں شمسی مہینے کی 18 تاریخ
18 ستمبر، نویں شمسی مہینے کی 18 تاریخ
18 اکتوبر، دسویں شمسی مہینے کی 18 تاریخ
18 نومبر، گیارہویں شمسی مہینے کی 18 تاریخ
18 دسمبر، بارہویں شمسی مہینے کی 18 تاریخ
18 محرم، پہلے قمری مہینے کی 18 تاریخ
18 صفر، دوسرے قمری مہینے کی 18 تاریخ
18 ربیع الاول، تیسرے قمری مہینے کی 18 تاریخ
18 ربیع الثانی، چوتھے قمری مہینے کی 18 تاریخ
18 جمادی الاول، پانچویں قمری مہینے کی 18 تاریخ
18 جمادی الثانی، چھٹے قمری مہینے کی 18 تاریخ
18 رجب، ساتویں قمری مہینے کی 18 تاریخ
18 شعبان، آٹھویں قمری مہینے کی 18 تاریخ
18 رمضان، نویں قمری مہینے کی 18 تاریخ
18 شوال، دسویں قمری مہینے کی 18 تاریخ
18 ذوالقعدہ، گیارہویں قمری مہینے کی 18 تاریخ
18 ذوالحجہ، بارہویں قمری مہینے کی 18 تاریخ

مزید دیکھیے
اٹھارہ (ضد اہبام)
اٹھارویں (ضد اہبام)

مبہم اعداد کی فہرستیں
Short description is different from Wikidata
```

**verdict:** drop
**note:** year-index page, pure template list

---

### 13 · urdu-wikipedia:121768

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 236 chars, 48 words, 8 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.102, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=3
- **url:** https://ur.wikipedia.org/wiki/%D8%A7%D8%B4%DA%A9%D9%86%D8%A7%D9%86

```text
اشکنان () ایک شہر ہے جو ایران میں واقع ہے۔ اس کی مجموعی آبادی 7,513 افراد پر مشتمل ہے، یہ صوبہ فارس میں واقع ہے۔

متعلقہ روابط
فہرست ایران کے شہر

حوالہ جات

ایران کے شہر
جغرافیہ شہرستان لامرد کے نامکمل مضامین
صوبہ فارس کے شہر
لر شخصیات
```

**verdict:** drop
**note:** template geo stub: one factual sentence plus navigation footers

---

### 14 · fineweb2-urd_Arab:<urn:uuid:64abf5c2-31ed-4bdf-972f-bda61c9f991c>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 13763 chars, 2631 words, 23 lines *(excerpt shows first 1500)*
- **script:** ratio 0.698 (arabic 0.698, latin 0.302)
- **repetition:** dup_line 0.002, top-ngram 0.008, dup-ngram 0.093
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** digits=1
- **url:** http://insaf.pk/news/khyber-pakhtunkhwa/item/1793226-cm-kpk-talking-to-media-at-hmc

```text
With the compliments of Press Secretary to Chief Minister KP Peshawar
HANDOUT NO. 1 /PESHAWAR/DT: 15-2-2017
Khyber Pakhtunkhwa Chief Minister Pervez Khattak has directed for the management, security and safety of Swat Motorway including security in the proposed industrial cities in Khyber Pakhtunkhwa. The provincial government would raise a force of 2600 personnel for the security and safety of CPEC related projects and routes. He directed to negotiate with NHA for the management and road safety mechanism for the Swat Motorway that the provincial government was constructing out of its own resources. He also okayed a special coordination unit for the CPEC that would integrate the entire CPEC related activities in the province. He was also for the merger of FATA into Khyber Pakhtunkhwa adding that extension of existing laws and system was the best solution at the moment.
These remarks he made during a comprehensive meeting of the provincial Home Department that focused on the raising of a full security and safety force for comprehensive security cover to the CPEC related activities and the proposed merger of FATA into Khyber Pakhtunkhwa and the futuristic look of the province after the merger of FATA into the province.
Advisor to Chief Minister on C&W Akbar Ayub, administrative secretaries of concerned departments, MD KPHA and other attended the meeting.
Chief Minister directed the meeting to negotiate with the NHA for the road management, safety and security of the Swat Motorw
```

**verdict:** drop
**note:** English press handout with a little Urdu

---

### 15 · urdu-wikipedia:121602

- **filter:** REJECT — too_short
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 135 chars, 22 words, 7 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.207, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=4
- **url:** https://ur.wikipedia.org/wiki/%D8%A7%DB%8C%D9%86%D8%A7%20%D8%A7%D9%88%DB%81%D9%88%D8%B1%D8%A7

```text
اینا اوہورا ایک فحش اداکارہ ہے۔

متعلقہ روابط
فہرست فحش اداکارائیں

حوالہ جات

1980ء کی پیدائشیں
بقید حیات شخصیات
جاپانی فحش اداکارائیں
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 16 · fineweb2-urd_Arab:<urn:uuid:cf145205-83cf-495b-9911-020f15852296>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 388 chars, 77 words, 5 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.046, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://urdu.geo.tv/latest/267310-

```text
23 اکتوبر ، 2021
لاہو ر کےسروسزاسپتال میں ڈینگی کی مریضہ انتقال کرگئی۔
ورثاء نے الزام لگایا ہےکہ اسپتال انتظامیہ نے وینٹی لیٹرمہیا کرنےسےانکارکردیا تھا اس وجہ سے مریضہ کا انتقال ہوا۔
دوسری جانب ایم ایس سروسز اسپتال کا مؤقف ہے کہ وینٹی لیٹرصرف کورونا مریضوں کےلیےہیں۔
واضح رہے کہ رواں سال پنجاب میں ڈینگی وائرس سے اب تک 25 افراد جان سے ہاتھ دھو بیٹھے ہیں جن میں سے 12 کا تعلق لاہور سے ہے ۔
```

**verdict:** keep
**note:** 

---

### 17 · fineweb2-urd_Arab:<urn:uuid:aae4baa0-1267-4dca-9d72-ea874333f244>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 2996 chars, 695 words, 29 lines *(excerpt shows first 1500)*
- **script:** ratio 0.693 (arabic 0.693, latin 0.307)
- **repetition:** dup_line 0.000, top-ngram 0.021, dup-ngram 0.082
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** alef=3, heh=2, kaf=1, yeh=2
- **url:** https://www.naadeali.com/shabe-qadr-ki-tasbeeh-se-har-mushkil-asan-ho/

```text
Shabe Qadr Ki Tasbeeh ” استغفر اللہ ربی من کل ذنب و اتوب الیہ” Ke Barkat Se Aap Allah Ke Bargha Se Apni Har Mushkil Ka Hal Aur Har Hajat Ke Takmeel Fori Hasil Kar Saktay Hain . Es Tasbeeh Ke Barkat Se Ap Ki Har Dua Qabool Ho Ghe Aur Ap Ke Jan , Aulad , Ghar , Karobar Aur Izat Allah Ke Hifazat Me Bhe Rahen Ghay .
Shabe Qadr Ki Tasbeeh
شب قدر کی تسبیح کی برکت سے آپ اپنی تمام حاجات کو اللہ کی بارگاہ سے رمضان شریف کے اختتام سے پہلے پہلے حاصل کر سکتے ہیں . ناظرین شب قدر کی تسبیح آپ کی تمام مشکلات کا حل ، تمام حاجات کی تکمیل اور زندگی کے ہر میدان میں کامیابی ہے ۔ اس تسبیح کی برکت سے آپ کو اللہ کی غیبی مدد حاصل ہو جائے گی جسکی بناء پر آپ کی ہر دعا اللہ کی بارگاہ میں ہمیشہ قبول ہوتی رہے گی ۔ اس تسبیح کے لئے آپ نے شب قدر میں عشاء کی نماز ادا کرنے کے بعد کسی بھی وقت 2 نفل نماز ہدیہ محمد آل محمد اس طرح ادا کرنے ہیں کہ ان دونوں نوافل میں آپ الحمد شریف کے بعد 3 – 3 بار سورہ اخلاص تلاوت کر یں ۔نوافل ادا کرنے کے بعد آپ نے تسبیح کے زریعے 100 مرتبہ
اور 10 مرتبہ درود ابراہیمی محبت سے زکر کریں ۔
اسی طرح آپ نے 12 نوافل ادا کرنے ہیں اور ہر دو نفل ادا کرنے کے بعد آپ نے 100 بار اوپر بیان کی گئی دعا مبارکہ اور 10 بار درود ابراہیمی پڑھنا ہے ۔ اس پورے عمل میں آپ 12 نوافل ، 600 بار پہلے بیان کی گئی دعا مبارکہ اور ساٹھ مرتبہ درود ابراہیمی پڑھ پائیں گے ۔ یہ پورا عمل کرنے کے بعد آپ اللہ کی بارگاہ سے اسکی رضا اور اپنی حاجت طلب کر لیں انشاء اللہ یہ ایک دن کا عمل کرنے سے آپ کو آپ کی تمام حاجات غیب سے حاصل ہونے کے اسباب پیدا ہونا شروع ہو جائیں گے ۔ شب قدر کی یہ تسبیح اللہ کی بارگاہ سے دولت ، رزق ، اچھا رشتہ ،
```

**verdict:** keep
**note:** 

---

### 18 · fineweb2-urd_Arab:<urn:uuid:9879400b-c5d9-4310-b1ec-ac3374c8aca0>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 3807 chars, 809 words, 16 lines *(excerpt shows first 1500)*
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.021, dup-ngram 0.098
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://www.qaumiawaz.com/culture/has-ajay-devgan-became-the-spokesperson-of-bjp-asks-former-chief-ministers-of-karnataka

```text
کیا بالی وڈ اداکار اجے دیوگن بی جے پی کے ترجمان بن گئے ہیں؟
بالی وڈ اداکار اجے دیوگن ہندی کو بھارت کی قومی زبان قرار دینے کے تنازع میں پھنستے جارہے ہیں۔ اب کرناٹک کے دو سابق وزرائے اعلٰی نے بھی دیوگن سے پوچھا ہے کہ کیا وہ بی جے پی کے ترجمان بن گئے ہیں-
بالی وڈ اداکار اجے دیوگن نے ہندی کو بھارت کی قومی زبان قرار دے کر اپنی پریشانیاں بڑھالی ہیں۔ یہ تنازع تھمنے کا نام نہیں لے رہا ہے۔ جنوبی صوبے کرناٹک کے دو سابق وزرائے اعلیٰ بھی اس تنازع میں کود پڑے ہیں اور انہوں نے اجے دیوگن کو مشورہ دیا کہ کوئی اہم بات کہنے سے قبل حقائق کی جانکاری حاصل کرلیا کریں۔
کرناٹک کے دو سابق وزرائے اعلیٰ کانگریس کے سدا رمیا اور جنتا دل (سیکولر) کے ایچ ڈی کماراسوامی نے اجے دیوگن کی سخت نکتہ چینی کی۔ دونوں رہنماؤں نے کہا کہ فلم اداکار کو اس بات کا علم ہونا چاہیے کہ ہندی بھارت کی قومی زبان نہیں ہے۔ کماراسوامی نے زیادہ سخت لہجہ اختیار کرتے ہوئے اجے دیوگن کو حکمران بھارتیہ جنتا پارٹی(بی جے پی) کا ترجمان قرا ردے دیا۔
سابق وزیر اعلی کماراسوامی نے ایک ٹوئٹ کرکے کہا،''ایسا لگتا ہے کہ اجے دیوگن بی جے پی کی ہندی قوم پرستی کے ایک ملک، ایک ٹیکس، ایک زبان اور ایک حکومت کی مہم کے ترجمان بن گئے ہیں۔‘‘ انہوں نے مزید کہا،''ہندی نہ تو کبھی ہماری قومی زبان رہی ہے اور نہ کبھی ہوگی۔ ہمارے ملک کی لسانی تنوع کا احترام کرنا ہر ایک بھارتی شہری کی ذمہ داری ہے۔‘‘
تنازع کیسے شروع ہوا؟
ہندی کے قومی زبان کے حوالے سے تنازع گزشتہ روز اس وقت شروع ہوا جب اجے دیوگن نے کہا کہ ''ہندی ہماری مادری زبان اور قومی زبان ہے اور ہمیشہ رہے گی۔‘‘ انہوں نے یہ بات جنوبی بھارت کے فلموں کے اداکار سدیپ سنجیو، جو سدیپ کے نام سے مشہور ہیں، کے ایک بیان پر اپ
```

**verdict:** keep
**note:** 

---

### 19 · fineweb2-urd_Arab:<urn:uuid:70805ab2-1ced-45f4-8527-db82984d06b2>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 950 chars, 163 words, 22 lines
- **script:** ratio 0.695 (arabic 0.695, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.023, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://global-asp.github.io/storybooks-csl/stories/ur/0342/

```text
ایک دن امی بہت سے پھل لائیں۔
有一天，妈妈买了很多水果。
ہم کچھ پھل کب کھا سکتے ہیں؟ ہم نے پوچھا۔ ہم آج رات کو پھل کھائیں گے۔ امی نے کہا۔
我们都问她：“什么时候可以吃水果？”妈妈说：“等今天晚上再吃。”
میرا بھائی رحیم لالچی ہے۔ وہ سب پھل چکھتا ہے۔ وہ بہت پھل کھاتا ہے۔
我哥哥拉希姆很贪吃，所有的水果都想尝尝。结果他吃了很多。
دیکھو رحیم نے کیا کیا؟ میرا چھوٹا بھائی چلایا۔ رحیم بہت شرارتی اور خود غرض ہے، میں نے کہا۔
弟弟叫着说：“看看拉希姆做了什么！”。我跟着说：“拉希姆很调皮很自私。”
ہم بھی رحیم سے ناراض ہیں لیکن رحیم تھوڑا سا بھی شرمندہ نہیں ہے۔
我们也对拉希姆很生气。可是拉希姆并不感到惭愧。
کیا تم رحیم کو سزا نہیں دے رہے؟ چھوٹے بھائی نے پوچھا۔
小弟弟问：“拉希姆不是该罚了吗？”
ماں نے خبردار کیا ‘رحیم، جلد ہی آپ سے معافی مانگے گا۔’
妈妈警告说：“拉希姆，你很快就会后悔的。”
رحیم بیمار محسوس کرنے لگتا ہے۔
不久，拉希姆果然开始感到恶心起来。
میرے پیٹ میں درد ہے، رحیم چلایا۔
拉希姆小声说：“我肚子很疼。”
امی جانتی تھیں کہ یہ ہو گا۔ پھل رحیم کو سزا دے رہے ہیں۔
妈妈早料到会发生这样的事情。拉希姆受到了水果的惩罚！
بعد میں رحیم نے معافی مانگی۔ میں کبھی دوبارہ لالچ نہیں کروں گا اُس نے وعدہ کیا۔ اور ہم سب نے اُس پر بھروسہ کر لیا۔
后来，拉希姆跟我们道歉说：“以后我再也不会贪吃了。”而我们这次都相信他！
```

**verdict:** drop
**note:** Urdu-Chinese parallel reader; half the document is unusable for this corpus

---

### 20 · fineweb2-urd_Arab:<urn:uuid:b4ad3354-3687-485b-8aef-a8388fa58fc8>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 4864 chars, 1046 words, 28 lines *(excerpt shows first 1500)*
- **script:** ratio 0.997 (arabic 0.997, latin 0.003)
- **repetition:** dup_line 0.000, top-ngram 0.023, dup-ngram 0.112
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://www.khaleejurdu.com/gulf-news/uae-holiday-rush-emirates-prepares-for-busy-travel-week-urges-passengers-to-take-covid-test/

```text
خلیج اردو: اسکول سیزن ختم ہوتے اور چھٹیوں کے موسم کے آغاز کے ساتھ ہی، دبئی میں مقیم ایمریٹس ایئر لائن توقع کر رہی ہے کہ اس مصروف سفری مدت کے دوران دبئی انٹرنیشنل کے ٹرمینل 3 سے 1.1 ملین سے زیادہ مسافر گزریں گے جو 21 دسمبر تک چلے گا۔
اس ہفتے کے آخر میں ٹرمینل 3 سے روانہ ہونے والے تقریباً 250,000 مسافروں میں ایک پیک کا اضافہ نظر آئے گا۔
ہوائی اڈے پر جلدی پہنچیں۔
ایئر لائن مسافروں کی حوصلہ افزائی کر رہی ہے کہ وہ اپنی پرواز کی روانگی سے کم از کم تین گھنٹے قبل ہوائی اڈے پر پہنچیں اور چیک ان ڈیسک پر جانے سے پہلے ان کے پاس اپنی منزل کے لیے تمام مطلوبہ دستاویزات کی دستیابی کو یقینی بنائیں۔
اپنے ہوائی اڈے کے تجربے کو تیز کرنے اور روانگی کو آسان بنانے کے لیے، مسافر اپنی پرواز کی روانگی سے 24 گھنٹے پہلے جسمانی طور پر چیک ان کر کے رش سے بچنے کا انتخاب کر سکتے ہیں، اپنے بیگ اتار سکتے ہیں اور اپنے بورڈنگ پاس جمع کر سکتے ہیں، 32 سیلف سروس بیگ ڈراپ مشینوں کا استعمال کرتے ہوئے، ٹرمینل 3 پر 16 چیک ان کیوسک دستیاب ہیں۔
سیلف سروس کیوسک استعمال کرنے والے مسافروں کو اب بھی اپنی پرواز کی روانگی سے 60 منٹ پہلے اپنی امیگریشن کےے قواعد پورے کرنے چاہئیں۔
مسافر اپنی پرواز کی روانگی سے 48 گھنٹے اور 90 منٹ پہلے تک آن لائن چیک ان کرنے کا انتخاب بھی کر سکتے ہیں اور منتخب مقامات کے لیے اپنے موبائل فون پر ڈیجیٹل بورڈنگ پاس ڈاؤن لوڈ کر سکتے ہیں۔
روانگی سے 60 منٹ سے کم وقت میں چیک کرنے والے افراد کو سفر کے لیے قبول نہیں کیا جائے گا۔
اس عمل کو مزید تیز کرنے کے لیے، صارفین مخصوص چیک ان ڈیسک، ایمریٹس لاؤنجز اور بورڈنگ گیٹس سے بغیر رابطے کے سفر کے لیے ٹرمینل 3 میں ایمریٹس کے بائیو میٹرک پاتھ کو بھی استعمال کر سکتے 
```

**verdict:** keep
**note:** 

---

### 21 · urdu-wikipedia:186893

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 271 chars, 45 words, 9 lines
- **script:** ratio 0.693 (arabic 0.693, latin 0.307)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=4
- **url:** https://ur.wikipedia.org/wiki/%D8%AC%D8%A7%D8%B1%D9%88%D8%B3%D8%A7%D9%86

```text
جاروسان ایران کا ایک رہائشی علاقہ جو Kakavand-e Gharbi Rural District میں واقع ہے۔

تفصیلات
جاروسان کی مجموعی آبادی 77 افراد پر مشتمل ہے۔

مزید دیکھیے
ایران
فہرست ایران کے شہر

حوالہ جات

جغرافیہ شہرستان دلفان کے نامکمل مضامین
Short description is different from Wikidata
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 22 · urdu-wikipedia:522648

- **filter:** REJECT — html_residue
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 1148 chars, 213 words, 30 lines
- **script:** ratio 0.945 (arabic 0.945, latin 0.055)
- **repetition:** dup_line 0.065, top-ngram 0.057, dup-ngram 0.000
- **url** 0.000 · **html** 0.057 · **U+FFFD** 0.00000
- **stage 4:** whitespace=14, yeh=1
- **url:** https://ur.wikipedia.org/wiki/%D8%A7%D9%86%D8%AC%D9%85%20%D8%B1%D9%88%D9%85%D8%A7%D9%86%DB%8C

```text
انجم رومانی (پیدائش: 28 ستمبر، 1920ء- وفات: 13 اپریل، 2001ء) پاکستان سے تعلق رکھنے والے اردو زبان کے ممتاز شاعر اور ماہر تعلیم تھے۔

حالات زندگی
انجم رومانی 28 ستمبر، 1920ء کو سلطان پور لودھی، کپور تھلہ، برطانوی ہندوستان میں پیدا ہوئے۔ ان کا اصل نام فضل دین تھا۔ وہ 1948ء سے 1972ء تک دیال سنگھ کالج، لاہور میں شعبۂ ریاضی کے صدر اور 1972ء سے 1977ء تک اسی کالج کے وائس پرنسپل بھی رہے۔ وہ حلقہ ارباب ذوق لاہور کے سیکریٹری کے عہدے پر بھی فائز رہے۔

ادبی خدمات
انجم رومانی کی تصانف میں کوئے ملامت، پس انداز، دنیا کے کنارے سے اور ثناء اور طرح کی شامل ہیں جبکہ ان کے کلام کی کلیات کلیات انجم رومانی کے نام سے اشاعت پزیر ہوچکی ہے۔

تصانیف
ثناء اور طرح کی (نعتیں)
دنیا کے کنارے سے
پس انداز
کوئے ملامت
کلیات انجم رومانی
اقبال کا منتخب فارسی کلام (ترجمہ)

نمونۂ کلام

<div style='text-align: center;'>
غزل

<div style='text-align: center;'>
غزل

وفات
انجم رومانی 13 اپریل، 2001ء کو لاہور، پاکستان میں وفات پاگئے۔ وہ لاہور میں گلشن راوی کے قبرستان میں سپردِ خاک ہوئے۔

حوالہ جات

1920ء کی پیدائشیں
2001ء کی وفیات
بیسویں صدی کے پاکستانی شعرا
پاکستانی اردو شعرا
پاکستانی ماہرین تعلیم
پاکستانی مترجمین
پاکستانی مسلم شخصیات
پاکستانی معلمین
لاہور کے شعرا
نعتیہ شاعر
```

**verdict:** keep
**note:** poet biography; the markup is a few <i>/<ref> tags in an otherwise clean body

---

### 23 · urdu-wikipedia:361701

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 481 chars, 90 words, 11 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.100, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=3
- **url:** https://ur.wikipedia.org/wiki/%DB%81%D9%86%D8%B1%DA%86%20%D8%B1%D9%88%D8%B1%D8%B1

```text
ہنرچ رورر ایک سوئزرلینڈ کے طبیعیات دان تھے۔ انھوں نے طبیعیات کا نوبل انعام بھی جیتا یہ انعام 1986 میں انھوں نے اپنے دو جرمن سائنس دان گرڈ بنگکے سائنس دان ارنسٹ رسکا کے ہمراہ سکیننگ ٹنلنگ مائکروسکوپ کے ڈزائن تخلیق کرنے کی وجہ سے ظاہر کرنے پر پر یہ انعام ملا۔

مزید دیکھیے
نوبل انعام برائے طبیعیات

حوالہ جات

1933ء کی پیدائشیں
2013ء کی وفیات
ریاستہائے متحدہ کی قومی اکادمی برائے سائنس کے ارکان
سویس نوبل انعام یافتہ
سوئس پروٹسٹنٹ
سوئس طبیعیات دان
نوبل انعام برائے طبیعیات وصول کنندہ
```

**verdict:** keep
**note:** 

---

### 24 · fineweb2-urd_Arab:<urn:uuid:2c96867e-9750-459c-9bb8-a97b613a10ff>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 1938 chars, 342 words, 10 lines *(excerpt shows first 1500)*
- **script:** ratio 0.636 (arabic 0.636, latin 0.362)
- **repetition:** dup_line 0.000, top-ngram 0.023, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** zero_width=2
- **url:** https://www.samaa.tv/urdu/entertainment/2020/08/2007676/

```text
اداکارہ حنا الطاف کے مارننگ شو میں دیئے گئے بیان پر ان کے شوہر اداکار آغا علی کو سوشل میڈیا پر تنقید سامنا ہے ۔
گزشتہ دنوں ایک مارننگ شو کے دوران اداکارہ حنا الطاف نے بتایا تھا کہ شادی سے پہلے آغا نے ان سے ایک وعدہ لیا تھا اور کہا کہ انہیں دنیا کی کوئی چیز نہیں چاہیے خدارا شادی کے بعد موٹی مت ہونا۔
View this post on Instagram
Shadi say pehly aik hi wada liya tha.Hina please Moti mat hona!!❤🤩. Two pure hearted people are here!!❤😍 #AaghaAli #hinaaltaf #Goodmorningpakistan #arydigital . . @aaghaaliofficial @hinaaltaf @itsnidayasir.official @arydigital.tv #aaghaaliofficial #AaghaAli #aaghaali #HinaAltaf #lollywood #actors #showbizpakistan #showbiz #hellopakistan #alisikander#showbizpakistan #pakistancelebrities#celebrities#pakistanidrama #pakistanshowbiz#yehdilmera#ehdewafa #zaranoorabbas #imranabbasnaqvi#hinaaltaf #sajalaly#entertainmentpopcorn #nimrahkhan #hinaaghakishadi #couplesgoals #lovebirds #jeetopakistan #fahadmustafa #areebahabib Admin:Chanda 💙
اداکارہ کی یہ ویڈیو وائرل ہوئی تو سوشل میڈیا پر طوفان برپا ہوگیا، صارفین کا کہنا تھا کہ آغا علی کا اپنی اہلیہ سے وزن سے متعلق لیا گیا وعدہ تضحیک آمیز ہے ۔
بعدازاں انسٹاگرام پر اپنا ردعمل دیتے ہوئے اداکار آغا علی کا کہنا تھا کہ میں نے اپنی اہلیہ سے کہا تھا کہ وہ غیر ضروری وزن پانے سے گریز کریں کیونکہ وہ ایک اداکارہ ہیں انہیں فٹ رہنے کی ضرورت ہے اور کوئی بھی پروڈیوسر اور ہدایتکار کسی زیادہ وزن والی ہیرون کو پسند نہیں کرتا ۔
انہوں نے بتایا کہ میں نے اپنا وزن کم کرنے کیلئے بہت محنت کی ہے جب میرا وزن بھی زیادہ تھا تو میں کچھ نہیں تھا 
```

**verdict:** keep
**note:** 

---

### 25 · fineweb2-urd_Arab:<urn:uuid:dbc8d235-e800-4247-89c7-48a2e4747582>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 1050 chars, 219 words, 3 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.050, dup-ngram 0.189
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://dailydharti.com/latest/2022-11-18/news-25668/

```text
ڈیلی دھرتی (ویب ڈیسک) تفصیلات کے مطابق چیئرمین تحریک انصاف عمران خان نے کہا ہے کہ موجودہ حکومت آرمی ایکٹ میں ترمیم اپنے فائدے کے لیے کررہی ہے، آرمی ایکٹ میں ترمیم کرکے یہ مسلح افواج کو پنجاب پولیس کے برابر لانا چاہتی ہے، آرمی ایکٹ میں ہونے والی مجوزہ ترمیم اعلی عدلیہ میں چیلنج ہوجائے گی۔سینئر صحافیوں سے غیر رسمی گفتگو کرتے ہوئے عمران خان کا کہنا تھا کہ حکومت فوج کو بھی پنجاب پولیس کے برابر لانا چاہتی ہے، آرمی ایکٹ میں ہونے والی مجوزہ ترمیم اعلی عدلیہ میں چیلنج ہوجائے گی۔ عمران خان نے کہا کہ نواز شریف وہ آرمی چیف لگانا چاہتا ہے جو مجھے نااہل کرے، مسلح افواج کے سربراہ کی تعیناتی چیف جسٹس سپریم کورٹ کی طرح ہونی چاہیے، نواز شرہف کے کیسز ختم کریں اور پھر اسے اقتدار میں لائیں۔
اپنی صحت پر انہوں ںے کہا کہ میرے معالجین کل میرا معائنہ کرکے اپنی رائے سے آگاہ کریں گے جس کے بعد راولپنڈی سے لانگ مارچ کی قیادت خود کروں گا۔
انہوں نے ارشد شریف قتل کیس پر کہا کہ ارشد شریف کے معاملے پر ہونے والا ظلم سب کے سامنے ہے، توشہ خانہ کیس میں انھوں نے مجھے خود عدالت میں جانے کا موقع دیا، میں برطانیہ اور امریکا کی عدالتوں میں نجی ٹی وی کے خلاف مقدمہ دائر کروں گا۔
```

**verdict:** keep
**note:** 

---

### 26 · urdu-wikipedia:204604

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 312 chars, 49 words, 8 lines
- **script:** ratio 0.688 (arabic 0.688, latin 0.312)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=3
- **url:** https://ur.wikipedia.org/wiki/%D8%B3%DB%8C%D9%86%D9%B9-%D9%BE%D8%AA%D8%B1%D9%86%DB%92-%D8%B1%DA%A9%D9%86

```text
سینٹ-پترنے-رکن ( فرانسیسی: Saint-Paterne-Racan) فرانس کا ایک فرانسیسی کمیون جو Canton of Neuvy-le-Roi میں واقع ہے۔

تفصیلات
سینٹ-پترنے-رکن کا رقبہ 47.77 مربع کیلومیٹر ہے اور اس کی مجموعی آبادی 1,697 افراد پر مشتمل ہے۔

مزید دیکھیے
فرانس
فہرست فرانس کے شہر

حوالہ جات

Short description is different from Wikidata
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 27 · fineweb2-urd_Arab:<urn:uuid:d34826b4-5ee3-49d4-8470-1d3791307633>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 440 chars, 87 words, 10 lines
- **script:** ratio 0.682 (arabic 0.682, latin 0.318)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://shuhada.punjabpolice.gov.pk/listing/shaheed/1436

```text
Saqlain Raza
District: RAJAN PUR
Department: Elite Police Force
Rank: ASI
Belt No.:679
Incident: Firing
Shahadat Date: 10 Nov 2019
Description:
دوران ڈیوٹی دہشت گردوں سے اندھا دھند فائرنگ کا تبادلہ ہو ا تو ثقلین رضا فریدی بیلٹ نمبر 679 انتہائی جرات اور بہادری سے دشمن کا مقابلہ کیا اور دشمن کی گولی لگنے کی وجہ سے مو قع پر جام شہادت نو ش کیا۔
اگر شہید کی فیملی کو ویلفیر کلیم کے سلسلے میں کسی قسم کی شکایات ہیں تو مندرجہ زیل لنک پر کلک کریں
```

**verdict:** drop
**note:** police martyr database record, form fields not prose

---

### 28 · urdu-wikipedia:361899

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 427 chars, 74 words, 7 lines
- **script:** ratio 0.719 (arabic 0.719, latin 0.281)
- **repetition:** dup_line 0.000, top-ngram 0.061, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=7
- **url:** https://ur.wikipedia.org/wiki/%DA%AF%D8%B1%D9%85%D8%A7%D8%A6%DB%8C%20%D8%A7%D9%88%D9%84%D9%85%D9%BE%DA%A9%20%DA%A9%DA%BE%DB%8C%D9%84%DB%8C%DA%BA

```text
گرمائی اولمپک کھیلیں (Summer Olympic Games) یا اولمپیاڈ کھیلیں (Games of the Olympiad) (فرانسیسی: Jeux olympiques d'été ) جو سب سے پہلے 1896ء میں منعقد ہوئے۔ -ہر چار سال بعد منعقد ہونے والا ایک بین الاقوامی کثیر کھیل مقابلہ ہے۔ ان کھیلوں کی کامیابی کو دیکھتے ہوئے 1924ء میں سرمائی اولمپک کھیلیں بھی شروع کی گئیں۔

کل وقتی جدول تمغا جات
سابقہ اقوام

حوالہ جات

اولمپکس
گرمائی اولمپکس
Short description is different from Wikidata
```

**verdict:** keep
**note:** 

---

### 29 · fineweb2-urd_Arab:<urn:uuid:4fd62cf5-523d-4df0-b1e4-18c0f956f878>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 697 chars, 144 words, 3 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.043, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://www.imroz.com.pk/29/04/2022/22379/

```text
لاس اینجلس : ہالی وڈ فلم “امیزنگ سپائیڈر مین” اور اس کے سیکوئل “امیزنگ سپائیڈر مین 2” میں سپائیڈر مین کا کردار نبھانے والے اداکار اینڈریو گارفیلڈ نے اداکاری کی دنیا سے بریک لے لیا۔
اینڈریو نے گذشتہ برسوں کے دوران متعدد پراجیکٹس میں اداکاری کی جس کی وجہ سے انہیں اہم کردار میں بہترین اداکار کیلئے آسکر نامزدگی بھی ملی تاہم 38 سالہ اداکار نے کچھ وقت کی بریک لینے کا فیصلہ کیا ہے۔ ایک انٹرویو میں اینڈریو نے کہا کہ میں واقعی بہت خوش ہوں کہ میں نے بریک لے کر اپنے لئے وقت نکالا ہے۔
انہوں نے کہا کہ میں وقفے کے دوران زیادہ سے زیادہ آرام کرنا چاہتا ہوں اور مختلف چیزیں سوچوں گا۔ اداکار نے یہ بھی کہا کہ میں دوسرے لوگوں کے کام دیکھنا چاہتا ہوں، موسیقی سننا ، دوستوں کے ساتھ رہنا اور برگر کھانا چاہتا ہوں۔
```

**verdict:** keep
**note:** 

---

### 30 · urdu-wikipedia:396837

- **filter:** REJECT — too_short, html_residue
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 96 chars, 16 words, 8 lines
- **script:** ratio 0.868 (arabic 0.868, latin 0.132)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.115 · **U+FFFD** 0.00000
- **stage 4:** whitespace=3
- **url:** https://ur.wikipedia.org/wiki/2040%D8%A1

```text
وفیات

دسمبر

<noinclude>

2040ء
2040ء کی دہائی
اکیسویں صدی
مستقبل کی دہائیاں
مستقبل کے خط زمانی
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 31 · urdu-wikipedia:919559

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 6019 chars, 1267 words, 30 lines *(excerpt shows first 1500)*
- **script:** ratio 0.992 (arabic 0.992, latin 0.008)
- **repetition:** dup_line 0.000, top-ngram 0.014, dup-ngram 0.037
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=50
- **url:** https://ur.wikipedia.org/wiki/%D9%86%D8%A7%D8%B2%DB%8C%20-%20%D8%B3%D9%88%D9%88%DB%8C%D8%AA%20%D8%A2%D8%A8%D8%A7%D8%AF%DB%8C%20%DA%A9%DB%8C%20%D9%85%D9%86%D8%AA%D9%82%D9%84%DB%8C

```text
نازی جرمنی اور سوویت یونین کے مابین جرمن - سوویت فرنٹیئر معاہدے کے مطابق ایک معاہدے کے تحت ، نازی - سوویت آبادی کی منتقلی 1939 اور 1941 کے درمیان نسلی جرمن (اصل) اور نسلی مشرقی سلاو (منصوبہ بند) کی آبادی کی منتقلی تھی ۔

تصور
اس کے دور میں ایڈولف ہٹلر کا ایک اہم مقصد یہ تھا کہ تمام جرمن بولنے والے لوگوں کو ایک علاقے میں متحد کیا جائے. جرمنی کی سرحدوں سے باہر لاکھوں نسلی جرمن آباد تھے ، زیادہ تر وسطی اور مشرقی یورپ میں ، جن کی سب سے بڑی تعداد روس کے جرمن باشندوں کی ہے۔ 12 ویں سے 18 ویں صدی کے درمیان مشرق کی طرف ہجرت کرنے کے بعد جرمن نسل کے ان گروہوں میں سے زیادہ تر سیکڑوں سالوں سے جرمنی سے باہر مقیم تھے۔

اس کے باوجود ، ہٹلر نے ان لوگوں کو مغرب کی طرف نازی جرمنی منتقل کرنے کا منصوبہ بنایا تھا۔ تاہم ، ہٹلر نے یہ بھی مانا تھا کہ نازی جرمنی کی 1937 کی سرحدیں اور علاقے ، یعنی آسٹریا اور سوڈین لینڈ کے "انشلوس" (الحاق) سے پہلے ، آبادی میں اس بڑے اضافے کو ایڈجسٹ کرنے کے لئے کافی ناکافی تھے۔ اس وقت ، زیادہ لبنسیرام یا "رہائشی جگہ" کے لئے پروپیگنڈا بہت بڑھ گیا ہے۔

قانونی بنیادیں
روس میں مقیم نسلی جرمنوں کی سب سے بڑی تعداد کے ساتھ ، ہٹلر جانتا تھا کہ وہ جوزف اسٹالن اور سوویت یونین کے مکمل تعاون کے بغیر ان تمام لوگوں کو دوبارہ آباد نہیں کرسکتا ہے۔ اگست 1939 کے آخر میں ( پولینڈ پر حملے اور یوروپ میں دوسری جنگ عظیم شروع ہونے سے ایک ہفتہ پہلے) ہٹلر نے اپنے وزیر خارجہ جوآخم وان رِبینٹرپ کو ماسکو بھیج دیا تاکہ سوویت یونین کے ساتھ عدم جارحیت کا معاہدہ طے کیا جاسکے۔ اس کو مولوتوف - ربنبروپ معاہدہ کے نام سے جانا جانے لگا۔ حقیقت میں ہٹلر کا مقصد جرمنی کو دو محاذوں پر لڑنے سے گریز کرنا تھا جب ایک
```

**verdict:** keep
**note:** 

---

### 32 · fineweb2-urd_Arab:<urn:uuid:81cf0029-b9b0-4b99-8a0f-4a55bfad06f3>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 1124 chars, 253 words, 13 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.096, dup-ngram 0.078
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** heh=7, presentation_forms=3, yeh=7
- **url:** https://forum.mohaddis.com/threads/%D9%85%DB%8C%D9%84%D8%A7%D8%AF-%D8%A8%D8%B4%D8%B1-%D8%B0%D8%A7%D8%AA-%DA%A9%D8%A7-%DB%81%D9%88%D8%AA%D8%A7-%DB%81%DB%92-%D9%86%D9%88%D8%B1-%D8%B0%D8%A7%D8%AA-%DA%A9%D8%A7-%D9%86%DB%81%DB%8C%DA%BA.24316/page-2

```text
میلاد بشر (انسان ) کا ہوتا ہے ‘ نور کا میلاد نہیں ہوتا۔
یہ اگر آپ کا وضع کردہ قاعدہ نہیں ہے تو ہمیں بتائیں کس کا قول ہے یہ؟
نور ذات کا میلاد نہیں ہوتا
جی نہیں ہوتا ہے
لیکن کس عالم نے کہا کہ نبی بشر نہیں؟
نبی صلی اللہ علیہ وسلم کو بھوک و پیاس لگتی تھی جس بنا پر آپ کھاتے پیتے تھےاور دوسروں کو بھی کھلاتے پلاتے تھے مثلاً صحابہ کرام ،آپ صلی اللہ علیہ وسلم انہیں کھانا کھلاتے تھے دودھ پلاتے تھے، ستو گھول کر پلاتے تھے کیونکہ آپ بشر ذات تھے مگر نبی صلی اللہ علیہ وسلم سے یہ کسی جگہ ثابت نہیں کہ حضرت جبرئیل علیہ السلام کو جو نور ذات تھے کبھی ناشتہ کرایا ہو اور ان کیلئے طعام، پانی، دودھ کا انتظام فرمایا
اف یہ قیاسات!!
ایک کام کرو، جنات کو بھی بھوک پیاس لگتی ہے کھاتے پیتے ہیں،بچے پیدا کرتے ہیں، انہیں بھی بشر کہنا شروع کر دو.
اور یہ تو بتاؤ کہ کس نے کہا کہ نبی صلی اللہ علیہ وسلم بشر نہیں؟
ہے کہ نور ذات جب بھی بظاہر شکل انسانی میں آتی تھی وہ تب بھی نہ کھاتی تھی اور نہ پیتی تھی۔ دیکھو حضرت ابراہیم علیہ السلام کے پاس جب
آپ کو جبرئیل علیہ السلام کے بشر بن کر آنے اور رسول صلی اللہ علیہ وسلم کے بشر ہونے میں کچھ فرق نظر آتا ہے؟
اور کیا نبی صلی اللہ علیہ وسلم کا قیاس فرشتوں پر کرنا عقلمندی ہے؟
قیاس کی حیثیت آپ کی نظر میں کیا ہے؟
```

**verdict:** keep
**note:** 

---

### 33 · urdu-wikipedia:1007196

- **filter:** REJECT — too_short
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 108 chars, 20 words, 5 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=1
- **url:** https://ur.wikipedia.org/wiki/%D9%85%D8%B1%DA%A9%D8%B2%20%D8%A7%D9%84%D8%AF%D8%B9%D9%88%DB%81%20%D8%A7%D9%84%D8%B3%D9%84%D9%81%DB%8C%DB%81

```text
مسلک اہلحدیث کا اہم مدرسہ

یہ ستیانہ بنگلہ، ضلع فیصل آباد میں واقع ہے،

اساتذہ
عبداللہ امجد چھتوی

حوالہ جات
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 34 · fineweb2-urd_Arab:<urn:uuid:44a045ed-f6df-4622-b88a-48212b00efa7>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 915 chars, 169 words, 6 lines
- **script:** ratio 0.618 (arabic 0.618, latin 0.379)
- **repetition:** dup_line 0.000, top-ngram 0.044, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** zero_width=1
- **url:** https://urdu.siasat.pk/news/2021-03-04/news-83974

```text
وزیراعظم کی کامیابی ہی ملک کی کامیابی ہے، وہی آخری امید ہیں، اداکار شان
معروف پاکستانی فلم اسٹار شان شاہد نے سماجی روابط کی ویب سائٹ ٹوئٹر پر ایک جاری کردہ ٹوئٹ میں کہا کہ بہترین پاکستان کے لیے وزیراعظم عمران خان ہماری آخری امید ہیں۔ اللہ تعالیٰ انہیں پاکستان کی خوشحالی اور عروج کے مقابل کھڑی تمام بری قوتوں سے لڑنے کی توفیق دے۔
@ImranKhanPTI you are Our hope♥🇵🇰 for Pakistan . May ALLAH give u strength to fight all evil forces that stand between the prosperity & rise of Pakistan .present times are tough but our trust in you is stronger than ever before Your success is Pakistan’s success.@fawadchaudhry pic.twitter.com/BU3vnqdKRx
— Shaan Shahid (@mshaanshahid) March 3, 2021
اداکار نے یہ بھی کہا کہ حالیہ وقت پاکستان کیلئے مشکل ہے، لیکن ہمارا آپ پر ہمارا اعتماد پہلے سے کہیں زیادہ مضبوط ہے، آپ کی کامیابی ہی دراصل پاکستان کی کامیابی ہے۔
شان شاہد اس سے پہلے بھی وزیر اعظم عمران خان پر اعتماد کا اظہار کر چکے ہیں
```

**verdict:** keep
**note:** 

---

### 35 · urdu-wikipedia:121962

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 226 chars, 43 words, 7 lines
- **script:** ratio 0.771 (arabic 0.771, latin 0.229)
- **repetition:** dup_line 0.000, top-ngram 0.106, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=3
- **url:** https://ur.wikipedia.org/wiki/%D8%AE%D9%88%D8%A7%D9%81

```text
خواف () ہے جو ایران میں واقع ہے۔ اس کی مجموعی آبادی 21,160 افراد پر مشتمل ہے، یہ صوبہ خراسان رضوی میں واقع ہے۔

متعلقہ روابط
فہرست ایران کے شہر

حوالہ جات

ایران کے شہر
شہرستان خواف
Short description is different from Wikidata
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 36 · fineweb2-urd_Arab:<urn:uuid:fe07689d-08c9-4367-bba1-8d76e280a7fe>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 972 chars, 201 words, 4 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.083, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://www.lahorenama.com/archives/37597

```text
لاہو ر(لاہورنامہ) ترجمان وزیر اعلی مسرت جمشید چیمہ نے شہید ارشد شریف کو انصاف دلوانے کیلئے دستخطی مہم میں شرکت کی ۔
اس موقع پر انہوں نے کہاکہ شہید ارشد شریف کیلئے آواز اٹھانے پر پی ایف یو جے کی شکرگزار ہوں، پاکستان میں ارشد شریف جیسے صحافی کا پہلا قتل نہیں تھا مگر اس کو آخری قتل بنائیں گے، اگر صحافیوں کے قاتلوں کو ماضی میں پھانسی پر لٹکایا جاتا تو مزید شہادتیں نہ ہوتیں.
ارشد شریف کو انصاف ملنے تک آواز اٹھاتے رہیں گے۔ ہمارا مطالبہ ہے کہ ارشد شریف کے قاتلوں کو پھانسی پر لٹکایا جائے۔ مسرت جمشید چیمہ نے کہا کہ اقوام متحدہ اور بین الاقوامی انسانی حقوق کی تنظیموں کو ارشد شریف کے قتل کیخلاف تحقیقات میں شامل کیا جائے، ارشد شریف نے پاکستان کے مسائل کی بات کی.
اسکا کوئی ذاتی ایجنڈا نہیں تھا، وہ ایک صحافی اور سچا محب وطن پاکستانی تھا، ارشد شریف پروفیشنلزم کی مثال آپ تھے، اپنے شہید بھائی کو انصاف دلانے کیلئے ہم سب کو مل کر جدوجہد کر نی ہو گی۔ انہوں نے کہا کہ ارشد شریف کی پوسٹ مارٹم رپورٹ انکی فیملی کو دی جائے۔ قتل کے کیس میں مدعی انکی فیملی ہے انہیں مطمئن کرنا ضروری ہے۔
```

**verdict:** keep
**note:** 

---

### 37 · fineweb2-urd_Arab:<urn:uuid:94e95c8c-b03f-455f-ab74-58b703a27e27>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 1405 chars, 275 words, 12 lines
- **script:** ratio 0.698 (arabic 0.698, latin 0.302)
- **repetition:** dup_line 0.000, top-ngram 0.017, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://www.kisanlink.com/en/article_detail/13

```text
Search Agricultural products and equipment
Author : Muhammad Afzal
Working to advance the whole of Pakistani agriculture that improve profitability, stewardship and quality of life by the use of Technology.
Studied at : KTH Royal Institute of Technology, Stockholm Sweden.
Co-founder : Nordic Experts AB Sweden
Lives in : Stavanger, Norway
From : Shorkot, Dist Jhang Pakistan
Timestamp: 31 December 2017 08:59 am
بیج ہمیشہ صاف ستھرا، تندرست اور توانا ہوناچاہئے۔ اور بیج اس کھیت سے حاصل کیاجائے۔ جہاں کوئی بیماری نہ آئی ہو۔ بیج کا اگاو 80 فیصد سے کم نہ ہو۔ اس کا اگاو معلوم کرنے کے لئے بیج کی لاٹ سےکم ازکم چار سو بیج لیں اور ان کو چوبیس گھنٹے کےلئے پانی میں بھگو دیں۔ پھر انہیں گیلے کپڑے میں لپیٹ کر سائے میں 36 تا48 گھنٹے کے لئے رکھیں۔ یہ احتیاط کریں کہ کپڑا گیلا رہے۔ اس دوران بیج انگوری مار آئےگا۔ اب نہیں گن کرفیصد اگاو نکال لیں اور شرح بیج اس کے مطابق استعمال کریں۔
دھان کی ایک ایکڑ کی پنیری اُگانے کے لئے شرح بیج بلحاظ قسم درج ذیل ہے۔
مندرجہ بالا شرح بیج 80 فیصد اُگاو والے بیج کےلئے ہے لیکن اگر اُگاو کم ہوتو اسی نسبت سے بیج کی مقدار میں اضافہ کریں۔
زیادہ پیداوار حاصل کرنے کے لئے پنجاب سیڈکارپوریشن کا تصدیق شدہ بیج اس کے قائم کردہ مراکز اور مقرر کردہ ڈیلروں سے حاصل کریں۔ اس کے علاوہ رائس ریسرچ انسٹی ٹیوٹ کا لا شاہ کا کو، نیاب فیصل آباد اور پرائیویٹ کمپنیوں سے بھی بیج مل سکتاہے۔ پنجاب سیڈ کارپوریشن کے پاس بھی اس سال چاول کی مختلف اقسام کا بیج مندرجہ ذیل مقدار میں موجود ہے۔ یہ بیج زہر آلود ہے۔
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 38 · fineweb2-urd_Arab:<urn:uuid:e664dfc6-0c50-4440-a171-ac2c10eda724>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 854 chars, 189 words, 12 lines
- **script:** ratio 0.684 (arabic 0.684, latin 0.316)
- **repetition:** dup_line 0.000, top-ngram 0.047, dup-ngram 0.230
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://danishgardi.pk/forums/reply/245736/

```text
Home › Forums › Siasi Discussion › اے پی سی سے دو دن پہلے اپوزیشن لیڈران کی آرمی چیف سے خفیہ ملاقات › اے پی سی سے دو دن پہلے اپوزیشن لیڈران کی آرمی چیف سے خفیہ ملاقات
- Professional
- Threads: 35
- Posts: 1730
- Total Posts: 1765
- Join Date:
2 Mar, 2017
- Location: Kala Shah kaku
Re: اے پی سی سے دو دن پہلے اپوزیشن لیڈران کی آرمی چیف سے خفیہ ملاقات
لیکن زیدی صاحب سوچنے والی بات یہ ہے کہ آرمی چیف نے بلایا اور یہ فورا ” بھاگے گئے اور دو دن بعد ہی با جماعت آرمی کو برا بھلا کہہ رہے تھے ، کیا یہ کھلی بکواس نہیں ، کیا یہ چیف کو کہہ نہیں سکتے تھے کہ آپ کون ہوتے ہیں ہمیں بلانے والے اور اگر آپ کی بات مان لی جائے تو کیا اپوزیشن اب آرمی چیف کی مدد سے عمران خان کو ہٹانے کی کوشش کر رہی ہے ؟؟ لگتا ہے آپ کے دل پے بھی چھریاں چل گئیں
Under what authority the Army Chief can summon the Politicians to meet him?
Can anyone quote a Constitutional clause/provision?
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 39 · fineweb2-urd_Arab:<urn:uuid:311fc491-c48b-4531-85b2-778bdbb2126f>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 1277 chars, 279 words, 8 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.085, dup-ngram 0.108
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://urdu.indianarrative.com/india-news/every-indian-is-proud-of-jammu-and-kashmir-pm-narendra-modi.html

```text
وزیر اعظم مودی نے ویڈیو پیغام کے ذریعے جموں و کشمیر کے روزگار میلے سے خطاب کیا، کہا آپ کو بدعنوانی سے نفرت ہے، میں نے آپ کا درد محسوس کیا ہے
نئی دہلی، 30 اکتوبر (اندیا نیرٹیو)
جموں و کشمیر کو ہر ہندوستانی کا فخر بتاتے ہوئے وزیر اعظم نریندر مودی نے کہا کہ ہمیں مل کر جموں و کشمیر کو نئی بلندیوں تک لے جانا ہے۔ جموں و کشمیر کے لوگ کرپشن سے نفرت کرتے ہیں۔ میں نے اس کے درد کو محسوس کیا ہے۔ وزیر اعظم اتوار کو ویڈیو پیغام کے ذریعے جموں و کشمیر روزگار میلے سے خطاب کر رہے تھے۔
وزیر اعظم نے کہا کہ جموں و کشمیر کے ہونہار نوجوانوں کے لیے آج کا دن بہت اہم ہے۔ انہوں نے تمام تین ہزار نوجوانوں کو مبارکباد دی جنہوں نے جموں و کشمیر میں 20 مختلف مقامات پر حکومت میں کام کرنے کے لیے تقرری لیٹر حاصل کیے ہیں۔
وزیر اعظم نے کہا کہ ان نوجوانوں کو مختلف محکموں جیسے پی ڈبلیو ڈی، محکمہ صحت، محکمہ خوراک اور سول سپلائی، حیوانات، جل شکتی اور تعلیم و ثقافت میں خدمات انجام دینے کا موقع ملے گا۔
وزیر اعظم نے مزیدکہا کہ آنے والے دنوں میں 700 تقرری لیٹر دیگر محکموں کے حوالے کرنے کی تیاریاں زور و شور سے جاری ہیں۔
جموں و کشمیر کی تاریخ میں 21 ویں صدی کی اس دہائی کی اہمیت کو اجاگر کرتے ہوئے وزیر اعظم نے کہا،
”اب وقت آگیا ہے کہ پرانے چیلنجوں کو پیچھے چھوڑ کر نئے امکانات سے بھرپور فائدہ اٹھایا جائے۔ مجھے خوشی ہے کہ جموں و کشمیر کے نوجوان اپنی ریاست اور عوام کی ترقی کے لیے بڑی تعداد میں آگے آ رہے ہیں۔
```

**verdict:** keep
**note:** 

---

### 40 · fineweb2-urd_Arab:<urn:uuid:8c2bc8ef-0c3f-429c-80d6-4d2b4e8461b6>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 341 chars, 71 words, 4 lines
- **script:** ratio 0.691 (arabic 0.691, latin 0.309)
- **repetition:** dup_line 0.000, top-ngram 0.053, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** http://aajkal.com.pk/tag/digital-currency

```text
ڈٰیجیٹل کرنسی بٹ کوائن آج کل گردش میں ہے اور اس کی قدر میں بتدریج اضافہ دیکھنے میں آ رہا ہے۔ یہ ایک کریپٹو کرنسی ہے۔ مرکزی کنٹرول نہ ہونے کی وجہ سے اس کی قدر اور پائے داری کے حوالے سے سوال ب... Read more
کیا عام عوام کو رمضان بازار کا فائدہ ہوتا ہے۔
View Results
© 2018 AAJKAL All rights of publications are reserved by Aajkal Urdu Newspaper
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 41 · urdu-wikipedia:921485

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 2362 chars, 527 words, 18 lines *(excerpt shows first 1500)*
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.059, dup-ngram 0.018
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=39
- **url:** https://ur.wikipedia.org/wiki/%D9%86%D8%B9%D9%85%D8%AA%20%D8%B3%D8%B1%D8%AD%D8%AF%DB%8C

```text
نعمت سرحدی پشتو فلموں کے فلم اسٹار تھے اور انہوں نے 600 کے قریب پشتو فلموں میں اداکاری کی ہے۔

لیکن ان کی زندگی کے حالات کے بارے میں بہت کم معلومات ہیں ، اور اس کی وجہ یہ ہے کہ نعمت سرحدی نے اپنے طویل کیریئر میں میڈیا سے دور رہتے اور گوشہ نشینی کی زندگی بسر کرنے کو ترجیح دی۔

نعمت سرحدی سال 2011 سے فلم انڈسٹری سے دور ہیں اور اپنی ساری زندگی تبلیغ کے میدان میں صرف کرتے ہیں ، جب وہ شہرت کے بلندیوں پر کھڑے تھے ، تب انہوں نے اپنا موبائل فون اپنے پاس نہیں رکھا ، نہ ہی ٹی وی اور ریڈیو پر۔ انٹرویوز اور پروگراموں کی تیاری اور عوامی اجتماعات میں شرکت کی۔

بس اس کی جھاڑی کے کنارے لاہور میں واقع اس کے گھر کے ایک کونے میں کھڑی ہوتی اور جب فلم کی شوٹنگ کا وقت آتا تو وہ لفظ درست کرتے اور کیمرے کے سامنے چلے جاتے۔

فلموں کا آغاز
اس کی پہلی پشتو فلم یوسف خان شیربانو 1970 میں ریلیز ہوئی جس میں وہ بدر منیر کے ساتھ نظر آئے ۔

اور پھر جب تک پشتو فلم بدر منیر بادشاہی تھی ، نعمت سرحدی اس کے ساتھ ہی مشہور رہے۔

لیکن ان کی مقبولیت کے باوجود ، نعمت سرحدی کی زندگی سادگی سے بھری ہوئی تھی۔ جب کسی نے فلمی اسٹوڈیو کا دورہ کیا اور نعمت سرحدی کو آمنے سامنے دیکھا تو کوئی یقین نہیں کرسکتا تھا کہ یہ عظیم اداکار نعمت سرحدی ہے۔

نعمت سرحدی کا کہنا ہے کہ وہ بچپن ہی سے فلموں اور اداکاری میں دلچسپی لیتے ہیں۔

یوسف خان شیر بانو میں ہیرو کے کردار میں بدر منیر اور نعمت سرحدی ولن کا کردار ادا کیا ، بلکہ دونوں ہیرو اور ولن کی حیثیت سے فلمی صنعت میں سرگرم رہے۔ اور حالیہ برسوں میں ، نعمت سرحدی مذہبی تبلیغ کی طرف راغب ہوئے ہیں اور انہوں نے فلمی دنیا پر دیرپا تاثر قائم کیا ہے۔

ان کا کہنا ہے کہ فلم یوسف خان شیر بانو میں ان ک
```

**verdict:** keep
**note:** 

---

### 42 · fineweb2-urd_Arab:<urn:uuid:84b0361e-6ae7-4b5d-931f-9fd9c0228c7b>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 2505 chars, 517 words, 23 lines *(excerpt shows first 1500)*
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.024, dup-ngram 0.061
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://www.express.pk/story/177791/

```text
- فیفا ورلڈ کپ؛ انگلینڈ کی ویلز کے خلاف فتح، ناک آؤٹ مرحلے میں رسائی
- فیفا ورلڈ کپ؛ امریکا نے ایران کو شکست دے کر ایونٹ سے باہر کر دیا
- کراچی بیوی اور 3 بیٹیوں کا لرزہ خیز قتل، زخمی والد نے اعتراف جرم کرلیا
- لاہور میں ون وے کی خلاف ورزی پر چالان کے ساتھ مقدمہ بھی درج کرنے کا فیصلہ
- وزیراعظم پنجاب اور کے پی اسمبلی کو تحلیل ہونے سے بچانے کیلیےمتحرک ہوگئے
- اسلام آباد اور گرد و نواح میں 3.6 شدت کا زلزلہ
- رواں مالی سال میں ترسیلات زر اور غیرملکی سرمایہ کاری میں کمی کا انکشاف
- لاہور میں جعلی ادویات خریدنے اور سپلائی میں ملوث مطلوب ملزمان گرفتار
- فیفا ورلڈ کپ؛ سینیگال کی اِیکواڈور کے خلاف فتح، ناک آؤٹ راؤنڈ میں رسائی
- قائد اعظم ٹرافی؛ سندھ کو شکست دے کر ناردرن پہلی بار چیمپئین بن گئی
- ہوشاب میں سیکیورٹی فورسز کے آپریشن میں 10 دہشت گرد ہلاک
- ایچ ای سی کی نظرثانی شدہ انڈرگریجویٹ پالیسی سامنے آگئی
- سندھ میں اڑیال کو شکار کرنے کی فیس 14 ہزار ڈالرز مقرر
- عالمی سب میرین کیبل میں خرابی کیوجہ سے پاکستان میں بھی انٹرنیٹ سروس متاثر
- وزیراعظم نے اعظم نذیر تارڑ کا استعفی مسترد کردیا، کام جاری رکھنے کی ہدایت
- واٹس ایپ ’میسج یور سیلف‘ فیچر جلد متعارف کرائے گا
- پاکستان نے معاشی استحکام کے لیے بینک آف چائنہ سے مدد مانگ لی
- فیفا ورلڈ کپ؛ نیدرلینڈز نے قطر کو شکست دے کر ایونٹ سے باہر کردیا
- پاکستان پہلی بار سینٹرل ایشین والی بال کا چیمپئن بن گیا
- یوکرین ایک نہ ایک روز نیٹو میں شامل ہو جائے گا؛ سیکرٹری جنرل
کراچی: ڈرگ کورٹ کے چیئرمین ساتھی محمد اسحاق ، ممبران ڈاکٹر غلام رسول ہالپوٹو نگہت قادری نے کراچی کے مزید 15میڈیکل اسٹورزکے32مالکان کیخلاف مقدمات کا چالان منظور کرلیا ہے اور تمام م
```

**verdict:** keep
**note:** news headline index — no article body, but the headlines are coherent Urdu

---

### 43 · urdu-wikipedia:1000755

- **filter:** REJECT — html_residue
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 1549 chars, 297 words, 19 lines *(excerpt shows first 1500)*
- **script:** ratio 0.980 (arabic 0.980, latin 0.020)
- **repetition:** dup_line 0.000, top-ngram 0.042, dup-ngram 0.000
- **url** 0.000 · **html** 0.021 · **U+FFFD** 0.00000
- **stage 4:** whitespace=4
- **url:** https://ur.wikipedia.org/wiki/%D9%86%D8%A7%D8%B5%D8%B1%20%DA%A9%D8%A7%D8%B3%DA%AF%D9%86%D8%AC%D9%88%DB%8C

```text
ناصر محمود خان المعروف ناصر کاسگنجوی (پیدائش: 10 اکتوبر 1928ء - 22 جون 2002ء) پاکستان سے تعلق رکھنے والے اردو زبان کے ممتاز شاعر تھے۔ انہوں نے غزل، قطعات، نظم اور نعت کی اصنافِ سخن میں طبع آزمائی کی۔

حالات زندگی
ناصر کاسگنجوی 10 اکتوبر 1928ءکو کاسگنج، ضلع ایٹہ، اتر پردیش ، برطانوی ہندوستان میں پیدا ہوئے۔ ان کا اصل نام ناصر محمود خان تھا لیکن ناصر کاسگنجوی کے قلمی نام شہرت پائی۔ ان کے والد کا نام احمد خان کیفی کاسگنجوی تھا۔ میٹرک اور انٹرمیڈیٹ کی تعلیم کاسگنج میں حاصل کی۔ تقسیم ہند کے بعد پاکستان منتقل ہو گئے۔گریجویشن کی تعلیم کراچی سے حاصل کی۔ اورینٹ ایئر ویز میں ملازمت اختیار کی۔ بعد ازاں وزارت صنعت کے ادارے سپلائی اینڈ ڈویلپمنٹ میں ملازمت کی۔ اس ادارے سے قبل از وقت ریٹائرمنٹ لے کر اپنی بہنوں کے قائم کردہ گلشن گرامر اسکول میں پرنسپل ہو گئے۔ وہ شاعری کی ابتدا سے تا عمر غزل کے نمائندہ شاعر رہے۔ والد کے دوست جگر مراد آبادی سے بے حد متاثررہے۔ ناصر کاسگنجوی فلمی صنعت سے بھی وابستہ رہے۔ انہوں نے پاکستان کی اولین سنیما اسکوپ فلم جان پہچان کے نغمات لکھے۔ان کا تصانیف خمارِ دوش، سرورِ امروز (غزلیات)، جذب و جنوں (منظومات)، ریزہ ریزہ سنگ (قطعات و رباعیات)، اور دیارِ گل (نعتیں) شامل ہیں۔

نمونۂ کلام

<div style='text-align: center;'>
نعت

وفات
ناصر کاسگنجوی کو 2001ء میں کینسر کا مرض لاحق ہو گیا تھا۔ اس مرض کے سبب 22 جون 2002ء کو کراچی، پاکستان میں انتقال کر گئے۔ وہ ملک پلانٹ گلشن اقبال سے ملحقہ قبرستان میں مدفون ہیں۔

حوالہ جات

1928ء کی پیدائشیں
2002ء کی وفیات
22 جون کی وفیات
پاکستانی مسلم شخصیات
کراچی کے شعرا
بیسویں صدی کے پاکستانی شعرا
پاکستانی اردو شعرا
کراچی میں وفات پانے والی شخصی
```

**verdict:** keep
**note:** poet biography, same as 22

---

### 44 · urdu-wikipedia:908416

- **filter:** REJECT — too_short
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 180 chars, 30 words, 5 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.122, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=4
- **url:** https://ur.wikipedia.org/wiki/%D9%86%D9%88%D8%B1%D9%88%D8%AF%D9%88%D9%85%20%D8%AE%D8%A7%D9%86%D8%AF%D8%A7%D9%86

```text
نورودوم خاندان کمبوڈیا پر حکومت کرنے والا شاہی خاندان ہے۔ اس کا موجودہ سربراہ اور کمبوڈیا کا موجودہ بادشاہ نورودوم سیہامونی ہے۔

مزید دیکھیے
کمبوڈیا

حوالہ جات

ایشیائی شاہی خاندان
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 45 · urdu-wikipedia:435350

- **filter:** REJECT — repetition:top_3gram, repetition:dup_5gram
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 1254 chars, 201 words, 41 lines
- **script:** ratio 0.945 (arabic 0.945, latin 0.055)
- **repetition:** dup_line 0.000, top-ngram 0.290, dup-ngram 0.415
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=35
- **url:** https://ur.wikipedia.org/wiki/%D8%A8%D9%81%DB%8C%D9%84%D9%88%20%D9%B9%D8%A7%D8%A4%D9%86%20%D8%B4%D9%BE

```text
بفیلو ٹاؤن شپ (Buffalo Township) کے لیے آپ مندرجہ ذیل صفحات سے رجوع کر سکتے ہیں۔

مقامات

ریاستہائے متحدہ

آرکنساس
بفیلو ٹاؤن شپ، کریگہیڈ کاؤنٹی، آرکنساس
بفیلو ٹاؤن شپ، ماریون کاؤنٹی، آرکنساس

الینوائے
بفیلو ٹاؤن شپ، اوگل کاؤنٹی، الینوائے

آئیووا
بفیلو ٹاؤن شپ، بیوکینن کاؤنٹی، آئیووا
بفیلو ٹاؤن شپ، کوسوتھ کاؤنٹی، آئیووا
بفیلو ٹاؤن شپ، لین کاؤنٹی، آئیووا
بفیلو ٹاؤن شپ، سکاٹ کاؤنٹی، آئیووا
بفیلو ٹاؤن شپ، وینیباگو کاؤنٹی، آئیووا

کنساس
بفیلو ٹاؤن شپ، بارٹن کاؤنٹی، کنساس
بفیلو ٹاؤن شپ، جیول کاؤنٹی، کنساس
بفیلو ٹاؤن شپ، کلاؤڈ کاؤنٹی، کنساس

مینیسوٹا
بفیلو ٹاؤن شپ، رائٹ کاؤنٹی، مینیسوٹا

مسوری
بفیلو ٹاؤن شپ، ڈینکلن کاؤنٹی، مسوری
بفیلو ٹاؤن شپ، مورگن کاؤنٹی، مسوری
بفیلو ٹاؤن شپ، نیوٹن کاؤنٹی، مسوری
بفیلو ٹاؤن شپ، پائیک کاؤنٹی، مسوری

اوہائیو
بفیلو ٹاؤن شپ، نوبل کاؤنٹی، اوہائیو

اوکلاہوما
بفیلو ٹاؤن شپ، بیکہم کاؤنٹی، اوکلاہوما
بفیلو ٹاؤن شپ، گارفیلڈ کاؤنٹی، اوکلاہوما
بفیلو ٹاؤن شپ، ہارپر کاؤنٹی، اوکلاہوما
بفیلو ٹاؤن شپ، لاتیمر کاؤنٹی، اوکلاہوما
بفیلو ٹاؤن شپ، نوبل کاؤنٹی، اوکلاہوما

پنسلوانیا
بفیلو ٹاؤن شپ، بٹلر کاؤنٹی، پنسلوانیا
بفیلو ٹاؤن شپ، پیری کاؤنٹی، پنسلوانیا
بفیلو ٹاؤن شپ، یونین کاؤنٹی، پنسلوانیا
بفیلو ٹاؤن شپ، واشنگٹن کاؤنٹی، پنسلوانیا

نام مقامات ضد ابہام صفحات
ٹاؤن شپ نام ضد ابہام صفحات
Short description is different from Wikidata
```

**verdict:** drop
**note:** disambiguation page listing 20 townships

---

### 46 · urdu-wikipedia:1100741

- **filter:** REJECT — repetition:dup_5gram
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 1279 chars, 248 words, 14 lines
- **script:** ratio 0.993 (arabic 0.993, latin 0.007)
- **repetition:** dup_line 0.000, top-ngram 0.091, dup-ngram 0.479
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=13
- **url:** https://ur.wikipedia.org/wiki/%D9%82%D8%A7%D8%B6%DB%8C%20%D8%A7%D8%AD%D9%85%D8%AF%20%D8%B3%D8%B9%DB%8C%D8%AF

```text
قاضی احمد سعید، ایک پاکستانی سیاست دان ہیں جو 2002 سے مئی 2018 تک پنجاب کی صوبائی اسمبلی کے رکن رہے۔

ابتدائی زندگی اور تعلیم
قاضی احمد سعید یکم جون 1968 کو ضلع رحیم یار خان میں پیدا ہوئے۔ انہوں نے قانون کی بیچلر کی ڈگری 1993 میں کراچی یونیورسٹی سے حاصل کیا اور ماسٹر آف آرٹس کی ڈگری 1995 میں شاہ عبداللطیف یونیورسٹی سے حاصل کی۔

سیاسی کیریئر
قاضی احمد سعید 2002 کے پاکستانی عام انتخابات میں حلقہ پی پی-286 (رحیم یار خان-II) سے پاکستان مسلم لیگ (ق) کے امیدوار کے طور پر پنجاب کی صوبائی اسمبلی کے لیے منتخب ہوئے تھے۔ انہوں نے 29,130 ووٹ حاصل کیے اور ایک آزاد امیدوار کو شکست دی۔ وہ 2008 کے پاکستانی عام انتخابات میں حلقہ پی پی 286 (رحیم یار خان-II) سے پاکستان مسلم لیگ (ف) کے امیدوار کے طور پر پنجاب کی صوبائی اسمبلی کے لیے دوبارہ منتخب ہوئے۔ انہوں نے 26,715 ووٹ حاصل کیے اور مسلم لیگ (ق) کے امیدوار کو شکست دی۔ وہ 2013 کے پاکستانی عام انتخابات میں حلقہ پی پی 286 (رحیم یار خان-II) سے پاکستان پیپلز پارٹی کے امیدوار کے طور پر پنجاب کی صوبائی اسمبلی کے لیے دوبارہ منتخب ہوئے۔

حوالہ جات

پاکستان مسلم لیگ (ق) کے ارکان صوبائی اسمبلی (پنجاب)
پاکستان مسلم لیگ (ف) کے سیاست دان
پاکستان پیپلزپارٹی کے ارکان صوبائی اسمبلی (پنجاب)
1968ء کی پیدائشیں
پنجاب ارکان صوبائی اسمبلی 2002ء تا 2007ء
پنجاب ارکان صوبائی اسمبلی 2008ء تا 2013ء
پنجاب ارکان صوبائی اسمبلی 2013ء تا 2018ء
بقید حیات شخصیات
```

**verdict:** keep
**note:** clean politician biography, same pattern as 1

---

### 47 · urdu-wikipedia:922439

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 1633 chars, 287 words, 16 lines *(excerpt shows first 1500)*
- **script:** ratio 0.959 (arabic 0.959, latin 0.041)
- **repetition:** dup_line 0.000, top-ngram 0.054, dup-ngram 0.059
- **url** 0.037 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=8
- **url:** https://ur.wikipedia.org/wiki/%D8%B4%D9%85%D9%88%D8%A6%D9%84%20%D8%A7%D8%AD%D9%85%D8%AF

```text
شموئل احمد ہندوستان کے معروف افسانہ نگار ہیں۔انھوں نے جنسی اور نفسیاتی موضاعات پر ناول اور افسانے لکھے۔ان کے چار افسانوی مجموعے ، تین ناول اور ایک ناولٹ شائع ہو چکے ہیں۔

افسانوی مجموعے:
بگولے (چودہ افسانے)، سرخاب پبلی کیشنز، پٹنہ،1988

سنگھار دان (دس افسانے)، معیار پبلی کیشنز، نئی دہلی، 1996

القمبوس کی گردن (نو افسانے)، نقاد پبلی کیشنز، پٹنہ، 2003

عنکبوت (گیارہ افسانے)، ایجوکیشنل پبلشنگ ہاؤس، نئی دہلی، 2010

اردو کی نفسیاتی کہانیاں(مرتبہ/تیرہ افسانے) ، ارم پبلشنگ ہاؤس، پٹنہ، 2014

ناول:
مہا ماری، نشاط پبلی کیشنز، پٹنہ، 2003

اے دل آوارہ (خود نوشت/ناول)، ایجوکیشنل پبلشنگ ہاؤس، نئی دہلی، 2015

گرداب ، ایجوکیشنل پبلشنگ ہاؤس، نئی دہلی، 2016

ناولٹ:
ندی ، موڈرن پبلشنگ ہاؤس، نئی دہلی، 1993

شموئل احمد 4 مئی 1943 کوریاست بہار کے ضلع بھاگل پورمیں پیدا ہوئے ۔ابتدائی تعلیم بھاگل پور میں ہی حاصل کی ۔1957 میں گیا سے میٹرک کیا ۔1960 میں انٹر اور 1968 میں جمشید پور سے سول انجنیئرنگ کی ڈگری حاصل کی۔ 1983 کے اوائل میں بوکارو میں بہ حیثیت انجنیئر نوکری کا آغاز کیا اور چیف انجنیئر کے عہدے سے 2003 میں سبکدوش ہوئے۔انھوں نے اوائل عمری سے ہی کہانیاں لکھنا شروع کر دی تھیں۔ان کی دو ابتدائی کہانیاں اس وقت شائع ہوئیں جب وہ درجہ ششم کے طالب علم تھے۔پہلا افسانہ ”صنم“ پٹنہ میں”چاند کا داغ“ کے نام سے نومبر دسمبر 1962 میں شائع ہوا ۔مگر پہلا افسانوی مجموعہ تاخیر سے منظرعام پر آیا۔ناولٹ ”ندی“ کے پانچ ایڈیشن شائع ہوچکے ہیں۔ناول ”مہاماری“ کا دوسرا ایڈیشن عرشیہ پبلی کیشنز ، دہلی سے شائع ہوا۔ناول کی کلیات میاٹرلنک پبلی کیشنز،لکھنو نے شائع کی ہے۔ان کے افسانوں کا ترجمہ ہندی، انگریزی، پنجابی اور دوسری زبانوں میں
```

**verdict:** keep
**note:** 

---

### 48 · fineweb2-urd_Arab:<urn:uuid:e5fe8767-5db3-4a47-9e74-4db668ee21d3>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 22377 chars, 5022 words, 64 lines *(excerpt shows first 1500)*
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.004, top-ngram 0.007, dup-ngram 0.022
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** heh=2, presentation_forms=1, yeh=2
- **url:** https://alert.com.pk/archives/30700

```text
تحریر : ڈاکٹر محمد مصطفیٰ
سلطان کے خاص دستے کے لیے ینی چری کے نوجوانوں کی خدمات لی جاتی تھی اور جب سلطان کسی سفر پر جاتا تو ینی چری کے ڈیڑھ سو (150)نوجوان سلطان کے آگے پیچھے دائیں بائیں سلطان کی حفاظت کے لیے ساتھ موجود ہوتے تھے۔ ینی چری میں جب کوئی سپاہی کمزور یا بوڑھا ہو جاتا تو اس کو کسی قلعے میں بطور چوکیدار رکھ دیا جاتا اور اس کی جگہ تندرست اور تجربے کار سپاہی رکھ کیا جاتا ۔
مندرجہ بالا سے واضح ہوتا ہے کہ حکومت اور لشکر کا نظام دراصل ایک تعلیمی نظام تھا اس کے تحت سرکاری اہل کاروں اور فوجیوں کو با قاعدہ ٹریننگ دی جاتی تھی اور پھر ان کی قابلیت کے حساب سے ان کو ان کے عہدوں پر مامور کر دیا جاتا تھا انتخاب کرتے وقت اس کی پوری جان پڑتال کی جاتی دماغی طور پر جسمانی طور پر اور پوری تسلی کر کے اس کو عہدے پر فائز کیا جاتا تھا ۔
سست کمزور ذہن والے افراد کو فوراً اس نظام سے نکال دیا جاتا تھا ان کے لیے اس نظام میں کوئی جگہ نہیں ہوتی تھی اور اگر ان میں کوئی غداری کرتا تو اس کی صرف ایک سزا تھی وہ تھی سزائے موت اور اس غدار کا سر قلم کر دیا جاتا تھا. عثمانی فوج میں نظم و ضبط کی بہت زیادہ سختی کی جاتی تھی اور میدان جنگ میں کوئی ایک دوسرے سے بات چیت نہیں کر سکتا تھا جب تک سلطان کا حکم نہ ہو ۔
مزید پڑھیں: سلطان محمد فاتح ۔۔۔۔۔۔۔۔۔۔۔ (نویں قسط)
فوج کی اس طرح ٹریننگ کی جاتی تھی کہ وہ بھوک پیاس میں بھی سفر قائم رکھتے تھے اطاعت فرمانبرداری ان میں خوب بھر دی جاتی تھی اور جنگ کے دوران ان کی رفتار بہت تیز ہوا کرتی تھی جس کی ایک وجہ تو یہ تھی کہ ان کے گھوڑے عربی نسل کے ہوتے تھے جو بھاگنے میں بہت تیز ہوتے تھے دوسرا عثمانی فوجیوں کے پاس سامان بہت کم ہوتا تھا اور اس کے مقابلے میں یورپی فوجوں کی ایک تو 
```

**verdict:** keep
**note:** 

---

### 49 · fineweb2-urd_Arab:<urn:uuid:14a20583-ae75-4d2c-b265-8b5370232260>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 282 chars, 55 words, 3 lines
- **script:** ratio 0.685 (arabic 0.685, latin 0.315)
- **repetition:** dup_line 0.000, top-ngram 0.057, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** http://noownews.com/kamran-khan-praises-chief-justice-saqib-nisar/

```text
Kamran Khan Praises Chief Justice Saqib Nisar.
چیف جسٹس ثاقب نثار کی نایاب خدمات! پاکستانیوں کے لیے چیف جسٹس کی جانب سے کیے جانے والے اہم فیصلوں نے پاکستانی معشیت کو ڈوبنے سے بچا لیا، جو پاکستان کی تاریخ میں سنہری حروف میں لکھے جائیں گئے
Posted by Dunya News on Tuesday, 3 July 2018
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 50 · urdu-wikipedia:1065774

- **filter:** REJECT — too_short, repetition:top_4gram
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 182 chars, 30 words, 3 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.319, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=2
- **url:** https://ur.wikipedia.org/wiki/%D9%BE%D8%A7%DA%A9%D8%B3%D8%AA%D8%A7%D9%86%20%D8%B1%DB%8C%D9%84%D9%88%DB%8C%D8%B2%20%D8%B1%D8%A7%D9%88%D9%84%D9%BE%D9%86%DA%88%DB%8C%20%DA%88%D9%88%DB%8C%DA%98%D9%86

```text
پاکستان ریلویز راولپنڈی ڈویژن کا دفتر راولپنڈی ریلوے اسٹیشن کے ساتھ متصل عمارت میں ہے۔ یہاں پر ڈویژنل سپریٹینڈٹ راولپنڈی کا دفتر بھی ہے۔

پاکستان ریلویز
پاکستان ریلویز راولپنڈی ڈویژن
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 51 · fineweb2-urd_Arab:<urn:uuid:6d74a28c-cb5e-4cf8-9060-64f35d3fa845>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 382 chars, 76 words, 1 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.063, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** http://voiceofasianews.com/live-news/2331552

```text
اسلام آباد(وائس آ ف ایشیا) تحریک انصاف نے سیالکوٹ میں پولیس کی کارروائی کو لندن پلان پر عملدرآمد کا آغاز قرار دیتے ہوئے سپریم کورٹ سے سوموٹو نوٹس لینے کا مطالبہ کیا ہے۔ماہر قانون ڈاکٹر بابر اعوان نے کہا ہے کہ سیالکوٹ میں لندن پلان پر عمل درآمد کا آغاز ہو گیا۔پی ٹی آئی کے خالی ہاتھ پرامن کارکنوں کی گرفتار آئین توہین ہے،سیالکوٹ میں آئین حقوق کی پامالی پر سپریم کورٹ سو موٹو نوٹس لے۔
```

**verdict:** keep
**note:** 

---

### 52 · urdu-wikipedia:122013

- **filter:** REJECT — too_short
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 168 chars, 29 words, 10 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.167, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=6
- **url:** https://ur.wikipedia.org/wiki/%D9%81%D9%84%DB%8C%DA%A9%20%D8%B4%D8%A7%DA%AF%D9%88%DB%8C%D9%84

```text
فلیک شاگویل ایک فحش اداکارہ ہے۔

متعلقہ روابط
فہرست فحش اداکارائیں
فحش فلم
فحش نگاری

حوالہ جات

1979ء کی پیدائشیں
انگریز فحش اداکارائیں
بقید حیات شخصیات
لندن کی شخصیات
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 53 · urdu-wikipedia:204677

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 301 chars, 50 words, 8 lines
- **script:** ratio 0.668 (arabic 0.668, latin 0.332)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=3
- **url:** https://ur.wikipedia.org/wiki/%D8%B3%DB%8C%D9%86-%D9%BE%D9%88%DB%8C%D8%B3

```text
سین-پویس ( فرانسیسی: Saint-Pavace) فرانس کا ایک فرانسیسی کمیون جو Canton of Le Mans-Nord-Campagne میں واقع ہے۔

تفصیلات
سین-پویس کا رقبہ 5.16 مربع کیلومیٹر ہے اور اس کی مجموعی آبادی 1,841 افراد پر مشتمل ہے۔

مزید دیکھیے
فرانس
فہرست فرانس کے شہر

حوالہ جات

Short description is different from Wikidata
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 54 · urdu-wikipedia:122009

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 245 chars, 38 words, 13 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.114, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=6
- **url:** https://ur.wikipedia.org/wiki/%D8%A7%DB%8C%D9%88%20%D8%A7%DB%8C%D9%86%D8%AC%D9%84

```text
ایو اینجل ایک فحش اداکارہ ہے۔

متعلقہ روابط
فہرست فحش اداکارائیں
فحش فلم
فحش نگاری

حوالہ جات

1983ء کی پیدائشیں
بقید حیات شخصیات
بوداپست کی اداکارائیں
کاروبار میں مجارستانی خواتین
کاروباری خواتین
مجارستانی فلمی اداکارائیں
ہنگیرین فحش اداکارائیں
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 55 · fineweb2-urd_Arab:<urn:uuid:7f6394eb-c91f-4f29-b1a3-40b7a1873c72>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 706 chars, 121 words, 4 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.057, dup-ngram 0.136
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://www.24urdu.com/01-Oct-2021/36441

```text
وزیراعظم سے ڈینش وزیر خارجہ کی ملاقات، دوطرفہ تعلقات، افغانستان کی صورتحال پر تبادلہ خیال
(24 نیوز)وزیراعظم عمران خان سے ڈنمارک کے وزیر خارجہ نے ملاقات کی ،ملاقات میں دوطرفہ تعلقات،ا فغانستان کی صورتحال پر تبادلہ خیال کیاگیا،وزیراعظم نے افغانستان میں انسانی بحران، معاشی تباہی کوروکنے کیلئے عالمی برادری کے کردار پر زور دیا۔
وزیراعظم عمران خان نے کہاکہ پرامن اور مستحکم افغانستان پاکستان اور خطے کیلئے بہت اہم ہے،افغانستان کے استحکام کیلئے جامع سیاسی ڈھانچہ اہم ہے،وزیراعظم عمران خان نے دونوں ممالک کے درمیان بڑھتے ہوئے تعاون پر اطمینان کااظہارکرتے ہوئے کہاکہ پاکستان تجارت، سرمایہ کاری ،توانائی کے شعبوں میں تعاون بڑھانے کیلئے پرعزم ہے ۔
یہ بھی پڑھیں: آرمی چیف جنرل باجوہ سے ڈنمارک کے وزیر خارجہ کی ملاقات
```

**verdict:** keep
**note:** 

---

### 56 · fineweb2-urd_Arab:<urn:uuid:e485d98a-5bc5-40d5-86e6-4dd46209db22>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 276 chars, 58 words, 2 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://hamidmirnews.com/%D8%AD%D8%A7%D8%B1%D8%AB-%D8%B1%D8%A4%D9%81-%D8%A8%DA%BE%DB%8C-%D8%B1%D9%88%D9%B9%DB%8C-%DA%AF%D8%B1%D9%88%D9%BE-%D9%85%DB%8C%DA%BA-%D8%B4%D8%A7%D9%85%D9%84/

```text
’معلوم نہ تھا تقریر سےبلاول پریشان ہونگے‘
وزیرِ خارجہ شاہ محمود قریشی کا کہنا ہے کہ مجھے نہیں معلوم تھا کہ میری ایک تقریر سے بلاول بھٹو زرداری اتنا پریشان ہو جائیں گے، پیپلز پارٹی کے قائد نے کہا کہ یہ مجھے بچپن سے جانتے ہیں، میں ان کو تب سے جانتا ہوں جب یہ جھڑکیاں کھاتے تھے۔۔
```

**verdict:** keep
**note:** 

---

### 57 · urdu-wikipedia:690779

- **filter:** REJECT — repetition:top_2gram, repetition:top_4gram
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 543 chars, 89 words, 19 lines
- **script:** ratio 0.911 (arabic 0.911, latin 0.089)
- **repetition:** dup_line 0.000, top-ngram 0.383, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=16
- **url:** https://ur.wikipedia.org/wiki/%D8%AC%D9%88%D8%A7%DB%81%D8%B1%20%D9%84%D8%A7%D9%84%20%D9%86%DB%81%D8%B1%D9%88%20%D8%A7%D8%B3%D9%B9%DB%8C%DA%88%DB%8C%D9%85%20%28%D8%B6%D8%AF%20%D8%A7%D8%A8%DB%81%D8%A7%D9%85%29

```text
جواہر لال نہرو اسٹیڈیم کے لیے آپ مندرجہ ذیل صفحات سے رجوع کر سکتے ہیں۔
جواہر لال نہرو اسٹیڈیم، گوا
جواہر لال نہرو اسٹیڈیم، دہلی
جواہر لال نہرو اسٹیڈیم، کویمبٹور
جواہر لال نہرو اسٹیڈیم، غازی آباد
جواہر لال نہرو اسٹیڈیم، چینائی
جواہر لال نہرو اسٹیڈیم، کوچی
جواہر لال نہرو اسٹیڈیم، شیلانگ
جواہر لال نہرو اسٹیڈیم، تروچراپلی

نہرو اسٹیڈیم، گوہاٹی
نہرو اسٹیڈیم، اندور
نہرو اسٹیڈیم، کوٹایم
نہرو اسٹیڈیم، پونے
نہرو اسٹیڈیم، درگاپور
نہرو اسٹیڈیم، تمکر
نہرو اسٹیڈیم، ہوبلی
نہرو اسٹیڈیم، شموگا

ضد ابہام صفحات
Short description is different from Wikidata
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 58 · fineweb2-urd_Arab:<urn:uuid:0333f057-306a-4cf9-9c42-49be760c25da>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 1214 chars, 230 words, 7 lines
- **script:** ratio 0.695 (arabic 0.695, latin 0.305)
- **repetition:** dup_line 0.000, top-ngram 0.030, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://roznamasahara.com/leaders-of-the-opposition-in-delhi-reached-the-palestinian-diplomat-and-offered-solidarity/

```text
نئی دہلی: اسرائیل اور فلسطین کے درمیان جاری جنگ کے بیچ حزب اختلاف کے رہنما دارالحکومت میں موجود فلسطینی سفارتکار پہنچ کر یکجہتی کا اظہار کیا۔ اس یکجہتی وفد میں سابق مرکزی وزیر منی شنکر ایئر اور بی ایس پی کے رکن پارلیمان دانش علی کے علاوہ سی پی آئی کے جنرل سکریٹری دیپانکر بھٹہ چاریہ بھی موجود تھے۔
Today, parliamentarians and politicians of different parties met Palestinian Ambassador & expressed deep concern for Palestinians people including innocent children being brutally killed in Gaza by Israeli forces. We demand interna’nal community to intervene & stop this madness. pic.twitter.com/C6VFO7rDw1
— Kunwar Danish Ali (@KDanishAli) October 16, 2023
دیپانکر بھٹہ چاریہ نے کہا کہ غزہ میں جنگ چل رہا ہے۔ وہاں فلسطین کے لوگ پریشانی میں ہے۔ غزہ میں جو حالات ہے اس سے لگتا ہے کہ دنیا تیسری عالمی جنگ کے دہانے پر کھڑی ہے۔
دیپانکر بھٹہ چارچہ نے مزید کہا کہ غزہ میں بے گناہ لوگوں کا قتل کیا جا رہا ہے۔ اس جنگ کے شکار معصوم فلسطینی بن رہے ہیں۔ ہم چاہتے ہیں کہ امن قائم ہوجائے، ہم یہاں فلسطین کے ساتھ کھڑا ہونے کے لئے آئے ہیں۔
یہ بھی پڑھیں: غزہ میں مرنے والوں کی تعداد بڑھ کر2670 ہوئی : وزارت
اس کے علاوہ فلسطینی سفارت کار پہنچنے والے رہنماؤں میں سماج وادی پارٹی کے جاوید علی خان، جے ڈی یو کے کے سی تیاگی بھی شامل تھے۔
```

**verdict:** keep
**note:** Urdu news quoting an English tweet; the Urdu is the substance

---

### 59 · fineweb2-urd_Arab:<urn:uuid:789dce8a-409a-40ce-95d6-f07f04af6a1c>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 778 chars, 175 words, 12 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.031, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://najoomi.com/urdu/star-sign/4435/%D8%AC%D9%88%D8%B2%D8%A7+%D9%85%D8%B1%D8%AF+%D8%A7%D9%88%D8%B1+%D8%AC%D9%88%D8%B2%D8%A7+%D8%B9%D9%88%D8%B1%D8%AA

```text
جوزا مرد اور جوزا عورت
ایسا جوڑا اچھی زندگی گزارتا ہے کیونکہ:
* دونوں آزاد طبع ہوتے ہیں۔
* ان کا ذہن تخلیقی ہوتا ہے۔
* یہ تخلیقی کاموں میں ایک دوسرے کی حوصلہ افزائی کرتے ہیں۔
* خاتون گھریلو امور کی طرف توجہ دیتی ہے۔
* مرد اپنی ذمہ داریاں نبھاتے ہیں۔
* یہ تقریبات میں آنا جانا پسند کرتے ہیں۔
* ایک دوسرے پر شک نہیں کرتے۔
* اپنی ملنسار اور نرم طبیعت کی وجہ سے لوگوں میں مقبول ہوتے ہیں۔ ایسے لوگوں کو چاہئے کہ ان حاسدوں سے ہوشیار رہیں جو ان کی خوش و خرم زندگی سے جلتے ہیں اور ان کا گھر برباد کرنے کی کوشش کرتے ہیں۔
ان لوگوں کو اپنے گھر کی خوش حالی اورسلامتی کے لئے ایک دوسرے کی ناگوار باتوں کو نظر انداز کرنا چاہئے۔
ان کی ذاتی اور گھر سے باہر کی مصروفیات کی وجہ سے اکثر ان کے بچوں کو ان کی مناسب توجہ نہیں ملتی، جس وجہ سے وہ خود سر ہو سکتے ہیں، لہٰذا یہ لوگ اس بات کو مد نظر رکھیں۔
```

**verdict:** keep
**note:** 

---

### 60 · urdu-wikipedia:43806

- **filter:** REJECT — html_residue
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 2777 chars, 519 words, 51 lines *(excerpt shows first 1500)*
- **script:** ratio 0.947 (arabic 0.947, latin 0.053)
- **repetition:** dup_line 0.033, top-ngram 0.042, dup-ngram 0.099
- **url** 0.000 · **html** 0.057 · **U+FFFD** 0.00000
- **stage 4:** whitespace=20
- **url:** https://ur.wikipedia.org/wiki/%D9%BE%D8%A7%DA%A9%D8%B3%D8%AA%D8%A7%D9%86%20%DA%A9%DB%8C%20%D8%A7%D9%86%D8%AA%D8%B8%D8%A7%D9%85%DB%8C%20%D8%AA%D9%82%D8%B3%DB%8C%D9%85

```text
پاکستان کو وفاقی دار الحکومت، چار صوبوں، آزاد کشمیر اور گلگت و بلتستان میں تقسیم کیا جاسکتا ہے جو اس کے بڑے بڑے علاقے ہیں۔ سرکاری طور پر پاکستان کے چار صوبے اور ایک وفاقی دار الحکومت ہے جس کے لیے آپ دیکھ سکتے ہیں: پاکستان کی انتظامی اکائیاں۔ مگر اس کے علاوہ چند علاقے ہیں جو ابھی باقاعدہ پاکستان میں شامل نہیں کیے جاتے اور ان کی آزاد حیثیت برقرار ہے جیسے آزاد کشمیر، قبائلی علاقے اور گلگت و بلتستان۔ لیکن اس کے باوجود یہ علاقے عملی طور پر پاکستان کے زیرِ اختیار ہیں چنانچہ انہیں پاکستان کا حصہ کہا جاتا ہے۔
فاٹا
پاکستان کے صوبوں کو اضلاع میں تقسیم کیا جاتا ہے۔ اگست 2000ء تک صوبوں کو ڈویژن اور ڈویژن کو اضلاع میں تقسیم کیا جاتا تھا مگر اگست 2000ء میں ڈویژن ختم کر دیے گئے اور اب صوبوں کو اضلاع میں تقسیم کیا جاتا ہے۔

پاکستان کی وزارتِ اطلاعات و نشریات کے ویب سائٹ (ویب سائٹ) کی معلومات (120مثلاً اضلاع) اور پاکستان کی وفاقی ادارہ برائے شماریات کے ویب سائٹ پر 14 نومبر 2009ء کو پائے جانے والی معلومات (مثلاً اضلاع کی تعداد 113) میں فرق تھا اور دونوں میں اضلاع کی تعداد اصل سے کم بتائی گئی تھی کیونکہ نئے اضلاع تشکیل پائے تھے۔ اسی طرح وزارتِ اطلاعات کے ویب سائٹ پر گلگت و بلتستان کا تذکرہ نہیں حالانکہ گلگت و بلتستان میں انتخابات بھی ہوچکے ہیں اور اس کا آرڈیننس جاری ہوئے اب کئی ماہ ہو گئے ہیں۔

یہی وجہ ہے کہ نیچے دی گئی معلومات ان دونوں مواقع الجال (ویب سائٹس) کے مدد کے علاوہ دوسرے ذرائع بشمول انگریزی ویکیپیڈیا سے مرتب کی گئی ہیں۔

نظامِ تقسیمِ پاکستان
پاکستان کو مختلف درجات میں تقسیم کیا گیا ہے۔ سب سے پہلا درجہ وفاق ہوتا ہے جو پوری ملک پر اختیار رکھتی ہے۔ دوسرا درجہ صوبہ ہے جو ایک مخصوص صوبے م
```

**verdict:** keep
**note:** 

---

### 61 · urdu-wikipedia:966553

- **filter:** REJECT — repetition:dup_5gram, repetition:dup_6gram, repetition:dup_7gram, repetition:dup_8gram, repetition:dup_9gram, repetition:dup_10gram
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 3458 chars, 684 words, 23 lines *(excerpt shows first 1500)*
- **script:** ratio 0.980 (arabic 0.980, latin 0.020)
- **repetition:** dup_line 0.000, top-ngram 0.042, dup-ngram 0.468
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=2
- **url:** https://ur.wikipedia.org/wiki/%D8%AC%DB%81%D8%A7%D9%86%DA%AF%DB%8C%D8%B1%20%D8%AE%D8%A7%D9%86%D8%B2%D8%A7%D8%AF%DB%81

```text
جہانگیر خانزادہ ایک پاکستانی سیاست دان ہیں جو اگست 2018 سے پنجاب کی صوبائی اسمبلی کے رکن ہیں۔ اس سے قبل وہ اکتوبر 2015 سے مئی 2018 تک پنجاب اسمبلی کے رکن رہے۔

ابتدائی زندگی اور تعلیم
جہانگیر خانزادہ 8 جولائی 1977ء کو شجاع خانزادہ کے گھر پیدا ہوئے۔

انہوں نے مارکیٹنگ میں ماسٹر آف بزنس ایڈمنسٹریشن کی ڈگری 2000 میں پریسٹن یونیورسٹی ، اسلام آباد سے حاصل کی۔

جہانگیر کے پاس برطانوی شہریت بھی ہے۔

عملی زندگی
بزنس گریجویٹ ہونے کے ناطے انہوں نے 2007ء سے 2015ء کے دوران سلک بینک کے نائب صدر کے طور پر خدمات انجام دیں۔

سیاسی زندگی
ایک سیاست دان جو کہ 2015ء سے 2018ء کے دوران رکن صوبائی اسمبلی پنجاب رہے ضمنی انتخابات میں منتخب ہونے کے بعد یہ نشست 2015ء میں اپنے والد کے خودکش حملے میں قتل ہونے کی وجہ سے خالی ہوئی تھی۔ امور اور کھیل؛ بطور وائس چیئرمین، ٹریفک ریفارمز پنجاب؛ ممبر، کابینہ کمیٹی برائے امن و امان؛ اور 2016ء سے 2018ء کے دوران پنجاب سیف سٹیز اتھارٹی کی کمیٹی کے ممبر کی حیثیت سے۔ وہ عام انتخابات 2018ء میں دوسری مدت کے لیے پنجاب اسمبلی میں واپس آئے ہیں۔ وہ سرکاری دوروں پر برطانیہ، چین، ترکی، اردن، فلسطین، آذربائیجان اور جنوبی کوریا جا چکے ہیں۔ ان کے والد بھی 2002ء سے 2015ء کے دوران مسلسل تین بار رکن پنجاب اسمبلی رہے اور 2002ء سے 2007ء کے دوران وزیر اعلیٰ پنجاب کے معاون خصوصی، وزیر برائے CMIT اور I&C، چیئرمین، وزیر اعلیٰ کی ٹاسک فورس برائے زراعت اور پولیس ٹریننگ ریفارمز کے دوران کام کیا۔ 2008ء سے 2013ء انہوں نے 16 اگست 2015ء کو اپنے قتل تک 2014ء سے 2015ء کے دوران وزیر برائے تحفظ ماحولیات اور وزیر داخلہ کے طور پر بھی خدمات انجام دیں۔ مسٹر جہانگیر خانزادہ کے پردادا، کیپٹن عجب خان نے ب
```

**verdict:** keep
**note:** clean politician biography

---

### 62 · fineweb2-urd_Arab:<urn:uuid:36b2888d-6383-484d-9e9f-e3ae7dfe5be5>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** code_switched
- **size:** 896 chars, 177 words, 14 lines
- **script:** ratio 0.892 (arabic 0.723, latin 0.169)
- **repetition:** dup_line 0.000, top-ngram 0.054, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://rekhtadictionary.com/meaning-of-daulat-lute-koelon-par-mohr?lang=ur

```text
تلاش شدہ نتائج
محفوظ شدہ الفاظ
"دَولَت لُٹے کوئِلوں پَر مُہْر" کے متعقلہ نتائج
دَولَت لُٹے کوئِلوں پَر مُہْر کے اردو معانی
- بجا اور باموقع خرچ کے موقع پر کفایت شعاری کرنے اور بے جا خرچ کی پروا نہ کرنے کو موقع پر بولتے ہیں
English meaning of daulat luTe ko.elo.n par mohr
- penny wise pound foolish
दौलत लुटे कोयलों पर मोहर के हिंदी अर्थ
- बजा और बामो का ख़र्च के मौक़ा पर किफ़ायत शिआरी करने और बेजा ख़र्च की पर्वा ना करने को मौक़ा पर बोलते हैं
اطلاع : ریختہ ڈکشنری کا یہ BETA ورژن ہے اور آزمائش کے لیے باضابطہ اشاعت سے پہلے جاری کیا گیا ہے۔کسی بھی قسم کے تضاد اور غلطیوں کی اصلاح کے لیے اپنے تجاویز و آرا ہمیں firstname.lastname@example.org پر ارسال کیجیے۔ یا رائے زنی کیجیے
حوالہ جات: ریختہ ڈکشنری کی ترتیب میں مستعمل مصادر اور مراجع کی فہرست دیکھیں ۔
رائے زنی کیجیے (دَولَت لُٹے کوئِلوں پَر مُہْر)
Delete 44 saved words?
کیا آپ واقعی ان اندراجات کو حذف کر رہے ہیں؟ انہیں واپس لانا ناممکن ہوگا۔
```

**verdict:** keep
**note:** Rekhta dictionary entry — Urdu lexical content with Hindi and English glosses, valuable

---

### 63 · fineweb2-urd_Arab:<urn:uuid:fced354b-1cd0-464d-b01a-055f630ac2aa>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 347 chars, 76 words, 9 lines
- **script:** ratio 0.587 (arabic 0.587, latin 0.413)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://pk.pornx.red/video7123_%D9%88%DB%81-%D8%AF%D9%84-%DA%A9%DB%92-%D8%AF%D9%88%D8%B1%DB%92-%DA%A9%D9%88-%D8%A7%DB%8C%DA%A9-%D8%A7%DA%86%DA%BE%D8%A7-%DA%88%DA%A9-%D8%AA%DA%A9-%DB%8C%DB%81-%D8%A8%D8%A7%DB%81%D8%B1-%D8%A2%D8%AA%D8%A7-%DB%81%DB%92-%D9%85%D9%86%DB%8C-%DA%A9%DB%92-%D8%A8%D8%A7%D8%B1%DB%92-%D9%85%DB%8C%DA%BA-%D9%85%D9%86%DB%81,-%D8%A7%D9%88%D8%B1-%D9%85%DB%8C%DA%BA-%D9%86%DB%92-%D8%A7%D8%B3%DB%92-%D9%BE%DB%8C%D9%86%DB%92-%DA%A9%DB%92.html

```text
PornX
PornX.Red
XNXX VIDEOS & PORN VIDEOS
وہ دل کے دورے کو ایک اچھا ڈک تک یہ باہر آتا ہے منی کے بارے میں منہ, اور میں نے اسے پینے کے
XNXX Free Videos
نوجوان Brunette اس کے پریمی کی طرف سے بلی میں چاٹ لیا تھا اور پچھواڑے میں بھاڑ میں جاؤ جب تک کہ یہ آزادی سے نہیں بھرتا ہے
HD
XNXX / XVIDEOS PORN HD PornX.Red
© 2021 PornX.Red - All rights reserved.
```

**verdict:** drop
**note:** porn spam

---

### 64 · urdu-wikipedia:363923

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 238 chars, 40 words, 8 lines
- **script:** ratio 0.810 (arabic 0.810, latin 0.190)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=4
- **url:** https://ur.wikipedia.org/wiki/%D9%81%D8%AE%D8%B1%D8%A7%D8%A8%D8%A7%D8%AF1

```text
فخراباد1 ایران کا ایک آباد مقام جو Sharifabad Rural District (Sirjan County) میں واقع ہے۔

تفصیلات
فخراباد1 کی مجموعی آبادی 1,313 افراد پر مشتمل ہے۔

مزید دیکھیے
ایران
فہرست ایران کے شہر

حوالہ جات

جغرافیہ شہرستان سیرجان کے نامکمل مضامین
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 65 · fineweb2-urd_Arab:<urn:uuid:49af7644-a522-4a0a-9fa9-9b6677ade1be>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 835 chars, 169 words, 6 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.050, dup-ngram 0.065
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://urdupoint2.com/archives/3046

```text
جمعرات کو یہاں محکمہ سروسز اینڈ جنرل ایڈمنسٹریشن کی طرف سے جاری کردہ نوٹیفکیشن میں کہا گیا ہے کہ "حکومت بلوچستان صوبے کے نئے امیدواروں کے ساتھ ساتھ خدمات انجام دینے والے سرکاری ملازمین کے حق میں 43 سال تک کی بالائی حد میں عمومی رعایت دینے پر خوش ہے۔”
نوٹیفکیشن میں کہا گیا ہے کہ اس کا اطلاق یکم جولائی 2022 سے 30 جون 2023 تک ہوگا۔
صوبائی وزیر خزانہ عبدالرحمن کھیتران نے کہا کہ "وزیر اعلیٰ بلوچستان عبدالقدوس بزنجو نے صوبے کے بے روزگار نوجوانوں کا دیرینہ مطالبہ پورا کر دیا ہے”۔
بلوچستان اسمبلی میں اراکین اسمبلی نے اس معاملے پر کئی بار آواز اٹھائی تھی، انہوں نے بے روزگار نوجوانوں پر زور دیا کہ وہ زیادہ سے زیادہ ملازمتوں کے لیے درخواست دیں۔
وزیر نے مزید کہا کہ حکومت غربت کے مسئلے کو ترجیحی بنیادوں پر حل کرنا چاہتی ہے۔
خیال رہے کہ سابق وزیراعلیٰ اسلم رئیسانی نے عمر کی زیادہ سے زیادہ حد 28 سے بڑھا کر 43 سال کرنے کا حکم جاری کیا تھا۔
```

**verdict:** keep
**note:** 

---

### 66 · fineweb2-urd_Arab:<urn:uuid:62b0d645-48a0-4b2a-971f-d53b127eba0f>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 3194 chars, 654 words, 3 lines *(excerpt shows first 1500)*
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.028, dup-ngram 0.055
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://kashmiruzma.net/%D9%85%D8%BA%D8%B1%D8%A8%DB%8C-%DB%81%D9%88%D8%A7%D8%A6%DB%8C%DA%BA-%D8%AC%D9%85%D9%88%DA%BA-%DA%A9%D8%B4%D9%85%DB%8C%D8%B1-%D9%85%DB%8C%DA%BA-%D8%AF%D8%A7%D8%AE%D9%84/

```text
سرینگر // محکمہ موسمیات کا کہنا ہے کہ جمعہ کی شب سے سنیچر کی شب تک کشمیر کے میدانی علاقوں میں 2سے 3انچ برف باری ہونے کا امکان ہے جبکہ بالائی علاقوں میں درمیانہ درجہ کی برف باری ہو سکتی ہے اور اتوار سے موسم بہتر ہونے کی توقع ہے۔جمعرات کو وادی میں مطلع ابرالود رہنے کے بیچ اگرچہ شبانہ درجہ حرارت میں قدرے بہتری آئی تاہم اس کے باوجود بھی یہاں سردی کی شدت برقرار ہے۔ شدید ٹھنڈ کا سلسلہ جاری رہنے کے باعث جھیل ڈل اوردیگرآبی ذخائر کی منجمد سطح میں او اضافہ دیکھنے کو نہیں ملا۔محکمہ موسمیات کے ڈائریکٹر سونم لوٹس نے کشمیر عظمیٰ سے بات کرتے ہوئے کہا کہ مغربی ہوائیں جموں کشمیر میں داخل ہوگئی ہیں اور موسمیاتی سسٹم اس بات کی نشاندہی کررہا ہے کہ کشمیر کے میدانی علاقوں 2سے3انچ برف پڑنے کا امکان ہے جبکہ کشمیر کے پہاڑی اور بالائی علاقوں سمیت لداخ کے زانسکار ، دراس ، کرگل ، منی مرگ میں درمیانہ درجہ کی برف باری ہوگی اور24 جنوری سے موسم ٹھیک ہونا شروع ہو جائے گا۔ انہوں نے مزید کہا کہ 23 اور24 جنوری کی رات کے درجہ حرات میں بہتری آگئی تاہم دن کے درجہ حرارت میں گراوٹ آنے کا امکان ہے ۔انہوں نے کہا کہ 24جنوری کے بعد کم سے کم درجہ حرات کے منفی 3سے4 رہنے کا امکان ہے ۔جمعہ کی صبح شہر سرینگر وادی کے تمام اضلاع میں موسم ابرالود رہا ۔ بادل رہنے کی وجہ سے شبانہ درجہ حرارت میں بہتری دیکھنے کو ملی اور جمعرات او ر جمعہ کی درمیانی رات کم سے کم درجہ حرات منفی 6.1ڈگری رہ گیا ۔،قاضی گنڈ میں منفی 6.2، پہلگام میں 7.0 ، کپوارہ میں منفی 4.8 ، کوکرناگ میں منفی 6.5 ، سیاحتی مقام گلمرگ میں منفی 6 ، اونتی پورہ میں منفی 8.0 ، شوپیاں میں منفی 8.5 ،اننت ناگ میں منفی 6.2 ، پلوامہ میں منفی 5.7 ، کولگام میں منفی 5.9 ، بانڈی پورہ می
```

**verdict:** keep
**note:** 

---

### 67 · fineweb2-urd_Arab:<urn:uuid:809542a0-8b39-45cd-81f3-b7d9d5104a1d>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 487 chars, 105 words, 4 lines
- **script:** ratio 0.631 (arabic 0.631, latin 0.369)
- **repetition:** dup_line 0.000, top-ngram 0.045, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://www.i2img.com/ur/jpg-to-webp

```text
لوڈنگ فائلوں کو اپ ڈیٹ کریں، براہ کرم انتظار کریں...
کیا JPG سے WEBP ؟
JPG to WEBP JPG امیجز کو WEBP فائل فارمیٹ میں تبدیل کرنے کا ایک مفت آن لائن ٹول ہے۔ اگر آپ ایک یا زیادہ JPG تصاویر کو WEBP میں تبدیل کرنا چاہتے ہیں، تو یہ آپ کا ٹول ہے۔ اس مفت آن لائن JPG سے WEBP کنورٹر کے ساتھ، آپ JPG امیجز کے کسی بھی بیچ کو ایک کلک میں جلدی اور آسانی سے WEBP میں تبدیل کر سکتے ہیں۔
This site uses cookies to ensure best user experience. By using the site, you consent to our Cookie, Privacy, Terms
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 68 · urdu-wikipedia:363316

- **filter:** REJECT — too_short
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 173 chars, 31 words, 6 lines
- **script:** ratio 0.759 (arabic 0.759, latin 0.241)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=4
- **url:** https://ur.wikipedia.org/wiki/%D9%81%D8%AF%D9%85

```text
فدم ایران کا ایک گاؤں جو Fathabad Rural District (Fars Province) میں واقع ہے۔

مزید دیکھیے
ایران
فہرست ایران کے شہر

حوالہ جات

جغرافیہ شہرستان قیر و کارزین کے نامکمل مضامین
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 69 · fineweb2-urd_Arab:<urn:uuid:bf7e4280-9a1c-447f-87cc-0a9608995a91>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 1033 chars, 216 words, 24 lines
- **script:** ratio 0.589 (arabic 0.589, latin 0.411)
- **repetition:** dup_line 0.065, top-ngram 0.064, dup-ngram 0.064
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://www.rekhta.org/ghazals/kabhii-milii-jo-tire-dard-kii-navaa-mujh-ko-azad-gulati-ghazals?lang=ur

```text
کبھی ملی جو ترے درد کی نوا مجھ کو
کبھی ملی جو ترے درد کی نوا مجھ کو
خموشیوں نے مجھی سے کیا جدا مجھ کو
بدن کے سونے کھنڈر میں کبھی جلا مجھ کو
میں تیری روح کی ضو ہوں نہ یوں بجھا مجھ کو
میں اپنی ذات کی ہم سائیگی سے ڈرتا ہوں
مرے قریب خدا کے لیے نہ لا مجھ کو
میں چپ ہوں اپنی شکست صدا کی وحشت پر
مجھے نہ بولنا پڑ جائے مت بلا مجھ کو
یہ میں تھا یا مرے اندر کا خوف تھا جس نے
تمام عمر دی تنہائی کی سزا مجھ کو
بھٹک رہا ہوں میں بے سمت راستوں کی طرح
کسی بھی سمت کا ہو راستہ دکھا مجھ کو
ہر اک نے دیکھا مجھے اپنی اپنی نظروں سے
کوئی تو میری نظر سے بھی دیکھتا مجھ کو
سمو کے آنکھوں میں امڈی گھٹائیں اے آزادؔ
وہ ایک درد کا صحرا بنا گیا مجھ کو
- کتاب : Dasht-e-Sada (Pg. 31)
Additional information available
Click on the INTERESTING button to view additional information associated with this sher.
About this sher
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Morbi volutpat porttitor tortor, varius dignissim.
rare Unpublished content
This ghazal contains ashaar not published in the public domain. These are marked by a red line on the left.
```

**verdict:** keep
**note:** Urdu ghazal; sufinama pages carry a Roman transliteration alongside

---

### 70 · urdu-wikipedia:122264

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 602 chars, 115 words, 16 lines
- **script:** ratio 0.959 (arabic 0.959, latin 0.041)
- **repetition:** dup_line 0.000, top-ngram 0.085, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=8, yeh=1
- **url:** https://ur.wikipedia.org/wiki/%D9%88%D8%A7%D8%B4%D9%86%DA%AF%D9%B9%D9%86%20%D9%85%DB%8C%D9%88%DA%86%D9%88%D9%84

```text
، نامی یہ کمپنی 2012 میں فارچون میگزین کی سرفہرست 1000 کمپنیوں میں شامل تھی۔ اس کا ہیڈکوارٹر سیئٹل، میں واقع ہے۔ فارچون کی رپورٹ کے مطابق 2012 میں اس میں سی ای او (CEO) کے عہدے پر Kerry K. Killinger کام کر رہے تھے۔

مزید دیکھیے
کمپنیوں کی فہرست

حوالہ جات

بیرونی روابط

2000ء کی دہائی کی اقتصادی تاریخ
2008ء میں تحلیل بینک
2009ء میں تحلیل بینک
ریاست واشنگٹن میں 1889ء کی تاسیسات
ریاست واشنگٹن میں قائم بینک
ریاست واشنگٹن میں 2009ء کی تحلیلات
ریاستہائے متحدہ کے کالعدم بینک
1889ء میں قائم ہونے والی امریکی کمپنیاں
1889ء میں قائم ہونے والے بینک
جے پی مورگن چیز
ویکی ڈیٹا سے مطابقت رکھنے والی مختصر تفصیل
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 71 · urdu-wikipedia:199785

- **filter:** REJECT — too_short, script_ratio
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 174 chars, 29 words, 6 lines
- **script:** ratio 0.610 (arabic 0.610, latin 0.390)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=4
- **url:** https://ur.wikipedia.org/wiki/%D8%B3%D8%AF%D9%88%D9%88%D9%88%D8%8C%20%D9%84%D8%A8%D8%B3%D8%B2%20%D8%B5%D9%88%D8%A8%DB%81

```text
سدووو، لبسز صوبہ پولینڈ کا ایک رہائشی علاقہ جو Gmina Trzebiechów میں واقع ہے۔

مزید دیکھیے
پولینڈ
فہرست پولینڈ کے شہر

حوالہ جات

Short description is different from Wikidata
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 72 · fineweb2-urd_Arab:<urn:uuid:276ef244-9f55-47cb-9764-73e77ee07281>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 3580 chars, 801 words, 18 lines *(excerpt shows first 1500)*
- **script:** ratio 0.962 (arabic 0.962, latin 0.038)
- **repetition:** dup_line 0.000, top-ngram 0.007, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://ur.andwedanced.com/bittersweet-truth-menace-among-us

```text
لوگ صرف سال کے اس وقت شکریہ ادا کرنے والے نہیں ہیں۔ Bittersweet بیل بہت شکر گزار ہے کہ آپ نے اس کو لگایا ہے اور آپ کے صحن میں ہر چیز کا گلا گھونٹنے کا فیصلہ کیا ہے۔
'بیٹر وِٹ وِیل' بیل نہیں بج رہی ہے؟ اوہ ، آپ نے اس پلانٹ کو دیکھا ہے ، یا تو سڑک کے کنارے یا ریک پر ہر موسم خزاں والے میگزین کے سرورق پر (کدو اور کڑوی چیز لازمی ساتھی لگتے ہیں)۔ یہ اور بیل کی چمکیلی پیلے رنگ کے بیجوں کی بھوسیوں کے ساتھ ڈھکی ہوئی بیل ہے جو سرخ رنگ کے بیجوں کو ظاہر کرنے کے لئے کھلتی ہے۔ رنگین امتزاج ناک آؤٹ ہے ، اسی وجہ سے ہر وہ شخص جو اپنے گھر میں رہنا چاہتا ہے سدرن رہائش موسم خزاں میں مینٹلز ، سائڈ بورڈز اور سامنے والے دروازوں کو سجانے کے لئے اس کا استعمال کرتا ہے۔
اس میں کیا غلط ہے؟ ٹھیک ہے ، پہلے آپ کو یہ جاننا ہوگا کہ وہاں دو دڑبلے ہیں۔ ایک اچھا آبائی ہے۔ دوسرا خوفناک بدمعاش ہے۔ پہلے ، بدمعاش کے بارے میں بات کریں۔
بدی Bittersweet
اورینٹل bittersweet ( سیلسٹرس مداری ) ، چین سے ، مشرقی امریکی جنگلات کے انتہائی گھناؤنے ، بے بنیاد اور تباہ کن ماتمی لباس میں شامل ہوگیا ہے۔ مجھے یاد ہے کرسمس کے وقت بچپن میں باہر جانا اور سامان ڈھونڈنے کے لئے گھنٹوں تلاش کرنا تھا۔ اب بیل مجھے ڈھونڈ رہی ہے۔ یہ پوری جنگل میں ، درختوں کا گلا گھونٹ کر مارتا ہے جیسے بالغ ڈاگ ووڈس یہ & quot show s خوبصورت بیر کے ساتھ کڈزو ہے۔
کچھ سال پہلے ، میں بڑی بے وقوفی کے ساتھ اورینٹل بٹر ویزٹ سے تیار کردہ چادر چڑھایا تھا۔ ایک ہی بیج زمین پر گر پڑا ہوگا ، کیونکہ اگلی موسم بہار میں یہ درندہ صفت پھل پھول اٹھا اور اس تک پہنچنے والی ہر چیز کو ہموار کرنا شروع کردیا۔ میں نے اسے کھینچنے کی کوشش کی ، لیکن زمین میں چھوڑا ہوا جڑ کا ہر ٹکڑا جلدی 
```

**verdict:** keep
**note:** 

---

### 73 · fineweb2-urd_Arab:<urn:uuid:7f2b2f39-f9a6-47f5-89e1-8111c4aa10b6>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 1797 chars, 399 words, 2 lines *(excerpt shows first 1500)*
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.025, dup-ngram 0.019
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://chitralexpress.com/updates/2022/03/21/63905/

```text
چترال(محکم الدین)سابق ضلع ناظم مغفرت شاہ نے کہا ہے ۔ کہ جماعت اسلامی چترال عام نوجوانوں کو لیڈر شپ کیلئے سامنے لانے پر یقین رکھتی ہے۔ جبکہ بعض دیگر پارٹیوں نے عوامی خد مت کے اس عہدے کیلئے شہزادوں کو پارٹی ٹکٹ دے دیےہیں ۔ جو کہ ان کا کام نہیں ہے ۔ اسلئے چترا ل کے عوا م خدمت کے جذبے سے سرشار نوجوان قیات کو سپورٹ کریں ۔ تاکہ چترال کے مسائل حل ہو سکیں ۔ ان خیالات کا اظہار انہوں نے ایون درخناندہ میں پیر کی شام ایک انتخابی کارنر میٹنگ سے خطاب کرتے ہوئے کیا ۔ اس موقع پر جماعت کے دیگر رہنما اور سنئیر کارکنان کے علاوہ بڑی تعداد میں مقامی لوگ موجود تھے ۔ مغفرت شاہ نے کہا کہ جماعت اسلامی نےتحصیل کونسل چترال کیلئے ایک آسان اور نوجوان امیدوار سامنے لانے کی کوشش کی ہے ۔جو وجیہ الدین کی صورت میں آپ کے سامنے حاضر ہے ۔ جس نے فروغ تعلیم کیلئے چترال میں نا قابل یقین خدمات انجام دی ہیں ۔ امیدوار تحصیل کونسل وجیہ الدین نے خطاب کرتے ہوئے کہا کہ چترال مسائل کا گڑھ ہے اور میں ان مسائل کو حل کرنےکے جذبے کے تحت آیا ہوں خدمت کو عبادت سمجھتا ہوں اور ان مسائل کو انشاللہ خوش اسلوبی سے حل کروں گا ۔ انہو ں نے کہا ۔ کہ جماعت اسلامی میں کسی کی مرضی نہیں چلتی اور نہ تحصیل کونسل میں چیر مین شپ الیکشن کیلئے میں خود میدان میں آیا ہوں ۔ بلکہ جماعت اکابریں نے یہ ذمہ داری مجھ پر ڈال دی ہے ۔ انہوں نے کہا کہ زندگی بھر ہم نے سوشل ورک کا تجربہ کیا ہے اور چترال کے موجودہ مسائل کے بارے میں معلومات اور ان کا حل میرے پاس موجود ہے۔میں عوام میں سے ہوں اور عوام ہی میں رہتا ہوں۔ اس لئے ووٹ کے حصول کیلئے کسی کو سبز باغ دیکھانےکا قائل نہیں ہوں ۔ لیکن یہ بات واضح کرنا مناسب سمجھا ہوں کہ میں عوام کا حق ضائع نہیں ہونے دونگا ۔ انہوں 
```

**verdict:** keep
**note:** 

---

### 74 · urdu-wikipedia:363925

- **filter:** REJECT — script_ratio
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 218 chars, 38 words, 8 lines
- **script:** ratio 0.645 (arabic 0.645, latin 0.355)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=4
- **url:** https://ur.wikipedia.org/wiki/%D9%81%D8%AE%D8%B1%D8%AF%D8%A7%D9%88%D8%AF

```text
فخرداود ایران کا ایک گاؤں جو Piveh Zhan Rural District میں واقع ہے۔

تفصیلات
فخرداود کی مجموعی آبادی 756 افراد پر مشتمل ہے۔

مزید دیکھیے
ایران
فہرست ایران کے شہر

حوالہ جات

Short description is different from Wikidata
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 75 · urdu-wikipedia:1072876

- **filter:** REJECT — too_short
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 193 chars, 34 words, 6 lines
- **script:** ratio 0.940 (arabic 0.940, latin 0.060)
- **repetition:** dup_line 0.000, top-ngram 0.171, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=4
- **url:** https://ur.wikipedia.org/wiki/%DA%AF%D8%B1%DB%8C%D9%B9%20%D8%A8%D8%A7%D8%B1

```text
گریٹ بار (لاطینی: Great Barr) مملکت متحدہ کا ایک مضافات جو مغربی مڈلینڈز (کاؤنٹی) میں واقع ہے۔

مزید دیکھیے
مملکت متحدہ
مملکت متحدہ کے شہروں کی فہرست

حوالہ جات

برمنگہم، مغربی مڈلینڈز کے علاقے
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 76 · urdu-wikipedia:121168

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 299 chars, 55 words, 8 lines
- **script:** ratio 0.707 (arabic 0.707, latin 0.293)
- **repetition:** dup_line 0.000, top-ngram 0.080, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=2
- **url:** https://ur.wikipedia.org/wiki/%DA%A9%D9%88%D8%B3%D8%AA%D9%88%DA%98%DB%92

```text
کوستوژے () ایک فرانسیسی کمیون ہے جو فرانس میں واقع ہے۔ اس کی مجموعی آبادی 134 افراد پر مشتمل ہے، یہ Canton of Prats-de-Mollo-la-Preste میں واقع ہے۔

نگار خانہ

متعلقہ روابط
فہرست فرانس کے شہر

حوالہ جات

کامنز زمرہ جس کا ربط ویکی ڈیٹا پر ہے
صفحات مع گراف
Short description is different from Wikidata
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 77 · urdu-wikipedia:428710

- **filter:** REJECT — too_short
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 133 chars, 25 words, 10 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=7
- **url:** https://ur.wikipedia.org/wiki/1241%DA%BE

```text
واقعات

ولادتیں

وفیات

مزید دیکھیے
ہجری شمسی

حوالہ جات

بیرونی روابط
ہجری تاریخ کو شمسی سال سے بدلیں
ہجری سال کی اسلام میں اہمیت

4
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 78 · urdu-wikipedia:363620

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 219 chars, 40 words, 8 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.155, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=4
- **url:** https://ur.wikipedia.org/wiki/%D9%81%DB%8C%D8%A6%D8%B1%DB%81%D9%88%D9%86%D8%8C%20%D8%B3%D8%A7%D8%B3%DA%A9%D8%A7%D9%B9%D9%88%D9%86

```text
فیئرہون، ساسکاٹون کینیڈا کا ایک محلہ جو ساسکچیوان میں واقع ہے۔

تفصیلات
فیئرہون، ساسکاٹون کی مجموعی آبادی 4,990 افراد پر مشتمل ہے۔

مزید دیکھیے
کینیڈا
فہرست کینیڈا کے شہر

حوالہ جات

کامنز زمرہ جس کا ربط ویکی ڈیٹا پر ہے
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 79 · fineweb2-urd_Arab:<urn:uuid:1d3bb729-0ad9-4019-a4e5-f873f12e0d87>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 863 chars, 196 words, 3 lines
- **script:** ratio 0.995 (arabic 0.995, latin 0.005)
- **repetition:** dup_line 0.000, top-ngram 0.037, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://dailymanzar.com/2022/09/23/%DB%8C%DB%81-%D9%81%D8%B1%D8%AF-%D8%AC%D8%B1%D9%85-%DB%81%DB%92-%D8%AC%D9%88-%D9%85%D9%88%D9%82%D9%88%D9%81-%DB%81%DB%92-%D9%81%D9%82%DB%81%D8%A7%D8%A1/

```text
کراچی: معروف قانون دانوں کا خیال ہے کہ اسلام آباد ہائی کورٹ نے پی ٹی آئی چیئرمین عمران خان کے بیان حلفی کے مطابق فرد جرم عائد کرنے کے لیے 3 اکتوبر کی تاریخ مقرر کی ہے۔
جیو نیوز کے پروگرام آج شاہ زیب خانزادہ کے ساتھ میں گفتگو کرتے ہوئے جسٹس (ر) شائق عثمانی نے کہا کہ عمران خان کے وکیل حامد خان کے بیان کو دیکھتے ہوئے غیر مشروط معافی سے متعلق مؤقف برقرار ہے۔ جسٹس عثمانی نے کہا کہ بظاہر جسٹس اطہر من اللہ نے فرد جرم 3 اکتوبر تک ملتوی کرتے ہوئے 29 ستمبر تک عمران کا بیان طلب کر لیا، اس کیس میں چیف جسٹس اکیلے نہیں دیگر ججز بھی ہیں اور ان سب کو حلف نامے پر غور کرنا ہوگا۔ آیا یہ غیر مشروط معافی کے معیار کو پورا کرتا ہے یا نہیں۔
جسٹس رشید اے رضوی نے یہ بھی کہا کہ فی الحال کچھ بھی حتمی نظر نہیں آتا۔ انہوں نے مزید کہا کہ توہین کے ملزم کو خود کو عدالت کے رحم و کرم پر ڈالنے کی ضرورت ہے اور IHC نے بظاہر کارروائی حلف نامہ کے لیے نہیں بلکہ فرد جرم کے لیے ملتوی کر دی ہے۔
```

**verdict:** keep
**note:** 

---

### 80 · fineweb2-urd_Arab:<urn:uuid:731dbfbe-9197-4d53-af9d-4a3c4aaf4e49>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 828 chars, 155 words, 6 lines
- **script:** ratio 0.570 (arabic 0.570, latin 0.430)
- **repetition:** dup_line 0.000, top-ngram 0.036, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://acenews.pk/urdu/102951/

```text
علی سدپارہ کے بیٹے ساجد سدپارہ نے والد کے ساتھ گزاری جانے والی آخری رات کی ویڈیو اپنے ٹوئٹر اکاؤنٹ پر شیئر کی ہے، ساجد علی سدپارا نے ویڈیو کے کیپشن میں لکھا کہ ٹیم اور میرے والد کے ساتھ آخری اور میری زندگی کی دشوار ترین رات۔
The last & hardest night of my life, together with team & my beloved father #AliSadpara
Fake account @Saajid_Sadpara will download & reproduce this as well. It’s painful but I have to share these to stop fake IDs. Please help @falamb3 @AliZafarsays @asmashirazi @fawadchaudhry pic.twitter.com/vM0nSqGmUu
— Sajid Ali Sadpara (@sajid_sadpara) February 20, 2021
یہ بھی پڑھیں: کوہ پیما علی سدپارہ سوشل میڈیا پر ٹاپ ٹرینڈ بن گیا
ویڈیو شیئر کرنے کے ساتھ ساتھ ساجد علی سدپارہ نے صارفین کو جعلی اکاؤنٹ کو فالو کرنے سے بھی خبردار کیا اور کہا کہ ان کی ویڈیوز جعلی اکاؤنٹ سے شیئر کی جا رہی ہیں جو سراسر غلط فعل ہے۔
```

**verdict:** keep
**note:** 

---

### 81 · fineweb2-urd_Arab:<urn:uuid:a87307f1-324e-4b70-aeb7-904350aa781b>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 4161 chars, 852 words, 19 lines *(excerpt shows first 1500)*
- **script:** ratio 0.680 (arabic 0.680, latin 0.320)
- **repetition:** dup_line 0.000, top-ngram 0.008, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://awaam.wordpress.com/

```text
A Company Registered under Section 42 of Companies Ordinance 1984. Corporate Universal Identification No. 0073421
Vision 21 is Pakistan based non-profit, non- partisan Socio-Political organisation. We work through research and advocacy. Our Focus is on Poverty and Misery Alleviation, Rights Awareness, Human Dignity, Women empowerment and Justice as a right and obligation.
We act and work side by side with the deprived and have-nots.
We invite you to join us in this mission. We welcome your help. We welcome your comments and suggestions. If you are interested in writing on Awaam, please contact us at: email@example.com
↑ Grab this Headline Animator
Syed Hammad Raza
With the month of October coming to an end, the hype about Pakistan Tehreek-e-Insaf’s Protest to be held on 2nd November, is getting bigger and bigger. Instilled with multiple anticipations about what Khan will bring, the dusty air of capital is becoming even foggier. With the slogan of “Aarahahy Khan, kaanprahayhain be-eman” the PTI fans are all set for the protest. However while there is a sudden thrill in capital air on one hand, on the other hand there is a mild concern of Capital residents over closing of important routes and a possible hindrance in daily life activities.
Read More
سید حماد رضا
کل شام جب آفس سے گھر کی جانب روانہ ہوا تو راستے میں ایک معصوم سی گڑیا نظر آئی۔اس کی عمر قریب چھ سال تھی، کاندھے پہ بیگ، چھرے پہ ٹیچر کی جانب سے دیا گیا ستارہ اور ہاتھ میں پانی کی بوتل تھی۔ اپنے بابا کی انگلی تھامے وہ اچھ
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 82 · urdu-wikipedia:1005104

- **filter:** REJECT — too_short
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 186 chars, 34 words, 6 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.151, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=1
- **url:** https://ur.wikipedia.org/wiki/%D8%AF%D8%B1%DB%8C%D8%A7%D8%A6%DB%92%20%D8%B3%D8%A8%D8%B1%D9%86%D8%A7%20%D8%B1%DB%8C%DA%A9%DA%BE%D8%A7

```text
دریائے سبرنا ریکھا (نیز معروف بہ سورنا ریکھا ندی) بھارتی ریاستوں جھارکھنڈ، مغربی بنگال اور اوڈیشا سے بہتا ہے۔

حوالہ جات

مغربی بنگال کے دریا
اڑیسہ کے دریا
بھارت کے دریا
جھاڑکھنڈ کے دریا
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 83 · urdu-wikipedia:428720

- **filter:** REJECT — too_short
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 133 chars, 25 words, 10 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=7
- **url:** https://ur.wikipedia.org/wiki/1251%DA%BE

```text
واقعات

ولادتیں

وفیات

مزید دیکھیے
ہجری شمسی

حوالہ جات

بیرونی روابط
ہجری تاریخ کو شمسی سال سے بدلیں
ہجری سال کی اسلام میں اہمیت

5
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 84 · fineweb2-urd_Arab:<urn:uuid:31fb4770-1e6f-42a6-8491-d60aa4d049d4>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 545 chars, 113 words, 2 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.088, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://dailypakistan.com.pk/29-Sep-2017/650816

```text
سرفراز احمدنے قومی ٹیسٹ ٹیم کی قیادت کرنیوالے5ویں وکٹ کیپرکااعزازحاصل کرلیا
ابو ظہبی (نیٹ نیوز) سرفراز احمد ٹیسٹ کرکٹ میں قومی ٹیم کی قیادت کرنے والے پاکستان کے پانچویں وکٹ کیپر بن گئے۔ انہوں نے یہ اعزاز سری لنکا کے خلاف سیریز کے پہلے ٹیسٹ میچ میں حاصل کیا۔ اس سے قبل امتیاز احمد، وسیم باری، راشد لطیف اور معین خان بھی بطور وکٹ کیپر ٹیسٹ ٹیم کی قیادت کا اعزاز حاصل کر چکے ہیں۔ سرفراز احمد کو اب تک 9 ون ڈے اور 11 ٹی ٹونٹی انٹرنیشنل میچز میں ٹیم کی قیادت کا موقع ملا ہے۔ مصباح الحق کی ریٹائرمنٹ کے بعد انہیں ٹیسٹ ٹیم کا کپتان بھی بنا دیا گیا تھا۔
```

**verdict:** keep
**note:** 

---

### 85 · urdu-wikipedia:182860

- **filter:** REJECT — too_short, script_ratio
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 177 chars, 29 words, 6 lines
- **script:** ratio 0.625 (arabic 0.625, latin 0.375)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=4
- **url:** https://ur.wikipedia.org/wiki/%D8%A8%D8%B1%D8%B2%D8%B2%D9%86%D9%86%DB%92%D8%8C%20%D9%86%DB%8C%D8%B3%D8%A7%20%DA%A9%D8%A7%D8%A4%D9%86%D9%B9%DB%8C

```text
برززننے، نیسا کاؤنٹی پولینڈ کا ایک رہائشی علاقہ جو Gmina Skoroszyce میں واقع ہے۔

مزید دیکھیے
پولینڈ
فہرست پولینڈ کے شہر

حوالہ جات

Short description is different from Wikidata
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 86 · urdu-wikipedia:389650

- **filter:** REJECT — repetition:top_2gram
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 949 chars, 130 words, 35 lines
- **script:** ratio 0.929 (arabic 0.929, latin 0.071)
- **repetition:** dup_line 0.000, top-ngram 0.474, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=31
- **url:** https://ur.wikipedia.org/wiki/%D9%88%D8%A7%D8%B4%D9%86%DA%AF%D9%B9%D9%86%20%DA%A9%D8%A7%D8%A4%D9%86%D9%B9%DB%8C

```text
واشنگٹن کاؤنٹی (Washington County) ریاستہائے متحدہ امریکا میں 30 کاؤنٹیوں کا نام ہے جو پہلے امریکی صدر جارج واشنگٹن کے نام پر ہے۔

کاؤنٹیاں

واشنگٹن کاؤنٹی، الاباما
واشنگٹن کاؤنٹی، آرکنساس
واشنگٹن کاؤنٹی، کولوراڈو
واشنگٹن کاؤنٹی، فلوریڈا
واشنگٹن کاؤنٹی، جارجیا
واشنگٹن کاؤنٹی، ایڈاہو
واشنگٹن کاؤنٹی، الینوائے
واشنگٹن کاؤنٹی، انڈیانا
واشنگٹن کاؤنٹی، آئیووا
واشنگٹن کاؤنٹی، کنساس
واشنگٹن کاؤنٹی، کینٹکی
واشنگٹن پیرش، لوزیانا
واشنگٹن کاؤنٹی، مینے
واشنگٹن کاؤنٹی، میری لینڈ
واشنگٹن کاؤنٹی، مینیسوٹا
واشنگٹن کاؤنٹی، مسیسپی

واشنگٹن کاؤنٹی، مسوری
واشنگٹن کاؤنٹی، نیبراسکا
واشنگٹن کاؤنٹی، نیو یارک
واشنگٹن کاؤنٹی، شمالی کیرولائنا
واشنگٹن کاؤنٹی، اوہائیو
واشنگٹن کاؤنٹی، اوکلاہوما
واشنگٹن کاؤنٹی، اوریگون
واشنگٹن کاؤنٹی، پنسلوانیا
واشنگٹن کاؤنٹی، روڈ آئلینڈ
واشنگٹن کاؤنٹی، ٹینیسی
واشنگٹن کاؤنٹی، ٹیکساس
واشنگٹن کاؤنٹی، یوٹاہ
واشنگٹن کاؤنٹی، ورمونٹ
واشنگٹن کاؤنٹی، ورجینیا
واشنگٹن کاؤنٹی، وسکونسن

ضد ابہام صفحات
Short description is different from Wikidata
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 87 · urdu-wikipedia:921538

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 5816 chars, 1219 words, 34 lines *(excerpt shows first 1500)*
- **script:** ratio 0.999 (arabic 0.999, latin 0.001)
- **repetition:** dup_line 0.000, top-ngram 0.011, dup-ngram 0.008
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=48
- **url:** https://ur.wikipedia.org/wiki/%D8%B3%D9%82%D9%88%D8%B7%20%D8%A8%D8%BA%D8%AF%D8%A7%D8%AF%20%281917%29

```text
سقوط بغداد (11 مارچ 1917) میسوپوٹیمیا مہم کے دوران پیش آیا ،جو پہلی جنگ عظیم میں برطانوی ہندوستانی فوج اور عثمانی ترک سلطنت کی افواج کے مابین لڑی گئی۔

جنرل سر فریڈرک اسٹینلے موڈے کی آمد
29 اپریل 1916 کو کوت گیریژن کے ہتھیار ڈالنے کے بعد ، میسوپوٹیمیا میں برطانوی فوج کا ایک بہت بڑا جائزہ لیا گیا۔ ایک نئے کمانڈر ، لیفٹیننٹ جنرل سر فریڈرک اسٹینلے ماؤڈ کو ، برطانیہ کی فوجی ساکھ کو بحال کرنے کا کام سونپا گیا تھا۔

جنرل موڈے نے اپنی فوج کی تعمیر نو میں 1916 کا باقی وقت صرف کیا۔ اس کی زیادہ تر فوجیں ہندوستان سے بھرتی کی گئیں اور پھر سمندر کے ذریعہ بصرہ بھیج دی گئیں۔ جب ان فوجیوں کو تربیت دی جارہی تھی ، برطانوی فوجی انجینئروں نے ساحل سے بصرہ اور اس سے آگے تک ایک فیلڈ ریلوے بنائی۔ جنرل موڈے نے مسلح ندی کشتیاں اور ندی سپلائی کرنے والے جہازوں کی ایک چھوٹی سی قوت بھی حاصل کی۔

انگریزوں نے اپنی نئی مہم 13 دسمبر 1916 کو شروع کی۔ برطانویوں کے پاس تقریبا 50،000 اچھی تربیت یافتہ اور اچھی طرح سے لیس فوجی دستے تھے: زیادہ تر برٹش انڈین انڈین ایکسپیڈیشنری فورس ڈی کے فوجی دستے کے ساتھ مل کر برٹش آرمی کے 13 ویں (مغربی) ڈویژن کے ساتھ میسوپوٹیمیا ایکسپیڈیشنری فورس تشکیل دیتے ہیں۔ ہندوستانی III کور (جس کو ٹائیگرز کور بھی کہا جاتا ہے) کی ہندوستانی ڈویژنوں میں برطانوی فوج کے یونٹ شامل تھے۔ جنرل خلیل پاشا کی مجموعی کمانڈ میں عثمانی افواج کم تھیں ، شاید تقریبا، 25،000 تھیں۔

بغداد پر مارچ

اس مہم پر انگریزوں کو کوئی دھچکا نہیں تھا۔ جنرل موڈے نے دریائے دجلہ کے دونوں اطراف میں پیش قدمی کرتے ہوئے محتاط انداز میں آگے بڑھا۔ اس نے اپنا عرفی نام سیسٹیمیٹک جو حاصل کیا۔ عثمانی افواج نے ایک مضبوط قلعے کے خلاف مقاب
```

**verdict:** keep
**note:** 

---

### 88 · urdu-wikipedia:363239

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** code_switched
- **size:** 288 chars, 55 words, 7 lines
- **script:** ratio 1.000 (arabic 0.804, latin 0.196)
- **repetition:** dup_line 0.000, top-ngram 0.056, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=4
- **url:** https://ur.wikipedia.org/wiki/%D9%81%DB%8C%D8%A8%DA%A9%DB%8C

```text
فیبکی سلووینیا کا ایک آباد مقام و cultural heritage site in Slovenia جو Inner Carniola میں واقع ہے۔

تفصیلات
فیبکی کا رقبہ 1.3 مربع کیلومیٹر ہے اور اس کی مجموعی آبادی 11 افراد پر مشتمل ہے اور 634.6 میٹر سطح سمندر سے بلندی پر واقع ہے۔

مزید دیکھیے
سلووینیا
فہرست سلووینیا کے شہر

حوالہ جات
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 89 · fineweb2-urd_Arab:<urn:uuid:80fadbd6-029b-4c37-af61-d67625e9c8c1>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 1305 chars, 278 words, 7 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.112, top-ngram 0.046, dup-ngram 0.132
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://urdu.92newshd.tv/about/%D8%B9%DB%8C%D8%AF-%D8%A7%D9%84%D8%A7%D8%B6%D8%AD%DB%8C-31-%D8%AC%D9%88%D9%84%D8%A7%D8%A6%DB%8C-%D8%A8%D8%B1%D9%88%D8%B2-%D8%AC%D9%85%D8%B9%DB%81-%DB%81%D9%88%DA%AF%DB%8C-%D9%81%D9%88%D8%A7

```text
عید الاضحی کب ہوگی، ذی الحج کا چاند کب نظر آئے گا، فواد چودھری نے بتا دیا
عید الاضحی کب ہوگی، ذی الحج کا چاند کب نظر آئے گا، فواد چودھری نے بتا دیا
اسلام آباد ( 92 نیوز) عید الاضحی، ذی الحج کا چاند کب نظر آئے گا ، وفاقی وزیر سائنس اینڈ ٹیکنالوجی فواد چودھری نے نیا پنڈورا باکس کھول دیا۔سماجی رابطہ کی ویب سائٹ ٹوئٹر پر ایک بار پھر انٹری دی اور پیشگوئی کی کہ عید الضحیٰ 31 جولائی 2020 بروزجمعہ ہوگی۔
ٹوئٹ میں فواد چودھری نے کہا کہ وزارت سائنس و ٹیکنالوجی کے کلینڈر کے مطابق عید الضحیٰ 31 جولائی کو ہوگی ، 21 جولائی کوذی الحج کا چاند نظرآئے گا ۔ذی الحج کا چاند کراچی اوراس کے ارد گرد علاقوں میں دوربین سے واضح طور پر نظرآئے گا جبکہ کئی علاقوں میں آنکھ سے بھی دیکھا جاسکے گا۔
انہوں نے شہریوں کو مشورہ دیا کہ چاند کی لوکیشن کیلئے آپ“رویت”ایپ بھی استعمال کرسکتے ہیں،فواد چودھری نے عیدالفطر کے چاند کی بھی پیشگوئی کی تھی جو سچ ثابت ہوگئی تھی۔
۔ فواد چوہدری نے اسلام آباد میں پریس کانفرنس کرتے ہوئے اتوار کو عید کے چاند کا اعلان کیا تھا ، ساتھ ہی کہا تھا کہ مذہبی تہوار کے موقع پر ہمیشہ چاند کا تنازعہ رہتا ہے، تاہم اب سائنسی ترقی سے چاند دیکھنے کا مسئلہ حل ہوگیا ہے، 1974 میں رویت ہلال کمیٹی بنی تھی، امید تھی مسئلہ حل ہوگا مگر رویت ہلال کمیٹی ہمیشہ تنازعات کا شکار رہی۔
انہوں نے بتایا تھا کہ 22 مئی کی رات 10 بجکر 39 منٹ پر شوال کے چاند کی پیدائش ہوئی جو آج غروب آفتاب کے بعد دوربین سے چاند واضح نظر آ جائے گا۔
```

**verdict:** keep
**note:** 

---

### 90 · fineweb2-urd_Arab:<urn:uuid:06cda779-97cc-4e8c-a42f-82110879bee7>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 364 chars, 71 words, 9 lines
- **script:** ratio 0.578 (arabic 0.578, latin 0.422)
- **repetition:** dup_line 0.000, top-ngram 0.066, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://pk.xxxbestporn.net/video7794_%D8%A7%DB%8C%DA%A9%D8%B3-%D8%A7%DB%8C%DA%A9%D8%B3-%D8%A7%DB%8C%DA%A9%D8%B3-%D8%A7%DA%86%DA%BE%DB%92-%D9%86%D9%88%D8%AC%D9%88%D8%A7%D9%86%D9%88%DA%BA-%DA%A9%DB%92-%D8%B3%D8%A7%D8%AA%DA%BE-%D8%AC%D9%88-%D8%AC%D8%A7%D9%86%D8%AA%DB%92-%DB%81%DB%8C%DA%BA-%DA%A9%DB%81-%D9%85%D8%B4%DA%A9%D9%84-%D8%B3%DB%92-%D8%A8%DA%BE%D8%A7%DA%91-%D9%85%DB%8C%DA%BA-%D8%AC%D8%A7%D8%A4-%DA%A9%D8%B3-%D8%B7%D8%B1%D8%AD-%D8%AC%D8%A7%D9%86%D8%AA%DB%92-%DB%81%DB%8C%DA%BA.html

```text
XXXPorn
XXXBestPorn.Net
XNXX VIDEOS & PORN VIDEOS
ایکس ایکس ایکس اچھے نوجوانوں کے ساتھ جو جانتے ہیں کہ مشکل سے بھاڑ میں جاؤ کس طرح جانتے ہیں
XNXX Free Videos
تین ویشیا رومانس محبت میں ان کے نوجوان محبت کرنے والوں کے ساتھ جہنم میں بھاڑ میں جاؤ جب تک کہ وہ مزید نہیں کر سکتے ہیں
HD
XNXX / XVIDEOS PORN HD XXXBestPorn.Net
© 2021 XXXBestPorn.Net - All rights reserved.
```

**verdict:** drop
**note:** porn spam

---

### 91 · urdu-wikipedia:361752

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 307 chars, 52 words, 9 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.293, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=4
- **url:** https://ur.wikipedia.org/wiki/%DA%AF%D8%B1%D8%A7%D8%AF%D8%B3%DA%A9%D9%88%20%D8%A8%D9%84%D8%AF%DB%8C%DB%81

```text
گرادسکو بلدیہ جمہوریہ مقدونیہ کا ایک جمہوریہ مقدونیہ کی بلدیات جو جمہوریہ مقدونیہ میں واقع ہے۔

تفصیلات
گرادسکو بلدیہ کا رقبہ 236.19 مربع کیلومیٹر ہے اور اس کی مجموعی آبادی 3,760 افراد پر مشتمل ہے۔

مزید دیکھیے
جمہوریہ مقدونیہ
فہرست جمہوریہ مقدونیہ کے شہر

حوالہ جات

گرادسکو بلدیہ
جمہوریہ مقدونیہ کی بلدیات
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 92 · fineweb2-urd_Arab:<urn:uuid:ee8fdcb9-143d-4c6a-bace-37994c4460d4>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 2839 chars, 587 words, 26 lines *(excerpt shows first 1500)*
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.019, dup-ngram 0.117
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://www.express.pk/story/2251406/1/

```text
- محکمہ جنگلات سندھ نے بنڈل اور بڈو جزیروں کو صوبے کی ملکیت قرار دے دیا
- قطار میں لگ کر روزانہ 38,000 روپے کمانے والا شخص
- فیس بک اورانسٹاگرام کی این ایف ٹی کی تیاری اور فروخت میں دلچسپی
- صدر جوبائیڈن نے امریکا میں پہلی مسلم خاتون کو وفاقی جج نامزد کردیا
- افغانستان میں شکست کے بعد را کے گروپس پاکستان میں دہشتگردی چاہتے ہیں، وزیر داخلہ
- خفیہ کیمروں سے خواتین کی برہنہ ویڈیو بنانے والے پولیس افسر کو 3 سال قید
- فیصل آباد میں ڈکیتی کے دوران اغواء ہونے والی خاتون سے جنسی زیادتی نہ ہونے کا انکشاف
- لاہور دھماکے کے بعد لوٹ مار کرنے والوں پر مقدمہ درج
- بیرون ملک جانے والوں کے لیے بوسٹر ڈوز مفت کردی گئی
- ملائیشیا کے سابق وزیراعظم مہاتیر محمد تشویشناک حالت میں اسپتال میں داخل
- گزشتہ ہفتے ڈالر، ریال، یورو اور پاؤنڈ کی قدر میں کمی ریکارڈ
- کورونا ویکسین تجربے کے لئے لے جائےجانے والے بندرفرارہوگئے
- پی ایس ایل 7 کے ریزرور پول میں تبدیلیوں پر فرنچائزز کو تحفظات
- عالمی برادری کی ذمہ داری ہے کہ وہ افغانوں کو فوری امداد فراہم کرے، وزیراعظم
- ٹنڈوالہیار میں ایم کیو ایم کارکن کے قتل کے سوگ میں کاروبار بند
- اسلام آباد ائیرپورٹ پر مسافر کے پیٹ سے 111 منشیات کے کیپسولز برآمد
- مالی سال کی پہلی ششماہی، کرنٹ اکاؤنٹ خسارہ 9 ارب ڈالر سے تجاوز
- جج کو اللہ کی ذات اور آئین کا ڈر ہونا چاہیے، جسٹس قاضی فائز عیسٰی
- سرگودھا میں بااثر افراد نے مبینہ طور پر 3 سگی بہنیں اغوا کرلیں
- ایچ بی ایل پی ایس ایل 7کے افتتاحی میچ کے تمام ٹکٹ فروخت
اسلام آباد: وزارت اطلاعات و نشریات نے مسلم لیگ (ن) کی نائب صدر مریم نواز کے انکشافات پر تحقیقات کیلئے کمیٹی قائم کردی۔
ایکسپریس نیوز کے مطابق گزشتہ روز مسلم لیگ (ن)
```

**verdict:** keep
**note:** 

---

### 93 · urdu-wikipedia:364108

- **filter:** REJECT — too_short, script_ratio
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 174 chars, 28 words, 6 lines
- **script:** ratio 0.542 (arabic 0.542, latin 0.458)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=4
- **url:** https://ur.wikipedia.org/wiki/%D9%81%D8%A7%D9%84%DB%8C%DA%A9%DB%8C%DA%A9%DB%8C-%D9%BE%D8%A7%D8%B1%DA%A9%DB%8C%D9%84%D8%A7

```text
فالیکیکی-پارکیلا پولینڈ کا ایک village of Poland جو Gmina Promna میں واقع ہے۔

مزید دیکھیے
پولینڈ
فہرست پولینڈ کے شہر

حوالہ جات

Short description is different from Wikidata
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 94 · fineweb2-urd_Arab:<urn:uuid:50b7992d-903f-4d63-ace7-834c3a8f5449>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 735 chars, 137 words, 10 lines
- **script:** ratio 0.692 (arabic 0.692, latin 0.308)
- **repetition:** dup_line 0.000, top-ngram 0.022, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://www.meezannews.com/2018/04/18/

```text
کوئٹہ پولیس کے ڈپٹی انسپکٹر جنرل عبدالرزاق چیمہ کا کہنا تھا کہ موٹرسائیکل پر سوار دہشت گردوں نے آٹو پارٹس کی دکان پر فائرنگ کی جس کے نتیجے میں شیعہ مسلک کا دکان دار موقع پر دم توڑ گئے۔۔۔۔۔
Trending
- مقبوضہ کشمیر میں لاک ڈاؤن جاری بھارتی فوجی کمانڈر کی خود کشی کرلی
- India intensifies restrictions on Indian Kashmir after Friday clashes
- US to hike existing, planned tariffs on Chinese imports: Trump
- Lebanese foreign minister lauds Hezbollah as pillar of national unity
- ہانگ کانگ میں سکیورٹی فورسز پر مظاہرین کے حملے متعدد افراد گرفتار
- مودی کو عرب امارات کا ایوارڈ سینیٹ چیئرمین نے دورہ منسوخ کردیا
- عرب امارات کی کشمیریوں کے خون سے غداری مودی کو اعزاز دیدیا
- مقبوضہ کشمیرجیل میں تبدیل راہول کو سرینگر ائیرپورٹ سے واپس کردیا
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 95 · fineweb2-urd_Arab:<urn:uuid:1f9aab89-8a8f-43c7-b4a3-f2e42f33521b>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 1872 chars, 410 words, 10 lines *(excerpt shows first 1500)*
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.032, dup-ngram 0.030
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://www.dawnnews.tv/news/1184162/

```text
پولیس اور ریسکیو ذرائع نے کہا ہے کہ پیر کی شام اورنگی ٹاؤن میں مشتبہ افراد کے قتل کے خلاف احتجاج کے دوران دو افراد کو گولی مار کر ہلاک کر دیا گیا۔
ڈی آئی جی ویسٹ ناصر آفتاب نے بتایا کہ پیر کی صبح پیر آباد اور پاکستان بازار میں مختلف واقعات میں لوگوں نے دو مشتبہ افراد کو مار مار کر ہلاک کردیا، تیسرے شخص کو زخمی کر دیا جبکہ مارے گئے ملزمان کے قبضے سے اسلحہ بھی برآمد ہوا ہے۔
تاہم شام کے وقت مقتولین کے لواحقین نے قصبہ موڑ پر اٹک پٹرول پمپ کے قریب احتجاجی مظاہرہ کیا اور دعویٰ کیا کہ ہلاک اور زخمی ہونے والے ملزمان بے گناہ تھے۔
ڈی آئی جی ویسٹ ناصر آفتاب نے کہا کہ احتجاج کے دوران موجود ایک شرپسند نے فائرنگ کر دی جس کے نتیجے میں تین افراد زخمی ہو گئے۔
پولیس سرجن ڈاکٹر سمیہ سید نے بتایا کہ زخمیوں کو عباسی شہید اسپتال منتقل کیا گیا جہاں ڈاکٹروں نے ان میں سے دو کو مردہ قرار دیا۔
ڈاکٹر سمیہ سید نے مزید کہا کہ پیرآباد سے 70 سالہ اور 23 سالہ شخص مردہ حالت میں ہسپتال لائے گئے تھے, معمر شخص کے سر پر گولی لگی تھی جس کو نکال لیا گیا ہے جبکہ نوجوان کو سینے میں گولی لگی تھی، تاہم ایک اور نوجوان جس کی عمر 20 سال کے اندر تھی اس کو علاج کے لیے داخل کیا گیا ہے۔
بعدازاں پولیس سرجن نے بتایا کہ احتجاج کے دوران ہلاک ہونے والے دونوں افراد کی شناخت 76 سالہ نور زمان اور 17 سالہ سلیمان خان کے نام سے ہوئی ہے۔
تاہم چھیپا ریسکیو سروس نے زخمی نوجوان کی شناخت وقاص افضل کے نام سے کی ہے، ایس ایس پی ویسٹ کی سربراہی میں پولیس کی نفری نے موقع پر پہنچ کر صورتحال پر قابو پالیا۔
کراچی پولیس ترجمان کے مطابق ایڈیشنل آئی جی کراچی جاوید اختر اوڈھو نے پیر کی شب قصبہ کالونی میں احتجاج کے دوران فائرنگ سے دو افراد کی ہلاکت کا نو
```

**verdict:** keep
**note:** 

---

### 96 · fineweb2-urd_Arab:<urn:uuid:86993480-6992-4206-bb54-9d47335d1544>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 1669 chars, 353 words, 9 lines *(excerpt shows first 1500)*
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.031, dup-ngram 0.100
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://bbcurdutv.com/%D8%A8%D8%AC%D9%84%DB%8C-5-%D8%B1%D9%88%D9%BE%DB%92-94-%D9%BE%DB%8C%D8%B3%DB%92-%D9%81%DB%8C-%DB%8C%D9%88%D9%86%D9%B9-%D9%85%DB%81%D9%86%DA%AF%DB%8C-%DA%A9%D8%B1%D8%AF%DB%8C-%DA%AF%D8%A6%DB%8C/

```text
اسلام آباد: نیشنل الیکٹریک پاور ریگولیٹری اتھارٹی (نیپرا) نے ماہانہ فیول ایڈ جسٹمنٹ کی مد میں بجلی 5 روپے 94 پیسے فی یونٹ مہنگی کردی ہے۔
نیپرا کی جانب سے جاری کردہ نوٹیفکیشن کے مطابق جنوری کی ماہانہ فیول ایڈجسٹمنٹ کی مد میں بجلی 5.94 پیسے فی یونٹ مہنگی ہونے کے بعد قیمت بڑھنے سے صارفین پر58 ارب روپےکا اضافی بوجھ پڑے گا۔
نوٹیفکیشن کے مطابق صارفین کو آئندہ ماہ کے بلوں میں اضافی ادائیگیاں کرنی ہوں گی تاہم اضافےکا اطلاق لائف لائن اور کےالیکٹرک صارفین پر نہیں ہوگا۔
بجلی، گھی کی قیمتوں میں اضافہ عمران نیازی کا ایک اور یوٹرن ہے: شہباز شریف
پاکستان مسلم لیگ (ن) کے صدر اور قائد حزب اختلاف شہباز شریف نے بجلی، گھی کی قیمتوں میں اضافے کو عمران نیازی کا ایک اور یوٹرن قرار دیتے ہوئے کہا ہے کہ عمران نیازی نے اپنی روایت برقرارکھی ہے۔
اپنے بیان میں انہوں نے کہا کہ بجلی کی قیمت میں 5.94 روپے فی یونٹ ماہانہ اضافہ عوام کے خلاف غیرملکی سازش ہے جو پی ٹی آئی حکومت نے کی ہے۔ 58 ارب روپے کا اضافی بوجھ مہنگائی سے تباہ حال عوام پر ڈالنا ظلم، زیادتی اور سفاکی کی انتہاءہے۔یہ ہے وہ ظلم ہے جسے روکنے کے لئے تحریک عدم اعتماد لائے ہیں۔
انہوں نے کہا کہ عوام دشمن ، جھوٹی حکومت سے نجات ہی قوم کو مہنگائی کے ظلم سے نجات دلائے گی ۔آئی ایم ایف کو پاکستان کے معاشی مفادات کے ہاتھ کاٹ کر دے دئیے ۔بجلی، گھی کی قیمتوں میں اضافے سے عوامی ریلیف کے جھوٹ کا پول کھل چکا ہے
ان کا کہنا تھا کہ گھی کی فی کلو قیمت میں 15 روپے، خوردنی تیل کی فی لیٹر15 روپے ریلیف پیکج کا منہ چڑا رہا ہے ۔گزشتہ ماہ خوردنی تیل 75 روپے فی لیٹر، گھی کی فی کلو قیمت 66 روپے تک اضافہ پہلے ہی کیا جاچکا ہے ۔
شہباز شریف نے کہا کہ بجٹ خسارہ ریکارڈ4.3 ٹریلین سے ا
```

**verdict:** keep
**note:** 

---

### 97 · fineweb2-urd_Arab:<urn:uuid:0eb96673-58b8-4e1d-8020-f17f17505bd7>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 4564 chars, 1052 words, 7 lines *(excerpt shows first 1500)*
- **script:** ratio 0.985 (arabic 0.985, latin 0.015)
- **repetition:** dup_line 0.000, top-ngram 0.010, dup-ngram 0.008
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://ur.progradeguttershiltonhead.com/look-inside-some-designer-sandy-gallin-s-most-coveted-homes

```text
Look Inside Some Designer Sandy Gallin S Most Coveted Homes
یہ مضمون اصل میں مارچ 2014 کے آرکیٹیکچرل ڈائجسٹ کے شمارے میں شائع ہوا تھا۔
برائے کرم اپنے موبائل فون بند کردیں۔ پردہ کرو! ایک حیرت انگیز دوسرے کام کے لئے تیار ہو جاؤ. اس میں سینڈی گیلن اداکار ہیں ، وہ لڑکا تھا جس کے پاس آپ تین دہائیوں سے زیادہ عرصے تک جاتے تھے اگر آپ کو لڑکے کی طرح گایا جاتا اور دس لاکھ روپے کی طرح لگتا تھا۔ شو بزنس میں ایک پریمیئر ٹیلنٹ مینیجرز اور پروڈیوسروں میں سے ایک کے طور پر ، گیلن اپنے مؤکلوں کو چن کر منتخب کرسکتے ہیں۔ ان کے روسٹر میں رچرڈ پرائر ، چیری ، ڈولی پارٹن ، مائیکل جیکسن ، ہووپی گولڈ برگ ، ماریہ کیری ، نیکول کڈمین ، رینی زیل وجر شامل تھے۔ . . ہمیشہ کے لئے ، اس کے ساتھی ، باربرا اسٹریسینڈ سے جون بون جووی تک ، کون ہے جو تفریحی دنیا کا رہتا ہے۔ اندرونی حلقے میں بیری (ڈیلر) ، ڈیوڈ (گیفین) ، کیلون (کلین) اور سینڈی کا مشہور حلقہ ہے۔ 'جیسے ہی میں بول سکتا تھا ،' ، نیو یارک سٹی کے بالکل باہر پلے بڑھے گیلن کو یاد آیا ، 'میں نے لاکھوں ڈالر رکھنے ، مشہور لوگوں کو جاننے اور اسٹار بننے کی بات کی۔' یہ کہا جانا چاہئے کہ بے لگام امید ، ان کی ناقابل تلافی خوبیوں میں سے ایک ہے۔
تاہم ، 1990 کی دہائی کے آخر میں ، گیلن ریٹائر ہوئے اور اس سب سے دور ہو گئے۔ صرف وہ نہیں کرتا تھا۔ اس کے بجائے وہ تفریحی صنعت کے افراد اور ان کے اہل خانہ کے لئے قابل اعتماد مکانات بن کر رہ گیا ہے ، جن میں مارلن اور جیفری کتزنبرگ ، جمی آئیون ، ڈیبورا اور ایلن گروبین ، اور شیلی اور ارونگ ازوف شامل ہیں۔ ایسا نہیں ہے کہ اس میں سے کسی کی بھی منصوبہ بندی نہیں کی گئی تھی۔ گیلن نے کبھی بھی ایک مناسب ڈیزائن آفس قائم نہیں کیا ، اور اس کی ک
```

**verdict:** keep
**note:** 

---

### 98 · urdu-wikipedia:247855

- **filter:** REJECT — repetition:top_4gram
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 262 chars, 46 words, 7 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.260, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=3
- **url:** https://ur.wikipedia.org/wiki/%D9%84%D8%A7%D9%84%DA%AF%D9%88%D9%84%D8%A7%20%28%DA%A9%D9%85%DB%8C%D9%88%D9%86%D9%B9%DB%8C%20%DA%88%DB%8C%D9%88%DB%8C%D9%84%D9%88%D9%BE%D9%85%DB%8C%D9%86%D9%B9%20%D8%A8%D9%84%D8%A7%DA%A9%29

```text
لالگولا (کمیونٹی ڈیویلوپمینٹ بلاک) ) بھارت کا ایک رہائشی علاقہ جو مغربی بنگال میں واقع ہے۔

تفصیلات
لالگولا (کمیونٹی ڈیویلوپمینٹ بلاک) کا رقبہ 134 مربع کیلومیٹر ہے اور اس کی مجموعی آبادی 267,593 افراد پر مشتمل ہے۔

مزید دیکھیے
بھارت
فہرست بھارت کے شہر

حوالہ جات
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 99 · fineweb2-urd_Arab:<urn:uuid:aac109d2-6ad0-41e7-bb54-bb06a3b9f127>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 1075 chars, 210 words, 6 lines
- **script:** ratio 0.678 (arabic 0.678, latin 0.322)
- **repetition:** dup_line 0.000, top-ngram 0.032, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://www.urdunews.com/node/433111/%D8%AF%D9%86%DB%8C%D8%A7/%D8%A7%D9%93%D8%B1%DA%86-%D8%A8%D8%B4%D9%BE-%DA%A9%DB%8C-%D8%AC%D9%84%DB%8C%D8%A7%D9%86%D9%88%D8%A7%D9%84%DB%81-%D8%B3%D8%A7%D9%86%D8%AD%DB%92-%D9%BE%D8%B1-%D9%85%D8%B9%D8%A7%D9%81%DB%8C

```text
برطانیہ سے انڈیا کے دورے پر آئے آرچ بشپ آف کینٹربری جسٹن ویلبائے نے اس وقت اپنی عاجزی و انکساری سے لاکھوں لوگوں کے دل جیت لیے جب انہوں نے جلیانوالہ باغ کے سانحے میں ہلاک ہونے والوں کی تعظیم میں نہ صرف امرتسر میں سانحے کے مقام پر تعظیمانہ سجدہ کیا بلکہ ذاتی حیثیت میں اس سانحے پر معافی بھی مانگی۔
انہوں نے کہا ’میرے پاس کوئی سرکاری عہدہ نہیں ہے کہ میں برطانیہ کی جانب سے معذرت کروں مگر میں اپنی ذاتی حیثیت میں اس بربریت پر معافی مانگنا چاہتا ہوں۔‘
جسٹن ویلبائے کا کہنا تھا کہ یہاں پر آمد نے ان کے اندر شرم کو بیدار کیا ہے کیونکہ یہ سانحہ برطانوی تاریخ پر بہت سے دھبوں میں سے ایک دھبہ ہے جب انگلستان کی افواج نے مسلمان، ہندوں اور سکھوں پر گولیاں برسائیں۔ ’اس غم و رنج جو اب تک نسلوں نے محسوس کیا ہے اس کو مسترد نہیں کیا جاسکتا۔‘
I feel a deep sense of grief, humility and profound shame having visited the site of the horrific #JallianwalaBagh massacre in Amritsar today.
Here, a great number of Sikhs – as well as Hindus, Muslims and Christians – were shot dead by British troops in 1919. pic.twitter.com/p5fDprIMbr
— Archbishop of Canterbury (@JustinWelby) September 10, 2019
```

**verdict:** keep
**note:** 

---

### 100 · urdu-wikipedia:920032

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 47454 chars, 10084 words, 129 lines *(excerpt shows first 1500)*
- **script:** ratio 0.982 (arabic 0.982, latin 0.018)
- **repetition:** dup_line 0.000, top-ngram 0.007, dup-ngram 0.060
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=264
- **url:** https://ur.wikipedia.org/wiki/%D8%AA%D8%A7%D8%B1%DB%8C%D8%AE%20%D8%B1%DB%8C%D8%A7%D8%B3%D8%AA%DB%81%D8%A7%D8%A6%DB%92%20%D9%85%D8%AA%D8%AD%D8%AF%DB%81

```text
ریاستہائے متحدہ کی تاریخ وہی ہے جو ماضی میں شمالی امریکہ میں واقع ریاستہائے متحدہ امریکہ میں ہوا تھا ۔

مقامی امریکی ہزاروں سالوں سے امریکہ میں مقیم تھے۔ 1607 میں انگریز لوگ اس جگہ گئے جہاں اب ورجینیا کے جیمسٹاؤن کہلاتے ہیں۔ دوسرے یورپی آباد کار نوآبادیات گئے ، زیادہ تر انگلینڈ اور بعد میں برطانیہ سے آئے تھے ۔ فرانس ، اسپین اور نیدرلینڈ نے بھی شمالی امریکا کو نوآبادیات بنا لیا۔ 1775 میں ، تیرہ کالونیوں اور برطانیہ کے مابین جنگ کا آغاز اس وقت ہوا جب نوآبادیاتی حکومت برطانیہ میں اپنی حکومت کو ٹیکس ادا کرنے پر ناراض تھے ، لیکن انہیں برطانیہ / برطانوی انتخابات میں ووٹ ڈالنے کا کوئی موقع نہیں دیا جارہا تھا ، تاکہ اس رقم کو کس طرح خرچ کیا جاسکے۔

19 اپریل 1775 کو طلوع آفتاب کے فورا بعد ، انگریزوں نے میساچوسٹس کے کونکورڈ میں میساچوسٹس ملیشیا کو اسلحے سے پاک کرنے کی کوشش کی ، اس جنگ کا آغاز " دنیا بھر میں سنی گئی گولیاں مارنے والی آواز سے کیا گیا۔ " 4 جولائی ، 1776 کو ، بانی باپوں نے ریاستہائے متحدہ امریکہ کا آزادی نامہ لکھا۔ انہوں نے انقلابی جنگ جیت کر ایک نیا ملک شروع کیا۔ انہوں نے 1787 میں آئین اور 1791 میں بل کے حقوق پر دستخط کیے۔ جنرل جارج واشنگٹن ، جنھوں نے جنگ کی قیادت کی تھی ، اس کے پہلے صدر بنے۔ 19 ویں صدی کے دوران ، ریاستہائے متحدہ نے مغرب میں بہت زیادہ زمین حاصل کی اور صنعتی بننا شروع ہوا۔ 1861 میں، میں نے کئی ریاستوں جنوبی ریاستہائے متحدہ نامی ایک نئے ملک کو شروع کرنے کے لیے امریکا کو چھوڑنے کے لیے کی کوشش ۔ اس کی وجہ سے امریکی خانہ جنگی کا آغاز ہوا ۔ جنگ کے بعد ، ہجرت دوبارہ شروع ہوئی۔ کچھ امریکی اس گلڈ ایج میں بہت امیر ہوئے اور اس ملک نے دنیا کی سب سے بڑی معیشت تیار کی۔
```

**verdict:** keep
**note:** 

---

### 101 · fineweb2-urd_Arab:<urn:uuid:8f49bf42-91e0-476d-a782-640da2ed0fe7>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 3004 chars, 576 words, 17 lines *(excerpt shows first 1500)*
- **script:** ratio 0.672 (arabic 0.672, latin 0.328)
- **repetition:** dup_line 0.000, top-ngram 0.018, dup-ngram 0.085
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://urdu.92newshd.tv/about/%D8%B1%D9%88%D8%A7%DA%BA-%D8%B3%D8%A7%D9%84-%DA%86%DB%8C%D9%86-%D8%B3%DB%92-%DA%AF%D9%88%D8%A7%D8%AF%D8%B1-%D8%AA%DA%A9-%DA%A9%D8%A7%D8%B1%DA%AF%D9%88-%DA%A9%DB%8C-%D8%AA%D8%B1%D8%B3%DB%8C%D9%84

```text
'رواں سال چین سے گوادر تک کارگو کی ترسیل شروع ہو جائیگی '
گوادر (92نیوز) چیف آف آرمی سٹاف جنرل راحیل شریف نے کہا ہے کہ دشمن انٹیلی جنس ایجنسیاں پاک چین اقتصادی راہداری منصوبے کے خلاف ہیں۔ رواں سال چین سے گوادر تک کارگو کی ترسیل شروع ہو جائے گی۔ بھارتی ایجنسی ”را“ پاکستان کو غیرمستحکم کرنے میں ملوث ہے۔ آپریشن ضرب عضب ایک آپریشن نہیں بلکہ سوچ کا نام ہے۔ دہشت گردی‘ شدت پسندی اور کرپشن کا خاتمہ بنیادی مقصد ہے۔
تفصیلات کے مطابق گوادرمیں ”بلوچستان میں امن اور ترقی” کے موضوع پر منعقد ہونے والے سیمینار سے خطاب کرتے ہوئے آرمی چیف جنرل راحیل شریف نے کہا کہ اقتصادی راہداری منصوبہ پورے خطے کی ترقی اور استحکام کا ضامن ہے۔ سی پیک ہمارا قومی عزم ہے جسے ہر قیمت پر عملی جامہ پہنائیں گے۔ خطے میں اپنا اثرورسوخ بڑھانے کے خواہش مند ممالک سی پیک سے پریشان ہیں۔
جنرل راحیل شریف نے کہا سب جانتے ہیں کہ جارحانہ مزاج رکھنے والی انٹیلی جنس ایجنسیاں اس عظیم منصوبے کے خلاف ہیں۔ بھارتی ایجنسی ”را“ پاکستان کو غیرمستحکم کرنے میں ملوث ہے لیکن ہم کسی کو پاکستان میں مسائل اور مشکلات پیدا کرنے کی اجازت نہیں دیں گے۔ بطور آرمی چیف یقین دلاتا ہوں کہ سی پیک کے تحفظ میں کوئی کسر اٹھا نہیں رکھیں گے جبکہ بلوچ عوام کو بھی یقین دلاتا ہوں کہ منصوبے کے سب سے زیادہ فوائد انہیں ہی حاصل ہوں گے۔
ضروری ہے کہ سب محاذ آرائی چھوڑ کر تعاون پر توجہ دیں۔ آرمی چیف کا کہنا تھا کہ دہشت گردی کے خلاف جنگ کے بعد ترقی میں ہم بہت آگے بڑھ چکے ہیں۔ ضرب عضب صرف آپریشن نہیں مکمل نظریہ ہے جو اب آخری مراحل میں داخل ہوچکا ہے۔ ضرب عضب کا مطلب دہشت گردی اورکرپشن کا خاتمہ ہے۔ انہوں نے کہا کہ ہمیں دہشت گردی کےخلاف ایک مشکل جنگ سے گزرنا پڑا۔
عالمی برادری
```

**verdict:** keep
**note:** 

---

### 102 · fineweb2-urd_Arab:<urn:uuid:efe31a48-ff5f-4aba-a34a-9cb9b4d896d0>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 710 chars, 136 words, 4 lines
- **script:** ratio 0.689 (arabic 0.689, latin 0.311)
- **repetition:** dup_line 0.000, top-ngram 0.037, dup-ngram 0.054
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://www.neonetwork.pk/09-Mar-2017/12802

```text
راولپنڈی: ترجمان افواج پاکستان نے بھارت کی جانب سے لائن آف کنٹرول کے قریب دہشتگردوں کی موجودگی کے دعوے کو مسترد کر دیا ہے۔ ڈی جی آئی ایس پی آر نے کہا ہے پاکستان اور بھارت کے فوجی حکام کا ہاٹ لائن پر رابطہ ہوا جس میں کنٹرول لائن پر دہشت گردوں کی نقل و حرکت کا بھارتی دعویٰ مسترد کر دیا۔
Indian concern on terrorists' movement along LOC were strongly rejected during hotline. Indian Army asked to look inward, share evidence. pic.twitter.com/wuF1jJ4bui— Maj Gen Asif Ghafoor (@OfficialDGISPR) March 9, 2017
ڈی جی آئی ایس پی آر کے مطابق بھارتی فوج سے کہا ہے کہ وہ دہشت گردوں کی موجودگی سے متعلق اپنے دعوے کے شواہد پیش کرے۔
نیو نیوز کی براہ راست نشریات، پروگرامز اور تازہ ترین اپ ڈیٹس کیلئے ہماری ایپ ڈاؤن لوڈ کریں
```

**verdict:** keep
**note:** 

---

### 103 · fineweb2-urd_Arab:<urn:uuid:15ba9ffb-5943-49df-8215-f9a9a3cc93a1>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 3802 chars, 820 words, 16 lines *(excerpt shows first 1500)*
- **script:** ratio 0.997 (arabic 0.997, latin 0.003)
- **repetition:** dup_line 0.000, top-ngram 0.014, dup-ngram 0.012
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://www.dw.com/ur/%D9%85%D8%B4%D8%B1%D9%82-%D9%88%D8%B3%D8%B7%DB%8C%D9%B0-%DA%A9%DB%92-%D9%84%DB%8C%DB%92-%D8%A7%DB%8C%DA%A9-%D9%86%DB%8C%D9%B9%D9%88-%D9%82%DB%8C%D8%A7%D9%85-%DA%A9%DB%92-%D9%85%D8%B1%D8%AD%D9%84%DB%92-%D9%85%DB%8C%DA%BA/a-62317714

```text
گزشتہ ہفتے کے آخر میں اردن کے بادشاہ کی وہ بات شہ سرخیوں کی زینت بن گئی، جب انہوں نے صحافیوں کو بتایا کہ وہ مشرق وسطیٰ میں ایک ایسے فوجی اتحاد کی حمایت کریں گے، جو مغربی دفاعی اتحاد نیٹو کی طرز پر قائم کیا جائے۔
امریکی نشریاتی ادارے سی این بی سی کے ساتھ گفتگوکرتے ہوئے اردن کے شاہ عبداللہ ثانی نے کہا، ''میں ان اولین لوگوں میں سے ایک ہوں گا، جو مڈل ایسٹ نیٹو کی حمایت کریں گے۔‘‘ ان کا مزید کہنا تھا، ''ہم سب جمع ہو رہے ہیں اور سوچ رہے ہیں کہ ہم کیسے ایک دوسرے کی مدد کر سکتے ہیں؟ ... جو میرے خیال میں اس خطے کے لیے ایک غیر معمولی بات ہے۔‘‘
'عرب نیٹو‘ کے قیام سے متعلق افواہیں دوسری جانب سے بھی سننے کو مل رہی ہیں۔ گزشتہ ہفتے اسرائیلی وزیر دفاع بینی گینٹس نے کہا تھا کہ اسرائیل نے امریکی سربراہی میں قائم ہونے والے ایک ایسے اتحاد میں شمولیت اختیار کر لی ہے، جسے انہوں نے 'مڈل ایسٹ ایئر ڈیفنس الائنس‘ یا MEAD کا نام دیا تھا۔ تاہم گینٹس نے یہ واضح نہیں کیا کہ مشرق وسطیٰ کے دیگر کون کون سے ملک اس اتحاد میں شامل ہیں۔ بین الاقوامی میڈیا ادارے، جن میں روئٹرز اور ایسوسی ایٹڈ پریس بھی شامل ہیں، اسرائیل کے اس بیان یا اس اتحاد کے نام کی تصدیق نہیں کر سکے۔
پھر رواں ہفتے کے آغاز پر وال اسٹریٹ جرنل نے ایسی خفیہ میٹنگز کے بارے میں رپورٹ کیا، جو مصر میں ہوئیں اور جن میں اسرائیل، سعودی عرب، قطر، اردن، مصر، متحدہ عرب امارات اور بحرین کے فوجی حکام کو شریک ہوتے ہوئے دیکھا گیا اور جنہوں نے دفاع کے معاملے پر تعاون کے بارے میں غور کیا۔
امن کے لیے اتحاد؟
'عرب نیٹو‘ کے قیام کی کئی ایک قابل فہم وجوہات بھی ہیں۔
امریکا جو مشرق وسطیٰ میں امن قائم رکھنے کا ذمہ دار ہے، گزشتہ کئی برسوں کے دوران بتدریج اس خطے سے نکل رہا
```

**verdict:** keep
**note:** 

---

### 104 · fineweb2-urd_Arab:<urn:uuid:2740de9f-44fa-46e6-bdb1-23b19a4a18fe>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 931 chars, 173 words, 6 lines
- **script:** ratio 0.658 (arabic 0.658, latin 0.342)
- **repetition:** dup_line 0.000, top-ngram 0.039, dup-ngram 0.112
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://pakonlinenews.com/pakistan/tahirul-qadri-request-people-stay-home/

```text
اسلام آباد: (پاک آنلائن نیوز) ڈاکٹر طاہرالقادری نے کورونا وائرس کے سبب لوگوں کو گھروں میں رہنے کا مشورہ دیتے ہوئے کہا ہے کہ لوگ اس وقت سے کتابیں پڑھنے کا فائدہ اٹھا لیں۔
سربراہ منہاج القرآن ڈاکٹر طاہرالقادری نے سماجی رابطے کی وب سائٹ ٹوئٹر پر کہا ہے کہ صورتحال معمول پر آنے تک لوگ اپنے گھروں میں رہیں۔
Stay at homes until the situation comes back to normal. Young people must utilize this time in seeking knowledge and reading books. Develop friendly relations with your neighbors. By opting good habits, one can transform this crucial time in a productive way.#COVID2019
— Dr Tahir-ul-Qadri (@TahirulQadri) April 14, 2020
انہوں نے نوجوانوں کو وقت سے فائدہ اٹھانے کا مشورہ دیتے ہوئے کہا ہے کہ نوجوانوں کو وقت سے فائدہ اٹھانا چاہئے اور اپنی معلومات میں اضافہ کریں اور مطالعہ کرنے میں مصروف رہیں اور ہمسایوں کے ساتھ اپنا رابطہ بڑھائیں۔
ان کا مزید کہنا ہے کہ اچھی عادات اپنا کر اس سخت اور مشکل وقت کو نتیجہ خیز انداز میں بدل سکتے ہیں۔
```

**verdict:** keep
**note:** 

---

### 105 · urdu-wikipedia:920854

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 4851 chars, 988 words, 33 lines *(excerpt shows first 1500)*
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.031, dup-ngram 0.041
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=39
- **url:** https://ur.wikipedia.org/wiki/%D8%B1%D8%A7%D8%AC%D9%86%D8%AF%D8%B1%20%DA%86%D9%88%D9%84%D8%A7%20%D8%A7%D9%88%D9%84%20%DA%A9%DB%8C%20%D8%AC%D9%86%D9%88%D8%A8%20%D9%85%D8%B4%D8%B1%D9%82%DB%8C%20%D8%A7%DB%8C%D8%B4%DB%8C%D8%A7%20%D9%85%DB%81%D9%85

```text
نوشتے اور تاریخی ذرائع کا دعوی ہے کہ قرون وسطی کے چولا کے بادشاہ راجندر چولا اول نے سریویجیا کو محکوم بنانے کے لیے 1025 میں انڈوچائنا، مالےجزیرہ نما اور انڈونیشیا میں ایک بحری مہم بھیجی۔ ترووالنگاڈو تختیاں، لیڈن گرانٹ اور راجندر چولا اول کی تمل کتبہ اس مہم کے بارے میں معلومات کا بنیادی ماخذ ہیں۔

ذرائع
مہم کے بارے میں معلومات کا سب سے مفصل ذریعہ راجندر چولا اول کا تمل کتبہ ہے۔ اسٹیل بیان کرتا ہے:

تریوالنگاڈو پلیٹوں میں، راجندر چولا اول کے چودھویں سال سے، اس نے کدرم پر فتح حاصل کرنے کا تذکرہ کیا ہے لیکن اس کی تفصیلات میں کوئی تفصیل نہیں ہے۔ مہم سے وابستہ مقامات کی نشان دہی کرنے کے لیے ہندوستان سے باہر کے کسی فرد کی پہلی کوشش ایپی گرافسٹ ای ہلٹشچ نے کی تھی، جس نے اس اسٹیل کو 1891 میں شائع کیا تھا۔ ہلٹشچ نے کتبہ میں مذکور راج گھرانوں کی نشان دہی کی جس میں پانڈیا خاندان کی حکمرانی تھی۔ 1903 میں، اس نے اپنا نظریہ واپس لیا اور کہا کہ کتبہ نے راجندر چولا اول کے برما میں باگو کی فتح کو بیان کیا۔ جارج کوڈ کے لی رائوومے ڈی سری وجیا نے کئی برسوں کی تحقیق کے بعد 1918 میں شائع کیا، دونوں نظریات کو مسترد کر دیا اور راجندر چولا اول کے جنوب مشرقی ایشیا کی فتح کی پہلی قائل وضاحت فراہم کی۔

اسباب
سری وجیہ اور جنوبی ہند کے چولا خاندان کے درمیان میں تعلقات ابتدائی طور پر راجا راجا چولا اول کے دور میں دوستانہ تھا۔ 1006 عیسوی میں، سریندر خاندان سے تعلق رکھنے والے ایک سریوی ججن مہاراجا، بادشاہ ماروی وجیاٹنگورمن نے، بندرگاہ قصبہ ناگپٹن میں چودامانی وہار تعمیر کیا تھا۔ تاہم، راجندر چولا اول کے دور میں، تعلقات بدتر ہو گئے جب چولا خاندان نے سری وجیائی شہروں پر حملہ کرنا شروع کیا۔

دشمنی کی وجوہات مبہم
```

**verdict:** keep
**note:** 

---

### 106 · urdu-wikipedia:121869

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 365 chars, 70 words, 10 lines
- **script:** ratio 0.862 (arabic 0.862, latin 0.138)
- **repetition:** dup_line 0.000, top-ngram 0.066, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=3
- **url:** https://ur.wikipedia.org/wiki/%D8%AA%D9%88%DB%8C%D8%B3%D8%B1%DA%A9%D8%A7%D9%86

```text
تویسرکان () ایک شہر ہے جو ایران میں واقع ہے۔ اس کی مجموعی آبادی 42,520 افراد پر مشتمل ہے، یہ صوبہ ہمدان میں واقع ہے۔

متعلقہ روابط
فہرست ایران کے شہر

حوالہ جات

ایران کے شہر
شہرستان تویسرکان میں آباد مقامات
کامنز زمرہ جس کا ربط ویکی ڈیٹا پر ہے
مقالے جن میں فارسی زبان کا متن ہے
جغرافیہ شہرستان تویسرکان کے نامکمل مضامین
Short description is different from Wikidata
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 107 · fineweb2-urd_Arab:<urn:uuid:09493158-8886-4330-b35d-8f9099f1ac30>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 1294 chars, 260 words, 9 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.039, dup-ngram 0.057
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** yeh=15
- **url:** https://urdu.arynews.tv/venezuela-is-going-to-be-crisis-free-soon/

```text
وینزویلا بحران، حکومت اور اپوزیشن مذاکرات کے لیے تیار
کراکس: وینزویلا میں جاری سیاسی بحران کے خاتمے کے لیے حکومت اور اپوزیشن مذاکرات کے لیے تیار ہوگئے، بات چیت رواں ہفتے ہوگی۔
تفصیلات کے مطابق وینزویلا میں سیاسی بحران کے باعث ملکی معاشی صورت حال بھی ابتر ہے، مذاکرات کے ذریعے حل نکالنے کی کوشش کی جائے گی۔
غیر ملکی خبر رساں ادارے کے مطابق وینزویلا کے خود ساختہ صدر جون گائیڈو نے ملکی حکومت کو ٹف ٹائم دے رکھا ہے، جبکہ آئینی صدر نکولاس مادورو کی جانب سے مخالفین کے خلاف کریک ڈاؤن بھی جاری ہے۔
ناروے حکام کا کہنا ہے کہ اقتصادی بحران اور سیاسی عدم استحکام کے شکار ملک وینزویلا میں حکومت اور اپوزیشن کے مابین ناروے کی ثالثی میں بات چیت اس ہفتے متوقع ہے۔
ناروے حکام کے مطابق فریقین اس ہفتے بارباڈوس میں ملیں گے اور ملک کو درپیش بحرانوں کا آئینی حل تلاش کریں گے۔ غیر ملکی میڈیا کا کہنا ہے کہ جون گائیڈ مذاکرات کے دوران اپنے رہنماؤں کی رہائی کا بھی مطالبہ رکھیں گے۔
دوسری جانب اقوام متحدہ نے اپنی حالیہ رپورٹ میں انکشاف کیا ہے کہ وینزویلا حکومت جبری طور پر عوامی رائے تبدیل کررہی ہے۔
رپورٹ میں کہا گیا ہے کہ حکومت کے ہاتھوں عام شہریوں کے ہلاکتوں کی تعداد چونکا دینے والی ہے، مذکورہ رپورٹ اقوام متحدہ کی انسانی حقوق کونسل میں پیش کی جائے گی۔
خیال رہے کہ وینزویلا میں اپوزیشن لیڈر جون گائیڈو کی حمایت دن بہ دن بڑھتی چلی جارہی ہے، امریکا سمیت کئی یورپی ریاستوں نے بھی جون گائیڈو کی حمایت کا اعلان کیا ہے۔
```

**verdict:** keep
**note:** 

---

### 108 · fineweb2-urd_Arab:<urn:uuid:6adc8309-edb0-4bda-bf75-b5ed854ce4ef>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 378 chars, 64 words, 6 lines
- **script:** ratio 0.660 (arabic 0.660, latin 0.340)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** http://www.express.com.pk/epaper/Index.aspx?Issue=NP_KHI&Page=FRONT_PAGE

```text
جرائم کے خاتمے کے لیے ٹوئٹر کا استعمال
آسٹریلوی آل راؤنڈر شین واٹسن پاکستان کے خلاف سیریز سے باہر
بھارت میں مسلمان طالب علم نے ایمانداری کی مثال قائم کردی
فیس بک کا خفیہ فولڈر
فواد خان کی پہلی بھارتی فلم ’’خوبصورت‘‘ ’’دعوت عشق‘‘ کے سامنے زیادہ خوبصورت....
Copyright © Century Publications. This material may not be published, broadcast, rewritten, redistributed or derived from.
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 109 · urdu-wikipedia:905985

- **filter:** REJECT — too_short
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 140 chars, 28 words, 3 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=1
- **url:** https://ur.wikipedia.org/wiki/%D8%A8%D8%AE%D8%B4%DB%8C%D8%A7%D9%84

```text
بخشیال وہورا کھتریوں کا ایک خاندان جو چکوال بھون کے مقام پر آباد ہے یہ فوجی خدمات کی ایک روایت رکھتے ہیں

حوالہ جات

پاکستان کے معاشرتی گروہ
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 110 · urdu-wikipedia:624665

- **filter:** REJECT — repetition:top_3gram
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 326 chars, 56 words, 9 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.270, dup-ngram 0.227
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=6
- **url:** https://ur.wikipedia.org/wiki/%DA%AF%D9%88%D8%B4%DB%8C%D9%86%20%D9%B9%D8%A7%D8%A4%D9%86%20%D8%B4%D9%BE%D8%8C%20%D8%B3%D9%B9%D8%A7%D8%B1%DA%A9%20%DA%A9%D8%A7%D8%A4%D9%86%D9%B9%DB%8C%D8%8C%20%D8%A7%D9%84%DB%8C%D9%86%D9%88%D8%A7%D8%A6%DB%92

```text
گوشین ٹاؤن شپ، سٹارک کاؤنٹی، الینوائے ریاستہائے متحدہ امریکا کا ایک ٹاؤن شپ جو سٹارک کاؤنٹی، الینوائے میں واقع ہے۔

تفصیلات
گوشین ٹاؤن شپ، سٹارک کاؤنٹی، الینوائے کی مجموعی آبادی 686 افراد پر مشتمل ہے۔

مزید دیکھیے
ریاستہائے متحدہ امریکا
ریاستہائے متحدہ کے شہر

حوالہ جات

الینوائے کے ٹاؤن شپ
سٹارک کاؤنٹی، الینوائے میں ٹاؤن شپ
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 111 · fineweb2-urd_Arab:<urn:uuid:4249e0af-e7b1-4b6c-994d-6471978fe9e2>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 324 chars, 66 words, 6 lines
- **script:** ratio 0.543 (arabic 0.543, latin 0.457)
- **repetition:** dup_line 0.000, top-ngram 0.049, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://digilog.pk/product-tag/40-pin-male-header/

```text
ویب سائٹ پر دی ہی تمام قیمتیں اصل میں تبدیل ہو چکی ہیں، قیمتوں کا آخری فیصلہ کمپنی اپ کے آرڈر کے موصول ہونے کے بعد کیا جائے گا. پیسے بھیجھنے کے بعد بھی قیمت تبدیل ہو سکتی ہے
No products in the cart.
Home | Products tagged “40 Pin Male Header”
Showing the single result
2.54mm Pitch 40 Pin Male Header In Pakistan
WhatsApp us
```

**verdict:** drop
**note:** e-commerce product page, cart furniture

---

### 112 · fineweb2-urd_Arab:<urn:uuid:5d4100ed-29d5-49e8-8bb3-2f253c901795>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 1296 chars, 247 words, 12 lines
- **script:** ratio 0.686 (arabic 0.686, latin 0.314)
- **repetition:** dup_line 0.000, top-ngram 0.037, dup-ngram 0.049
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://publicnews.com/56148/

```text
جنیوا: (ویب ڈیسک) عالمی ادارہ صحت (ڈبلیو ایچ او) نے کورونا وائرس کے خاتمے کی ممکنہ تاریخ کا اعلان کر دیا ہے۔
غیر ملکی میڈیا کے مطابق یہ اہم بات ورلڈ ہیلتھ آرگنائزیشن کے ایمرجنسی پروگرام کی سربراہ ماریا وان نے اپنے ایک بیان میں کہی۔
Increased transmissibility means more cases.
More cases mean more people being hospitalised and dying.
Countries need to act quickly to drive down transmission.pic.twitter.com/wYMwnaofLD
— Wellcome (@wellcometrust) December 16, 2021
ماریا وان نے کہا ہے کہ ہمیں سائنسدانوں کی جانب سے کی جانے والی تحقیقات سے یہ بات پتا چلی ہے کہ عالمی وبا کورونا وائرس آئندہ سال 2022ء تک ختم ہو جائے گی۔
دوسری جانب یورپی مرکز برائے انسداد امراض نے کورونا کی نئی قسم اومیکرون کے بارے میں شدید خدشات کا اظہار کرتے ہوئے کہا ہے کہ جنوری اور فروری 2020ء میں اس کے کیسز میں اضافہ دیکھنے میں آ سکتا ہے۔
The trajectory of the pandemic is in our hands. It has always been in our hands. What happens now & into 2022 is up to us.
— Maria Van Kerkhove (@mvankerkhove) November 7, 2021
اپنی جائزہ رپورٹ میں یورپی مرکز برائے انسداد امراض نے کہا کہ اومیکرون انتہائی تیزی سے یورپ کے شہریوں کو اپنی لپیٹ میں لے سکتا ہے۔
خیال رہے کہ اس سے قبل ورلڈ ہیلتھ آرگنائزیشن کے سربراہ ٹیڈروس آڈہانوم گیبریسوس نے کہا تھا کہ اومیکرون دنیا کے 77 ملوں میں پھیل چکا ہے، اور مزید ممالک بھی اس کی لپیٹ میں آ سکتے ہیں۔
```

**verdict:** keep
**note:** 

---

### 113 · fineweb2-urd_Arab:<urn:uuid:510ab948-8ede-461a-8d5b-f6fba1024913>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 818 chars, 177 words, 4 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.040, dup-ngram 0.056
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://urdu.alarabiya.net/middle-east/2018/08/08/%D8%B4%D8%A7%D9%85%DB%8C-%D8%AE%D8%A7%D8%AA%D9%88%D9%86-%D8%A7%D9%88%D9%84-%DA%86%DA%BE%D8%A7%D8%AA%DB%8C-%DA%A9%DB%92-%D8%B3%D8%B1%D8%B7%D8%A7%D9%86-%D9%85%DB%8C%DA%BA-%D9%85%D8%AA%D8%A8%D9%84%D8%A7-%DB%81%D9%88-%DA%AF%D8%A6%DB%8C%DA%BA

```text
شامی خاتون اول اسماء الاسد چھاتی کے سرطان میں مبتلا ہو گئیں۔ شامی ذرائع ابلاغ نے بدھ کے روز اس خبر کا انکشاف کرتے ہوئے بتایا کہ بشار الاسد کی اہلیہ کو چھاتی کے سرطان کا مرض لاحق ہو گیا ہے جس کے بعد اس موذی مرض کے پہلے درجے کا علاج شروع کر دیا گیا ہے۔
شام کی سرکاری خبر رساں ایجنسی کی جانب سے بیالیس سالہ اسماء الاسد کی مسکراتے چہرے والی تصاویر جاری کی گئی ہیں جس میں وہ شوہر کے پاس کسی ہسپتال میں کرسی پر بیٹھی ہیں اور ان کے بائیں ہاتھ پر کینولا لگا ہوا ہے۔
ادھر شامی صدر کے سرکاری انسٹاگرام اکاونٹ سے جاری کردہ بیان میں بتایا گیا ہے کہ "اسماء الاسد کے سینے میں سرطان کی تشخیص ہوئی ہے۔ مرض انتہائی ابتدائی مرحلے میں ہے اور اس کا علاج شروع کر دیا گیا ہے۔"
شامی خاتون اول بننے سے پہلے اسماء الاسد بینکنگ کے شعبے سے وابستہ تھیں۔ وہ لندن میں مقیم شامی والدین کے ہاں پیدا ہوئیں۔ بشار الاسد سے ان کی شادی سنہ 2000ء میں ہوئی۔
```

**verdict:** keep
**note:** 

---

### 114 · urdu-wikipedia:10788

- **filter:** REJECT — html_residue
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 447 chars, 84 words, 20 lines
- **script:** ratio 0.851 (arabic 0.851, latin 0.149)
- **repetition:** dup_line 0.000, top-ngram 0.045, dup-ngram 0.000
- **url** 0.000 · **html** 0.025 · **U+FFFD** 0.00000
- **stage 4:** whitespace=11, yeh=3
- **url:** https://ur.wikipedia.org/wiki/2006%D8%A1

```text
جنوری

فروری

مارچ
19 مارچ - پاکستانی اداکار محمد علی کا انتقال۔

اپریل
11 اپریل - پاکستان میں عید میلاد النبی کے دن سانحہ نشتر پارک کراچی (2006ء بم دھماکا)

مئی

جون

جولائی
10 جولائی - پاکستانی شاعر و مصنف، احمد ندیم قاسمی لاہور میں انتقال کر گئے۔

اگست

ستمبر

اکتوبر

نومبر

دسمبر
30 دسمبر - عراقی صدر صدام حسین کو عراق میں پھانسی دے دی گئی۔

<noinclude>

2006ء
کامنز زمرہ جس کا ربط ویکی ڈیٹا پر ہے
Short description is different from Wikidata
```

**verdict:** keep
**note:** year article with real event entries

---

### 115 · urdu-wikipedia:623388

- **filter:** REJECT — html_residue
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 2431 chars, 473 words, 35 lines *(excerpt shows first 1500)*
- **script:** ratio 0.962 (arabic 0.962, latin 0.038)
- **repetition:** dup_line 0.041, top-ngram 0.041, dup-ngram 0.000
- **url** 0.000 · **html** 0.041 · **U+FFFD** 0.00000
- **stage 4:** whitespace=33
- **url:** https://ur.wikipedia.org/wiki/%D8%B3%D8%B1%D8%AF%D8%A7%D8%B1%20%D9%86%D9%82%D9%88%DB%8C%20%D8%A7%D9%85%D8%B1%D9%88%DB%81%D9%88%DB%8C

```text
پروفیسر سردار نقوی امروہوی (پیدائش:21 مارچ، 1941ء - وفات: 5 فروری، 2001ء ) پاکستان کے ممتاز اردو مرثیہ گو شاعر تھے۔

حالات زندگی اور تعلیمی سفر
سید سردار محمد نقوی المعروف سردار نقوی 21 مارچ، 1941ء کو امروہہ، اتر پردیش، برطانوی ہندوستان میں پیدا ہوئے۔ والد کا نام سید انوار محمد نقوی تھا۔ ابتدائی تعلیم کا سلسلہ امروہہ ہی میں اپنی والدہ کے نانا حکیم سید حیدر نظر کی زیرِ نگرانی ہوا۔ تقسیم ہند کے بعد اپنے وطن سے ہجرت کر کے کراچی آ گئے اور یہیں باقی تعلیم مکمل کی۔ کراچی یونیورسٹی سے بی ایس سی (آنرز) اور 1962ء میں ایم ایس سی (ریاضی) کی اسناد حاصل کیں ۔

کیرئیر کا آغاز
پروفیسر سردار نقوی نے ملازمت کی ابتدا 1963ء میں جیالوجیکل سروے ڈپارٹمنٹ سے کی۔ 1965ء تک اسٹنٹ ڈائریکٹر کی پوسٹ پر رہے پھر گورنمنٹ کالج برائے طلبہ، کوئٹہ میں شعبہ جیالوجی کے استاد اور بانی کی حیثیت سے خدمات کا آغاز کیا تاہم 1970ء میں کراچی آ گئے اور یہاں محکمہ تعلیم کے مختلف اہم عہدوں پر فائز رہے۔ 1977ء میں ڈی جے کالج کراچی کے شعبہِ جیالوجی میں استاد مقرر ہوئے اور 1997ء میں بحیثیت پروفیسر اور سربراہِ شعبہ جیالوجی کے (ذاتی درخواست پر قبل از وقت) ریٹائرمنٹ لے لی۔

شعر و سخن
انہوں شاعری کی ابتدا 1957ء میں سولہ برس کی عمر میں کی۔ ابتدا میں ہی ترقی پسند تحریک سے متاثر ہوئے اور اپنی شاعری کا رشتہ انسانی دکھ اور آلام سے جوڑا۔ انہوں نے نعت، منقبت، غزل، مرثیہ ہر صنف میں لکھا۔ تاہم مرثیہ گوئی میں ملک گیر شہرت پائی۔ ایک عرصہ تک ریڈیو پاکستان کراچی اور پی ٹی وی پر ان کا مرثیہ تحت اللفظ ہر سال باقاعدگی سے پیش ہوا۔ سردار نقوی جب گورنمنٹ کالج، کوئٹہ میں تعینات تھے اس دوران اس شہر میں اردو مرثیہ متعارف کرنے کا سہرا بھی ان کے اور اثر ج
```

**verdict:** keep
**note:** poet biography

---

### 116 · fineweb2-urd_Arab:<urn:uuid:0ba84f2f-f895-466a-b161-42892cd03370>

- **filter:** REJECT — repetition:dup_5gram
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 1592 chars, 326 words, 11 lines *(excerpt shows first 1500)*
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.065, dup-ngram 0.413
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://www.minhaj.org/urdu/tid/14830/%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD-%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD-%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD-%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD-%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD-%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD-%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD-%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD-%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD:-%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD-%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD-%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD-%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD-%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD%EF%BF%BD.html

```text
سپریم کورٹ بلا تاخیر ذوالفقار مرزا کو طلب کرے: شیخ الاسلام ڈاکٹرمحمد طاہر القادری
ذوالفقار مرزا کے خدشہ کے تناظر میں سپریم کورٹ ان کے بیان اور
دستاویزات کو فوری طور پر اپنے ریکارڈ میں لے
پاکستان کے موجودہ حالات میں ریکارڈ تلف ہونے کے امکانات کو رد نہیں کیا جاسکتا
ذوالفقار مرزا کے بیانات درست ہیں یا غلط اس کا تعین بھی دستاویزات کو چیک کرنے سے
ہی ممکن ہوگا
شیخ الاسلام ڈاکٹر محمد طاہرالقادری کی لندن سے ناظم اعلیٰ رحیق عباسی سے ٹیلیفونک
گفتگو
شیخ الاسلام ڈاکٹر محمد طاہرالقادری نے کہا ہے کہ کراچی کی صورتحال کے حوالے سے ذوالفقار مرزا کی طرف سے سامنے لائی گئی دستاویزات اور ان کے بیانات انتہائی اہم ہیں۔ مبینہ حقائق اور دستاویزات درست ہیں یا غلط اس کا فیصلہ ہونا بہت ضروری ہے اس لئے سپریم کورٹ بلا تاخیر ذوالفقار مرزا کو طلب کرکے دستاویزی ثبوت اور مکمل بیان ریکارڈ پر لائے۔ ذوالفقار مرزا نے خود جس خدشہ کا اظہار کیا ہے اس تناظر میں ضروری ہے کہ سپریم کورٹ ان کے بیان اور دستاویزات کو فوری طور پر اپنے ریکارڈ میں لے لے، کیونکہ پاکستان کے موجودہ حالات میں ریکارڈ تلف ہونے کے امکانات کو رد نہیں کیا جاسکتا۔ وہ لندن سے تحریک منہاج القرآن کے ناظم اعلیٰ ڈاکٹر رحیق احمد عباسی سے ٹیلیفونک گفتگو کر رہے تھے۔
ڈاکٹر محمد طاہرالقادری نے کہا کہ ذوالفقار مرزا کے بیانات درست ہیں یا غلط اس کا تعین بھی دستاویزات کو چیک کرنے سے ہی ممکن ہوگا۔ اس لئے سپریم کورٹ ذوالفقار مرزا کو بلا کر قانونی تقاضوں کو فی الفورپورا کرے۔ انہوں نے کہا ہے کہ سپریم کورٹ کا کراچی میں جاری قتل و غارت گری اور ٹارگٹ کلنگ کی بدترین لہر پر از خود نوٹس لینا خوش آئند ہے مگر اعلیٰ عدلیہ پر بھاری ذمہ داری عائد ہوتی ہے کہ تحقیقات کے بعد ایسا ٹھوس
```

**verdict:** keep
**note:** political statement, real Urdu prose

---

### 117 · fineweb2-urd_Arab:<urn:uuid:aa4995d4-aa0e-47d9-a801-1dff7e0e1be3>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 2967 chars, 642 words, 12 lines *(excerpt shows first 1500)*
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.022, dup-ngram 0.109
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://www.humsub.com.pk/32229/abbas-baig/

```text
(مرزا عباس بیگ)
2۔ عوام کے حقِ حکمرانی کی عمل پذیری کے نتیجے میں اجتماعی بصیرت بروئے کار آتی ہے جس کا منطقی یا لازمی نتیجہ بہتر نظامِ حکومت و ریاست ہے۔ کسی بھی ملک کے بہتر نظام حکومت و ریاست کا مطلب عوام کی بہتری اور خوشحالی ہے۔
3۔ اگر فردِ واحد کے ذریعے نظامِ حکومت چلانے کے نتیجے میں عوام کی بہتری اور خوشحالی کا زیادہ امکان ہوتا تو آج بھی دنیا میں اسی نظامِ کہنہ کا سکَہ رائج ہوتا یا آج جس جس ملک میں بادشاہت یا جرنیلی حکومتیں ہیں وہ دنیا کی قیادت کرنے والے اور اپنے عوام کے حقوق کی زیادہ سے زیادہ رکھوالی کرنے والے ممالک شمار ہوتے۔
4۔ اہلِ امریکہ نے جمہوریت کی روح کو پانے کے لیے اپنے مخصوص حالات کو پیشِ نظر رکھتے ہوئے اپنے ملک کے لیے ایک آئین ترتیب دیا ہے، جس میں ملکی نظام چلانے کے بنیادی اصول درج ہیں۔ تاہم ماضی میں جب جب زمینی حقائق بدلے تو انھوں نے اپنے آئین میں ضروری تبدیلیاں بھی کیں۔
5۔ جمہوریت کی روح کو پانے کے لیے امریکی عوام اپنے بنائے ہوئے آئین یا بنیادی اصولوں و ضوابط پر مسلسل عمل کرتے آ رہے ہیں جس کی وجہ سے وہاں جمہوریت کی روح اور ان کے عملِ اجتماعی میں فاصلہ کم سے کم ہوتا جا رہا ہے جس کے نتیجے میں عوام کی حالت مقابلتاْ بھتر ہے۔
6۔ پاکستان میں بھی جمہوریت کی روح کو پانے کے لیے بہت تگ و دو کے بعد عوام ایک اچھے نظمِ حکومت کے بنیادی خدوخال یا 1973 کے آئین پر متفق ہو کر اپنا سفر شروع کر چکے ہیں۔
7۔ پاکستان کے بدلے ہوئے حالات میں اگر 1973 کے آئین میں کوئی ایسی چیز ہے یا نہیں ہے جس کی موجودگی یا نہ ہونے کی وجہ سے عوام کے حقِ حکمرانی میں رکاوٹ آتی ہے تو اسے تبدیل کیا جانا چاہیے۔
9۔ پاکستان کے عوام کو ماضی میں جمہوری اصول کی بار بار پامالی کو ذہن میں رکھتے ہوئے، اپنی زبوں حال
```

**verdict:** keep
**note:** 

---

### 118 · urdu-wikipedia:122278

- **filter:** REJECT — too_short
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 150 chars, 26 words, 9 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.187, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=6
- **url:** https://ur.wikipedia.org/wiki/%DB%81%D9%86%D9%B9%D8%B1%20%D8%A8%D8%B1%D8%A7%D8%A6%D8%B3

```text
ہنٹر برائس ایک فحش اداکارہ ہے۔

متعلقہ روابط
فہرست فحش اداکارائیں
فحش فلم
فحش نگاری

حوالہ جات

1980ء کی پیدائشیں
2011ء کی وفیات
امریکی فحش اداکارائیں
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 119 · fineweb2-urd_Arab:<urn:uuid:32a373b8-5e57-45cd-95a4-bd2b3af9c40c>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 594 chars, 118 words, 1 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.084, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://jang.com.pk/amp/1166673-national

```text
سکھر (بیورورپورٹ ) پیلزپارٹی کے مرکزی رہنما وفاقی وزیر برائے آبی وسائل سید خورشید شاہ کی بگڑتی صحت کا معاملہ، سید خورشید شاہ کا برطانیہ سے علاج کرانے کیلئے احتساب عدالت سکھر میں درخواست دائر کردی گئی ہے،احتساب عدالت نے بیماری کے متعلق میڈیکل بورڈ تشکیل دینے کا حکم دے دیا،عدالت نے حکم دیا کہ قابل ڈاکٹروں پر مشتمل میڈیکل بورڈ خورشید شاہ کی صحت کا معائنہ کرے گا، سکھر کی غلام محمد مہر میڈیکل کالج کے پرنسپل کو بورڈ بنانے کے لئے لیٹر جاری کردیا گیا، خورشید شاہ کے وکیل ایڈوکیٹ مکیش کمار کارڑا نے عدالت کو بتایا کہ سید خورشید شاہ کا صرف ایک بار نام ایگزٹ کنٹرول لسٹ سے نکالنے کی درخواست کی گئی ہے۔
```

**verdict:** keep
**note:** 

---

### 120 · urdu-wikipedia:711333

- **filter:** REJECT — html_residue
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 315 chars, 58 words, 10 lines
- **script:** ratio 0.949 (arabic 0.949, latin 0.051)
- **repetition:** dup_line 0.000, top-ngram 0.044, dup-ngram 0.000
- **url** 0.000 · **html** 0.041 · **U+FFFD** 0.00000
- **stage 4:** whitespace=9
- **url:** https://ur.wikipedia.org/wiki/1685%D8%A1

```text
واقعات
<onlyinclude>

پیدائشیں
23 فروری – جارج فریدریک ہاندل، جرمنی کا مکپوزر (وفات۔ 1759ء)
18 اگست – بروک ٹیلر، برطانوی ریاضی دان تھا جس نے ٹیلر سلسلہ دریافت کیا، (وفات :1731ء)

وفیات

6 فروری – بادشاہ چارلس دوم شاہ انگلستان، اسکاٹ لینڈ اور آئرلینڈ (پ۔ 1630ء)

حوالہ جات

1685ء
کامنز زمرہ جس کا ربط ویکی ڈیٹا پر ہے
```

**verdict:** keep
**note:** year article with real event entries

---

### 121 · fineweb2-urd_Arab:<urn:uuid:5982e7d7-ccd0-4ca4-888c-4c5a0bfde21e>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 3785 chars, 775 words, 20 lines *(excerpt shows first 1500)*
- **script:** ratio 0.904 (arabic 0.904, latin 0.096)
- **repetition:** dup_line 0.000, top-ngram 0.031, dup-ngram 0.081
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** http://thewireurdu.com/89521/ramdevs-remarks-doctors-associations-to-hold-nationwide-protest-complaint-lodged-in-bengal/

```text
ایلوپیتھی پر یوگ گرو رام دیو کےتبصرے سے ناراض ریزیڈنٹ ڈاکٹروں کے ایسوسی ایشن کے کنفیڈریشن نے کہا ہے کہ وہ ایک جون کو ملک بھر میں مظاہرہ کریں گے۔ انہوں نے رام دیو سے بنا شرط عوامی طور پر معافی مانگنے کو بھی کہا ہے۔ اسی بیان پر آئی ایم اے کی مغربی بنگال اکائی نے پولیس میں شکایت درج کروائی ہے۔
نئی دہلی: ایلوپیتھی پر یوگ گرو رام دیو کےتبصرے سے ناراض ریزیڈنٹ ڈاکٹروں کے ایسوسی ایشن کےکنفیڈریشن کے ممبروں نے سنیچر کو کہا کہ وہ ایک جون کو ملک گیر احتجاجی مظاہرہ کریں گے اور اسے یوم سیاہ کےطور پر منائیں گے۔
کنفیڈریشن نے بیان جاری کر رام دیو سے بنا کسی شرط عوامی طور پر معافی مانگنے کو کہا ہے۔
Even after raising objections to statements by Mr. Ram Kishan Yadav (#RamdevBaba), no action has been taken yet. We are hereby declaring Nationwide #BlackDayProtest on 1st June,2021 at workplace, without hampering healthcare services @ANI @ians_india @MoHFW_INDIA @drharshvardhan pic.twitter.com/nyWlguxomL
— FORDA INDIA (@FordaIndia) May 29, 2021
بتا دیں کہ سوشل میڈیا پر بڑے پیمانے پر شیئر کیے گئے ایک ویڈیو میں رام دیو کو کہتے سنا گیا تھا کہ ‘ایلوپیتھی ایک اسٹپڈ اور دیوالیہ سائنس ہے’۔انہوں نے یہ بھی کہا کہ ایلوپیتھی کی دوائیں لینے کے بعد لاکھوں لوگوں کی موت ہو گئی، جس کے بعد تنازعہ کھڑا ہو گیا۔
ایلوپیتھی کو اسٹپڈ اور دیوالیہ سائنس بتانے پر یوگ سکھانے والے رام دیو کے خلاف وبائی امراض سے متعلق قانون کے تحت کارروائی کرنے کی ڈاکٹروں کے سب سے بڑےادارےانڈین میڈیکل ایسوسی ایشن(آئی ایم اے)و ڈاکٹروں کے دیگر اداروں کی مانگ کے بعد وزیر صحت ڈاکٹر ہرش وردھن نے رام دیو کو ایک خط لکھ کر ان سے گزارش کی تھی کہ وہ اپن
```

**verdict:** keep
**note:** 

---

### 122 · urdu-wikipedia:675192

- **filter:** REJECT — too_short
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 124 chars, 25 words, 6 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** teh_marbuta=1, whitespace=1
- **url:** https://ur.wikipedia.org/wiki/%D8%A7%D9%84%D8%A7%D8%B3%D8%B1%D8%A7%D8%A1%20%D8%A2%DB%8C%D8%AA%2026

```text
سورہ الاسراء مکی سورہ ہے جبکہ اِس کی آیات 126 تا 128 مدینہ منورہ میں نازل ہوئی ہیں۔

ترجمہ

مقام نزول

تفسیر

حوالہ جات
آیات
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 123 · urdu-wikipedia:429721

- **filter:** REJECT — too_short
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 133 chars, 25 words, 10 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=6
- **url:** https://ur.wikipedia.org/wiki/722%DA%BE

```text
واقعات

ولادتیں

وفیات

مزید دیکھیے
ہجری شمسی

حوالہ جات

بیرونی روابط
ہجری تاریخ کو شمسی سال سے بدلیں
ہجری سال کی اسلام میں اہمیت

2
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 124 · fineweb2-urd_Arab:<urn:uuid:17a9cd65-43b5-432a-886f-55e9f9b0a022>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 1653 chars, 303 words, 11 lines *(excerpt shows first 1500)*
- **script:** ratio 0.660 (arabic 0.660, latin 0.340)
- **repetition:** dup_line 0.071, top-ngram 0.034, dup-ngram 0.264
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://urdu.arynews.tv/coas-important-statement/

```text
دنیا دہشت گردی کے خلاف جنگ میں ہماری قربانیوں کو تسلیم کرے، آرمی چیف
افغانستان میں امن چاہتے ہیں مگرپاکستان کااحترام،سیکیورٹی مقدم ہے
راولپنڈی: آرمی چیف آف اسٹاف جنرل قمر جاوید باجوہ نے کہا ہے کہ پاکستان نے دہشت گردی کے خلاف جنگ میں سب سے زیادہ قربانیاں دیں اور اسے کامیاب بنایا، اب دنیا ہماری قربانیوں کو تسلیم کرے۔
پاک فوج کے شعبہ تعلقاتِ عامہ (آئی ایس پی آر) سے جاری بیان میں آرمی چیف کا کہنا تھا کہ دہشت گردوں کے خلاف جنگ کے ساتھ خطے میں امن کے لیے بھی ہم نے اپنے تعاون اور مدد فراہم کی۔
“We have paid the highest military, economic, political and social cost and the world should acknowledge that. We shall continue to contribute towards peace in Afghanistan but Pakistan’s honour and Pakistan’s security shall always stay premier” COAS. (2 of 2).
— Maj Gen Asif Ghafoor (@OfficialDGISPR) November 20, 2018
اُن کا کہنا تھا کہ پاکستان نے دہشت گردی کے خلاف کامیاب جنگ لڑی اور اس کی سب سے بھاری قیمت بھی اداکی، جنرل قمر جاوید باجوہ کا کہنا تھا ’ہم نےفوجی، اقتصادی، سماجی، سیاسی طور پر سب سےزیادہ قربانیاں دیں اب وقت ہے کہ دنیا ہماری قربانیوں کو تسلیم کرے‘۔
“Pakistan has successfully fought against terrorism while also contributing to regional peace. Pakistan has done much more for peace in Afghanistan than any other country”, COAS. (1 of 2).
— Maj Gen Asif Ghafoor (@OfficialDGISPR) November 20, 2018
آرمی چیف کا کہنا تھا کہ ’پاکستان کاعلاقائی امن میں بھی کردارسب سےنمایاں ہے، ہماری جانب سے افغانستان میں قیامِ امن کے لیے کوششیں بھی کی گئیں یہ سلسلہ آئندہ بھی جاری رکھیں گے‘۔
سپہ سالار کا کہنا 
```

**verdict:** keep
**note:** 

---

### 125 · urdu-wikipedia:922457

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 74501 chars, 15863 words, 160 lines *(excerpt shows first 1500)*
- **script:** ratio 0.998 (arabic 0.998, latin 0.002)
- **repetition:** dup_line 0.000, top-ngram 0.006, dup-ngram 0.064
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=569
- **url:** https://ur.wikipedia.org/wiki/%D9%88%DB%8C%D9%86%D8%B2%D9%88%DB%8C%D9%84%D8%A7%20%D9%85%D8%B8%D8%A7%DB%81%D8%B1%DB%92%20%282014%20%E2%80%93%20%D8%AA%D8%A7%D8%AD%D8%A7%D9%84%29

```text
سن 2014 میں ، وینزویلا میں مظاہروں ، سیاسی مظاہروں اور شہری بغاوت کا ایک سلسلہ ملک کے اعلی سطح پر شہری تشدد ، افراط زر ، اور بنیادی سامان اور خدمات کی دائمی قلت کی وجہ سے شروع ہوا۔ ان بدتر حالات کے بارے میں وضاحتیں مختلف ہوتی ہیں جس پر قیمتوں پر سخت قابو اور طویل مدتی ، وسیع تر سیاسی بدعنوانی کے نتیجے میں بنیادی سرکاری خدمات کی کم فنڈنگ کا الزام عائد کیا جاتا ہے۔ جنوری میں اداکارہ اور سابق مس وینزویلا مینیکا سپیئر کے قتل کے بعد جنوری میں مظاہرے ہوئے ، سن کرسٹبل میں یونیورسٹی کے ایک کیمپس میں فروری کے ایک طالب علم عصمت دری کی کوشش کے بعد فروری میں سن 2014 ء کے مظاہرے اس واقعے کے ساتھ شروع ہوئے۔ اس کے نتیجے میں طلباء کے مظاہرین کی گرفتاریوں اور ان کے قتل نے پڑوسی شہروں تک ان کی توسیع اور اپوزیشن رہنماؤں کی شمولیت کو فروغ دیا۔ اس سال کے ابتدائی مہینوں میں مظاہرین اور سرکاری فوج کے مابین بڑے مظاہروں اور پرتشدد جھڑپوں کی خصوصیت رہی تھی جس کے نتیجے میں تقریبا 4 4،000 گرفتاریوں اور 43 افراد کی موت واقع ہوئی تھی ، بشمول حکومت کے حامی اور مخالفین دونوں۔ 2014 کے اختتام اور 2015 تک ، مسلسل قلت اور تیل کی کم قیمتوں کے باعث نئے سرے سے احتجاج شروع ہوا۔

سن 2016 تک وینزویلا کے پارلیمانی انتخابات اور 2016 کے ریفرنڈم کے آس پاس ہونے والے واقعات کے بعد ہونے والے تنازعہ کے بعد احتجاج ہوا۔ یکم ستمبر 2016 کو ، مظاہروں کا سب سے بڑا مظاہرہ ہوا ، جس میں 10 لاکھ سے زیادہ وینزویلاین ، یا پوری قوم کی 3٪ سے زیادہ افراد صدر مادورو کے خلاف دوبارہ انتخاب کے مطالبے کے لئے جمع ہو گئیں ، اس پروگرام کو "سب سے بڑا مظاہرے" کے طور پر بیان کیا گیا۔ وینزویلا کی تاریخ "۔ 21 اکتوبر 2016 کو حکومت کی طرف جھکاؤ والی قومی
```

**verdict:** keep
**note:** 

---

### 126 · fineweb2-urd_Arab:<urn:uuid:bf25f636-2add-4d1d-b88b-8bfbc71f7dd0>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 1755 chars, 328 words, 3 lines *(excerpt shows first 1500)*
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.044, dup-ngram 0.081
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://zamaswat.com/swat-news/2021/03/26/37193.html/

```text
سوات، کورونا ایس اوپیزکی خلاف ورزی، عام دکانداروں سے 53ہزار وصول
ضلعی انتظامیہ صرف دکانداروں کے پیچھے لگی ہوئی ہیں،بے جا جرمانوں سے تنگ آگئے ہیں، متاثرہ دکاندار
سوات(زما سوات ڈاٹ کام)سوات میں کورونا ایس او پیز کی خلاف ورزی پر ایک ہفتے کے دوران ضلعی انتظامیہ نے65ہزار جرمانہ وصول کرلیا، سب سے زیادہ جرمانہ دکانداروں سے وصول کیا گیاجو53ہزار پانچ سو روپے ہیں۔ سوات میں ضلعی انتظامیہ نے15مارچ سے21مارچ تک ایک ہفتے کے دوران ایس او پیز کی خلاف ورزی پر مختلف کارروائیاں کیں۔ ضلعی انتظامیہ کی جانب سے جاری کردہ رپورٹ کے مطابق 680عام دکانوں کا معائنہ کیا گیا اور ایس او پیز کی خلاف ورزی کرنے پر36دکانداروں پر جرمانہ عائد کیا گیا،جن سے مجموعی طور پر53ہزار500روپے وصول کئے گئے اور باقی دکانداروں کو وارننگ دے دی گئی۔ اسی طرح رپورٹ میں کہا گیا ہے کہ56مارکیٹوں کا معائنہ کیا گیا،32ٹرانسپورٹ اڈوں کا معائنہ کیا گیا اور صرف ایک اڈے پر ہزار روپے جرمانہ عائد کیا گیا۔160پبلک ٹرانسپورٹ گاڑیوں کا معائنہ اور25کو وارننگ دی گئی۔345عام لوگوں کو کورونا ایس اوپیز کے حوالے سے انسپکٹ کیا گیا جس میں 97کو وارننگ اور پانچ افراد سے 1000روپے جرمانہ وصول کیا گیا۔31پٹرول پمپس کا معائنہ اور8کو وارننگ دی گئی۔70ریسٹورنٹس کا معائنہ،10کو وارننگ دی گئی اور 2روسٹورنٹس سے ایس او پیز کی خلاف ورزی پر دس ہزار روپے وصول کئے گئے۔اسی طرح 33تعلیمی اداروں،دو شادی ہالز اور62متفرق اداروں و کاروباروں کا معائنہ کیا گیا۔ ضلعی انتظامیہ کے مطابق مجموعی طور پر ایک ہفتے کے دوران1471معائنے کئے گئے،392کو وارننگ دی گئی اور44سے جرمانہ 65ہزار پانچ سو روپے وصول کیا گیا۔ ضلعی انتظامیہ کی رپورٹ کے مطابق سب سے زیادہ جرمانہ بازار میں عام دکانداروں سے وصول 
```

**verdict:** keep
**note:** 

---

### 127 · urdu-wikipedia:908540

- **filter:** REJECT — too_short
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 152 chars, 27 words, 6 lines
- **script:** ratio 0.958 (arabic 0.958, latin 0.042)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=5
- **url:** https://ur.wikipedia.org/wiki/%D9%BE%DA%A9%D8%A7%D9%86%D8%8C%20%D9%BE%D8%A7%DB%81%D8%A7%D9%86%DA%AF

```text
پکان (لاطینی: Pekan) ملائیشیا کا ایک آباد مقام جو پاہانگ میں واقع ہے۔

مزید دیکھیے
ملائیشیا
ملائیشیا کے شہروں کی فہرست

حوالہ جات

پاہانگ کے آباد مقامات
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 128 · urdu-wikipedia:1085863

- **filter:** REJECT — script_ratio, html_residue
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 453 chars, 72 words, 14 lines
- **script:** ratio 0.686 (arabic 0.686, latin 0.314)
- **repetition:** dup_line 0.000, top-ngram 0.119, dup-ngram 0.000
- **url** 0.000 · **html** 0.038 · **U+FFFD** 0.00000
- **stage 4:** whitespace=4
- **url:** https://ur.wikipedia.org/wiki/%D9%88%DB%8C%D8%B3%D9%B9%20%D9%BE%D9%88%D9%B9%D9%88%D9%85%DB%8C%DA%A9%20%D9%BE%D8%A7%D8%B1%DA%A9

```text
{{Infobox NRHP
|name=ویسٹ پوٹومیک پارک
|nrhp_type=cp
|partof=East and West Potomac Parks Historic District
|partof_refnum=73000217<ref name="nris">
ویسٹ پوٹومیک پارک (لاطینی: West Potomac Park) ریاست ہائے متحدہ کا ایک آباد مقام جو واشنگٹن، ڈی سی میں واقع ہے۔

مزید دیکھیے
ریاست ہائے متحدہ
ریاست ہائے متحدہ کے شہروں کی فہرست

حوالہ جات

نیشنل مال اور میموریل پارکس
واشنگٹن، ڈی سی میں پارک
واشنگٹن، ڈی سی میں رگبی یونین اسٹیڈیم
ساؤتھ ویسٹ (واشنگٹن، ڈی سی)
```

**verdict:** drop
**note:** {{Infobox}} template dump, the document is markup

---

### 129 · fineweb2-urd_Arab:<urn:uuid:cf5e893d-3ade-4713-ba06-31159a2eae6e>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 5302 chars, 1165 words, 12 lines *(excerpt shows first 1500)*
- **script:** ratio 0.981 (arabic 0.981, latin 0.019)
- **repetition:** dup_line 0.000, top-ngram 0.014, dup-ngram 0.017
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** heh=1
- **url:** https://didi588.space/category-9/page-360211.html

```text
لیکن ہم نے زور دے کر کہا کہ ہم دیکھ رہے ہیں کہ مالیاتی پالیسی کی ترتیبات مستقبل قریب میں ایک جیسی ہی رہیں گی۔ موجودہ معاشی پالیسی سے ہماری معیشت کو کافی تعاون حاصل ہے۔ سیویگر پانچ ماہ گزر جانے کے بعد بھی کہتے ہیں کہ وہ اداس ہیں۔ یہ ایک بہت برا تجربہ تھا۔ ہم نے دو سالوں تک اس ٹرپ کی منصوبہ بندی کی تھی۔ یہ انتہائی گھناؤنا جرم ہے۔ اپنی ڈگریوں کی آزادی کے ل to اپنے نمونے کے سائز سے 1 کو گھٹائیں۔ مثال کے طور پر ، 25 کے نمونے کے سائز میں df = 25 - 1 = 24 ڈگری آزادی ہے۔ اپنی اہم قدر تلاش کرنے کے لئے ٹی اسکور ٹیبل کا استعمال کریں۔ اگر آپ 95 آپ ایک scalper ہیں اگر فیصد اعتماد کا وقفہ چاہتے ہیں تو ، ٹیبل پر 0.05 کے لیبل والے کالم کو دو دم دم والے اقدار کیلئے یا 0.01 کالم ایک دم ٹیبل پر استعمال کریں۔ اس قدر کی تلاش کریں جو آپ کے اعتماد کی سطح اور آپ کی آزادی کی ڈگریوں کو پارہ پارہ کرے۔ ڈی ایف = 24 کے ساتھ اور 95 فیصد اعتماد پر ، ٹی = 2.064۔
اس طرح ، ہم نے ایف سی اے کے ذریعے باقاعدہ دلالوں پر نظر آنے والے سب سے زیادہ عام طور پر دیکھے جانے والے تعلیمی اور تجارتی ٹولز کی ایک فوری فہرست ایک ساتھ رکھی ہے۔ صرف اس بات پر غور کرنے کے بعد کہ آئین اعلی معمول بن کر قانونی نظام میں سب سے زیادہ مقام رکھتا ہے ، کیا آئینی ریاست کے قانون کے بارے میں بات کرنا ممکن ہے ، یہ بات امریکہ میں انیسویں صدی کے اوائل میں اس وقت ہوتی ہے جب سن 1803 کے جج مارشل نے ماربری بمقابلہ میڈیسن کیس میں ، ایک وفاقی قانون کے تحت اور کاسٹیلی آندرے کے معیار کے مطابق خط میں میگنا کارٹا کی بالادستی کا اعلان کیا تھا ، جس کا حوالہ پہلے دیا جا چکا ہے۔ ". آئین سازی اصول بن گئ اور اس کے علاوہ ، متنازعہ اقتدار کی پیداوار ، جو خودمختار ط
```

**verdict:** keep
**note:** 

---

### 130 · fineweb2-urd_Arab:<urn:uuid:c4922de5-de7d-476c-b519-812b95d98158>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 899 chars, 169 words, 4 lines
- **script:** ratio 0.658 (arabic 0.658, latin 0.342)
- **repetition:** dup_line 0.000, top-ngram 0.050, dup-ngram 0.082
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://dailygulfnews.pk/2021/06/11/%D8%B1%D9%88%D8%B3-%D9%86%DB%92-%D9%BE%D8%A7%DA%A9%D8%B3%D8%AA%D8%A7%D9%86%DB%8C-%DA%86%D8%A7%D9%88%D9%84-%DA%A9%DB%8C-%D8%A8%D8%B1%D8%A2%D9%85%D8%AF%D8%A7%D8%AA-%D8%B3%DB%92-%D9%BE%D8%A7%D8%A8%D9%86/

```text
اسلام آباد (گلف آن لائن) روس نے پاکستانی چاول کی برآمدات سے پابندی ہٹا دی چاول کی برآمدات شروع ہو گئی. پاک روس تعلقات مزید مضبوط ہونے لگے،روس نے پاکستانی چاول کی برآمدات سے پابندی ہٹادی،روس کی جانب سے پاکستانی چاول پر پابندی 2018 میں لگائی گئی تھی، پاکستان آج سے روس کو چاول برآمد کرے گا، مشیر تجارت عبدالرزاق داؤد نے ٹویٹ پر تصدیق کردی۔
Breakthrough in Rice Exports! We are glad to share that Russia has allowed import of Pakistan’s rice from 11 June 2021. Initially 4 firms have been allowed & more will be allowed after virtual inspection by Russian Authorities which would be coordinated by DPP.
— Abdul Razak Dawood (@razak_dawood) June 11, 2021
مشیرتجارت نے لکھا کہ ہمیں یہ بتاتے ہوئے خوشی ہورہی ہے کہ روس نے گیارہ جون سے پاکستان کے چاول کی برآمد کی اجازت دے دی ہے،ابتدائی طور پر چار کمپنیوں کو اجازت ملی ہے،اسے پاکستان اور روس کے تجارتی تعلقات میں بہتری کے حوالے سے اہم پیش رفت سمجھا جارہاہے۔
```

**verdict:** keep
**note:** 

---

### 131 · urdu-wikipedia:182745

- **filter:** REJECT — too_short, script_ratio
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 168 chars, 27 words, 6 lines
- **script:** ratio 0.620 (arabic 0.620, latin 0.380)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=4
- **url:** https://ur.wikipedia.org/wiki/%D8%A8%D8%B1%D8%B2%D8%B3%DA%A9%DB%8C-%DA%A9%D9%88%D9%88%D8%A7%DA%A9%DB%8C

```text
برزسکی-کوواکی پولینڈ کا ایک رہائشی علاقہ جو Gmina Chorzele میں واقع ہے۔

مزید دیکھیے
پولینڈ
فہرست پولینڈ کے شہر

حوالہ جات

Short description is different from Wikidata
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 132 · fineweb2-urd_Arab:<urn:uuid:b82f0876-48f3-4fb7-b763-11c5a91b1945>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 16580 chars, 3393 words, 58 lines *(excerpt shows first 1500)*
- **script:** ratio 0.999 (arabic 0.999, latin 0.001)
- **repetition:** dup_line 0.000, top-ngram 0.008, dup-ngram 0.038
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** digits=1, heh=2, presentation_forms=1, teh_marbuta=1, yeh=2
- **url:** https://www.wujood.com/41684/

```text
... loading ...
پاکستان بار بار یہی بات دہرارہا ہے لیکن بھارت فوجی قبضے اورتسلط پراَڑاہوا ہے ،نتیجہ آنے تک مقد س اورجائزجدوجہد جاری رکھیں گے
بھارتی مظالم کے آگے سینہ سپر87سالہ ناتواں بزرگ لیکن جواں عزائم اورمضبوط اعصاب کے مالک چیئرمین آل پارٹیز حریت کانفرنس
انٹرویوپینل:شیخ امین ۔مقصود منتظر
وجود:1990 سے لیکر آج تک ہزاروں نامور عسکری کمانڈر اور سیاسی رہنماشہید ہوئے ۔ آپ کی نظر میں وہ کیا خاص چیز تھی جس نے حزب المجاہدین کے کمانڈربرہان وانی کو مقبولیت کی بلندیوں تک پہنچا یا اور 8جولائی کو کشمیرکی تاریخ میں ناقابل فراموش دن کے طور پر رقم کرایا ۔
سیدعلی گیلانی:شہید بُرہان وانی کی شہادت کے بعد پوری وادی ہی نہیں بلکہ چناب ویلی اور پیر پنچال کے مسلمان بھی حرکت میں آگئے اور انہوں نے بھارت کے فوجی تسلط سے آزادی حاصل کرنے کا عہد کیا۔ برہان مظفرکے خلوص اور یکسوئی کے نتیجے میں یہ انقلابی لہر اُبھر آئی۔
وجود : موجودہ عوامی تحریک کے د وران عوام نے آپ کے احتجاجی پروگراموں پر من و عن عمل کیا اور تاحال کررہے ہیں جو یقیناًخوش آئند بات ہے۔لیکن بظا ہر دیکھنے میں آرہا ہے کہ بھارتی قیادت اپنی ہٹ دھرمی پر قائم ہے ۔ کیا اس ہٹ دھرمی کا توڑ کرنے کیلیے آپ کے پاس کوئی متبادل حکمت عملی ہے؟
سید علی گیلانی:موجودہ تحریک اور جدوجہد میں ہمارے پروگرام کا عوام نے بھرپور ساتھ دیا۔ عظیم اور بے مثال قربانیاں بھی دی گئیں جن کا ہمیں بھرپور احساس ہے اور ہم دل کی عمیق گہرائیوں کے ساتھ مظلوم عوام کے شکرگزار اور احسان مند ہیں۔ بھارت کی ضد اور ہٹ دھرمی کا ہمارے پاس کوئی علاج نہیں ہے۔ سوائے اس کے کہ فوجی تسلط کے خلاف ہماری جدوجہد میں استقامت کا ہر سطح اور ہر مرحلے پر مظاہرہ کیا جائے۔ بھارت کی حکومت اور سیاسی قیادت نشۂ قوت 
```

**verdict:** keep
**note:** 

---

### 133 · urdu-wikipedia:919624

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 1253 chars, 251 words, 10 lines
- **script:** ratio 0.959 (arabic 0.959, latin 0.041)
- **repetition:** dup_line 0.000, top-ngram 0.032, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=2
- **url:** https://ur.wikipedia.org/wiki/%D8%A8%DB%8C%D8%B1%D9%88%D8%AA%20%D8%AF%DA%BE%D9%85%D8%A7%DA%A9%DB%92%202020%D8%A1

```text
لبنان کے دار الحکومت بیروت میں 4 اگست 2020ء بروز منگل یکے بعد دیگرے کئی زوردار دھماکے ہوئے۔ یہ دھماکے بیروت کی بندرگاہ پر ہوئے جن کے نتیجے میں تا دم تحریر 100 افراد کی ہلاکت اور 4,000 افراد کے زخمی ہونے کی اطلاعات ہیں؛ جب کہ بیسیوں افراد لاپتہ ہیں۔

لبنان کی جنرل سیکیورٹی کے ڈائریکٹر جنرل عباس ابراھیم کے مطابق بیروت کی بندرگاہ پر 2,750 ٹن امونیم نائٹریٹ بغیر کسی حفاظتی اقدامات کے ذخیرہ کیا گیا تھا جو ان دھماکوں کا سبب بنا۔ انہوں نے بتایا کہ یہ مواد گزشتہ 6 سال سے وہاں موجود تھا۔ ماہرین کے اندازے کے مطابق ان دھماکوں کی شدت کئی سو ٹن بارودی مواد کے برابر تھی۔

دھماکے
پہلے ایک ہلکا دھماکا ہوا جس سے شعلے بھڑکے اور دھویں کا ایک بادل فضا میں بلند ہوا اور بجلی کی چمک جیسے کوندے لپکے عینی شاہدین کے مطابق یہ آتش بازی جیسا عمل لگتا تھا۔اس کے بعد مقامی وقت کے مطابق 18:08:18 پر دوسرا اور شدید دھماکا ہوا۔ اس دھماکے نے وسطی بیروت کو ہلا کر رکھ دیا، سرخی مائل دھوئیں اور گرد کا بادل فضا میں پھیل گیا۔ یہ دھماکا اس قدر شدید تھا کہ اس کے اثرات شمالی اسرائیل اور 240 کلومیٹر(150 میل) دور قبرص میں بھی محسوس کیے گئے۔ ریاستہائے متحدہ امریکا کی جیولوجیکل سروس کے مطابق دھماکے کی شدت 3.3 درجے کے زلزلے کے برابر تھی۔

حوالہ جات

2020ء میں ایشیا میں آفات
2020ء میں دھماکے
صنعتی آتشزدگیاں اور دھماکے
فلم شدہ حادثاتی اموات
Short description is different from Wikidata
```

**verdict:** keep
**note:** 

---

### 134 · urdu-wikipedia:362470

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** code_switched
- **size:** 252 chars, 44 words, 8 lines
- **script:** ratio 1.000 (arabic 0.827, latin 0.173)
- **repetition:** dup_line 0.000, top-ngram 0.103, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=4
- **url:** https://ur.wikipedia.org/wiki/%D8%B2%DA%86%D9%BE%DB%8C%D9%84%D9%88%DA%A9%D8%A7%20%D8%B1%DB%8C%D9%88%DA%BA

```text
زچپیلوکا ریوں یوکرین کا ایک raion of Ukraine جو خارکیو اوبلاست میں واقع ہے۔

تفصیلات
زچپیلوکا ریوں کا رقبہ 793.6 مربع کیلومیٹر ہے اور اس کی مجموعی آبادی 15,704 افراد پر مشتمل ہے۔

مزید دیکھیے
یوکرین
فہرست یوکرین کے شہر

حوالہ جات

en:Zachepylivka Raion
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 135 · fineweb2-urd_Arab:<urn:uuid:faebcdb7-e7b3-4835-b2cd-ffd0ada51abc>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 3035 chars, 586 words, 20 lines *(excerpt shows first 1500)*
- **script:** ratio 0.669 (arabic 0.669, latin 0.331)
- **repetition:** dup_line 0.046, top-ngram 0.032, dup-ngram 0.199
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://urdu.92newshd.tv/about/%D8%AE%DB%8C%D8%A8%D8%B1%D9%BE%D8%AE%D8%AA%D9%88%D9%86%D8%AE%D9%88%D8%A7-%D8%A7%D9%88%D8%B1-%D8%A8%D9%84%D9%88%DA%86%D8%B3%D8%AA%D8%A7%D9%86-%D9%85%DB%8C%DA%BA-%D8%AA%DB%8C%D9%86-%D8%B1%D9%88%D8%B2

```text
خیبرپختونخوا اور بلوچستان میں تین روزہ انسداد پولیو مہم کا آغاز ہو گیا
May 16, 2016
خیبرپختونخوا اور بلوچستان میں تین روزہ انسداد پولیو مہم کا آغاز ہو گیا
پشاور / کوئٹہ (92نیوز) خیبرپختونخوا‘ فاٹا اور بلوچستان میں تین روزہ انسداد پولیو مہم شروع ہو گئی۔ خیبرپختونخوا میں پانچ سال سے کم عمر کے 56 لاکھ بچوں جبکہ قبائلی علاقوں میں 9 لاکھ 65 ہزار 633 بچوں کو پولیو سے بچاو کے قطرے پلائے جائیں گے۔
تفصیلات کے مطابق خیبرپختونخوا میں پانچ سال سے کم عمر کے 56 لاکھ بچوں کو پولیو سے بچاو کے قطرے پلانے کے لئے 17 ہزار ٹیمیں تشکیل دی گئی ہیں۔ 14 ہزار پولیو ورکرز گھر گھر جا کر جبکہ 3 ہزار پولیو ٹیموں کے 9ہزار ورکرز ٹرانسپورٹ اڈوں، تجارتی مراکز اور اہم شاہراہوں پر بچوں کو پولیو سے بچاو کے قطرے پلائیں گے۔ اس مقصد کے لئے 3ہزار لیڈی ہیلتھ ورکررز کی تعیناتی کی گئی ہے۔
مہم کے لئے سکیورٹی انتہائی سخت کر دی گئی ہے۔ پشاور سمیت تمام بڑے اور حساس اضلاع میں موٹر سائیکل کی ڈبل سواری پر پابندی عائد کر دی گئی ہے۔ قبائلی علاقوں میں 9 لاکھ 65 ہزار 633 بچوں کو پولیو سے بچاو کے قطرے پلائے جائیں گے جس کے لئے 3ہزار 78 ٹیمیں تشکیل دی گئی ہیں۔
پولیو کے حوالے سے حساس قبائلی علاقوں باڑہ اور جمرود ‘ایف آر بنوں کے علاقوں باکاخیل، جانی خیل،بندی خیل اور تین ٹانگہ اور شمالی اور جنوبی وزیرستان میں بھی مہم کے لئے سکیورٹی کے سخت انتظامات کئے گئے ہیں۔
دریں اثنا بلوچستان کے تین اضلاع میں انسداد پولیو مہم آج سے شروع ہوگئی۔ پولیومہم کے دوران 5سال تک کے عمر کے 23لاکھ 94ہزارسے زائدبچوں کو پولیو سے بچاو کے قطرے پلانے کاہدف مقرر کیاگیاہے جس کیلئے 6773موبائل ٹیمیں ،825فکسڈ سائٹ اور 340ٹرانزٹ پوائنٹس بنائے گئے ہیں جبکہ افغان مہاجرین کے
```

**verdict:** keep
**note:** 

---

### 136 · urdu-wikipedia:120973

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** code_switched
- **size:** 232 chars, 44 words, 6 lines
- **script:** ratio 1.000 (arabic 0.897, latin 0.103)
- **repetition:** dup_line 0.000, top-ngram 0.103, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=4
- **url:** https://ur.wikipedia.org/wiki/%D9%86%D9%88%D9%85%D8%A7%D8%B2%D9%88%D8%8C%20%D8%B4%DB%8C%D8%B2%D9%88%DA%A9%D8%A7

```text
نومازو، شیزوکا ایک special city of Japan ہے جو جاپان میں واقع ہے۔ اس کی مجموعی آبادی 198,926 افراد پر مشتمل ہے، یہ شیزوکا پریفیکچر میں واقع ہے۔

متعلقہ روابط
جاپان کے شہر

حوالہ جات

جاپان کے آباد ساحلی مقامات
شیزوکا پریفیکچر کے شہر
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 137 · fineweb2-urd_Arab:<urn:uuid:f71011d4-67ac-4c3c-a7f2-b638a3fe2de4>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 1316 chars, 276 words, 11 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.034, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** http://beta.aaj.tv/news/30276915/

```text
ٹرانسپیرنسی انٹرنیشنل کی رپورٹ کے مطابق پاکستان کرپشن پرسیپشن انڈیکس 2021 میں 180 ممالک میں سے 140 ویں نمبر پر آگیا ہے۔
ملک 2020 میں عالمی بدعنوانی کی فہرست میں 124 ویں نمبر پر تھا۔
رپورٹ کے مطابق پاکستان کا سکور جو پہلے 31 تھا، اس سال انڈیکس میں تین پوائنٹس کی کمی سے 28 پر آ گیا۔
دنیا نیوز کے مطابق نواز شریف نے ایک بیان میں کہا کہ عمران نیازی کے دور میں کرپشن تیزی سے بڑھ رہی ہے اور دنیا اب کہہ رہی ہے کہ وہ چور ہے۔
سی پی آئی نے دنیا بھر کے 180 ممالک اور خطوں کو ان کے عوامی شعبے کی بدعنوانی کی سطح کے مطابق درجہ بندی کیا ہے۔
عالمی سطح پر رپورٹ میں انکشاف کیا گیا ہے کہ دنیا بھر میں بدعنوانی کی سطح رکی ہوئی ہے۔
اس سال ممکنہ 100 پوائنٹس میں سے صرف 43 پر، مسلسل دسویں سال عالمی اوسط میں کوئی تبدیلی نہیں ہوئی۔
متعدد وعدوں کے باوجود 131 ممالک نے گزشتہ دہائی میں بدعنوانی کے خلاف کوئی قابل ذکر پیش رفت نہیں کی۔
کرپشن انڈیکس میں سرفہرست ممالک میں ڈنمارک، فن لینڈ اور نیوزی لینڈ 88 پوائنٹس کے ساتھ شامل ہیں، سب سے نیچے والوں میں 11 پوائنٹس کے ساتھ جنوبی سوڈان، شام اور صومالیہ 13 پوائنٹس کے ساتھ شامل ہیں۔
ٹرانسپرنسی انٹرنیشنل ایک عالمی تحریک ہے جو 100 سے زیادہ ممالک میں کام کر رہی ہے، نگران ادارے کا مقصد کرپشن کی ناانصافی کا خاتمہ ہے۔
ٹرانسپرنسی انٹرنیشنل نے اپنے بیان میں کہا کہ "ہم لوگوں کی زندگیوں پر سب سے زیادہ اثر ڈالنے والے مسائل پر توجہ مرکوز کرتے ہیں اور طاقتوروں کو عام بھلائی کے لیے ذمہ دار ٹھہراتے ہیں۔"
```

**verdict:** keep
**note:** 

---

### 138 · urdu-wikipedia:919632

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 38620 chars, 8211 words, 130 lines *(excerpt shows first 1500)*
- **script:** ratio 0.989 (arabic 0.989, latin 0.011)
- **repetition:** dup_line 0.001, top-ngram 0.009, dup-ngram 0.046
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=269
- **url:** https://ur.wikipedia.org/wiki/%D8%AC%D8%A7%D9%BE%D8%A7%D9%86%20%D9%BE%D8%B1%20%D9%82%D8%A8%D8%B6%DB%81

```text
دوسری جنگ عظیم کے اختتام پر جاپان پر اتحادیوں کے قبضے کی قیادت ، برطانوی دولت مشترکہ کی حمایت کے ساتھ ، اتحادی طاقتوں کے سپریم کمانڈر ، جنرل ڈگلس میک آرتھر نے کی۔ جرمنی پر قبضے کے برعکس ، سوویت یونین کو جاپان پر کسی حد تک اثر و رسوخ کی اجازت نہیں تھی۔ جاپان کی تاریخ میں یہ غیر ملکی موجودگی واحد موقع ہے جب اس پر کسی غیر ملکی طاقت کا قبضہ رہا ہے۔ میک آرتھر کے اصرار پر شہنشاہ ہیروہیتو شاہی تخت پر قائم رہا۔ جنگی وقت کی کابینہ کو اتحادیوں کے لئے قابل قبول کابینہ کے ساتھ تبدیل کیا گیا اور پوٹسڈم اعلامیے کی شرائط پر عمل درآمد کرنے کا عہد کیا ، جس میں ملک کو پارلیمانی جمہوریت بننے کا مطالبہ کیا گیا تھا۔ میک آرتھر کی رہنمائی کے تحت ، جاپانی حکومت نے بڑے پیمانے پر معاشرتی اصلاحات متعارف کروائیں اور معاشی اصلاحات نافذ کیں جنھیں صدر روز ویلٹ کے تحت 1930 کی دہائی میں امریکی " نیو ڈیل " کی ترجیحات یاد آگئیں ۔ جاپانی آئین کو جامع طور پر زیربحث کیا گیا اور شہنشاہ کی نظریاتی طور پر وسیع طاقتیں ، جو کئی صدیوں سے کنونشنوں کے ذریعہ پابند تھیں جو وقت کے ساتھ ساتھ تیار ہوئیں ، قانون کے ذریعہ سختی سے محدود ہوگئیں۔ یہ قبضہ ، جس کا خفیہ نام آپریشن بلیک لسٹ تھا، اس کا خاتمہ ا سان فرانسسکو امن معاہدے ، کے ذریعے کیا گیا تھا ، اس پر 8 ستمبر 1951 کو دستخط ہوئے تھے اور 28 اپریل 1952 سے اس پر عمل درآمد ہوا تھا ، جس کے بعد جاپان کی خودمختاری ریوکیو جزائر پر ، 1972 ء تک کی رعایت کے ساتھ مکمل طور پر بحال کر دی گئی تھی۔

جاپانی ہتھیار ڈالنا

ابتدائی مرحلہ
جاپان نے 15 اگست 1945 کو اتحادیوں کے سامنے ہتھیار ڈال دیئے ، جب جاپانی حکومت نے اتحادیوں کو مطلع کیا کہ اس نے پوٹسڈم ڈیکلریشن کو قبول کرلیا ہے۔ اگلے دن ، شہنش
```

**verdict:** keep
**note:** 

---

### 139 · fineweb2-urd_Arab:<urn:uuid:58226fe1-1592-4cab-b3d6-a5d86ba78544>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 849 chars, 167 words, 4 lines
- **script:** ratio 0.696 (arabic 0.696, latin 0.304)
- **repetition:** dup_line 0.000, top-ngram 0.047, dup-ngram 0.000
- **url** 0.027 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://thepakistantoday.com/rajpal-yadav-speaks-out-against-the-extremism-of-his-own-country/

```text
گذشتہ برسوں کے دوران ہندوستان میں شدت پسند گروہوں کے ذریعہ نقل مکانی کا عمل انتہائی عام ہو رہا ہے۔ سینکڑوں افراد کے انتہا پسند گروہوں کے ذریعہ درجنوں مسلم مردوں کو موت کے گھاٹ اتار دیا گیا اور زیادہ افسوسناک حقیقت یہ ہے کہ ان قتل و غارت کے الزامات کو کبھی بھی انصاف کے کٹہرے میں نہیں لایا گیا۔
ہجوم کے حالیہ پرتشدد بڑھے ہوئے واقعات پر راج پال یادیو آخر کار بول اُٹھے ۔ اپنے ٹویٹر اکاؤنٹ پر شیئر کیے گئے ایک ویڈیو پیغام میں ، راج پال یادو نے کہا: “آپ سینکڑوں میں جمع ہو جاتے ہیں اور اپنے درمیان ایک بوڑھے کو پکڑتے ہیں۔ آپ نے اسے مار ڈالا اور فخر محسوس کیا۔ کیا یہ فخر کی بات ہے یا شرم کی بات؟ “
Indian actor @rajpalofficial speaking truth about Govt sponsored RSS attacks against Muslims and risking his life we need to speak for the rights of non-Muslims in Pakistan without any fear https://t.co/3mVLdZHO1e
— Hamid Mir (@HamidMirPAK) April 26, 2020
```

**verdict:** keep
**note:** 

---

### 140 · fineweb2-urd_Arab:<urn:uuid:9356e702-0f96-4fd9-aa7c-bfe4d092559a>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 2165 chars, 435 words, 20 lines *(excerpt shows first 1500)*
- **script:** ratio 0.690 (arabic 0.690, latin 0.309)
- **repetition:** dup_line 0.000, top-ngram 0.023, dup-ngram 0.020
- **url** 0.021 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://news360.tv/latest/60034/

```text
علی ظفر کے وکلا نے ریما عمر کو قانون کا سبق یاد دلا دیا
ریما عمر نے ٹویٹ کے ذریعے علی ظفر کے مقدمہ جیتنے کے دعوے کو غلط قرار دیا، گلوکار کے وکلا نے ریما عمر کو قانونی جواب دیئے۔
میشا شفیع کی وکیل ریما عمر نے ٹوئٹر پر گلوکار علی ظفر کے دعووں کو غلط قرار دینے کے لیے عدالتی فیصلے کے ایک حصے کی تصویر شیئر کی ہے۔
انہوں نے لکھا کہ جیت کے خودساختہ دعووں اور مکمل طور پر غلط معلومات پھیلانے پر یہ پوسٹ لکھ رہی ہوں۔
یہ بھی پڑھیے
جنسی ہراسانی میں ملوث گورنر بھائی کی مدد : سی این این کا اینکرنوکری سے فارغ
آسٹریلوی پارلیمنٹ کے ایک تہائی ملازمین جنسی ہراسانی کا نشانہ بنے
خیال رہے کہ علی ظفر نے چند روز پہلے سوشل میڈیا پر دعویٰ کیا تھا کہ میشا شفیع کا کیس ختم ہوچکا ہے جس کے بعد قانونی طور پر میں بےگناہ ہوں۔
ریما عمر کی جانب سے پوسٹ کیے گئے عدالتی فیصلے کی شق نمبر 12 میں درج ہے کہ یہ کیس پہلے وفاقی محتسب کی عدالت میں پیش کیا جائے گا اور اس شکایت پر فیصلہ اس لیے نہیں ہوسکتا کیوں کہ ابھی کیس اس فورم پرپیش نہیں کیا گیا۔
ریما عمر کی ٹویٹ کے جواب میں علی ظفر کی وکیل بیرسٹر عنبرین قریشی نے لکھا کہ عدالت کی طرف سے قصوروار قرار دیئے جانے تک علی ظفر بےگناہ تھے، ہیں اور رہیں گے۔ علی ظفر نے کو کہا وہ قانونی طور پر درست ہے۔
He was, is and always will be innocent until proven otherwise i.e by court of law- not by self proclaimed social media justices who become the judge, jury and executioners with zero information. What he said is factually and legally correct. https://t.co/JuHdV2u4NI
— Barrister Ambreen Qureshi 🇵🇰 (@ambreenqureshi) January 21, 2022
گلوکار کے دوسرے وکیل عمر طارق گل نے بھی ریما عمر کو جواب
```

**verdict:** keep
**note:** 

---

### 141 · fineweb2-urd_Arab:<urn:uuid:8ae9f04a-5cda-41ee-a5fa-3704b80f9f26>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 1045 chars, 194 words, 11 lines
- **script:** ratio 0.611 (arabic 0.611, latin 0.389)
- **repetition:** dup_line 0.085, top-ngram 0.083, dup-ngram 0.193
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://urdu.arynews.tv/%D8%A7%D9%86%D8%B5%D8%A7%D8%B1-%D8%A8%D8%B1%D9%86%DB%8C-%D9%88%DB%8C%D9%84%D9%81%DB%8C%D8%A6%D8%B1-%D9%B9%D8%B1%D8%B3%D9%B9-%DA%A9%D9%88-%D8%A8%DA%BE%D8%A7%D8%B1%D8%AA%DB%8C-%D9%84%DA%91%DA%A9%DB%8C/

```text
انصار برنی ویلفیئر ٹرسٹ کو بھارتی لڑکی کے ورثاء کی تلاش
کراچی: پاکستان میں موجود بھارتی لڑکی اپنے خاندان سے ملنے کیلئے بے تاب ہے۔
تفصیلات کے مطابق انصار برنی ویلفیر ٹرسٹ انٹرنیشل کو پاکستان میں موجود ایک بھارتی لڑکی گیتا عرف گڈی کے خاندان کی تلاش ہے۔
مذکورہ لڑکی سننے اور بولنے کی صلاحیت سے بھی محروم ہے۔ گیتا عرف گڈی گزشتہ پندرہ سال سے پاکستان میں موجود ہے اور بھارت میں اپنے گھر والوں کے پاس جانے کی منتظر ہے۔
گیتا کے خاندان کی تلاش میں انصار برنی ویلفیر ٹرسٹ کے سربراہ انصار برنی بھرپور کوشش کررہے ہیں۔
انصار برنی کا کہنا ہے کہ مذکورہ لڑکی کو چھ یا سات سا ل کی عمر میں واہگہ بارڈر پر ریلوے پولیس نے اپنی تحویل میں لیا تھا۔
Ansar Burney Trust in search of family of a missing Indian girl Geeta alias Guddy in Pakistan since last 15 years pic.twitter.com/qGkIxdsbWa
— Ansar Burney (@AnsarBurney) August 1, 2015
— Ansar Burney (@AnsarBurney) August 2, 2015
Ansar Burney Trust International is in search of family of a missing Indian deaf and dumb girl in Pak since 15 years pic.twitter.com/DwBM9ycGl3
— Ansar Burney (@AnsarBurney) August 2, 2015
```

**verdict:** keep
**note:** 

---

### 142 · urdu-wikipedia:919370

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 1254 chars, 272 words, 12 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.052, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=5
- **url:** https://ur.wikipedia.org/wiki/%D8%A8%D8%AF%D9%86%20%DA%A9%DB%8C%20%D8%B3%D9%88%D8%B1%D8%A7%D8%AE%20%DA%A9%D8%A7%D8%B1%DB%8C

```text
بدن کی سوراخ کاری، جسم کی سوراخ کاری، چھیدنا یا چھید کرنا ایک طرح سے جسامت میں تبدیلی ہے، جس کے لیے جسم کے کسی حصے میں سوراخ کیا جاتا ہے، یا کبھی کوئی حصے کو کاٹا جاتا ہے۔ عام طور سے یہ کام عورتوں کے لیے کیا جاتا ہے تاکہ وہ زیورات پہن سکیں۔ ان میں سب سے زیادہ یہ کام کان یا ناک میں سوراخ کرنے کے لیے ہوتا ہے۔ خواتین کان کی بالیاں اور ناک میں نتھ پہںتی ہیں۔ بھارت میں دنیا کے کئی ممالک کی طرح ناک اور کان کی سوراخ کاری زیادہ تر عورتوں کے لیے کی جاتی ہے، تاہم کچھ بھارت کے مرد اور اسی طرح کچھ دیگر ممالک کے مرد بھی کان اور ناک میں سوراخ کرواتے ہیں۔ اس کے علاوہ دنیا میں جدید فیشن کی وجہ سے لوگ اور بھی اعضا کی سوراخ کاری کرواتے ہیں، جیسے کہ مرد اور عورتیں پستانوں کی سوراخ کاری کرواتے ہیں اور نامختون مرد اپنے ذَکَر کے حشفے کی سوراخ کرواتے ہیں اور وہاں ایک طرح بالی لگاتے ہیں اور عورتیں بھی اپنے عضو تناسل میں اسی طرح کی تبدیلیاں لاتی ہیں۔

بدن کی سوراخ کاری کی شہرت جدید دنیا میں عالمی ہو چکی ہے۔ تاہم اس کی تاریخ 5000 سال سے بھی زیادہ پرانی ہے۔ قدیم زمانے میں عجیب و غریب سوراخ کاری، جیسے کہ زبان اور ہونٹ کی سوراخ کاری کے بھی ثبوت ملتے ہیں۔

مزید دیکھیے
باڈی پینٹنگ
والدین کی رضا مندی

حوالہ جات

1990ء کی دہائی کا فیشن
2000ء کی دہائی کا فیشن
2010ء کی دہائی کا فیشن
جسم کی فنکاری
جسم میں تبدیلی
خودکار پیمانے کے ساتھ متعدد تصاویر استعمال کرنے والے صفحات
```

**verdict:** keep
**note:** 

---

### 143 · fineweb2-urd_Arab:<urn:uuid:b084d1e8-c6cc-44d0-b9dd-5e4d887da267>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 1667 chars, 319 words, 11 lines *(excerpt shows first 1500)*
- **script:** ratio 0.689 (arabic 0.689, latin 0.252)
- **repetition:** dup_line 0.062, top-ngram 0.028, dup-ngram 0.221
- **url** 0.014 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://urdu.arynews.tv/fawad-chaudhry-appeal-to-all-punjabis-in-indian-army-to-refuse-to-deny-duty-in-kashmir/

```text
فواد چوہدری کی بھارتی فوج میں پنجابیوں سے کشمیریوں پر مظالم کا حصہ نہ بننے کی اپیل
اسلام آباد : وزیر سائنس اینڈ ٹیکنالوجی فواد چوہدری نے بھارتی فوج کے پنجابی سپاہیوں سے کشمیریوں پر مظالم کا حصہ نہ بننے کی اپیل کرتے ہوئے کہا مقبوضہ کشمیرمیں ڈیوٹی سے انکار کردیں۔
تفصیلات کے مطابق وزیر سائنس اینڈ ٹیکنالوجی فوادچوہدری نے سماجی رابطے کی ویب سائٹ ٹوئٹر پر بھارتی فوج کے پنجابی سپاہیوں کے نام گرمکھی میں پیغام دیتے ہوئے بھارتی فوج میں پنجابیوں سے اپیل کی کہ ناانصافی اور ظلم کا حصہ بننے اور مقبوضہ کشمیرمیں ڈیوٹی سے انکار کردیں۔
ਮੈਂ ਇੰਡੀਅਨ ਆਰਮੀ ਵਿਚ ਸਾਰੇ ਪੰਜਾਬੀ ਜਵਾਨਾਂ ਨੂੰ ਬੇਨਤੀ ਕਰਦਾ ਹਾਂ ਕਿ ਇੰਡੀਅਨ ਸਰਕਾਰ ਦੇ ਮਜ਼ਲੂਮ ਕਸ਼ਮੀਰੀਆਂ ਤੇ ਹੋ ਰਹੇ ਜ਼ੁਲਮ ਦੇ ਖ਼ਿਲਾਫ਼ ਆਪਣੀ ਆਰਮੀ ਡਿਊਟੀ ਤੋਂ ਇਨਕਾਰ ਕਰ ਦਿਓ !!
I appeal to all Punjabis in Indian army to refuse to be part of injustice/zulm and deny duty in Kashmir
— Ch Fawad Hussain (@fawadchaudhry) August 13, 2019
فوادچوہدری کا کہنا تھا کہ ظلم کو مسترد کرنے کا کہنا مداخلت ہے؟ انصاف پسند بھارتی مودی سرکار کے فاشزم کو مسترد کردیں، امن بغیر مزاحمت کے ممکن نہیں ہے۔
Asking to refuse cruelty is interference? I call upon all Just Indians to refuse Narendra Modi fascism and refuse to abide by rules of his Govt…. peace is not possible without resistance https://t.co/Y6sEA3x7Q9
— Ch Fawad Hussain (@fawadchaudhry) August 13, 2019
یاد رہے گذشتہ روز بھارتی وزیراعظم نریندرمودی کی جانب سے عید کی مبارکباد پر وفاقی وزیر فواد چوہدری نے جواب دیتے ہوئے کہا تھا مودی جی آپ کا اور آپ کی حکومت کا ہر اقدام آپ کے عید کےا من کے پیغام کے مخالف ہے۔۔ آپ نے لاکھوں لوگوں کی خوشیاں اورامن چھین لیا
```

**verdict:** keep
**note:** 

---

### 144 · fineweb2-urd_Arab:<urn:uuid:605bcf1a-71d4-43f1-ad55-e9c0f3397106>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 2018 chars, 429 words, 3 lines *(excerpt shows first 1500)*
- **script:** ratio 0.996 (arabic 0.996, latin 0.004)
- **repetition:** dup_line 0.000, top-ngram 0.030, dup-ngram 0.167
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://www.khouj.com/featured/332922/

```text
فنانشل ایکشن ٹاسک فورس کا اجلاس، پاکستان کو گرے لسٹ سے نکالا گیا یا نہیں؟ فٹیف کے صدر ڈاکٹر مارکوس پلیئر نے بڑے راز سے پردہ اٹھا دیا، سب حیران رہ گئے۔
تفصیلات کے مطابق سربراہ فٹیف نے کہا کہ آج پاکستان کو گرے لسٹ سے نہیں نکالا گیا، اگر پاکستان on-site وزٹ کا مرحلہ کامیابی سے عبور کرلیتا ہے تو اسے گرے لسٹ سے نکال دیا جائے گا۔ انہوں نے کہا کہ فیٹف ٹیم کے دورے کے دوران پاکستان کو اس بات کو یقینی بنانا ہوگا کہ وہ ثابت کرے کہ اس نے منی لانڈرنگ اور دہشت گرد گروپس کی فنڈنگ سے مثر طریقے سے نمٹ لیا ہے۔ فیٹف کی جانب سے جاری اعلامیے میں کہا گیا ہے کہ پاکستان نے 34 آئٹمز پر مبنی اپنے دو ایکشن پلان مکمل کر لیے ہیں، پاکستان کا دورہ کر کے شرائط کی تکمیل کی تصدیق کی جائے گی۔ فیٹف کا کہنا ہے کہ کورونا صورت حال کا جائزہ لیتے ہوئے جلد از جلد پاکستان کا دورہ کیا جائے گا، پاکستان نے منی لانڈرنگ، دہشت گردی کی فنانسنگ روکنے کیلئے اصلاحات مکمل کیں۔ فیٹف کا کہنا ہے کہ پاکستان نے منی لانڈرنگ، دہشت گردی کی فنڈنگ روکنے کیلئے اصلاحات مکمل کیں۔ اقوام متحدہ کی فہرست میں شامل دہشت گرد گروپوں، رہنماوں کی پراسیکیوشن پرپاکستان نے بہت پیش رفت کی ہے، منی لانڈرنگ کی تحقیقات اور پراسیکیوشن میں بھی پاکستان میں مثبت رجحان رہا ہے۔
وزیر مملکت برائے خارجہ امور حنا ربانی کھر نے پاکستانی قوم کو مبارکباد دیتے ہوئے کہا ہے کہ فنانشل ایکشن ٹاسک فورس (فیٹف) نے پاکستان کے دونوں ایکشن پلان کو مکمل قرار دے دیا ہے۔ حنا ربانی کھر کا کہنا ہے کہ پاکستان اس رفتار کو جاری رکھنے، معیشت کو فروغ دینے کے عزم کا اعادہ کرتا ہے۔ انہوں نے کہا کہ آج تمام پاکستانیوں کیلئے خوشی کا دن ہے، قوم کو مبارک باد پیش کرتے ہیں، فیٹف نے پاکستان کو تمام نکات
```

**verdict:** keep
**note:** 

---

### 145 · urdu-wikipedia:920393

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 13420 chars, 2832 words, 159 lines *(excerpt shows first 1500)*
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.005, top-ngram 0.013, dup-ngram 0.019
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** alef=1, digits=79, heh=33, teh_marbuta=1, whitespace=185, yeh=67
- **url:** https://ur.wikipedia.org/wiki/%D9%82%DB%8C%D8%A7%D9%85%20%D8%A7%D9%84%D8%AF%DB%8C%D9%86%20%D8%AE%D8%A7%D8%AF%D9%85

```text
قیام الدین خادم (پ:1274 ش ھ صوبہ ننگرہار - م :1358 ش ھ) ایک افغان پشتو زبان صحافی، مصنف ، شاعر ، کابل یونیورسٹی ادب کا لیکچرر ، اور ایک مصنف. وہ فلسفیانہ نظریات کا ماہر عالم تھا۔

پس منظر

قیام الدین خادم سال 1286 ش ھ میں صوبہ ننگرہار کے ضلع کاما میں ایک روحانی گھرانے میں پیدا ہوا۔ مرحوم خادم کے والد مرحوم ملا حسام الدین اخوند ، علاقے کے ایک مشہور اور عالم دین تھے۔ خادم صاحب ڈھائی سال لاہور میں مقیم رہے ، جہاں انھوں نے شاعری ، تحریر اور ادب سے پراسرار دلچسپی پیدا کی ۔وہ لاہور ہی رہے اور ان سے شادی کی۔ قائم الدین خادم اپنی نظم اور ابتدا کے بارے میں ایک نظم میں کہتے ہیں:

پشتو ادب میں ان کا ایک خاص مقام ہے اور اسی وجہ سے انہیں پشتو زبان و ادب کے چمکتے ہوئے ستاروں میں سے ایک سمجھا جاتا ہے۔ انہوں نے پشتو زبان و ادب پر دلچسپ نظمیں اور نثر لکھے ہیں۔ وہ اپنی ادبی کاوشوں کے علاوہ سیاست میں بھی شامل تھے اور بیدار یوتھ پارٹی کے بانی ممبروں میں شامل نہیں تھے۔

استاد قیام الدین خادم افغانستان کی ایک مشہور سیاسی شخصیات میں سے ہیں جنہوں نے وقت گزرنے کے ساتھ ساتھ ہمیشہ بڑی بڑی سیاسی اقدام کیئے۔ بیدار ہونے والی یوتھ پارٹی کے بانیوں میں سے ایک ہونے کے علاوہ ، اسی سال انہوں نے افغان سوشل ڈیموکریٹک پارٹی کی بنیاد رکھی ، جسے "افغان قوم" کے نام سے جانا جاتا ہے۔ پارٹی کی پہلی کانگریس اسی سال کابل کے میونڈ روڈ کے دوسرے حصے پر خادم صاحب کے گھر پر منعقد ہوئی تھی۔ پارٹی کو دیگر نو قومی شخصیات ، پارٹی کے پبلشنگ آرگنائزیشن ، پارٹی کے دیگر کیڈر ممبران اور نامزد کیا گیا تھا۔ سنٹرل کمیٹی تشکیل دی گئی۔ اس پارٹی کا مقصد اور چارٹر بھی استاد قیام الدین خادم نے لکھے تھے ، اور پہلی بانی کانگریس میں اس کے ہر مضمو
```

**verdict:** keep
**note:** 

---

### 146 · fineweb2-urd_Arab:<urn:uuid:9b5fcd47-43e9-47e9-9400-80936fb0bde2>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 818 chars, 156 words, 17 lines
- **script:** ratio 0.517 (arabic 0.517, latin 0.483)
- **repetition:** dup_line 0.100, top-ngram 0.051, dup-ngram 0.098
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://www.rekhta.org/mazahiya/haath-men-laathii-pakad-kar-ishq-farmaaenge-kyaa-syed-fahimuddin-mazahiya?lang=ur

```text
ہاتھ میں لاٹھی پکڑ کر عشق فرمائیں گے کیا
ہاتھ میں لاٹھی پکڑ کر عشق فرمائیں گے کیا
بابا جی کچھ اور دن بھی آپ جی پائیں گے کیا
ڈاکٹر کی فیس کا سن کر مریض محترم
آپریشن سے ہی پہلے کوچ فرمائیں گے کیا
ٹیوشنیں گھر میں پڑھاتے ہیں یہی کافی نہیں
مدرسے میں ماسٹر جی خاک پڑھائیں گے کیا
قیمتیں دالوں کی بھی بڑھ جائیں گی سوچا نہ تھا
لوگ دھکوں کے سوا اب اور کچھ کھائیں گے کیا
رسم و رہ گو افسروں سے اس قدر اچھی نہیں
ہم اگر مکھن لگائیں وہ نہ لگوائیں گے کیا
Additional information available
Click on the INTERESTING button to view additional information associated with this sher.
About this sher
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Morbi volutpat porttitor tortor, varius dignissim.
rare Unpublished content
This ghazal contains ashaar not published in the public domain. These are marked by a red line on the left.
```

**verdict:** keep
**note:** Urdu ghazal

---

### 147 · urdu-wikipedia:121238

- **filter:** REJECT — too_short
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 185 chars, 37 words, 5 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.130, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=3
- **url:** https://ur.wikipedia.org/wiki/%D8%AC%D8%A6%D9%88%D9%86%D8%AC%D9%88

```text
جئونجو ایک شہر ہے جو جنوبی کوریا میں واقع ہے۔ اس کی مجموعی آبادی 654,040 افراد پر مشتمل ہے، یہ شمالی جئولا صوبہ میں واقع ہے۔

نگار خانہ

متعلقہ روابط
فہرست جنوبی کوریا کے شہر

حوالہ جات
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 148 · fineweb2-urd_Arab:<urn:uuid:47f5ca19-f510-4dac-9b7a-c96d2beaca2d>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 862 chars, 159 words, 8 lines
- **script:** ratio 0.680 (arabic 0.680, latin 0.320)
- **repetition:** dup_line 0.000, top-ngram 0.065, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://urdu.arynews.tv/indian-plane-crashes/

```text
بھارتی طیارہ گرکر تباہ
نئی دہلی: بھارتی ائیرفورس کا مگ21طیارہ گرکر تباہ ہوگیا جس کے نتیجے میں اسکواڈرن لیڈر ہلاک ہوا ہے۔
غیرملکی خبررساں ادارے کی رپورٹ کے مطابق جنگی جہاز کا یہ حادثہ بھارتی ریاست پنجاب میں پیش آیا، بھارتی ائیرفورس کا مگ21طیارہ گرکرتباہ ہونے سے اسکواڈرن لیڈر ہلاک ہوگیا۔
بھارتی ایئرفورس کا کہنا ہے کہ طیارہ رات کو معمول کی ٹریننگ پر تھا۔
رپورٹ میں کہا گیا ہے کہ حادثے کے بعد متعلقہ اداروں نے واقعے کی تحقیقات کا آغاز کردیا۔ ابتدائی طور پر امکان ظاہر کیا جارہا ہے کہ یہ حادثہ تکنیکی خرابی کے باعث ممکن ہے۔
واقعے سے متعلق مکمل تحقیقات کے بعد ہی اصل حقائق سامنے آئیں گے۔
There was an aircraft accident last night involving a Bison aircraft of IAF in the western sector. The pilot, Sqn Ldr Abhinav Choudhary, sustained fatal injuries. IAF condoles the tragic loss and stands firmly with the bereaved family.
— Indian Air Force (@IAF_MCC) May 21, 2021
```

**verdict:** keep
**note:** 

---

### 149 · urdu-wikipedia:122110

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 411 chars, 81 words, 10 lines
- **script:** ratio 0.856 (arabic 0.856, latin 0.144)
- **repetition:** dup_line 0.000, top-ngram 0.078, dup-ngram 0.117
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=3
- **url:** https://ur.wikipedia.org/wiki/%D8%A2%D9%86%DB%8C%D8%A7%D9%86%DA%AF

```text
آنیانگ (لاطینی: Anyang) ایک پریفیکچر سطح شہر ہے جو چین میں واقع ہے۔ اس کی مجموعی آبادی 5,172,834 افراد پر مشتمل ہے، یہ ہینان میں واقع ہے۔

متعلقہ روابط
فہرست چین کے شہر

حوالہ جات

چھوٹے پیغام خانوں کا استعمال کرنے والے مضامین
کامنز زمرہ جس کا ربط ویکی ڈیٹا پر ہے
مضامین جن میں آسان چینی زبان کا متن شامل ہے
مضامین جن میں روایتی چینی زبان کا متن شامل ہے
ہینان کے شہر
Short description is different from Wikidata
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 150 · urdu-wikipedia:363350

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 201 chars, 38 words, 7 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=4
- **url:** https://ur.wikipedia.org/wiki/%D9%81%D8%A7%DA%AF%D8%A7%DA%AF%D9%86%D8%A7

```text
فاگاگنا اطالیہ کا ایک کمونے جو صوبہ اودینے میں واقع ہے۔

تفصیلات
فاگاگنا کا رقبہ 37.0 مربع کیلومیٹر ہے اور اس کی مجموعی آبادی 6,279 افراد پر مشتمل ہے۔

مزید دیکھیے
اطالیہ
فہرست اطالیہ کے شہر

حوالہ جات
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 151 · fineweb2-urd_Arab:<urn:uuid:6fccee0d-a792-4582-a040-340151f2e003>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 405 chars, 70 words, 6 lines
- **script:** ratio 0.687 (arabic 0.687, latin 0.313)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** http://www.express.com.pk/epaper/Index.aspx?Issue=NP_KHI&Page=FRONT_PAGE

```text
پنجاب پولیس کی پھرتیاں، اصل ملزم کے بجائے 13 ماہ کا بچہ عدالت میں پیش
روس نے ترکی کے ساتھ دفاعی تعلقات منقطع کر دیئے
منصوبےغیرملکی پیسوں سے بنتے اورچلانے کیلئے بھی بیرونی رقم کا انتظارکیاجاتاہ....
علم کے دیار کو ایک لیڈران چاہیئے
آزاد کشمیر سمیت ملک کے مختلف حصوں میں زلزلے کے جھٹکے
Copyright © Century Publications. This material may not be published, broadcast, rewritten, redistributed or derived from.
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 152 · urdu-wikipedia:675187

- **filter:** REJECT — too_short
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 106 chars, 21 words, 6 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** teh_marbuta=1
- **url:** https://ur.wikipedia.org/wiki/%D8%A7%D9%84%D8%AD%D8%AC%D8%B1%20%D8%A2%DB%8C%D8%AA%2087

```text
سورہ الحجر مکی سورہ ہے لیکن آیت 87 مدینہ منورہ میں نازل ہوئی ہے۔

ترجمہ

مقام نزول

تفسیر

حوالہ جات

آیات
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 153 · urdu-wikipedia:919995

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 321 chars, 61 words, 5 lines
- **script:** ratio 0.980 (arabic 0.980, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.103, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=1, zwnj=1
- **url:** https://ur.wikipedia.org/wiki/%D8%A7%D8%A8%D8%AA%D8%AF%D8%A7%D8%A6%DB%8C%20%D8%AC%D8%AF%DB%8C%D8%AF%20%D8%AC%D8%A7%D9%BE%D8%A7%D9%86%DB%8C

```text
ابتدائی جدید جاپانی (جاپانی:近世日本語 تلفظ:کِینسائی نِہوَنگَو) وسطی جاپانی کے بعد اور جدید جاپانی سے پہلے جاپانی زبان کا مرحلے تھا. اس منتقلی کی مدت میں جاپانی زبان نے بہت سے وسطی خصوصیات کو ترک کر دیا اور اس کے جدید شکل کے قریب بن گئی.

حوالہ جات
جاپانی زبان
قرون وسطی زبانیں
غیر حوالہ معدومیت کی تاریخ والے زبانوں کے مضامین
```

**verdict:** keep
**note:** 

---

### 154 · urdu-wikipedia:264046

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 2180 chars, 273 words, 19 lines *(excerpt shows first 1500)*
- **script:** ratio 0.479 (arabic 0.479, latin 0.521)
- **repetition:** dup_line 0.000, top-ngram 0.019, dup-ngram 0.030
- **url** 0.263 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** heh=1, whitespace=13
- **url:** https://ur.wikipedia.org/wiki/%D9%86%D9%88%D8%A6%DB%8C%D8%B3%D8%AA%D8%B1%D8%A7%20%D8%B3%DB%8C%D9%86%DB%8C%D9%88%D8%B1%D8%A7%20%D8%AF%DB%8C%D9%84%20%D9%85%D9%86%D8%B2%D8%A7%D9%86%D9%88%20%DA%A9%D8%A7%20%DA%AF%D8%B1%D8%AC%D8%A7%DA%AF%DA%BE%D8%B1

```text
نوئیسترا سینیورا دیل منزانو کا گرجاگھر (اسپینی زبان میں: Iglesia de Nuestra Seora Del Manzano یا Iglesia de Santa Mara del Manzano) ایک گرجاگھر ہے۔ یہ گرجاگھر برگوس صوبے میں کاستروجیریز (Castrojeriz) کے شہر میں موجود ایک کیتھولک گرجاگھر ہے۔ یہاں کی عمارت کی تعمیر کاستیلے کی رانی بیرینگاریا (Berengaria) کی وصیت سے ہوا ہے جو کہ فرڈنینڈ سوّم کی ماں اور الفانسو آٹھویں کی اہلیہ تھی۔ یہ گرجاگھر ایک پہاڑی کی تلچھٹ میں وقوع پزیر ہے جہاں ایک محل بھی موجود ہے۔

عجائب گھر

آج کل گرجاگھر مسیحی مذہب سے متعلقہ اشیاء کے ساتھ ایک عجائب خانہ بھی دکھاتا ہے۔ نمائش پر کئی لکڑی کی چیزیں، چودہویں صدی میں بنی مورتیاں ہیں۔ کئی تصاویر، کتابیں اور دیگر اشیاء کو بھی رکھا گیا ہے۔ عجائب گھر میں بہ طور خآص کیمنو دے سینٹیاگو جا رہے زائرین کی سہولت کے لیے سامان موجود ہے جو سامنے کے راستے والے دروازے سے ہوکر گزرتے ہیں۔

عجائب گھر کی ایک اہم خصوصیت شان دار جرمن ساختہ کانچ ہے جو گرجاگھر کے شمال کی جانب لگی ہے۔ اُن میں سے کچھ تو پندرھویں صدی سے ہے اور انہیں انیگو لوپیز ڈی مینڈوزا (Iigo Lpez de Mendoza) نے خاص طور سے یہاں دے رکھا تھا۔

مستقل عجائب گھر کے علاوہ یہاں کئی سنگیت کی محافل اور مختصر مدتی نمائشیں لگی رہتی ہیں۔

حوالہ جات

خارجی روابط

La iglesia de Ntra. Sra. del Manzano de Castrojeriz
Iglesia de Ntra. Sra. del Manzano
Images of Nuestra Señora del Manzano church and museum
http://www.shutterstock.com/pic-64471684/stock-photo-collegiate-church-of-nuestra-senora-del-manzano-castrojeriz.html
http://www.123rf.com/photo_9491958_collegiate-church-of-nuestra-senora-del-manzano-castrojeriz.html
http://www.cuat
```

**verdict:** keep
**note:** 

---

### 155 · urdu-wikipedia:429769

- **filter:** REJECT — too_short
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 133 chars, 25 words, 10 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=6
- **url:** https://ur.wikipedia.org/wiki/770%DA%BE

```text
واقعات

ولادتیں

وفیات

مزید دیکھیے
ہجری شمسی

حوالہ جات

بیرونی روابط
ہجری تاریخ کو شمسی سال سے بدلیں
ہجری سال کی اسلام میں اہمیت

7
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 156 · fineweb2-urd_Arab:<urn:uuid:b14592d3-439d-40b3-96db-0acd209cb6ea>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 4408 chars, 964 words, 9 lines *(excerpt shows first 1500)*
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.055, dup-ngram 0.019
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://salamurdu.com/ikhtilaf-rai.html

```text
پاکستان وہ ملک ہے جہاں پر ہر کسی کو آزادی کے ساتھ بولنے اور لکھنے کا پورا حق حاصل ہے مگر بہت افسوس ہے کہ سچ بولنے کے بعد عوام کا جو رویہ شاہد خان آفریدی کے خلاف دیکھا گیا، اس کے بعد دوسرے سٹار کا سچ بولنا اور لکھنا بھی مشکل ہو جائے گا، شاہد آفریدی وہ شخص ہیں جنہوں نے اپنی ساری زندگی پاکستان کے لیے وقف کر دی، کرکٹ کے بعد اب وہ اپنی فاؤنڈیشن سے پاکستان کے لوگوں کی مدد کر رہے ہیں۔۔
آئیے ایک مختصر سی نظر شاہد آفریدی کے کیرئیر پر ڈالتے ہیں، صاحبزادہ محمد شاہد خان آفریدی 1 مارچ 1975 کو خیبر ایجنسی میں پیدا ہوئے، کسی کو نہیں پتا تھا کہ پیدا ہونے والا یہ بچہ کل بڑا ہو کر پاکستان کا نام پوری دنیا میں روشن کرے گا۔ 4 اکتوبر 1996 کے دن کا سورج اپنے ساتھ ایک ایسے کرکٹر کی قسمت لے کر طلوع ہوا تھا، جسے دنیا آج بھی شاہد خان آفریدی کے نام سے جانتی ہے، 16 سال کی چھوٹی میں بطور بولر ٹیم میں شامل ہونے والے اس لڑکے نے حیرت انگیز طور پر بطور بیسٹمین پہلی اننگز میں شاندار ریکارڈ قائم کیا۔
تاریخ گواہ ہے کہ ایسے کرکٹر جنہوں نے ایک اوور میں 6 چھکے بھی لگائے مگر ان کو اتنی پذیرائی نہیں ملی جتنی آفریدی کو ملی، لوگ صرف شاہد آفریدی کی بیٹنگ دیکھنے گراؤنڈ میں آتے تھے اور جب یہ آؤٹ ہو جاتا تھا تو گراونڈ خالی ہو جاتا تھا۔ شاہد آفریدی نے بیٹنگ، بولنگ، فیلڈنگ اور کپتانی کے شعبے میں بھی اپنا لوہا منوایا۔ آسٹریلیا کے مشہور کرکٹرز اسٹیووا نے ایک بار کہا تھا کہ مجھے دس لکڑی کے ٹکڑے اور ایک شاہد آفریدی دے دو پھر مجھ سے کوئی میچ نہیں جیت سکتا، 2005 میں انڈیا کے خلاف اپنی دوسری تیز ترین اننگز کے دوران جب روی شاستری کمنٹری کر رہے تھے تو انکی زبان سے نکلنے والے دو جملے ( بوم بوم ) شاہد آفریدی کے لیے ایک اور پہچان بن گئ
```

**verdict:** keep
**note:** 

---

### 157 · urdu-wikipedia:201305

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 304 chars, 49 words, 8 lines
- **script:** ratio 0.679 (arabic 0.679, latin 0.321)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=3
- **url:** https://ur.wikipedia.org/wiki/%D8%B3%DB%8C%D9%86%D9%B9-%D8%A8%D8%B1%D8%A7%D9%86%DA%86%D8%B1

```text
سینٹ-برانچر ( فرانسیسی: Saint-Brancher) فرانس کا ایک فرانسیسی کمیون جو Canton of Quarré-les-Tombes میں واقع ہے۔

تفصیلات
سینٹ-برانچر کا رقبہ 22.02 مربع کیلومیٹر ہے اور اس کی مجموعی آبادی 334 افراد پر مشتمل ہے۔

مزید دیکھیے
فرانس
فہرست فرانس کے شہر

حوالہ جات

Short description is different from Wikidata
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 158 · urdu-wikipedia:363217

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 267 chars, 46 words, 7 lines
- **script:** ratio 0.916 (arabic 0.916, latin 0.084)
- **repetition:** dup_line 0.000, top-ngram 0.172, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=5
- **url:** https://ur.wikipedia.org/wiki/%D8%A7%DB%8C%D9%81%DB%94%20%D8%AC%DB%92%DB%94%20%D9%B9%D9%88%D8%B1%D8%A7%D8%B3%20%DA%A9%D8%A7%D8%B2%D9%88%DB%92

```text
ایف۔ جے۔ ٹوراس کازوے ریاستہائے متحدہ امریکا کا ایک geographical object جو گلین کاؤنٹی، جارجیا میں واقع ہے۔

مزید دیکھیے
ریاستہائے متحدہ امریکا
فہرست ریاستہائے متحدہ امریکہ کے شہر

حوالہ جات

گلین کاؤنٹی، جارجیا میں نقل و حمل
ویکی ڈیٹا سے مطابقت رکھنے والی مختصر تفصیل
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 159 · urdu-wikipedia:362058

- **filter:** REJECT — too_short
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 188 chars, 33 words, 8 lines
- **script:** ratio 0.858 (arabic 0.858, latin 0.142)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=3
- **url:** https://ur.wikipedia.org/wiki/%D8%B0%D8%A8%D9%84%D8%AA%DB%8C%D9%B9%D8%B2

```text
ذبلتیٹز ( جرمنی: Zabeltitz) جرمنی کا ایک گاؤں جو زاکسن میں واقع ہے۔

تفصیلات
ذبلتیٹز کی مجموعی آبادی 2,899 افراد پر مشتمل ہے۔

مزید دیکھیے
جرمنی
فہرست جرمنی کے شہر

حوالہ جات

en:Zabeltitz
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 160 · fineweb2-urd_Arab:<urn:uuid:c136c1db-109b-41c9-849c-4c0895f46bf8>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 1148 chars, 222 words, 6 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.063, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://urdu.arynews.tv/foreign-office-pakistan-us-anti-terrorism-dialogue/

```text
اسلام آباد : امریکہ اور پاکستان کے اعلیٰ سطح وفود کے درمیان دوروزہ انسداد دہشت گردی مذاکرات چھ اور سات مارچ کو اسلام آباد میں وزارت خارجہ میں ہوئے ۔
دو روزہ اجلاس کی صدارت امریکی محکمہ خارجہ کے قائم مقام رابطہ کار برائے انسداد دہشت گردی کرسٹوفر لینڈ برگ اور پاکستان کی وزارتِ خارجہ کے ایڈیشنل سیکرٹری برائے اقوام متحدہ اور اقتصادی سفارت کاری سید حیدر شاہ نے کی۔
ترجمان دفتر خارجہ ممتاز زہرہ بلوچ کے اعلامیہ کے مطابق 2روزہ بات چیت میں کثیرالجہتی فورمز پر انسداد دہشت گردی تعاون کا جائزہ لیا گیا، مذکرات میں علاقائی انسداد دہشت گردی کے منظر نامے کا جائزہ زیر بحث رہا۔
مذکرات میں سائبر سیکورٹی اور انتہا پسندی کا مقابلہ کرنے سمیت متعدد موضوعات کا احاطہ کیا گیا، پاکستان میں امریکی امداد کے منصوبوں پر بھی تبادلہ خیال کیا گیا، انسداد منی لانڈرنگ، انصاف کے شعبے میں صلاحیتوں کے پروان پر توجہ دی گئی۔
ترجمان دفترخارجہ کے مطابق فریقین نے دہشت گردی کیخلاف صلاحیت بڑھانے میں ان منصوبوں کی اہمیت کو اجاگر کیا اور دہشت گردی کی مالی معاونت کیخلاف اپنے تجربات کا تبادلہ کیا،
فریقین نے دہشت گردی کی تمام اقسام اور مشترکہ خطرے سے نمٹنے کےعزم کا اعادہ کیا، وفود کی جانب سے مزید بات چیت جاری رکھنے اور دہشت گردی کیخلاف بہتر افہام و تفہیم پیدا کرنے پر اتفاق کیا گیا۔
```

**verdict:** keep
**note:** 

---

### 161 · urdu-wikipedia:903623

- **filter:** REJECT — too_short
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 192 chars, 38 words, 8 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.177, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=5
- **url:** https://ur.wikipedia.org/wiki/%D8%A8%D8%A7%D8%B4%20%D8%AF%D8%B1%D8%A7%D9%82%20%D9%85%D8%B3%D8%AC%D8%AF

```text
باش دراق مسجد ترکی کی ایک مسجد جو ازمیر میں واقع ہے۔

مزید دیکھیے
ترکی
ترکی میں اسلام

حوالہ جات

1652ء میں مکمل ہونے والی مذہبی عمارات
گنبد والی مذہبی عمارات و ساخات
ترک مسجد کے نامکمل مضامین
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 162 · fineweb2-urd_Arab:<urn:uuid:dbb98260-a7ee-4d1a-ba43-21d60aba1c33>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 8043 chars, 1751 words, 20 lines *(excerpt shows first 1500)*
- **script:** ratio 0.990 (arabic 0.990, latin 0.010)
- **repetition:** dup_line 0.003, top-ngram 0.013, dup-ngram 0.004
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** heh=23
- **url:** https://meliorations.space/category-11/page-854475.html

```text
بہت CFD مارکیٹ زیادہ تحریری بلاگوں کے ساتھ اپنے ڈیش بورڈ کو بے ترتیبی نہیں کرنا چاہتے؟ بس اس پر عمل کریں ، پھر۔ تحریری کیفے مشورے لکھنے ، وسائل لکھنے ، تحقیقاتی مواد سے متعلق لنکس وغیرہ کے ل your آپ کا ایک واحد وسیلہ ہے۔ بلاگر سوالوں کے جوابات دینے کے لئے کافی دوستانہ ہے ، اور اگر آپ کوئی سوال پوچھتے ہیں جس کا جواب پہلے ہی دیا گیا ہو تو آپ کو موجودہ لنکس کی طرف رہنمائی کرنے کے لئے کافی مریض ہے۔ گبرو ۔6 کے اہم فوائد: عمدہ استثنیٰ اور نظربندی کی شرائط کو غیر ضروری سمجھنا۔ گبرو خلیوں میں اور آزادانہ رینج پر رہ سکتا ہے ، جس میں صرف معمول کے ٹیکے لگانے کی ضرورت ہوتی ہے۔ ان کی پرسکون نوعیت کی وجہ سے وہ نجی صحن کے دوسرے باشندوں کا ساتھ حاصل کرسکیں۔
جب سرکاری معاہدوں کے لئے منافع کی رقم کا حساب لگاتے ہو تو سرکاری ایجنسیاں کتنی فیس ادا کرنا ہے اس کا تعین کرنے سے پہلے معاہدے کی تخمینہ قیمت سے سہولیات کے لئے وابستہ سرمائے کی رقم کو ختم کردیتی ہیں۔ اسی طرح ، حکومت کے لئے خریدی گئی جائیداد پر بھی منافع کا الاؤنس لاگو نہیں ہوتا ہے اور ٹھیکیدار کو اس کی واپسی کی جاتی ہے۔ مجھے پاور اڈاپٹر کی اچھی حالت برقرار رکھنے اور اس کی عمر بڑھانے کے لئے کیا کرنا چاہئے؟ ہائبرڈ کو دیا جانے والا نام ان کی خصوصیات کی وجہ سے ہے:
- CFD مارکیٹ
اسٹاک مساوات میں کیسے کام کرتا ہے؟ آخر کار ، بانڈز کے مقابلے میں اسٹاکس میں طویل مدتی سرمایہ - اور متعلقہ ٹیکس کا بل پیدا کرنے کا زیادہ امکان ہے۔ تاہم ، طویل مدتی دارالحکومت کے منافع (ایک سال سے زیادہ عرصے میں رکھے ہوئے اثاثوں کی فروخت پر حاصل ہونے والے) پر فی الحال آمدنی سے زیادہ سازگار شرحوں پر محصول عائد کیا جاتا ہے (ایک زمرے میں بانڈز اور بانڈ فنڈز سے دلچسپی شامل ہے)
```

**verdict:** keep
**note:** 

---

### 163 · fineweb2-urd_Arab:<urn:uuid:2a55fd2b-77a8-4ddf-a295-39eecfd1ac73>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 1704 chars, 370 words, 18 lines *(excerpt shows first 1500)*
- **script:** ratio 0.993 (arabic 0.993, latin 0.007)
- **repetition:** dup_line 0.000, top-ngram 0.025, dup-ngram 0.055
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://ur.sjdsbrewers.com/hale-s-ales-celebrates-30-years

```text
ہیلز ایلز نے 30 سال منائے
فریمونٹ میں ہیلس ایلس بریوری اینڈ پب کے بانی مائیک ہیل کا کہنا ہے کہ 'تیس سال قبل تازہ ، سوادج دستکاری کے لئے ایک اکیلے تلاش کرنا آسان نہیں تھا۔' حقیقت میں یہ تقریبا ناممکن تھا۔ '
بہت کم کرافٹ بنانے والوں نے کافی تیزی سے یہ دیکھا ہے کہ کاروبار میں اب تک بڑھتی ہوئی صنعت میں کچھ بھی نہیں بڑھ رہا ہے جو اب ہے۔ مائک ہیل چند لوگوں میں سے ایک ہے۔
اس سال فریمنٹ میں ہیلز ایلز نے 30 سال چھوٹی بریوری ہونے کا جشن منایا۔ مائیک کے ذریعہ کولویلا ، واشنگٹن میں 1983 میں قائم کیا گیا تھا ، ہیلز ایلز نے 2013 میں اس صنعت کے ایک تسلیم شدہ سرخیل کی سربراہی کی۔ جو لوگ بہت سارے لوگوں کو معلوم نہیں ہوسکتے ہیں وہ یہ ہے کہ ہیل کی بریوری فی الحال شمال مغرب میں آزادانہ طور پر ملکیت میں چلنے والی شراب کی بریوری ہے۔
ہیل کا کہنا ہے کہ ، 'سوائے میرے کچھ عرصے سے ملازمین کے جن کا کاروبار میں حصہ ہے ، ہیل کی اب بھی مقامی سرمایہ کاروں کے چھوٹے گروہ کی ملکیت ہے جس نے یہ سوچ کر اپنے ڈالر تیار کیے کہ یہ ہماری اپنی بریوری کھولنا ایک تفریحی خیال ہوگا۔'
ہال سالگرہ کے موقع پر خصوصی پروگراموں کے سلسلے کے ساتھ نشان زد کریں گے جس میں…
- ریاست کے باروں اور ریستوراں میں ہیلوں کی بریوری پروموشن راتوں ،
- ایک بلو آؤٹ 'آپ کا شکریہ' ستمبر میں ہیلی پیلیڈیم میں سالگرہ کی پارٹی ، جو ایک گودام بریوری میں کارکردگی کا مرکز بنا،
- چھوٹے بیچ کی خصوصی بیئر کا سلسلہ سال بھر جاری ہوتا ہے ، جس میں ایک خصوصی 30 ویں سالگرہ امپیریل پیلے بھی شامل ہے
ہیل کا کہنا ہے کہ ، 'ہم سمجھتے ہیں کہ ہماری 30 ویں برسی منانا واقعی عام طور پر کرافٹ بیئر کا جشن ہے۔ 'یہ ہمیشہ آسان نہیں رہا تھا لیکن اس میں بہت لطف آتا ہے۔'
مزید معلومات 
```

**verdict:** keep
**note:** 

---

### 164 · urdu-wikipedia:428605

- **filter:** REJECT — too_short
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 133 chars, 25 words, 10 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=7
- **url:** https://ur.wikipedia.org/wiki/1335%DA%BE

```text
واقعات

ولادتیں

وفیات

مزید دیکھیے
ہجری شمسی

حوالہ جات

بیرونی روابط
ہجری تاریخ کو شمسی سال سے بدلیں
ہجری سال کی اسلام میں اہمیت

3
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 165 · urdu-wikipedia:1090364

- **filter:** REJECT — script_ratio, html_residue
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 789 chars, 117 words, 22 lines
- **script:** ratio 0.599 (arabic 0.599, latin 0.401)
- **repetition:** dup_line 0.000, top-ngram 0.071, dup-ngram 0.000
- **url** 0.000 · **html** 0.020 · **U+FFFD** 0.00000
- **stage 4:** whitespace=2
- **url:** https://ur.wikipedia.org/wiki/%DA%A9%DB%8C%D8%B3%D9%84%20%DB%81%D9%84%D8%8C%20%D9%86%DB%8C%D9%88%20%D8%B3%D8%A7%D8%A4%D8%AA%DA%BE%20%D9%88%DB%8C%D9%84%D8%B2

```text
{{Infobox Australian place
|type=suburb
|name=کیسل ہل، نیو ساؤتھ ویلز
|city=Greater Western Sydney
|state=nsw
|image=(1) Public School Castle Hill.jpg
|caption=Public school (1879)
|lga=ہارنزبی شائر
|lga2=دی ہلز شائر
|postcode=2154
|coordinates=|alternative_location_map=Australia Sydney
|local_map=yes
|zoom=12
|relief=1
|pop=39,594
|pop_year=|pop_footnotes=<ref name="ABS">

کیسل ہل سڈنی، نیو ساؤتھ ویلز، آسٹریلیا کا ایک چھوٹا شہر ہے، جو سڈنی سینٹرل بزنس ڈسٹرکٹ سے 34 کلومیٹر شمال مغرب میں واقع ہے اور پیراماٹا، نیو ساؤتھ ویلز سے 9.5 کلومیٹر شمال میں واقع ہے۔
یہ ہلز ڈسٹرکٹ، نیو ساؤتھ ویلز کے علاقے میں ہے، جو دی ہلز شائر اور ہارنزبی شائر کے مقامی حکومتی علاقوں کے درمیان میں تقسیم ہے۔

کیسل ہل، نیو ساؤتھ ویلز
سڈنی کے مضافات
1802ء میں آباد ہونے والے مقامات
آسٹریلیا میں 1802ء کی تاسیسات
```

**verdict:** drop
**note:** {{Infobox}} template dump

---

### 166 · fineweb2-urd_Arab:<urn:uuid:49562cc1-1014-46ee-bb47-497508912291>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 387 chars, 69 words, 6 lines
- **script:** ratio 0.672 (arabic 0.672, latin 0.328)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** http://www.express.com.pk/epaper/thumbnails.aspx?Issue=NP_LHE&Page=Commerce_PageBW&Date=20120328&Pageno=6

```text
اسپیشل اولمپکس؛ کھلاڑیوں کو مختلف گروپس میں تقسیم کر دیا گیا
ہاکی کی بہتری کے لیے انڈومنٹ فنڈز قائم کرنے کا مطالبہ
یوراج سنگھ نے شعیب ملک کا چیلنج قبول کرلیا
ون ڈے رینکنگ؛ یاسر شاہ نے44درجے ترقی کی اونچی اُڑان بھر لی
پاکستان سپر لیگ کا انعقاد پھر کھٹائی میں پڑ گیا
Copyright © Century Publications. This material may not be published, broadcast, rewritten, redistributed or derived from.
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 167 · fineweb2-urd_Arab:<urn:uuid:28309046-fe03-4afe-ae69-805bee91497f>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 3235 chars, 634 words, 24 lines *(excerpt shows first 1500)*
- **script:** ratio 0.631 (arabic 0.631, latin 0.369)
- **repetition:** dup_line 0.000, top-ngram 0.023, dup-ngram 0.021
- **url** 0.007 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://urdu.siasat.pk/social-media-news/2021-08-19/news-113356

```text
میں بھول گئی تھی، یہ تو لڑکی کی اپنی غلطی ہے ‘خاتون کو ہراساں کرنے پر فنکار برہم’
یوم آزادی پر اپنی آزادی کا ناجائز فائدہ اٹھاتے ہوئے چار سو درندوں نے خاتون ٹک ٹاکر عائشہ کو زدکوب کیا, بدتمیزی کی اور جہالت کی انتہا کو چھو گئے,جس پر پورا ملک یک زبان واقعے کی شدید الفاظ میں مذمت کر رہا ہے,وائرل ویڈیو نے فنکاروں کو بھی مایوس کردیا, پاکستانی فنکار عائشہ کے ساتھ ہونے والے ظلم پر شدید برہم ہیں کہتے ہیں عائشہ کے گنہگاروں کو عبرت کا نشانہ بنایا جائے۔
اداکار عدنان صدیقی نے واقعے میں ملوث ملزمان کے خلاف سخت ایکشن کا مطالبہ کرتے ہوئے کہا کہ اب ایسی صورت حال میں کہ جب ہمارے پاس مینارِ پاکستان واقعے کے تمام تر شواہد موجود ہیں تو ملزمان اب تک سلاخوں کے پیچھے کیوں نہیں گئے؟‘ انہوں نے سوال کیا کہ کیا ہم ان پولیس اہل کاروں کو اس بھیانک فعل کے ذمہ داران کو سلاخوں کے پیچھے ڈال کر ایکشن میں نہیں دیکھ سکتے ہیں؟
Now that we hav a plethora of evidence of what unfolded at #minarepakistan Can we finally see our police in action by putting those men responsible for this gruesome act behind the bars? Is this too much to ask for our women?#400men #lahoreincident #needanswers #protectourwomen
— Adnan Siddiqui (@adnanactor) August 18, 2021
اداکارہ ماہرہ خان نے کہا میں معافی چاہتی ہوں۔ ، بے چارے 400 آدمی، خود کو روک نہ سکے۔
Damn I’m sorry.. I keep forgetting – it was Her fault!! Poor 400 men.. they couldn’t help it. #MinarePakistan
— Mahira Khan (@TheMahiraKhan) August 17, 2021
عائزہ خان نے بھی واقعے کی مذمت کرتے ہوئے لکھا کہ گھررہیں محفوظ رہیں،جان کو خطرہ ہے، یہ سب کورونا کی وجہ کہتے آئے ہیں، لیکن اب شرم 
```

**verdict:** keep
**note:** 

---

### 168 · urdu-wikipedia:919905

- **filter:** REJECT — too_short
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 85 chars, 15 words, 4 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=2, zwnj=1
- **url:** https://ur.wikipedia.org/wiki/%DA%AF%D9%88%DA%A9%D8%AE%D8%A7%D9%86%20%D8%AA%D9%88%D8%B1%DB%81

```text
حوالہجات
بقید حیات شخصیات
ترک فٹبال کھلاڑی
ویکی ڈیٹا سے مطابقت رکھنے والی مختصر تفصیل
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 169 · urdu-wikipedia:678516

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 311 chars, 54 words, 11 lines
- **script:** ratio 0.579 (arabic 0.579, latin 0.421)
- **repetition:** dup_line 0.000, top-ngram 0.045, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=5
- **url:** https://ur.wikipedia.org/wiki/%D9%82%D8%A7%D8%B2%D8%A7%D9%86%20%D8%A7%D8%B1%DB%8C%D9%86%D8%A7

```text
قازان ارینا (; ) قازان، روس میں ایک اسٹیڈیم ہے۔

حوالہ جات

بیرونی روابط

Official website
Stadium information
Stadium construction progress
Gallery with pictures of the stadium on Sports.ru

2013ء میں پایہ تکمیل کھیل مقامات
2018ء فیفا عالمی کپ اسٹیڈیم
روس میں فٹ بال مقامات
کامنز زمرہ جس کا ربط ویکی ڈیٹا پر ہے
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 170 · urdu-wikipedia:201611

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 311 chars, 49 words, 8 lines
- **script:** ratio 0.691 (arabic 0.691, latin 0.309)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=3
- **url:** https://ur.wikipedia.org/wiki/%D8%B3%DB%8C%D9%86%D9%B9-%DA%A9%DB%8C%D8%B1-%D8%AF%D8%B3-%DA%AF%D9%B9%D8%B3

```text
سینٹ-کیر-دس-گٹس ( فرانسیسی: Saint-Cyr-des-Gâts) فرانس کا ایک فرانسیسی کمیون جو Canton of L'Hermenault میں واقع ہے۔

تفصیلات
سینٹ-کیر-دس-گٹس کا رقبہ 21.08 مربع کیلومیٹر ہے اور اس کی مجموعی آبادی 531 افراد پر مشتمل ہے۔

مزید دیکھیے
فرانس
فہرست فرانس کے شہر

حوالہ جات

Short description is different from Wikidata
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 171 · fineweb2-urd_Arab:<urn:uuid:96543719-080a-4013-96e9-4adcc3490546>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 1653 chars, 333 words, 2 lines *(excerpt shows first 1500)*
- **script:** ratio 0.998 (arabic 0.998, latin 0.002)
- **repetition:** dup_line 0.000, top-ngram 0.021, dup-ngram 0.018
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://www.waqiatimes.com/%D9%88%D9%81%D8%A7%D9%82%DB%8C-%D9%88%D8%B2%DB%8C%D8%B1%D8%A7%D8%B7%D9%84%D8%A7%D8%B9%D8%A7%D8%AA-%D9%81%D9%88%D8%A7%D8%AF-%DA%86%D9%88%DB%81%D8%AF%D8%B1%DB%8C-%D9%86%DB%92-%D8%A7%DB%8C%D9%85-%DA%88/

```text
رسائی نیوزاسلام آباد:نمائندہ رسائی نیوز کے مطابق سرکاری ٹی وی کے اکاؤنٹس سے رقم کی بڑے پیمانے پر منتقلی کے معاملے پر وزیر اطلاعات فواد چوہدری نے ایم ڈی پی ٹی وی ارشد خان پر ایف آئی آر درج کرانے کا حکم دے دیا اور رقم کی منتقلی کے معاملات کی تحقیقات کی ہدایت کردی۔وزیر اطلاعات کی جانب سے وفاقی پولیس کے سربراہ کو خط میں لکھا گیا ہے کہ پی ٹی وی کے کھاتوں سے بھاری ادائیگیاں کی گئی ہیں، ادارے کے اکاؤنٹس سے 31 لاکھ 80 ہزار اور 17 لاکھ 60 ہزار روپے کے مشکوک چیک کیش کروائے گئے، پی ٹی وی اکاؤنٹس سے رقم کی منتقلی ضابطہ فوجداری کا مقدمہ بنتا ہے، معاملے کی میرٹ پر تحقیقات کر کے آگاہ کیا جائے۔پی ٹی وی یونین کے جنرل سیکرٹری نے وزیر اطلاعات کو درخواست دی تھی کہ ادارے کے کھاتوں کی تحقیقات کرائی جائے، درخواست کے ساتھ تمام بڑی بڑی ادائیگیوں کے ثبوت اور کھاتوں کی نقول بھی منسلک ہیں۔واضع رہےنومبر 2018 میں ارشدخان کو قائم مقام ایم ڈی پی ٹی وی تعینات کیا گیا تھا۔
انفارمیشن ٹیکنالوجی کی مدد سے کاروبار اور تجارتی سرگرمیوں میں خواتین اور نوجوانوں کی شرکت بڑھانے کی ضرورت ہے،صدر مملکت ڈاکٹر عارف علوی کی ڈیجیٹل تعاون تنظیم کے وفد سے ملاقات میں گفتگو وزیر اعظم عمران خان آج سمندر پار پاکستانیوں کی سہولت کے لیے ڈیجیٹل پورٹل کا آغاز کریں گے ، پورٹل سے پاور آف اٹارنی کی تصدیق ہو سکے گی اپوزیشن اصلاحات کیلئے عدالت کی بجائے سپیکر آفس آئے، ہم اوورسیز پاکستانیوں کو ووٹ کا حق دینے سے پیچھے نہیں ہٹ سکتے، یہ ہمارا انتخابی وعدہ تھا، چوہدری فواد حسین مستحق افراد کو آٹے، دالوں اور گھی پر سبسڈی ملے گی، جمعہ سے 8171 میسج سروس بحال ہوجائے گی، ڈاکٹر ثانیہ نشتر وزیراعظم سے ڈی جی ISI لیفٹیننٹ جنرل فیض حمید کی الواداعی ملاقات 
```

**verdict:** keep
**note:** 

---

### 172 · urdu-wikipedia:1007996

- **filter:** REJECT — repetition:dup_5gram, repetition:dup_6gram, repetition:dup_7gram
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 4064 chars, 847 words, 12 lines *(excerpt shows first 1500)*
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.089, dup-ngram 0.597
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=34
- **url:** https://ur.wikipedia.org/wiki/%D9%81%D8%A7%D8%B1%D9%88%D9%82%20%D8%B1%D8%B4%DB%8C%D8%AF

```text
فاروق رشید ڈار (پیدائش: 15 اکتوبر 1958ء کو کراچی ، سندھ )، ایک سابق پاکستانی کرکٹ کھلاڑی ہیں ۔

فرسٹ کلاس کیریئر
رشید نے 17 فروری 1979ء کو 1978/79ء بی سی سی پی پیٹرنز ٹرافی کے دوران کراچی بلیوز کے خلاف الائیڈ بینک لمیٹڈ کے لیے اپنا آغاز کیا۔ پہلی اننگز میں رشید نے 30 رنز بنائے۔ دوسری اننگز میں، اس نے 0/8 (2 اوور) کے اعداد و شمار حاصل کیے اور اس نے بیٹنگ نہیں کی کیونکہ الائیڈ بینک لمیٹڈ کو اپنی دوسری اننگز کھیلنے کی اجازت نہیں ملی۔ میچ برابری پر ختم ہوا۔ رشید نے اپنا اگلا میچ الائیڈ بینک لمیٹڈ کے لیے راولپنڈی کے خلاف 1982/83ء قائد اعظم ٹرافی کے دوران 16 اکتوبر 1982ء کو کھیلا۔ پہلی اننگز میں رشید نے 5 رنز بنائے۔ دوسری اننگز میں رشید نے 20 * سکور کیے کیونکہ الائیڈ بینک لمیٹڈ نے 7 وکٹوں سے فتح حاصل کی۔ رشید نے اپنا اگلا میچ مسلم کمرشل بینک کے خلاف 22 اکتوبر 1982ء کو کھیلا۔ پہلی اننگز میں انہوں نے 39 رنز بنائے۔ دوسری اننگز میں انہوں نے گیند بازی نہیں کی اور 0 رنز بنائے۔ مسلم کمرشل بینک 27 رنز سے جیت گیا۔ رشید نے اپنا اگلا میچ 29 اکتوبر 1982ء کو ریلوے کے خلاف کھیلا۔ پہلی اننگز میں انہوں نے 0 رنز بنائے۔ دوسری اننگز میں انہوں نے 23 رنز بنائے۔ الائیڈ بینک لمیٹڈ نے یہ میچ 81 رنز سے جیت لیا۔ رشید نے اپنا اگلا میچ 4 نومبر 1982ء کو لاہور سٹی کے خلاف کھیلا۔ پہلی اننگز میں انہوں نے 6 رنز بنائے۔ دوسری اننگز میں، اس نے بیٹنگ نہیں کی کیونکہ میچ ڈرا پر ختم ہوا۔ رشید نے اپنا اگلا میچ 10 نومبر 1982ء کو پاکستان انٹرنیشنل ایئر لائنز کے خلاف کھیلا۔ پہلی اننگز میں انہوں نے 6 رنز بنائے۔ دوسری اننگز میں انہوں نے 27 * رنز بنائے۔ میچ ڈرا کی صورت میں نکلا۔ رشید نے اپنا اگلا میچ یونائیٹڈ بینک لمیٹڈ کے خلاف
```

**verdict:** keep
**note:** cricketer biography; dup-ngram is career-record prose about one person

---

### 173 · urdu-wikipedia:364086

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 339 chars, 62 words, 7 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.133, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=4
- **url:** https://ur.wikipedia.org/wiki/%D9%81%D8%A7%D9%84%DA%A9%D9%88%D9%86%20%D9%85%DB%8C%D8%B3%D8%A7%D8%8C%20%D9%B9%DB%8C%DA%A9%D8%B3%D8%A7%D8%B3

```text
فالکون میسا، ٹیکساس ریاستہائے متحدہ امریکا کا ایک مردم شماری نامزد مقام جو زاپاٹا کاؤنٹی، ٹیکساس میں واقع ہے۔

تفصیلات
فالکون میسا، ٹیکساس کا رقبہ 4.0 مربع کیلومیٹر ہے اور اس کی مجموعی آبادی 405 افراد پر مشتمل ہے اور 112 میٹر سطح سمندر سے بلندی پر واقع ہے۔

مزید دیکھیے
ریاستہائے متحدہ امریکا
فہرست ریاستہائے متحدہ امریکہ کے شہر

حوالہ جات
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 174 · fineweb2-urd_Arab:<urn:uuid:559f2de7-a3a5-4cb2-9a87-defc679da5bb>

- **filter:** REJECT — html_residue
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 4320 chars, 937 words, 22 lines *(excerpt shows first 1500)*
- **script:** ratio 0.928 (arabic 0.928, latin 0.072)
- **repetition:** dup_line 0.000, top-ngram 0.035, dup-ngram 0.000
- **url** 0.033 · **html** 0.067 · **U+FFFD** 0.00000
- **stage 4:** zero_width=2
- **url:** http://cricurdu.co.uk/%DA%A9%DA%BE%DB%8C%D9%84/t20-league/psl/%DB%8C%D9%88%D9%86%D8%B3-%D8%AE%D8%A7%D9%86-%DA%A9%DB%8C-%DA%88%D8%A7%D8%A6%D8%B1%DB%8C-%DA%A9%D8%A7-%D8%B1%D8%A7%D8%B2/

```text
دس ہزار رنز بنانے والے نے دل جیت لیا !
اگر یہ لکھوں کہ یونس خان پر پیار آنے لگا ہے تو غلط نہیں ہو گا۔
وہ یونس خان جو کرکٹ سےلگن ، سخت محنت اور بیٹنگ کے حوالے سے تو مشہور تھا ہی مگر اس کی ایک پہچان جلد غصہ میں آجانا، کھلاڑیوں اورکرکٹ بورڈ سے پھڈے ، حتی کہ غیرملکی کوچز سے الجھ جانا بھی رہی ہے
زمبابوے کے کرکٹر اور پاکستان کرکٹ ٹیم کے سابق کوچ گرانٹ فلاور نے بھی کچھ عرصہ قبل انکشاف کیاتھا کہ ایک مرتبہ ان کے بیٹنگ ٹپس دینے سے یونس خان اس قدر تنگ ، غصہ میں آ گئے کہ انہوں نے ایک چھری اٹھا کر ان کی گردن پر رکھ دی تھی ، اس وقت ہیڈ کوچ مکی آرتھر بھی گرانٹ فلاورکے پاس بیٹھے ہوئے تھے ۔
دیکھا جائے تو یہ ایک بہت بڑا انکشاف تھا کہ ایک غیر ملکی کوچ کے ساتھ ایسا سلوک کیا گیا مگر معاملہ جلد ہی ٹھنڈا پڑ گیا تھا-
اگر گرانٹ ان دنوں ہی یہ واقعہ سامنے لے آتے جب وہ پاکستان کے بیٹنگ کوچ تھے تو یونس کے کرکٹ کیریئر کے لئے بڑا مسئلہ بن سکتا تھا مگر ایک عرصہ بعد اب اس انکشاف کو کسی نے زیادہ اہمیت نہیں دی ہے
، تاہم لگتا یہی ہے کہ ان گزرے سالوں میں یونس خان نے زندگی سے بہت کچھ سیکھا ہے اور وہ ایک بالکل مختلف یونس خان نظر آ رہے ہیں ۔
یونس خان کی ڈائری کا “راز”
پاکستان و انگلینڈ کے مابین اگست و ستمبر 2020میں کھیلی جانے والی ٹیسٹ و ٹی ٹوئنٹی سیریز میں ایک بات جو بہت زیادہ نوٹ کی گئی وہ بیٹنگ کوچ یونس خان کا میچز کے دوران مسلسل کچھ لکھتے رہنا تھا ۔
سوشل میڈیا پر بہت میمز بھی بنیں کہ آخر یونس ڈائری میں کیا لکھتے ہیں ؟
کسی نے کہاکہ یونس خان وقت گزاری کے لئے کارٹون بناتے رہتے ہیں تو کوئی بولا کہ شاید میچ کی سکورنگ کرتے ہوں گے مگر اس راز سے پردہ تو یونس خان ہی اٹھا سکتے تھے ، جو انہوں نے اٹھا دیا ہے ۔ یونس خان نے 
```

**verdict:** keep
**note:** cricket article with an embedded Twitter card

---

### 175 · urdu-wikipedia:338223

- **filter:** REJECT — repetition:top_4gram
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 364 chars, 62 words, 10 lines
- **script:** ratio 0.858 (arabic 0.858, latin 0.142)
- **repetition:** dup_line 0.000, top-ngram 0.223, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=3
- **url:** https://ur.wikipedia.org/wiki/%D9%88%D8%B3%D8%B7%DB%8C%20%D8%A7%DB%8C%D8%AA%DA%BE%D9%86%D8%B2%20%28%D8%B9%D9%84%D8%A7%D9%82%D8%A7%D8%A6%DB%8C%20%D8%A7%DA%A9%D8%A7%D8%A6%DB%8C%29

```text
وسطی ایتھنز (علاقائی اکائی) ) یونان کا ایک یونان کی علاقائی اکائیاں جو اتیکا (علاقہ) میں واقع ہے۔

تفصیلات
وسطی ایتھنز (علاقائی اکائی) کا رقبہ 87.4 مربع کیلومیٹر ہے اور اس کی مجموعی آبادی 1,029,520 افراد پر مشتمل ہے۔

مزید دیکھیے
یونان
فہرست یونان کے شہر

حوالہ جات

یونان کی علاقائی اکائیاں
Short description is different from Wikidata
وسطی ایتھنز (علاقائی اکائی)
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 176 · fineweb2-urd_Arab:<urn:uuid:f999247e-4ff6-456e-a9b1-adaf462e9df3>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 423 chars, 89 words, 13 lines
- **script:** ratio 0.696 (arabic 0.696, latin 0.304)
- **repetition:** dup_line 0.000, top-ngram 0.154, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** teh_marbuta=1
- **url:** https://islamhouse.com/ur/videos/255365/

```text
To view this video please enable JavaScript, and consider upgrading to a web browser that supports HTML5 video
علمی زمرے:
اس ویڈیو سی ڈی میں قرآن وحدیث کی روشنی میں اللہ تعالی کی معرفت کی تفصیل اور اس کی معرفت میں رکاوٹوں کو بیان کیا گیا ھے۔
اللہ کی معرفت - 7
MP4 38.8 MB
ارکانِ ایمان ایک اجمالی تعارُف
اللہ کون ہے؟
آیہ الکرسی اور عظمتِ الہی
اللہ کہاں ہے؟
اللہ کی معرفت
اللہ کی معرفت - 6
اللہ کی معرفت - 5
اللہ کی معرفت - 4
```

**verdict:** drop
**note:** video page: JS notice and furniture dominate

---

### 177 · urdu-wikipedia:363022

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 354 chars, 57 words, 11 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.203, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=6
- **url:** https://ur.wikipedia.org/wiki/%D8%A7%DB%8C%D9%88%D8%A7%D9%86%D9%88-%D9%81%D8%B1%D8%A7%D9%86%DA%A9%DB%8C%D9%88%D8%B3%DA%A9%20%D8%A7%D9%88%D8%A8%D9%84%D8%A7%D8%B3%D8%AA

```text
ایوانو-فرانکیوسک اوبلاست یوکرین کا ایک یوکرین کے اوبلاست جو یوکرین میں واقع ہے۔

تفصیلات
ایوانو-فرانکیوسک اوبلاست کا رقبہ 13,900 مربع کیلومیٹر ہے اور اس کی مجموعی آبادی 1,381,700 افراد پر مشتمل ہے۔

مزید دیکھیے
یوکرین
فہرست یوکرین کے شہر

حوالہ جات

ایوانو-فرانکیوسک اوبلاست
1939ء میں قائم ہونے والے ممالک اور علاقے
غالیسیا (مشرقی یورپ)
یوکرین کے اوبلاست
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 178 · fineweb2-urd_Arab:<urn:uuid:aa51d915-a54c-4baf-88aa-8b2b9ae99534>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 860 chars, 176 words, 9 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.059, dup-ngram 0.098
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** http://www.lahorenama.com/archives/2009

```text
لاہور : محکمہ اینٹی کرپشن لاہور ریجن نے بلدیہ عظمیٰ لاہور کے شالیمار زون میں تعینات 20 افسران کے خلاف مقدمہ درج کرنے کا فیصلہ کیا ہے۔ بتایا گیا ہے کہ محکمہ لاہور اینٹی کرپشن لاہور ریجن ان افسران کے خلاف بعض مالی بے ضابطگیوں کے حوالے سے تحقیقات کر رہی ہے۔ اس سلسلے میں محکمہ اینٹی کرپشن پنجاب نے ان افسران کو ریکارڈ سمیت طلب کر رکھا تھا لیکن افسران کی جانب سے انکوائری ٹیم کے روبرو پیش نہ ہونے پر محکمہ اینٹی کرپشن نے ان افسران کے خلاف مقدمہ درج کرنے کا فیصلہ کیا تھا۔
مزید پڑھیں
ہمارا فیس بک پیج
حالیہ پوسٹس
- لاہور پولیس کا یوم یکجہتی کشمیر پر فول پروف انتظامات کا جائزہ، بلال صدیق
- چین نے ہمیشہ بین الاقوامی قوانین کی پاسداری کی ہے،وانگ ای
- جوہانسبرگ کے مینڈیلا اسکوائر میں لالٹین فیسٹیول گالا کی تشہیری ویڈیو کی دھوم
- چین دوسرے ممالک کی خودمختاری کا احترام کر تا ہے، وزارت خا رجہ
- نئی توانائی کی گاڑیوں سے ماحول دوست ترقی کو فروغ ملے گا، چینی وزارت صنعت
```

**verdict:** keep
**note:** 

---

### 179 · fineweb2-urd_Arab:<urn:uuid:67d0a642-7560-47a5-9583-0a2c2b3e3941>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 966 chars, 190 words, 1 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.052, dup-ngram 0.114
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://www.ia.com.pk/markete_oriented_subjects_will_be_introduced/

```text
روزگار سے آبادی کے تناسب میں پائے جانے والے فرق کو دور کرنے اور عوام کو سستی ذرائع سے جدید تعلیم تک رسائی کی فراہمی کے لئے پنجاب کا محکمہ ہائر ایجوکیشن (ایچ ای ڈی) بی ایس کالجوں میں مارکیٹ پر مبنی نئے مضامین متعارف کروا رہا ہے۔چونکہ محکمہ نئے اصلاحات کے ایجنڈے کے تحت صوبے میں تعلیم کی انتظامیہ کو بہتر بنانے پر کام کر رہا ہے ، لہذا صوبائی وزیر راجہ یاسر ہمایوں سرفراز نے سرکاری شعبے کے کالجوں میں نئے جدید مضامین متعارف کرانے کی منظوری دے دی ہے۔متعارف کروائے گئے نئے مضامین میں بائیوٹیکنالوجی مائکروبیولوجی ، فوڈ سائنس ، میڈیکل لیب ٹیکنالوجی ، سیاحت اور مہمان نوازی اور ڈیٹا سائنس شامل ہیں۔ ڈی پی آئی کالجز ، ڈاکٹر عاشق حسین ، آئندہ تعلیمی سال میں منتخب کالجوں میں اس پروگرام کا آغاز کریں گے۔صوبائی سیکرٹری برائے اعلی تعلیم ندیم محبوب نے انکشاف کیا کہ تعلیمی سال 2021-22 کے آغاز سے مارکیٹ پر مبنی نئے مضامین ابتدائی طور پر چار اضلاع کے 16 کالجوں میں متعارف کروائے جائیں گے۔بعد ازاں ، یہ مضامین مرحلہ وار انداز میں صوبہ بھر کے تمام کالجوں میں متعارف کروائے جائیں گے۔
```

**verdict:** keep
**note:** 

---

### 180 · urdu-wikipedia:364083

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 365 chars, 65 words, 9 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.123, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=4
- **url:** https://ur.wikipedia.org/wiki/%D9%81%D8%A7%D9%84%DA%A9%D9%88%D9%86%20%DB%81%DB%8C%D8%BA%D9%B9%D8%B3%D8%8C%20%D9%85%DB%8C%D9%86%DB%8C%D8%B3%D9%88%D9%B9%D8%A7

```text
فالکون ہیغٹس، مینیسوٹا ریاستہائے متحدہ امریکا کا ایک شہر جو مینیسوٹا میں واقع ہے۔

تفصیلات
فالکون ہیغٹس، مینیسوٹا کا رقبہ 5.80 مربع کیلومیٹر ہے اور اس کی مجموعی آبادی 5,321 افراد پر مشتمل ہے اور 291 میٹر سطح سمندر سے بلندی پر واقع ہے۔

مزید دیکھیے
ریاستہائے متحدہ امریکا
فہرست ریاستہائے متحدہ امریکہ کے شہر

حوالہ جات

ریمسی کاؤنٹی، مینیسوٹا میں شہر
مینیسوٹا کے شہر
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 181 · urdu-wikipedia:121667

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 286 chars, 54 words, 8 lines
- **script:** ratio 0.823 (arabic 0.823, latin 0.177)
- **repetition:** dup_line 0.000, top-ngram 0.084, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=3
- **url:** https://ur.wikipedia.org/wiki/%D8%A2%DB%8C%D8%B3%DA%A9

```text
آیسک () ایک شہر ہے جو ایران میں واقع ہے۔ اس کی مجموعی آبادی 5,023 افراد پر مشتمل ہے، یہ صوبہ خراسان جنوبی میں واقع ہے۔

متعلقہ روابط
فہرست ایران کے شہر

حوالہ جات

ایران کے شہر
جغرافیہ شہرستان سرایان کے نامکمل مضامین
صوبہ خراسان جنوبی کے شہر
Short description is different from Wikidata
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 182 · urdu-wikipedia:919840

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 2117 chars, 462 words, 13 lines *(excerpt shows first 1500)*
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.017, dup-ngram 0.029
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** alef=3, digits=10, heh=5, kaf=1, presentation_forms=2, teh_marbuta=5, whitespace=7, yeh=10
- **url:** https://ur.wikipedia.org/wiki/%D8%AD%D8%AC%D8%A7%D8%B2%20%D8%B3%DB%92%20%D8%A2%DA%AF%20%DA%A9%D8%A7%20%D9%86%DA%A9%D9%84%D9%86%D8%A7

```text
رسول اکرم صلی اللہ علیہ وسلم نے جن علاماتِ قیامت کی خبر دی ہے ان میں ایک چھوٹی علامت ہے،سر زمینِ حجاز سے آگ کا ظہور۔

ابو ھریرہ رضی اللہ عنہ سے روایت ہے کہ رسول اکرم صلی اللہ علیہ وسلم نے فرمایا:

"لَا تَقُومُ السَّاعَہُ حَتَّی تَخْرُجَ نَارٌ مِنْ اَرْضِ الْحِجَازِ، تُضِیءُ اَعْنَاقَ الْاِبِلِ بِبُصْرَی"

”قیامت قائم نہیں ہو گی یہاں تک کہ سر زمینِ حجاز سے ایک آگ نکلے گی اور بُصریٰ میں اونٹوں کی گردنوں کو روشن کر دے گی“۔

یہ حدیث اس بات پر دلالت کرتی ہے کہ سرزمینِ حجاز سے آگ کا ظاہر ہونا قیامت کی ایک علامت ہے۔

حافظ ابن کثیر، ابن حجر، امام قرطبی رحمہم اللہ وغیرہ اس بات پر متفق ہیں کہ 654ھ میں یہ علامت ظاہر ہوچکی ہے.۔

حافظ ابن کثیر رحمہ اللہ فرماتے ہیں کہ: ارض حجاز سے وہ عظیم آگ ظاہر ہوچکی ہے جس سے بُصری (ملک شام کے شہر حوران) کے اونٹنیوں کے گردنیں روشن ہو گئی تھیں، کہا جاتا ہے کہ یہ آگ تین ماہ تک رہی، اور یہ اس قدر شدید تھی کہ مدینہ کی خواتین اس کی روشنی میں سوت کاتا کرتی تھیں۔

علامہ ابوشامہ رحمہ اللہ* اس واقعے کی تفصیل بیان کرتے ہوئے لکھتے ہیں کہ : جمادی الآخرہ 654ھ کی 3 تاریخ اور بدھ کی رات تھی، جب مدینہ منورہ میں ایک ہولناک گونج سنائی دی، اس کے بعد زلزلہ آیا، اس نے زمین، دیواروں، چھتوں، لکڑیوں اور دروازوں تک کو لرزا دیا، یہ سلسلہ بدھ کی رات سے لیکر جمعہ کے دن تک جاری رہا، پھر اس کے بعد ایک عظیم آگ مدینہ کے مقام حرہ (جو بنو قریظہ کے قریب تھا) سے ظاہر ہوئی، یہ آگ ہمیں مدینہ میں اپنے گھروں میں بیٹھے نظر آ رہی تھی، ہمیں یوں محسوس ہوا کہ یہ ہمارے قریب ہی موجود ہے، مدینہ کی وادیاں آگ سے بھر گئیں، آگ ان میں وادی شظا کی جانب یوں چل رہی تھی جیسے پانی بہتا ہے، یہ آگ بلند و بالا عما
```

**verdict:** keep
**note:** 

---

### 183 · fineweb2-urd_Arab:<urn:uuid:61a7ba31-dd4e-4b04-b682-354f8bf4a86e>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 1902 chars, 388 words, 11 lines *(excerpt shows first 1500)*
- **script:** ratio 0.674 (arabic 0.674, latin 0.326)
- **repetition:** dup_line 0.050, top-ngram 0.036, dup-ngram 0.082
- **url** 0.012 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://urdu.arynews.tv/jealous-filmmakers-have-formed-assassination-squad-to-kill-rrr-director/

```text
اپنے عجیب و غریب بیانات اور ٹوئٹس کی وجہ سے خبروں میں رہنے والے فلم ہدایت کار رام گوپال ورما نے کہا کہ کچھ بھارتی فلمساز آر آر آر کے ہدایت کار راجامولی کو قتل کرنے کی سازش کررہے ہیں۔
فلمساز رام گوپال ورما نے سوشل میڈیا پر کہا کہ وہ فلم سازوں کے ایک ’قاتل اسکوارڈ‘ کا حصہ ہیں جو ایس ایس راجامولی کو مارنا چاہتے ہیں، رات گئے اپنے اس سنسنی خیز ٹویٹس سے رام گوپال ورما نے سوشل میڈیا پر ہنگامہ برپا کردیا۔
انہوں نے ایک ٹوئٹ میں ایس ایس راجامولی کی تعریف کرتے ہوئے لکھا کہ ’ آپ نے آصف کے مغل اعظم سے لے کر رمیش کے شولے، کرن جوہر کی اور بھارت کے سنجے لیلا بھنسالی تک سب کو پیچھے چھوڑ دیا ہے، اس لیے میں آپ کے ہاتھ چومنا چاہتا ہوں‘۔
Hey @ssrajamouli U basically SURPASSED every film maker from #KaAsif who made #MughaleAzam till #RameshSippy who made #Sholay and also the likes of Aditya Chopras, Karan Johars and the bhansalis of India and I want to suck ur little toe for that https://t.co/KCgN0u2eJa
— Ram Gopal Varma (@RGVzoomin) January 23, 2023
آر آر آر: شائقین نے آسکر ایوارڈ کی اُمید باندھ لی
ہدایتکار رام گوپال ورما نے ایک اور ٹوئٹ میں لکھا کہ’جناب راجا مولی مہربانی کرکے آپ اپنی سیکیورٹی بڑھا لیں کیوں کہ بھارت میں ایک حاسد فلمساز گروپ نے آپ کو مارنے کے لیے ایک قاتل اسکواڈ تشکیل دی ہے، میں بھی اس گروپ کا حصہ ہوں، میں یہ راز آپ کو بتا رہا ہوں کیوں کہ میں نے پی رکھی ہے‘۔
And sir @ssrajamouli , please increase ur security because there is a bunch of film makers in india who out of pure jealousy formed an assassination squad to kill you , of which I am also a part ..Am just spilling out the secr
```

**verdict:** keep
**note:** 

---

### 184 · fineweb2-urd_Arab:<urn:uuid:e7788a0a-d87a-432d-b7b8-22e847efe6aa>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 4053 chars, 848 words, 29 lines *(excerpt shows first 1500)*
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.016, dup-ngram 0.012
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://www.express.pk/story/626887/

```text
- ابتدائی مرحلے میں تشخیص سے چھاتی کا کینسر قابل علاج ہے
- حیدر علی طبیعت ناسازی کے باعث اسپتال منتقل
- شمالی وزیرستان میں پولیوکی تصدیق کے بعد بچہ انتقال کرگیا
- حکومت کا پیٹرول کی فی لیٹر قیمت میں 12 روپے 63 پیسے کمی کا اعلان
- وزیراعظم ہاؤس سے غائب ہونے والے سائفر کا سراغ مل گیا
- انٹرنیشنل ٹی 20 میچز بابر اعظم نے ایک اور سنگ میل عبور کرلیا
- انگلینڈ نے چھٹے ٹی ٹوینٹی میں پاکستان کو باآسانی شکست دے دی
- یوکرینی شہروں کے الحاق پر امریکا نے روس پر پابندیاں مزید سخت کردیں
- ماں اور بیٹا 18 کلو منشیات اسمگل کرنے کی کوشش میں گرفتار
- 2 اکتوبر سے لاہور اور کراچی تک مسافر ٹرینیں بحال کر نے کا فیصلہ
- سائفر کی کاپی وزیراعظم ہاؤس کے ریکارڈ سے غائب، تحقیقات کے لیے کابینہ کمیٹی قائم
- مدرسے کے 9 سالہ طالبعلم پرتشدد کرنے والا معلم گرفتار
- احتجاجی طلبا پر سرعام تشدد کرنے والی پرنسپل کو عہدے سے ہٹا دیا گیا
- ملکہ برطانیہ کے انتقال کی وجہ سامنے آگئی
- انٹر بینک میں ڈالر کمی کے بعد 228.45 روپے کا ہوگیا
- وفاقی کابینہ کے اجلاس سے قبل تمام اراکین سے موبائل فون لے لیے گئے
- وفاقی کابینہ نے ریکوڈک پر ریفرنس سپریم کورٹ بھیجنے کی منظوری دے دی
- افغان سرزمین سے پاک فوج پر فائرنگ سے سپاہی شہید
- سمندری حدود کی خلاف ورزی پر 16 بھارتی ماہی گیر گرفتار
- ایل پی جی کی قیمت میں 10 روپے فی کلو کمی
لاہور: حکومت کی سمت درست ہے، تعلیم، صحت، خوراک، سماجی تحفظ و دیگر بنیادی حقوق کے حوالے سے موثر کام ہو رہا ہے۔ یہی وجہ ہے کہ غربت میں بتدریج کمی آرہی ہے تاہم ان منصوبوں کا دائرہ کار دوردراز علاقوں تک پھیلانے کی ضرورت ہے۔
40 فیصد آبادی غربت کا شکار ہے جس کی وجہ سے دہشت گردی، جرائم و دیگر معاشرتی مسائل میں اضافہ
```

**verdict:** keep
**note:** 

---

### 185 · fineweb2-urd_Arab:<urn:uuid:40302212-f569-41a9-83f6-f4eaba63adeb>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** code_switched
- **size:** 766 chars, 150 words, 12 lines
- **script:** ratio 0.868 (arabic 0.803, latin 0.065)
- **repetition:** dup_line 0.000, top-ngram 0.037, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://www.rekhtadictionary.com/meaning-of-nukta-uthaanaa?lang=ur

```text
تلاش شدہ نتائج
محفوظ شدہ الفاظ
"نُکتَہ اُٹھانا" کے متعقلہ نتائج
نُکتَہ اُٹھانا کے اردو معانی
- کسی بات کو موضوع بحث بنانا، کوئی بات یا خیال پیش کرنا، کوئی لطیف یا علمی بات برائے بحث پیش کرنا
नुक्ता उठाना के हिंदी अर्थ
- किसी बात को चर्चा का विषय बनाना, किसी बात या विचार को प्रस्तुत करना, कोई सूक्ष्म या वैज्ञानिक बात चर्चा हेतु प्रस्तुत करना
اطلاع : ریختہ ڈکشنری کا یہ BETA ورژن ہے اور آزمائش کے لیے باضابطہ اشاعت سے پہلے جاری کیا گیا ہے۔کسی بھی قسم کے تضاد اور غلطیوں کی اصلاح کے لیے اپنے تجاویز و آرا ہمیں email@example.com پر ارسال کیجیے۔ یا رائے زنی کیجیے
حوالہ جات: ریختہ ڈکشنری کی ترتیب میں مستعمل مصادر اور مراجع کی فہرست دیکھیں ۔
رائے زنی کیجیے (نُکتَہ اُٹھانا)
Delete 44 saved words?
کیا آپ واقعی ان اندراجات کو حذف کر رہے ہیں؟ انہیں واپس لانا ناممکن ہوگا۔
```

**verdict:** keep
**note:** 

---

### 186 · urdu-wikipedia:363822

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** code_switched
- **size:** 337 chars, 58 words, 9 lines
- **script:** ratio 1.000 (arabic 0.776, latin 0.224)
- **repetition:** dup_line 0.000, top-ngram 0.089, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=4
- **url:** https://ur.wikipedia.org/wiki/%D9%81%D8%A7%DA%A9-%D9%81%D8%A7%DA%A9%20%D8%B1%DB%8C%DA%AF%DB%8C%D9%86%DA%A9%DB%8C

```text
فاک-فاک ریگینکی انڈونیشیا کا ایک regency of Indonesia جو مغربی پاپوا (صوبہ) میں واقع ہے۔

تفصیلات
فاک-فاک ریگینکی کا رقبہ 11,036.48 مربع کیلومیٹر ہے اور اس کی مجموعی آبادی 77,112 افراد پر مشتمل ہے۔

مزید دیکھیے
انڈونیشیا
فہرست انڈونیشیا کے شہر

حوالہ جات

کامنز زمرہ جس کا ربط ویکی ڈیٹا پر ہے
Short description is different from Wikidata
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 187 · urdu-wikipedia:187326

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 251 chars, 44 words, 9 lines
- **script:** ratio 0.698 (arabic 0.698, latin 0.302)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=4
- **url:** https://ur.wikipedia.org/wiki/%D8%AC%D9%88%D8%B1%DA%A9

```text
جورک ایران کا ایک گاؤں جو Shesh Pir Rural District میں واقع ہے۔

تفصیلات
جورک کی مجموعی آبادی 254 افراد پر مشتمل ہے۔

مزید دیکھیے
ایران
فہرست ایران کے شہر

حوالہ جات

جغرافیہ شہرستان سپیدان کے نامکمل مضامین
Short description is different from Wikidata
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 188 · fineweb2-urd_Arab:<urn:uuid:db657d1e-42f9-4e4d-b3e5-9ff5559a1993>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 984 chars, 196 words, 21 lines
- **script:** ratio 0.594 (arabic 0.594, latin 0.406)
- **repetition:** dup_line 0.081, top-ngram 0.098, dup-ngram 0.079
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://www.rekhta.org/ghazals/jhapatte-hain-jhapatne-ke-liye-parvaaz-karte-hain-khalid-mahmood-ghazals?lang=ur

```text
جھپٹتے ہیں جھپٹنے کے لیے پرواز کرتے ہیں
جھپٹتے ہیں جھپٹنے کے لیے پرواز کرتے ہیں
کبوتر بھی وہی کرنے لگے جو باز کرتے ہیں
وہی قصے وہی باتیں کہ جو غماز کرتے ہیں
ترے ہم راز کرتے ہیں مرے دم ساز کرتے ہیں
بصد حیلے بہانے ظلم کا در باز کرتے ہیں
وہی جاں باز جن پر ہر گھڑی ہم ناز کرتے ہیں
زیادہ دیکھتے ہیں جب وہ آنکھیں پھیر لیتے ہیں
نظر میں رکھ رہے ہوں تو نظر انداز کرتے ہیں
ستایش گھر کے پنکھوں سے ہوا تو کم ہی آتی ہے
مگر چلتے ہیں جب ظالم بہت آواز کرتے ہیں
زمانے بھر کو اپنا راز داں کرنے کی ٹھہری ہے
تو بہتر ہے چلو اس شوخ کو ہم راز کرتے ہیں
ڈراتا ہے بہت انجام نمرودی مجھے خالدؔ
خدا لہجے میں جب بندے سخن آغاز کرتے ہیں
Additional information available
Click on the INTERESTING button to view additional information associated with this sher.
About this sher
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Morbi volutpat porttitor tortor, varius dignissim.
rare Unpublished content
This ghazal contains ashaar not published in the public domain. These are marked by a red line on the left.
```

**verdict:** keep
**note:** Urdu ghazal

---

### 189 · urdu-wikipedia:363420

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** code_switched
- **size:** 244 chars, 44 words, 7 lines
- **script:** ratio 1.000 (arabic 0.747, latin 0.253)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=3
- **url:** https://ur.wikipedia.org/wiki/%D9%81%D8%A7%DA%AF%D9%84%D8%A7%D9%88%DB%8C%DA%A9

```text
فاگلاویک ( سویڈش: Fåglavik) سویڈن کا ایک urban area of Sweden جو Herrljunga Municipality میں واقع ہے۔

تفصیلات
فاگلاویک کا رقبہ 0.57 مربع کیلومیٹر ہے اور اس کی مجموعی آبادی 209 افراد پر مشتمل ہے۔

مزید دیکھیے
سویڈن
فہرست سویڈن کے شہر

حوالہ جات
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 190 · urdu-wikipedia:1000712

- **filter:** REJECT — too_short
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 79 chars, 15 words, 3 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://ur.wikipedia.org/wiki/%D9%BE%D9%B9%DB%8C%D8%A7%D9%84%DB%81%20%DB%81%D8%A7%D8%A4%D8%B3

```text
پٹیالہ ہاؤس دہلی میں پٹیالہ کے مہاراجا کی سابق رہائش گاہ تھی۔

تاریخ

حوالہ جات
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 191 · urdu-wikipedia:920119

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 1431 chars, 268 words, 23 lines
- **script:** ratio 0.810 (arabic 0.810, latin 0.190)
- **repetition:** dup_line 0.000, top-ngram 0.046, dup-ngram 0.000
- **url** 0.035 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=18
- **url:** https://ur.wikipedia.org/wiki/%D8%A7%D9%82%D9%88%D8%A7%D9%85%20%D9%85%D8%AA%D8%AD%D8%AF%DB%81%20%D8%AA%D8%B1%D9%82%DB%8C%D8%A7%D8%AA%DB%8C%20%D9%BE%D8%B1%D9%88%DA%AF%D8%B1%D8%A7%D9%85

```text
اقوام متحدہ کا ترقیاتی پروگرام اقوام متحدہ کا عالمی ترقیاتی نیٹ ورک ہے۔ یہ تبدیلی کی حمایت کرتا ہے اور لوگوں کو اپنے لیے بہتر زندگی کی تعمیر میں مدد کے لیے علم، تجربے اور وسائل سے ممالک کو جوڑتا ہے۔ یہ ترقی پزیر ممالک کو ماہر مشورے، تربیت اور تعاون فراہم کرتا ہے، جس میں کم سے کم ترقی یافتہ ممالک کی امداد پر بڑھتی زور دیا جاتا ہے۔ اس سے اقوام عالم میں تکنیکی اور سرمایہ کاری کے تعاون کو فروغ ملتا ہے۔

عالمی سفیر

Antonio Banderas
کونی بریٹون
Didier Drogba
ہوکون، ولی عہد ناروے
Iker Casillas
Marta Vieira da Silva
Misako Konno
مشیل یؤ
Nikolaj Coster-Waldau
The Roca Brothers
Match Against Poverty: زین الدین یزید زیدان, رونالڈو

حوالہ جات

بیرونی روابط

جیکسن ، آر جی اے ، اقوام متحدہ کے ترقیاتی نظام کی صلاحیت کا ایک مطالعہ۔ 2 جلدیں ، جنیوا: اقوام متحدہ ، 1969۔
مٹچم ، چاڈ جے۔ 'اقوام متحدہ میں آسٹریلیائی اور ترقیاتی تعاون: غربت میں کمی کی طرف۔' آسٹریلیا اور اقوام متحدہ میں ، جیمز کاٹن اور ڈیوڈ لی نے ترمیم کیا ، 191-221۔ کینبرا: محکمہ برائے امور خارجہ اور تجارت اور سڈنی: لانگویویل کتابیں ، 2013۔
مچیم ، چاڈ جے ، جیکسن ، سر رابرٹ گل مین (1911-1991) ، آسٹریلیائی لغت کی سیرت ، نیشنل سینٹر آف سیرت ، آسٹریلیائی نیشنل یونیورسٹی ، http://adb.anu.edu.au/biography/jackson-sir-robert -گلمین -20715 / ٹیکسٹ31511 ، آن لائن 2016 شائع ، 5 ستمبر 2017 کو آن لائن تک رسائی حاصل کی۔
سرکاری یو این ڈی پی کی ویب سائٹ

اقتصادی ترقی
ریاستہائے متحدہ میں 1965ء کی تاسیسات
اقوام متحدہ کے ترقیاتی پروگرام
Short description is different from Wikidata
```

**verdict:** keep
**note:** 

---

### 192 · urdu-wikipedia:396870

- **filter:** REJECT — too_short, html_residue
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 96 chars, 16 words, 8 lines
- **script:** ratio 0.868 (arabic 0.868, latin 0.132)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.115 · **U+FFFD** 0.00000
- **stage 4:** whitespace=3
- **url:** https://ur.wikipedia.org/wiki/2063

```text
وفیات

دسمبر

<noinclude>

2060ء کی دہائی
2063ء
اکیسویں صدی
مستقبل کی دہائیاں
مستقبل کے خط زمانی
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 193 · urdu-wikipedia:780634

- **filter:** REJECT — repetition:top_2gram
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 4704 chars, 866 words, 202 lines *(excerpt shows first 1500)*
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.377, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=2, yeh=1
- **url:** https://ur.wikipedia.org/wiki/%D8%A7%D9%82%D9%88%D8%A7%D9%85%20%D9%85%D8%AA%D8%AD%D8%AF%DB%81%20%DA%A9%D9%86%D9%88%D9%86%D8%B4%D9%86%20%D8%A8%D8%B1%D8%A7%D8%A6%DB%92%20%D8%AD%D9%82%D9%88%D9%82%20%D8%A7%D8%B7%D9%81%D8%A7%D9%84

```text
اقوام متحدہ کا بچوں کے حقوق پر کنونشن کے 42 نکات ہیں جو تمام بچوں کے حقوق کے بارے میں بتاتے ہیں۔ یہ 1989ء میں تیار ہوا اور ناروے میں اس پر 1991 میں اس پر دستخط ہوئے تھے۔ اس قانون کا تعلّق بچوں اور 18 سال سے کم عمر کے نو عمروں سے ہے اوریہ والدین کے بچوں کے بارے میں فرائض اور بچوں کے والدین پر حقوق کے بارے میں تفصیلات موجود ہیں۔

افادیت
جارجیا یونیورسٹی میں قانون کے پروفیسر جوناتھن ٹوڈرز کا خاص مضمون نوجوانوں کے حقوق کے مسائل پر ہے جن کا اس کنونشن میں احاطہ کیا گیا ہے۔ وہ کہتے ہیں’’بچوں کے حقوق کا کنونشن بچوں کے انسانی حقوق کا سب سے زیادہ جامع معاہدہ ہے ۔ اب تک جتنے ملک انسانی حقوق کے معاہدے ہیں وہ سب اس کی توثیق کر چکے ہیں۔ ان کی تعداد کسی بھی معاہدے کے مقابلے میں زیادہ ہے۔درجنوں ملکوں میں اس معاہدے کی وجہ سے قوانین میں، پالیسیوں میں اور بچوں کے بارے میں لوگوں کی رویوں میں تبدیلیاں آئی ہیں۔ نتیجہ یہ ہے کہ ان ملکوں میں اب بچوں کے ساتھ خراب سلوک میں نمایاں کمی آئی ہے ۔‘‘

حوالہ جات

آذربائیجان کے معاہدے
آرمینیا کے معاہدے
آسٹریا کے معاہدے
آسٹریلیا کے معاہدے
آئرلینڈ کے معاہدے
آئس لینڈ کے معاہدے
آئل آف مین کے معاہدے
اتحاد القمری کے معاہدے
ارتریا کے معاہدے
ارجنٹائن کے معاہدے
اردن کے معاہدے
اروبا کے معاہدے
ازبکستان کے معاہدے
استوائی گنی کے معاہدے
استونیا کے معاہدے
اسرائیل کے معاہدے
البانیہ کے معاہدے
الجزائر کے معاہدے
انڈورہ کے معاہدے
انڈونیشیا کے معاہدے
ایران کے معاہدے
ایکواڈور کے معاہدے
ایل سیلواڈور کے معاہدے
اینٹیگوا و باربوڈا کے معاہدے
اطالیہ کے معاہدے
بارباڈوس کے معاہدے
بحرین کے معاہدے
برازیل کے معاہدے
برکینا فاسو کے معاہدے
برمودا کے معاہدے
برونائی کے معاہدے
برونڈی کے معاہدے
بلغا
```

**verdict:** keep
**note:** UN Convention on the Rights of the Child article — the repeated bigram is the topic

---

### 194 · fineweb2-urd_Arab:<urn:uuid:d1cdd237-0df5-4311-85f1-ce1f0ccfcb6d>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 3339 chars, 685 words, 32 lines *(excerpt shows first 1500)*
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.018, dup-ngram 0.023
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://www.express.pk/story/2254880/

```text
- پشاور میں آپریشن کے دوران پولیس اہلکار شہید، اشتہاری ملزم بھی ہلاک
- خطرناک عمران خان
- تعلیمی ادارے کھلنے پر طالبعلم کا اسکول کے دروازے پر سجدہ شکر، ویڈیو وائرل
- نیب کارروائی میں سابق میونسپل کمشنر کراچی سمیت 3 افسران گرفتار، سونے کی اینٹیں برآمد
- آسٹریلیا کے ساتھ ٹیسٹ میچز ایک ہی وینیو پرکرانا ممکن نہیں ،پی سی بی
- پاکستان میں کرپشن میں مزید اضافہ ہوگیا، ٹرانسپیرنسی انٹرنیشنل
- عالمی ادارے کی رپورٹ فردجرم ہےکرپٹ حکمران استعفیٰ دیں ، شہبازشریف
- ثانیہ مرزا آسٹریلین اوپن میں کیریئر کا آخری میچ ہار گئیں
- لاہور میں 55 سے زائد وارداتوں میں ملوث مدثر عرف بچھو ہلاک
- دنیا کی سب سے طاقتور دوربین اپنے مدار میں پہنچ گئی
- برکینافاسو میں فوج نے اقتدارپرقبضہ کرلیا
- امریکی جنگی طیارے کوبحری بیڑے پرلینڈنگ کے وقت حادثے کا سامنا،7 اہلکار زخمی
- ٹیسٹ میچزایک ہی شہرمیں ہوں تومناسب ہوگا، کرکٹ آسٹریلیا
- آپ کا پروفائل کس نے دیکھا ہے؛ ٹک ٹاک جلد ہی یہ بھی بتائے گا
- زخمی خاتون کا ایکسرے بطور این ایف ٹی بیچنے کی کوشش ناکام
- شاخ گوبھی میں سرطان کے خلاف نہایت مؤثر کیمیکل دریافت
- یوکرین پرکشیدگی، امریکی فوجیوں کوہائی الرٹ کردیا گیا
- ہیٹی میں 5.3شدت کا زلزلہ،2 افراد ہلاک
- کورونا وباء نے مزید 17 افراد کی زندگیوں کو نگل لیا ؛ 6357 نئے کیسز رپورٹ
- ای سی سی، تمباکو کی کم سے کم قیمت کی منظوری
اسٹاک ہوم: سویڈن میں کیے گئے ایک تفصیلی مطالعے میں دل کی تیز دھڑکنوں اور دماغی بیماریوں کے درمیان واضح اور مضبوط تعلق سامنے آیا ہے۔ تاہم ماہرین کا کہنا ہے کہ فی الحال دھڑکنوں کی تیز رفتار کو دماغی امراض کی وجہ قرار نہیں دیا جاسکتا۔
کیرولنسکا انسٹی ٹیوٹ کی ڈاکٹر یومی ایماہوری کی قیادت میں یہ مطالعہ 60 سال 
```

**verdict:** keep
**note:** 

---

### 195 · urdu-wikipedia:122214

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 418 chars, 80 words, 9 lines
- **script:** ratio 0.928 (arabic 0.928, latin 0.072)
- **repetition:** dup_line 0.000, top-ngram 0.038, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=8
- **url:** https://ur.wikipedia.org/wiki/%D8%A7%D9%84%D8%A7%D8%B3%DA%A9%D8%A7%20%D8%A7%DB%8C%D8%A6%D8%B1%20%DA%AF%D8%B1%D9%88%D9%BE

```text
، نامی یہ کمپنی 2012 میں فارچون میگزین کی سرفہرست 1000 کمپنیوں میں شامل تھی۔ اس کا ہیڈکوارٹر Tukwila، میں واقع ہے۔ فارچون کی رپورٹ کے مطابق 2012 میں اس میں سی ای او (CEO) کے عہدے پر William S. Ayer کام کر رہے تھے۔

مزید دیکھیے
کمپنیوں کی فہرست

حوالہ جات

بیرونی روابط

1985ء میں قائم ہونے والی امریکی کمپنیاں
ریاست واشنگٹن میں 1985ء کی تاسیسات
سی ایٹل، واشنگٹن میں واقع کمپنیاں
نیو یارک اسٹاک ایکسچینج میں درج کمپنیاں
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 196 · fineweb2-urd_Arab:<urn:uuid:4e669a4a-9d2a-402f-a106-ef89a23584ad>

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 2365 chars, 503 words, 26 lines *(excerpt shows first 1500)*
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.038, dup-ngram 0.026
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** https://www.express.pk/story/1245621/24/

```text
- مفتاح اسماعیل کے دور میں اضافی پیٹرولیم لیوی وصول کرنے کا انکشاف
- پی ٹی آئی لانگ مارچ کو اسلام آباد میں داخل نہیں ہونے دیا جائے گا، وزیر داخلہ
- آڈیو لیکس کے بعد عمران خان دنیا کا سب سے بڑا جھوٹا شخص ثابت ہوگیا، وزیراعظم
- لاہور کے پوش علاقے میں چوری کی بڑی واردات
- حب میں گھر پر دستی بم حملہ، 6 زخمی
- حکومت اگلے ہفتے تاریخی کسان پیکج کا اعلان کرے گی، وزیراعظم
- کراچی میں کم سن طالبہ کے ساتھ مبینہ زیادتی کی کوشش پر اسکول پرنسپل گرفتار
- آصف زرداری کی علالت، علاج کیلیے بیرونِ ملک فوری منتقلی کا امکان مسترد
- شیر خوار بچوں سے زیادہ ذہین طوطے
- جسم کے صحت مند خلیے کینسر کے پھیلاؤ میں کیسے مدد کرتے ہیں؟
- فزکس کا نوبل انعام امریکا، فرانس اور آسٹریا کے سائنس دانوں کے نام
- بجلی کا طویل بریک ڈاؤن؛ بنگلادیش تاریکی میں ڈوب گیا
- کراچی سمیت سندھ بھر میں موٹرسائیکل کی ڈبل سواری پر پابندی عائد
- خاتون کی خودکشی پر بے حسی دکھانے والی ایف آئی اے افسر معطل
- ہمالیہ میں برف کا تودہ گرنے سے 2 کوہ پیما ہلاک؛19 لاپتہ
- ٹانگ کی سرجری کے بعد جونی بیرسٹو کا رواں سال کرکٹ نہ کھیلنے کا اعلان
- پی ٹی آئی نے آزادی مارچ کی کامیابی کیلیے کارکنان سے حلف لے لیا
- گرل فرینڈ کو ہاسٹل بلاکر ڈاکٹرز نے اجتماعی زیادتی کا نشانہ بنا ڈالا
- کسانوں اور حکومت کے درمیان مذاکرات کامیاب، اسلام آباد دھرنا ختم
- پشاور میں پاک فوج کے قافلے پر دہشت گردوں کے حملہ میں 2 جوان شہید
لندن: عرفان خان کی ٹوئٹر پر ہنستی مسکراتی تصویر نے اداکار کی خراب صحت سے متعلق تمام قیاس آرائیوں کا خاتمہ کردیا۔
چند ماہ قبل بھارتی اداکار عرفان خان نے اس بات کا انکشاف کیا کہ وہ جان لیوا بیماری میں مبتلا ہوگئے ہیں، عرفان خان کے مطابق انہیں نیور
```

**verdict:** keep
**note:** 

---

### 197 · urdu-wikipedia:121691

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 375 chars, 59 words, 17 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.112, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=4
- **url:** https://ur.wikipedia.org/wiki/%D8%A7%DB%8C%D9%84%D8%A7%D8%B1%20%D9%84%D8%A7%D8%A6%DB%8C

```text
ایلار لائی ایک فحش اداکارہ ہے۔

مزید دیکھیے
فہرست فحش اداکارائیں

حوالہ جات

1984ء کی پیدائشیں
اکیسویں صدی کی نارویجن گلوکارائیں
ایرانی خواتین ماڈل
ایرانی فحش اداکارائیں
ایرانی گلوکارائیں
بقید حیات شخصیات
تہران کی شخصیات
نارویجن پاپ گلوکار
نارویجن خواتین ماڈل
نارویجن گلوکارائیں
نارویجین فحش اداکارائیں
ویکی ڈیٹا سے مطابقت رکھنے والی مختصر تفصیل
اکیسویں صدی کے نارویجن گلوکار
```

**verdict:** drop
**note:** template stub, 375 chars of one sentence plus categories

---

### 198 · urdu-wikipedia:363641

- **filter:** ACCEPT — —
- **stratum:** uniform · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 415 chars, 73 words, 10 lines
- **script:** ratio 0.877 (arabic 0.877, latin 0.123)
- **repetition:** dup_line 0.000, top-ngram 0.108, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=4
- **url:** https://ur.wikipedia.org/wiki/%D9%81%DB%8C%D8%A6%D8%B1%D9%85%DB%8C%D8%A7%DA%88%DB%8C%D8%8C%20%DA%A9%DB%8C%D9%86%D9%B9%DA%A9%DB%8C

```text
فیئرمیاڈی، کینٹکی ریاستہائے متحدہ امریکا کا ایک شہر جو جیفرسن کاؤنٹی میں واقع ہے۔

تفصیلات
فیئرمیاڈی، کینٹکی کا رقبہ 0.2 مربع کیلومیٹر ہے اور اس کی مجموعی آبادی 264 افراد پر مشتمل ہے اور 160 میٹر سطح سمندر سے بلندی پر واقع ہے۔

مزید دیکھیے
ریاستہائے متحدہ امریکا
فہرست ریاستہائے متحدہ امریکہ کے شہر

حوالہ جات

کینٹکی میں 1953ء کی تاسیسات
1953ء میں آباد ہونے والے مقامات
Short description is different from Wikidata
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 199 · fineweb2-urd_Arab:<urn:uuid:904ff23c-4339-4ba8-acd3-7522b6790825>

- **filter:** REJECT — script_ratio
- **stratum:** rejected · **source:** fineweb2-urd_Arab · **stage-3 label:** urdu
- **size:** 419 chars, 77 words, 6 lines
- **script:** ratio 0.697 (arabic 0.697, latin 0.303)
- **repetition:** dup_line 0.000, top-ngram 0.000, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** no change
- **url:** http://express.com.pk/epaper/thumbnails.aspx?Issue=NP_LHE&Page=Commerce_PageBW&Date=20120328&Pageno=6

```text
ایشین گیمز؛ ہاکی میچ میں پاکستان نے چین کو 2 گول سے ہرا دیا
سری لنکا کیخلاف کامیابی حوصلہ افزا ہے، ہاکی کپتان
گوانگژو ٹینس میں مونیکا نیکو لسیکو نے ٹرافی حاصل کرلی
شمالی کوریا کے ویٹ لفٹر اوم یون چول نے اپنا ہی عالمی ریکارڈ توڑ دیا
قومی ٹی ٹوئنٹی کرکٹ، کراچی زیبراز نے سپر اوور میں ہتھیار ڈال دیے
Copyright © Century Publications. This material may not be published, broadcast, rewritten, redistributed or derived from.
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---

### 200 · urdu-wikipedia:1089344

- **filter:** REJECT — too_short, repetition:top_4gram
- **stratum:** rejected · **source:** urdu-wikipedia · **stage-3 label:** urdu
- **size:** 146 chars, 31 words, 4 lines
- **script:** ratio 1.000 (arabic 1.000, latin 0.000)
- **repetition:** dup_line 0.000, top-ngram 0.260, dup-ngram 0.000
- **url** 0.000 · **html** 0.000 · **U+FFFD** 0.00000
- **stage 4:** whitespace=3
- **url:** https://ur.wikipedia.org/wiki/%D8%A8%D8%B1%D9%84%D9%86%D8%8C%20%D9%85%D8%B4%DB%8C%20%DA%AF%D9%86

```text
برلن، مشی گن کے حسب ذیل مدلولات ہو سکتے ہیں:
برلن ٹاؤن شپ، آئونیا کاؤنٹی، مشی گن
برلن ٹاؤن شپ، سینٹ کلیر کاؤنٹی، مشی گن
برلن چارٹر ٹاؤن شپ، مشی گن
```

**verdict:** drop
**note:** template stub: one factual sentence plus section headers and category footers

---
