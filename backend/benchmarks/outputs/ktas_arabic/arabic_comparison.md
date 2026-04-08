# KTAS Arabic vs English — Parity Benchmark

**Date:** 20260408T220311Z
**Cases:** 1262
**Translation:** Gemini CLI (Egyptian colloquial Arabic)

## Head-to-Head

| Metric | Arabic | English | Delta |
|--------|--------|---------|-------|
| Exact match | 39.9% | 36.8% | +3.1% |
| Within-one | 82.6% | 81.5% | +1.1% |
| Under-triage | 13.1% | 9.1% | +4.0% |
| Over-triage | 47.1% | 54.1% | -7.1% |
| Critical under-triage | 3.6% | 1.3% | +2.2% |

## Parity Differences (381 cases)

| Row | Arabic Complaint | English | Actual | AR ESI | EN ESI | AR✓ | EN✓ |
|-----|-----------------|---------|--------|--------|--------|-----|-----|
| 8 | مع وجع أو ضيقة في الصدر | With chest discomfort | 3 | 4 | 2 | ✗ | ✗ |
| 11 | إكزيما في جفن العين | Eczema, Eyelid | 5 | 4 | 3 | ✗ | ✗ |
| 15 | وجع في البطن | abd pain | 4 | 3 | 4 | ✗ | ✓ |
| 21 | لثتي ورمة | Gingival swelling | 4 | 4 | 3 | ✓ | ✗ |
| 23 | صباعي اتعور/اتخبط | Finger Injury | 4 | 4 | 3 | ✓ | ✗ |
| 25 | ضعف حركي في الجنب اليمين | Rt. side motor weakness | 3 | 3 | 2 | ✓ | ✗ |
| 30 | وجع في دراعي | pain, arm | 4 | 3 | 4 | ✗ | ✓ |
| 35 | أغمى عليا | syncope | 3 | 3 | 2 | ✓ | ✗ |
| 37 | دم نازل مع البراز | hematochezia | 3 | 3 | 2 | ✓ | ✗ |
| 39 | أغمى عليا | syncope | 4 | 3 | 2 | ✗ | ✗ |
| 48 | نهجان / كرشة نفس | dyspnea | 3 | 3 | 2 | ✓ | ✗ |
| 49 | مش دريان باللي حواليه | mental change | 2 | 1 | 2 | ✗ | ✓ |
| 64 | ترجيع | vomiting | 3 | 3 | 2 | ✓ | ✗ |
| 68 | وجع في الربع التحتاني اليمين م | right lower quadrant abdo | 3 | 4 | 3 | ✗ | ✓ |
| 69 | تقل في جنبي اليمين | right hemiparesis | 2 | 3 | 2 | ✗ | ✓ |
| 71 | ورم في الرسغ الشمال | left wrist swelling | 4 | 4 | 3 | ✓ | ✗ |
| 73 | وجع في البطن | abd pain | 3 | 3 | 4 | ✓ | ✗ |
| 76 | وجع في فم المعدة | epigastric pain | 3 | 4 | 3 | ✗ | ✓ |
| 83 | وجع أعلى البطن | upper abdominal pain | 3 | 4 | 3 | ✗ | ✓ |
| 84 | ورم في الخد | Edema, Cheek | 4 | 4 | 3 | ✓ | ✗ |
| 86 | وجع في فم المعدة | epigastric pain | 3 | 4 | 3 | ✗ | ✓ |
| 87 | وجع في فم المعدة | epigastric pain | 3 | 4 | 3 | ✗ | ✓ |
| 89 | وجع في أسفل الظهر | pain, low back | 3 | 4 | 2 | ✗ | ✗ |
| 93 | وجع في ظهري | pain, back | 3 | 4 | 3 | ✗ | ✓ |
| 96 | وجع أعلى البطن يمين | right upper abdominal pai | 3 | 4 | 3 | ✗ | ✓ |
| 97 | بطني كلها بتوجعني | Generalized abdominal pai | 3 | 4 | 3 | ✗ | ✓ |
| 99 | وجع في البطن | abd pain | 3 | 3 | 4 | ✓ | ✗ |
| 102 | وجع حاد في فم المعدة | acute epigastric pain | 3 | 4 | 3 | ✗ | ✓ |
| 104 | خبطة في الكوع | Elbow Injury | 3 | 4 | 3 | ✗ | ✓ |
| 106 | وجع في الجنب اليمين (الخاصرة) | Rt. flank pain | 3 | 4 | 3 | ✗ | ✓ |
