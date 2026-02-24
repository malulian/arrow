# תיקון בעיית עדכון המלאי בדוחות עבודה

## הבעיה
דוחות עבודה (Work Reports) שנשלחו (submitted) ללא עדכון סטטוס submit תקין, לא ניכו פריטים מהמלאי כפי שצריך.

## הפתרון
הפתרון כולל שני חלקים:

### 1. מניעה לעתיד
עדכנתי את הקוד ב-`work_report.py` כך שהפונקציה `deduct_parts_from_inventory()` תבדוק אם כבר קיימת טרנזקציה של ניכוי מהמלאי לפני שהיא מנכה שוב. זה ימנע כפילויות בעתיד.

**שינויים שבוצעו:**
- הוספת בדיקה ב-`deduct_parts_from_inventory()` שבודקת אם כבר קיים `Inventory Transaction` לפני ביצוע הניכוי
- אם כבר קיימת טרנזקציה, הפונקציה תדלג על הפריט

### 2. תיקון דוחות קיימים
יש שתי דרכים לתקן דוחות קיימים:

#### אפשרות א': דרך ממשק המשתמש (UI)
1. עבור לרשימת **Work Report**
2. לחץ על הכפתור **"Fix Inventory for Submitted Reports"** בסרגל העליון
3. אשר את הפעולה
4. המערכת תציג סיכום של:
   - כמה דוחות תוקנו
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

## מה הפונקציה עושה?

הפונקציה `fix_inventory_for_submitted_reports()` מבצעת את השלבים הבאים:

1. מחפשת את כל הדוחות שנשלחו (docstatus = 1)
2. לכל דוח, בודקת אם יש לו פריטים שנוכו
3. לכל פריט, בודקת אם כבר קיימת טרנזקציה של ניכוי
4. אם אין טרנזקציה:
   - מנכה את הכמות מה-`Inventory Item`
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
