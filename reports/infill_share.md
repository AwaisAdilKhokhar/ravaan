# §8.3's infill row — exact-match and token-F1

`scripts/infill_eval.py` over `data/packed-urdu` (`validation` split), 64 sequences a span, greedy decode.

Scored under preregistration §8's rule: **the AR arm's generation is cut to the gold span's token length.** `exact (raw)` is the same metric with the rule switched off and is a diagnostic, not the endpoint — see `ravaan/evaluation/infill.py`.

| checkpoint | infill share | decoder | span | exact | token-F1 | exact (raw) | cut | mean generated |
|---|---|---|---|---|---|---|---|---|
| `urdu-ar/ar-s0_f1 · infill 10%` | 10% | left-to-right | 1 | 0.000 | 0.000 | 0.000 | 100% | 19.2 |
| `urdu-ar/ar-s0_f1 · infill 10%` | 10% | left-to-right | 2 | 0.000 | 0.055 | 0.000 | 100% | 23.3 |
| `urdu-ar/ar-s0_f1 · infill 10%` | 10% | left-to-right | 4 | 0.000 | 0.059 | 0.000 | 100% | 30.4 |
| `urdu-ar/ar-s0_f1 · infill 10%` | 10% | left-to-right | 8 | 0.000 | 0.112 | 0.000 | 98% | 37.2 |
| `urdu-ar/ar-s0_f1 · infill 10%` | 10% | left-to-right | 16 | 0.000 | 0.148 | 0.000 | 95% | 45.3 |
| `urdu-ar/ar-s0_f1 · infill 10%` | 10% | left-to-right | 32 | 0.000 | 0.150 | 0.000 | 92% | 60.0 |
| `urdu-ar/ar-s0_f1 · infill 10%` | 10% | left-to-right | 64 | 0.000 | 0.152 | 0.000 | 89% | 87.7 |
| `urdu-ar-fim50/ar-s0_f1 · infill 50%` | 50% | left-to-right | 1 | 0.031 | 0.031 | 0.000 | 100% | 19.5 |
| `urdu-ar-fim50/ar-s0_f1 · infill 50%` | 50% | left-to-right | 2 | 0.000 | 0.016 | 0.000 | 100% | 23.8 |
| `urdu-ar-fim50/ar-s0_f1 · infill 50%` | 50% | left-to-right | 4 | 0.000 | 0.098 | 0.000 | 98% | 29.9 |
| `urdu-ar-fim50/ar-s0_f1 · infill 50%` | 50% | left-to-right | 8 | 0.000 | 0.102 | 0.000 | 97% | 37.3 |
| `urdu-ar-fim50/ar-s0_f1 · infill 50%` | 50% | left-to-right | 16 | 0.000 | 0.174 | 0.000 | 95% | 46.1 |
| `urdu-ar-fim50/ar-s0_f1 · infill 50%` | 50% | left-to-right | 32 | 0.000 | 0.174 | 0.000 | 89% | 58.2 |
| `urdu-ar-fim50/ar-s0_f1 · infill 50%` | 50% | left-to-right | 64 | 0.000 | 0.174 | 0.000 | 88% | 86.2 |
| `urdu-diff/diff-s0_f1 · infill 10%` | 10% | confidence | 1 | 0.516 | 0.516 | 0.516 | 0% | 1.0 |
| `urdu-diff/diff-s0_f1 · infill 10%` | 10% | confidence | 2 | 0.234 | 0.359 | 0.234 | 0% | 2.0 |
| `urdu-diff/diff-s0_f1 · infill 10%` | 10% | confidence | 4 | 0.078 | 0.301 | 0.078 | 0% | 4.0 |
| `urdu-diff/diff-s0_f1 · infill 10%` | 10% | confidence | 8 | 0.000 | 0.184 | 0.000 | 0% | 8.0 |
| `urdu-diff/diff-s0_f1 · infill 10%` | 10% | confidence | 16 | 0.000 | 0.219 | 0.000 | 0% | 16.0 |
| `urdu-diff/diff-s0_f1 · infill 10%` | 10% | confidence | 32 | 0.000 | 0.189 | 0.000 | 0% | 32.0 |
| `urdu-diff/diff-s0_f1 · infill 10%` | 10% | confidence | 64 | 0.000 | 0.172 | 0.000 | 0% | 64.0 |
| `urdu-diff/diff-s0_f1 · infill 10%` | 10% | gumbel 2 | 1 | 0.516 | 0.516 | 0.516 | 0% | 1.0 |
| `urdu-diff/diff-s0_f1 · infill 10%` | 10% | gumbel 2 | 2 | 0.219 | 0.336 | 0.219 | 0% | 2.0 |
| `urdu-diff/diff-s0_f1 · infill 10%` | 10% | gumbel 2 | 4 | 0.062 | 0.305 | 0.062 | 0% | 4.0 |
| `urdu-diff/diff-s0_f1 · infill 10%` | 10% | gumbel 2 | 8 | 0.000 | 0.189 | 0.000 | 0% | 8.0 |
| `urdu-diff/diff-s0_f1 · infill 10%` | 10% | gumbel 2 | 16 | 0.000 | 0.202 | 0.000 | 0% | 16.0 |
| `urdu-diff/diff-s0_f1 · infill 10%` | 10% | gumbel 2 | 32 | 0.000 | 0.200 | 0.000 | 0% | 32.0 |
| `urdu-diff/diff-s0_f1 · infill 10%` | 10% | gumbel 2 | 64 | 0.000 | 0.195 | 0.000 | 0% | 64.0 |

## Locked-span preservation (§8.1, reported per §8.3)

Every row: 1.000.

## What the misses look like

**`urdu-ar/ar-s0_f1 · infill 10%` · left-to-right · span 1** (F1 0.000, wrote 20 tokens)

- gold: تو
- generated: کے

**`urdu-ar/ar-s0_f1 · infill 10%` · left-to-right · span 2** (F1 0.000, wrote 24 tokens)

- gold: پرنس
- generated: کے لیے

**`urdu-ar/ar-s0_f1 · infill 10%` · left-to-right · span 4** (F1 0.000, wrote 32 tokens)

- gold: پہنچ چکے تھے۔ انہوں
- generated: کے بعد پرنس

**`urdu-ar/ar-s0_f1 · infill 10%` · left-to-right · span 8** (F1 0.250, wrote 40 tokens)

- gold: 10بار پرنس 50 تک پہنچ چکے
- generated: کے بعد پرنس کو دوبارہ منتخب کیا

**`urdu-ar/ar-s0_f1 · infill 10%` · left-to-right · span 16** (F1 0.062, wrote 48 tokens)

- gold: کو جنوری میں ٹیسٹ سائیڈ سے ڈراپ کر دیا گیا تھا لیکن وہ پھر بھی ٹیم
- generated: کے لیے ایک میچ میں ایک وکٹ حاصل کی۔ پرنس نے اپنے پہلے میچ میں

**`urdu-ar/ar-s0_f1 · infill 10%` · left-to-right · span 32** (F1 0.219, wrote 64 tokens)

- gold: کے دوسرے ڈویژن میں چھوڑ دیا گیا۔ پرنس کاؤنٹی کے سب سے زیادہ رنز بنانے والے کھلاڑی تھے اور اس سال 1,000 سے زیادہ رنز بنانے والے لنکاشائر
- generated: پرنس کو دوبارہ منتخب کیا گیا اور اس نے اپنے پہلے میچ میں بھی اپنی پہلی سنچری بنائی۔  حوالہ جات  کرکٹ عالمی کپ 2011 کے کھلاڑی کرکٹ عالمی

**`urdu-ar/ar-s0_f1 · infill 10%` · left-to-right · span 64** (F1 0.256, wrote 61 tokens)

- gold: جنوبی افریقہ نے فروری 2012ء میں اپنے سینٹرل کنٹریکٹس کا اعلان کیا تو پرنس کو اس فہرست میں شامل کیا گیا اور سلیکٹرز کے کنوینر نے کہا کہ اگرچہ پرنس کو جنوری میں ٹیسٹ سائیڈ سے ڈراپ کر دیا گیا تھا لیکن وہ پھر بھی ٹیم کے پلان کا حصہ رہے۔  ریٹائرمنٹ تک کی قیادت (
- generated: کے لیے ایک روزہ بین الاقوامی کرکٹ میں ڈیبیو کیا۔ انہوں نے اپنا فرسٹ کلاس ڈیبیو 19 جنوری 2013ء کو کیا، اس کے بعد سے وہ ایک روزہ بین الاقوامی کرکٹ میں واپس آئے ہیں۔  حوالہ جات  جنوبی افریقا کے کرکٹ کھلاڑی جنوبی افریقا کے ٹیسٹ کرکٹ کھلاڑی بقید حیات شخصیات 1995ء کی پیدائشیں

**`urdu-ar-fim50/ar-s0_f1 · infill 50%` · left-to-right · span 1** (F1 0.000, wrote 20 tokens)

- gold: تو
- generated: کے

**`urdu-ar-fim50/ar-s0_f1 · infill 50%` · left-to-right · span 2** (F1 0.000, wrote 24 tokens)

- gold: پرنس
- generated: نے اپنی

**`urdu-ar-fim50/ar-s0_f1 · infill 50%` · left-to-right · span 4** (F1 0.000, wrote 32 tokens)

- gold: پہنچ چکے تھے۔ انہوں
- generated: کے لیے ایک سنچری

**`urdu-ar-fim50/ar-s0_f1 · infill 50%` · left-to-right · span 8** (F1 0.250, wrote 40 tokens)

- gold: 10بار پرنس 50 تک پہنچ چکے
- generated: کے لیے ایک سنچری بنائی۔ پرنس

**`urdu-ar-fim50/ar-s0_f1 · infill 50%` · left-to-right · span 16** (F1 0.125, wrote 48 tokens)

- gold: کو جنوری میں ٹیسٹ سائیڈ سے ڈراپ کر دیا گیا تھا لیکن وہ پھر بھی ٹیم
- generated: کے لیے ایک سال کے لیے منتخب کیا گیا تھا اور اس نے اپنے کیریئر کا

**`urdu-ar-fim50/ar-s0_f1 · infill 50%` · left-to-right · span 32** (F1 0.125, wrote 38 tokens)

- gold: کے دوسرے ڈویژن میں چھوڑ دیا گیا۔ پرنس کاؤنٹی کے سب سے زیادہ رنز بنانے والے کھلاڑی تھے اور اس سال 1,000 سے زیادہ رنز بنانے والے لنکاشائر
- generated: کے لیے ایک میچ میں 10 وکٹیں حاصل کیں۔  حوالہ جات  جنوبی افریقا کے کرکٹ کھلاڑی جنوبی افریقا کے ٹیسٹ کرکٹ کھلاڑی جنوبی افریقا کے کرکٹ کھلاڑی بقید حیات شخصیات

**`urdu-ar-fim50/ar-s0_f1 · infill 50%` · left-to-right · span 64** (F1 0.281, wrote 96 tokens)

- gold: جنوبی افریقہ نے فروری 2012ء میں اپنے سینٹرل کنٹریکٹس کا اعلان کیا تو پرنس کو اس فہرست میں شامل کیا گیا اور سلیکٹرز کے کنوینر نے کہا کہ اگرچہ پرنس کو جنوری میں ٹیسٹ سائیڈ سے ڈراپ کر دیا گیا تھا لیکن وہ پھر بھی ٹیم کے پلان کا حصہ رہے۔  ریٹائرمنٹ تک کی قیادت (
- generated: کے لیے ایک روزہ بین الاقوامی کرکٹ میں ڈیبیو کیا گیا تھا، اور اس نے اپنے پہلے میچ میں جنوبی افریقہ کے خلاف جنوبی افریقہ کے لیے اپنا ایک روزہ ڈیبیو کیا تھا۔ پرنس نے اپنے پہلے ایک روزہ میں جنوبی افریقہ کے لیے اپنا ایک روزہ ڈیبیو کیا، اور اس نے اپنے پہلے ایک روزہ میں جنوبی افریقہ کے لیے

**`urdu-diff/diff-s0_f1 · infill 10%` · confidence · span 1** (F1 0.000, wrote 1 tokens)

- gold: تو
- generated: اور

**`urdu-diff/diff-s0_f1 · infill 10%` · confidence · span 2** (F1 0.000, wrote 2 tokens)

- gold: تک رہا۔
- generated: بعد اپنی

**`urdu-diff/diff-s0_f1 · infill 10%` · confidence · span 4** (F1 0.000, wrote 4 tokens)

- gold: پہنچ چکے تھے۔ انہوں
- generated: بنا سکے۔ پرنس

**`urdu-diff/diff-s0_f1 · infill 10%` · confidence · span 8** (F1 0.000, wrote 8 tokens)

- gold: 10بار پرنس 50 تک پہنچ چکے
- generated: اننگز میں ویسٹ انڈیز کی ٹیم میں شامل

**`urdu-diff/diff-s0_f1 · infill 10%` · confidence · span 16** (F1 0.250, wrote 16 tokens)

- gold: کو جنوری میں ٹیسٹ سائیڈ سے ڈراپ کر دیا گیا تھا لیکن وہ پھر بھی ٹیم
- generated: کاؤنٹی کے خلاف جنوبی افریقہ کے اسکواڈ میں شامل کیا گیا تھا اور وہ 2012ء

**`urdu-diff/diff-s0_f1 · infill 10%` · confidence · span 32** (F1 0.125, wrote 32 tokens)

- gold: کے دوسرے ڈویژن میں چھوڑ دیا گیا۔ پرنس کاؤنٹی کے سب سے زیادہ رنز بنانے والے کھلاڑی تھے اور اس سال 1,000 سے زیادہ رنز بنانے والے لنکاشائر
- generated: میں آسٹریلیا کی ٹیسٹ سیریز کے لیے جنوبی افریقہ کی قومی ٹیم کے اسکواڈ میں شامل کیا گیا تھا۔ وہ 2013ء اور 2013ء میں جنوبی افریقہ کی قومی کرکٹ ٹیم

**`urdu-diff/diff-s0_f1 · infill 10%` · confidence · span 64** (F1 0.344, wrote 64 tokens)

- gold: جنوبی افریقہ نے فروری 2012ء میں اپنے سینٹرل کنٹریکٹس کا اعلان کیا تو پرنس کو اس فہرست میں شامل کیا گیا اور سلیکٹرز کے کنوینر نے کہا کہ اگرچہ پرنس کو جنوری میں ٹیسٹ سائیڈ سے ڈراپ کر دیا گیا تھا لیکن وہ پھر بھی ٹیم کے پلان کا حصہ رہے۔  ریٹائرمنٹ تک کی قیادت (
- generated: ٹیم نے 2012ء میں جنوبی افریقہ کے خلاف پہلے میچ میں جنوبی افریقہ کے خلاف پہلے میچ میں جنوبی افریقہ کے خلاف انگلینڈ کے خلاف سیریز میں شامل کیا تھا۔  ٹیسٹ کیریئر پرنس کو 2012ء اور 2012ء میں جنوبی افریقہ کے خلاف انگلینڈ کے خلاف انگلینڈ کے خلاف انگلینڈ کے خلاف انگلینڈ کے خلاف اپنا ڈیبیو پرنس (

**`urdu-diff/diff-s0_f1 · infill 10%` · gumbel · span 1** (F1 0.000, wrote 1 tokens)

- gold: تو
- generated: اور

**`urdu-diff/diff-s0_f1 · infill 10%` · gumbel · span 2** (F1 0.000, wrote 2 tokens)

- gold: تک رہا۔
- generated: بعد اپنی

**`urdu-diff/diff-s0_f1 · infill 10%` · gumbel · span 4** (F1 0.000, wrote 4 tokens)

- gold: پہنچ چکے تھے۔ انہوں
- generated: بنا سکے۔ پرنس

**`urdu-diff/diff-s0_f1 · infill 10%` · gumbel · span 8** (F1 0.000, wrote 8 tokens)

- gold: 10بار پرنس 50 تک پہنچ چکے
- generated: اننگز میں ٹیسٹ ٹیم کے کپتان بن گئے

**`urdu-diff/diff-s0_f1 · infill 10%` · gumbel · span 16** (F1 0.188, wrote 16 tokens)

- gold: کو جنوری میں ٹیسٹ سائیڈ سے ڈراپ کر دیا گیا تھا لیکن وہ پھر بھی ٹیم
- generated: کاؤنٹی کے خلاف 2012ء میں انگلینڈ کے خلاف کاؤنٹی ٹیسٹ سیریز کے لیے کاؤنٹی ٹیم

**`urdu-diff/diff-s0_f1 · infill 10%` · gumbel · span 32** (F1 0.188, wrote 32 tokens)

- gold: کے دوسرے ڈویژن میں چھوڑ دیا گیا۔ پرنس کاؤنٹی کے سب سے زیادہ رنز بنانے والے کھلاڑی تھے اور اس سال 1,000 سے زیادہ رنز بنانے والے لنکاشائر
- generated: کے لیے ویسٹ انڈیز کے اسکواڈ میں شامل ہونے کے لیے اسکواڈ میں منتخب کیا گیا تھا۔ مارچ 2013ء میں لنکا لنکاشائر کے دورے کے مقابلے میں ویسٹ انڈیز

**`urdu-diff/diff-s0_f1 · infill 10%` · gumbel · span 64** (F1 0.219, wrote 64 tokens)

- gold: جنوبی افریقہ نے فروری 2012ء میں اپنے سینٹرل کنٹریکٹس کا اعلان کیا تو پرنس کو اس فہرست میں شامل کیا گیا اور سلیکٹرز کے کنوینر نے کہا کہ اگرچہ پرنس کو جنوری میں ٹیسٹ سائیڈ سے ڈراپ کر دیا گیا تھا لیکن وہ پھر بھی ٹیم کے پلان کا حصہ رہے۔  ریٹائرمنٹ تک کی قیادت (
- generated: ٹیم نے 2012ء--13ء کے سیزن میں جنوبی افریقہ کے خلاف سیریز بنائی۔ نومبر 2012ء کے درمیان آسٹریلیا کے خلاف جنوبی افریقہ کے خلاف جنوبی افریقہ کے خلاف سیریز اور 2012ء کے آخر میں آسٹریلیا کے خلاف سیریز کا آغاز کیا۔ 2012ء کے سیزن میں آسٹریلیا کے خلاف سیریز میں سری لنکا کے خلاف سیریز (

