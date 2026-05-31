# KTAS Arabic vs English — Parity Benchmark

**Date:** 20260408T223414Z
**Cases:** 1262
**Translation:** Gemini CLI (Egyptian colloquial Arabic)

## Head-to-Head

| Metric | Arabic | English | Delta |
|--------|--------|---------|-------|
| Exact match | 459/1262 = 36.4% (95% Wilson CI 33.8% to 39.1%) | 477/1262 = 37.8% (95% Wilson CI 35.2% to 40.5%) | -1.4% |
| Within-one | 1037/1262 = 82.2% (95% Wilson CI 80.0% to 84.2%) | 1030/1262 = 81.6% (95% Wilson CI 79.4% to 83.7%) | +0.6% |
| Under-triage | 132/1262 = 10.5% (95% Wilson CI 8.9% to 12.3%) | 77/1262 = 6.1% (95% Wilson CI 4.9% to 7.6%) | +4.4% |
| Over-triage | 671/1262 = 53.2% (95% Wilson CI 50.4% to 55.9%) | 708/1262 = 56.1% (95% Wilson CI 53.3% to 58.8%) | -2.9% |
| Critical under-triage | 13/1262 = 1.0% (95% Wilson CI 0.6% to 1.8%) | 16/1262 = 1.3% (95% Wilson CI 0.8% to 2.0%) | -0.2% |

## Parity Differences (246 cases)

| Row | Arabic Complaint | English | Actual | AR ESI | EN ESI | AR✓ | EN✓ |
|-----|-----------------|---------|--------|--------|--------|-----|-----|
| 11 | إكزيما في جفن العين | Eczema, Eyelid | 5 | 4 | 3 | ✗ | ✗ |
| 21 | لثتي ورمة | Gingival swelling | 4 | 4 | 3 | ✓ | ✗ |
| 23 | صباعي اتعور/اتخبط | Finger Injury | 4 | 4 | 3 | ✓ | ✗ |
| 30 | وجع في دراعي | pain, arm | 4 | 3 | 4 | ✗ | ✓ |
| 41 | نهجان وسرعة تنفس | hyperventilation | 4 | 2 | 3 | ✗ | ✗ |
| 49 | مش دريان باللي حواليه | mental change | 2 | 1 | 2 | ✗ | ✓ |
| 59 | رفرفة في قلبي / ضربات قلب سريع | palpitation | 3 | 2 | 3 | ✗ | ✓ |
| 64 | ترجيع | vomiting | 3 | 3 | 2 | ✓ | ✗ |
| 68 | وجع في الربع التحتاني اليمين م | right lower quadrant abdo | 3 | 4 | 3 | ✗ | ✓ |
| 71 | ورم في الرسغ الشمال | left wrist swelling | 4 | 4 | 3 | ✓ | ✗ |
| 76 | وجع في فم المعدة | epigastric pain | 3 | 4 | 3 | ✗ | ✓ |
| 83 | وجع أعلى البطن | upper abdominal pain | 3 | 4 | 3 | ✗ | ✓ |
| 84 | ورم في الخد | Edema, Cheek | 4 | 4 | 3 | ✓ | ✗ |
| 86 | وجع في فم المعدة | epigastric pain | 3 | 4 | 3 | ✗ | ✓ |
| 87 | وجع في فم المعدة | epigastric pain | 3 | 4 | 3 | ✗ | ✓ |
| 89 | وجع في أسفل الظهر | pain, low back | 3 | 4 | 2 | ✗ | ✗ |
| 93 | وجع في ظهري | pain, back | 3 | 4 | 3 | ✗ | ✓ |
| 96 | وجع أعلى البطن يمين | right upper abdominal pai | 3 | 4 | 3 | ✗ | ✓ |
| 97 | بطني كلها بتوجعني | Generalized abdominal pai | 3 | 4 | 3 | ✗ | ✓ |
| 102 | وجع حاد في فم المعدة | acute epigastric pain | 3 | 4 | 3 | ✗ | ✓ |
| 104 | خبطة في الكوع | Elbow Injury | 3 | 4 | 3 | ✗ | ✓ |
| 106 | وجع في الجنب اليمين (الخاصرة) | Rt. flank pain | 3 | 4 | 3 | ✗ | ✓ |
| 109 | وجع أسفل البطن ناحية الشمال | LLQ pain | 3 | 3 | 4 | ✓ | ✗ |
| 116 | وجع في عيني الشمال | ocular pain, Lt. | 3 | 4 | 3 | ✗ | ✓ |
| 117 | جرح مفتوح | Open Wound | 2 | 2 | 1 | ✓ | ✗ |
| 118 | وجع في الرجل الشمال | leg pain left | 3 | 3 | 4 | ✓ | ✗ |
| 120 | خبطة في دراعي | Arm Injury | 3 | 3 | 2 | ✓ | ✗ |
| 143 | دوخة | dizziness | 3 | 4 | 3 | ✗ | ✓ |
| 146 | دوخة | dizziness | 3 | 4 | 3 | ✗ | ✓ |
| 148 | محاولة انتحار | Suicidal Attempt | 2 | 1 | 2 | ✗ | ✓ |
