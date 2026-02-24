# תיקון בעיית עדכון המלאי בדוחות עבודה

## הבעיה
דוחות עבודה (Work Reports) נשארים בסטטוס **Draft** ולא **Submitted**, ולכן הפריטים לא מנוכים מהמלאי.

## הפתרון
הפתרון כולל שלושה חלקים:

### 1. מניעה לעתיד
עדכנתי את הקוד ב-`work_report.py` כך שהפונקציה `deduct_parts_from_inventory()` תבדוק אם כבר קיימת טרנזקציה של ניכוי מהמלאי לפני שהיא מנכה שוב. זה ימנע כפילויות בעתיד.

**שינויים שבוצעו:**
- הוספת בדיקה ב-`deduct_parts_from_inventory()` שבודקת אם כבר קיים `Inventory Transaction` לפני ביצוע הניכוי
- אם כבר קיימת טרנזקציה, הפונקציה תדלג על הפריט

### 2. Submit אוטומטי לדוחות Draft
פונקציה חדשה שיכולה לעשות Submit לכל הדוחות ה-Draft ולנכות מהמלאי בבת אחת.

### 3. תיקון דוחות Submitted קיימים - Submit דוח בודד
1. פתח **Work Report** שאתה רוצה לשלוח
2. לחץ על הכפתור הכחול **"Submit & Deduct from Inventory"**
3. אשר את הפעולה
4. הדוח יעבור ל-Submitted והמלאי יתעדכן

#### אפשרות ב': Submit כל הדוחות ה-Draft בבת אחת
1. עבור לרשימת **Work Report**
2. לחץ על הכפתור **"Submit All Draft Reports"** בסרגל העליון (תחת Actions)
3. אשר את הפעולה
4. המערכת תציג סיכום של:
   - כמה דוחות עברו Submit
   - כמה דוחות תוקנו
   - כמה פריד': הרצת סקריפט ישירות (למתקדמים)

**Submit All Draft Reports:**
```bash
bench --site [site-name] execute "arrow.arrow_aviation_mx.doctype.work_report.work_report.fix_inventory_for_submitted_reports(submit_drafts=True)"
```

**Fix Submitted Reports Only:**
```bash
bench --site [site-name] execute "arrow.arrow_aviation_mx.doctype.work_report.work_report.fix_inventory_for_submitted_reports(submit_drafts=False)"
   - כמה פריטים נוכו
   - כמה דוחות נבדקו בסך הכל
   - רשימת שגיאות (אם יש)

#### אפשרות ב': הרצת סקריפט ישירות
```bash
bench --site [site-name] execute arrow.arrow_aviation_mx.doctype.work_report.work_report.fix_inventory_for_submitted_reports
```

או הרצת הקובץ:
```bash
bench --site [site-name] execute fix_inventory_deduction.fix_inventory_for_submitted_reports
```

## מה הפונקציה עושה?submit_drafts=False)` מבצעת:

**כאשר `submit_drafts=False` (ברירת מחדל):**
1. מחפשת דוחות שכבר Submitted (docstatus = 1)
2. בודקת לכל דוח אם יש פריטים שנוכו
3. לכל פריט, בודקת אם כבר קיימת טרנזקציה של ניכוי
4. אם אין טרנזקציה:
   - מנכה את הכמות מה-`Inventory Item`
   - יוצרת `Inventory Transaction` חדשה
   - מעדכנת את תאריך המשיכה האחרונה

**כאשר `submit_drafts=True`:**
1. מחפשת את כל הדוחות (Draft + Submitted)
2. לדוחות Draft עם פריטים:
   - מבצעת Submit אוטומטית
   - ה-hook של `on_submit` מנכה את המלאי
3. לדוחות Submitted - מתקנת חסרים כמו למעלה

### פרמטרים
- **`submit_drafts`** (bool, default=False):
  - `True` = Submit דוחות Draft + תקן Submitted
  - `False` = תקן רק דוחות Submittedem`
   - יוצרת `Inventory Transaction` חדשה
   - מעדכנת את תאריך המשיכה האחרונה

## בטיחות

הפונקציה בטוחה להרצה מרובה:
- היא בודקת אם כבר קיימת טרנזקציה לפני שהיא מנכה
- היא לא תנכה פריט יותר מפעם אחת
- כל שגיאה נרשמת ב-error log ולא עוצרת את התהליך

## קבצים שהשתנו

1. **`arrow/arrow_aviation_mx/doctype/work_report/work_report.py`**
   - עדכון פונקציה `deduct_parts_from_inventory()` עם בדיקת כפילויות
   - הוספת פונקציה `fix_inventory_for_submitted_reports()`

2. **`arrow/arrow_aviation_mx/doctype/work_report/work_report_list.js`** (חדש)
   - הוספת כפתור בממשק המשתמש להרצת התיקון

3. **`fix_inventory_deduction.py`** (חדש)
   - סקריפט עצמאי להרצה ישירה

## בדיקה

לאחר הרצת התיקון, כדאי לבדוק:

1. **Inventory Transaction** - לוודא שכל הדוחות השלימו יצרו טרנזקציות:
   ```
   SELECT 
       COUNT(DISTINCT wr.name) as total_submitted_reports,
       COUNT(DISTINCT it.reference_name) as reports_with_transactions
   FROM `tabWork Report` wr
   LEFT JOIN `tabInventory Transaction` it 
       ON it.reference_doctype = 'Work Report' 
       AND it.reference_name = wr.name
   WHERE wr.docstatus = 1
   ```

2. **Inventory Item** - לוודא שהכמויות נכונות במלאי

## תמיכה

אם יש בעיות או שאלות, בדוק את ה-error logs:
```
bench --site [site-name] show-log
```
