# KTAS Arabic vs English — Parity Benchmark

**Date:** 20260408T223414Z
**Cases:** 1262
**Translation:** Gemini CLI (Egyptian colloquial Arabic)

## Head-to-Head

| Metric | Arabic | English | Delta |
|--------|--------|---------|-------|
| Exact match | 36.4% | 37.8% | -1.4% |
| Within-one | 82.2% | 81.6% | +0.6% |
| Under-triage | 10.5% | 6.1% | +4.4% |
| Over-triage | 53.2% | 56.1% | -2.9% |
| Critical under-triage | 1.0% | 1.3% | -0.2% |

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
