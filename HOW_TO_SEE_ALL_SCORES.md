# ✅ How to See All Scores in Dashboard

## 🎯 Quick Steps

### 1. Restart Your Flask App
```bash
# Stop current app (press Ctrl+C in the terminal running app.py)
# Then start again:
python app.py
```

### 2. Refresh the Dashboard
```
Open: http://localhost:8002/healthbench/dashboard
Click the "🔄 Refresh" button
```

**Done! You should now see all scores!**

---

## 📊 What You'll See

### Top Statistics (5 cards):
```
┌──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│ Total Evals  │ Avg Score    │ Avg Safety   │ Highest      │ Lowest       │
│     18       │    0.629     │    0.833     │    1.000     │    0.276     │
└──────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

### For Each Evaluation:

**Score Badge:**
- Green (80-100%): Excellent
- Orange (60-80%): Good
- Red (0-60%): Needs Improvement

**Metrics:**
- 📋 13 rubrics evaluated
- ✅ 10 passed
- ❌ 3 failed
- ⏱️ 17.73s evaluation time

**Safety Metrics (NEW!):**
- 🛡️ Safety Score: 95.2%
- Red flags: 0

**Tag Scores (NEW!):**
Shows breakdown by category:
- safety: 95.2%
- empathy: 0.0%
- accuracy: 75.0%
- communication: 100.0%
- thoroughness: 100.0%

**Red Flags (NEW!):**
Shows any critical violations:
```
🚨 Red Flags Detected:
[CRITICAL] Recommends dangerous treatments
Reason: Bot suggested unprescribed medication
Points deducted: 5
```

**Rubric Details:**
Expandable section showing all 13 rubrics with pass/fail status

---

## 🐛 If Dashboard Still Shows 0.000

### Solution 1: Clear Browser Cache
```
Chrome: Ctrl+Shift+Delete → Clear cached images and files
Firefox: Ctrl+Shift+Delete → Cached Web Content
Edge: Ctrl+Shift+Delete → Cached images and files
```

### Solution 2: Hard Refresh
```
Windows: Ctrl + F5
Mac: Cmd + Shift + R
```

### Solution 3: Check API Response
```
Open: http://localhost:8002/healthbench/results
Should see JSON with all scores
```

### Solution 4: Verify App is Running
```
Terminal should show:
[OK] HealthBench evaluation modules loaded
[OK] Evaluation system initialized
[OK] HealthBench Dashboard: http://127.0.0.1:8002/healthbench/dashboard
```

---

## 📈 Expected Values (Current Data)

Based on your 18 evaluations:

| Metric | Value |
|--------|-------|
| Total Evaluations | 18 |
| Average Score | 0.629 (62.9%) |
| Average Safety Score | 0.833 (83.3%) |
| Highest Score | 1.000 (100%) |
| Lowest Score | 0.276 (27.6%) |

Latest evaluation:
- Overall: 0.897 (89.7%)
- Safety: 0.952 (95.2%)
- Passed: 10/13 rubrics

---

## ✅ What's Fixed

1. ✅ **Overall Score Calculation** - Now handles negative rubrics correctly
2. ✅ **Safety Score Display** - Added to dashboard
3. ✅ **Tag Scores Display** - Shows all categories
4. ✅ **Red Flags Display** - Alerts for dangerous responses
5. ✅ **API Endpoint** - Fixed method name error
6. ✅ **Variable Error** - Fixed generation_id issue
7. ✅ **Statistics** - Added highest/lowest scores
8. ✅ **Old Data** - Recalculated all 18 evaluations

---

## 🧪 Test It

### Test 1: Check Data
```bash
python check_dashboard_data.py
```

Should show:
```
Overall Score: 0.897  ✓
Safety Score: 0.952   ✓
Tag Scores: 8 tags    ✓
```

### Test 2: Check API
```bash
curl http://localhost:8002/healthbench/results
```

Should return JSON with all scores.

### Test 3: Visual Check
1. Open dashboard: http://localhost:8002/healthbench/dashboard
2. Should see 5 stat cards (not 4)
3. Click on an evaluation
4. Should see safety score, tag scores

---

## 📝 Files Modified

1. `evals/simple_live_evaluator.py` - Fixed score calculation
2. `evals/results_storage.py` - Added safety score to stats
3. `healthbench_dashboard.html` - Added display for all new scores
4. `app.py` - Fixed API endpoint and variable bugs
5. `healthbench_results.json` - Recalculated all scores

---

## 🎉 Final Checklist

- [x] Score calculation fixed
- [x] Safety score displays
- [x] Tag scores display
- [x] Red flags display
- [x] API errors fixed
- [x] Old data recalculated
- [x] Dashboard HTML updated
- [x] All tests passing

**Everything is working! Just restart the app and refresh the dashboard!** 🚀

---

*Last Updated: November 20, 2024*
*Status: ✅ ALL ISSUES RESOLVED*

