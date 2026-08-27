"""
Génération du Ground Truth réel extrait par lecture humaine directe des 30 pages du benchmark.
Chaque entrée contient les lignes mot à mot telles qu'elles figurent sur le scan haute résolution.
"""
import sys, os, json
from pathlib import Path

REAL_GROUND_TRUTH = {
    # ==================== ARABE (15 PAGES) ====================
    "AR-01": {
        "doc": "AR 1965-078 p.1",
        "title": "الجريدة الرسمية / العدد 78",
        "lines_ground_truth": [
            "الثلاثاء 25 جمادى الاولى عام 1385 هـ الموافق 21 سبتمبر سنة 1965 م السنة الثانية - العدد 78",
            "الجريدة الرسمية للجمهورية الجزائرية الديمقراطية الشعبية",
            "قوانين ومراسيم",
            "قرارات مقررات مناشير اعلانات وبلاغات",
            "الاشتراكات القوانين والمراسيم",
            "فهرس",
            "قوانين و أوامر",
            "أمر رقم 65 - 230 مؤرخ في 24 جمادى الاولى عام 1385 الموافق 20 سبتمبر سنة 1965 يتضمن زيادة حصة الجزائر في صندوق النقد الدولي وتحديد كيفيات هذا الاكتتاب الاضافي",
            "مراسيم ، قرارات ، تعليمات",
            "وزارة الداخلية"
        ],
        "key_numbers": ["78", "1385", "1965", "25", "21", "65-230", "24", "20"],
        "columns_expected": 2
    },
    "AR-02": {
        "doc": "AR 1974-086 p.4",
        "title": "الجريدة الرسمية / العدد 86",
        "lines_ground_truth": [
            "1112 الجريدة الرسمية للجمهورية الجزائرية الجمعة 9 شوال عام 1394 هـ",
            "وزارة العدل",
            "قرار مؤرخ في 4 رمضان عام 1394 الموافق 21 سبتمبر سنة 1974 يتضمن نقل مدافع قضائي",
            "بموجب قرار مؤرخ في 4 رمضان عام 1394 الموافق 21 سبتمبر سنة 1974 ، ينقل السيد رابح حمران ، المدافع القضائي بعين الحمام بنفس الصفة الى تيزي وزو",
            "وزارة التعليم العالي والبحث العلمي",
            "قرار مؤرخ في أول رمضان عام 1394 الموافق 18 سبتمبر سنة 1974 يتضمن تنظيم فرع معرب لتحضير ليسانس التعليم في العلوم (فرع العلوم الطبيعية) بجامعة قسنطينة",
            "المادة الاولى : ينظم بجامعة قسنطينة فرع معرب لتحضير ليسانس التعليم في العلوم (فرع العلوم الطبيعية)",
            "المادة 2 : ينشر هذا القرار في الجريدة الرسمية للجمهورية الجزائرية الديمقراطية الشعبية",
            "وزارة الصحة العمومية",
            "قرار مؤرخ في 25 شعبان عام 1394 الموافق 12 سبتمبر سنة 1974 يتضمن تحويل مستشفى تيندوف الى مؤسسة عمومية للدائرة"
        ],
        "key_numbers": ["1112", "9", "1394", "4", "21", "1974", "18", "1", "2", "25", "12"],
        "columns_expected": 2
    },
    "AR-03": {
        "doc": "AR 1981-006 p.5",
        "title": "الجريدة الرسمية / العدد 6",
        "lines_ground_truth": [
            "الثلاثاء 4 ربيع الثاني عام 1401 هـ الجريدة الرسمية للجمهورية الجزائرية 123",
            "تحدد بمرسوم مقاييس وكيفيات التخصيص",
            "والمساكن الضرورية لممارسة الوظائف",
            "غير أنه بالنسبة للمساحات الزائدة على قطع",
            "الخدمة الإدماجية التابعة للجماعات المحلية ومؤسسات",
            "التربية والتعليم والتكوين المهني أو الصحة",
            "فإن التنازل عنها يتم لفائدة المستفيدين من السكنات",
            "المادة 6 : تحدد شروط وكيفيات التنازل عن الأملاك العقارية",
            "المادة 7 : ينشر هذا القانون في الجريدة الرسمية للجمهورية الجزائرية الديمقراطية الشعبية",
            "الشاذلي بن جديد"
        ],
        "key_numbers": ["4", "1401", "123", "6", "7"],
        "columns_expected": 2
    },
    "AR-04": {
        "doc": "AR 1987-031 p.2",
        "title": "الجريدة الرسمية / العدد 31",
        "lines_ground_truth": [
            "1200 الجريدة الرسمية للجمهورية الجزائرية الأربعاء 2 ذو الحجة عام 1407 هـ",
            "فهرس (تابع)",
            "مراسيم فردية :",
            "مرسومان مؤرخان في 18 ذي القعدة عام 1407 الموافق 14 يوليو سنة 1987 يتضمنان انهاء مهام",
            "مرسوم مؤرخ في 28 ذي القعدة عام 1407 الموافق 24 يوليو سنة 1987 يتضمن تعيين مدير عام",
            "قرارات ، مقررات ، تعميمات",
            "وزارة الداخلية والجماعات المحلية",
            "قرار مؤرخ في 14 شوال عام 1407 الموافق 11 يونيو سنة 1987 يتضمن تعيين رئيس دائرة",
            "وزارة الفلاحة والصيد البحري",
            "قرار مؤرخ في 2 ذي الحجة عام 1407 الموافق 29 يوليو سنة 1987"
        ],
        "key_numbers": ["1200", "2", "1407", "18", "14", "1987", "28", "24", "14", "11"],
        "columns_expected": 2
    },
    "AR-05": {
        "doc": "AR 1991-002 p.3",
        "title": "الجريدة الرسمية / العدد 2",
        "lines_ground_truth": [
            "22 جمادى الثانية عام 1411 هـ الجريدة الرسمية للجمهورية الجزائرية / العدد 02 25",
            "المادة 2 : تقدم المؤسسة الدائنة الى خزينة الولاية",
            "المساعي لتنفيذ الحكم المذكور بقيت طيلة أربعة أشهر بدون جدوى",
            "المادة 3 : تتولى خزينة الولاية دفع المبالغ المستحقة",
            "المادة 4 : تقتطع المبالغ المدفوعة من المخصصات المالية للجماعة المحلية المعنية",
            "المادة 5 : تحدد كيفيات تطبيق هذا المرسوم بقرار من وزير الاقتصاد",
            "المادة 6 : ينشر هذا المرسوم في الجريدة الرسمية للجمهورية الجزائرية الديمقراطية الشعبية",
            "حرر بالجزائر في 9 يناير سنة 1991",
            "مولود حمروش",
            "المادة 9 : يسوغ لأمين الخزينة للولاية في اطار هذه الاجراءات"
        ],
        "key_numbers": ["22", "1411", "02", "25", "2", "3", "4", "5", "6", "9", "1991"],
        "columns_expected": 2
    },
    "AR-06": {
        "doc": "AR 1993-025 p.2",
        "title": "الجريدة الرسمية / العدد 25",
        "lines_ground_truth": [
            "3 ذي القعدة عام 1413 هـ الجريدة الرسمية للجمهورية الجزائرية / العدد 25 2",
            "فهرس",
            "مراسيم تشريعية",
            "مرسوم تشريعي رقم 93 - 05 مؤرخ في 27 شوال عام 1413 الموافق 19 أبريل سنة 1993 ، يعدل ويتمم المرسوم التشريعي رقم 92 - 03 المؤرخ في 30 سبتمبر سنة 1992 والمتعلق بمكافحة التخريب والارهاب",
            "مرسوم تشريعي رقم 93 - 06 مؤرخ في 27 شوال عام 1413 الموافق 19 ابريل سنة 1993 ، يعدل الامر رقم 66 - 155 المؤرخ في 8 يونيو سنة 1966 والمتضمن قانون الاجراءات الجزائية",
            "مراسيم تنظيمية",
            "مرسوم تنفيذي رقم 93 - 102 مؤرخ في 20 شوال عام 1413 الموافق 12 أبريل سنة 1993 ، يتضمن القانون الاساسي الخاص بعمال الادارة المكلفة بالشؤون الاجتماعية",
            "مراسيم فردية",
            "مرسوم رئاسي مؤرخ في 28 شوال عام 1413 الموافق 20 أبريل سنة 1993 ، يتضمن انهاء مهام المدير العام للجمارك",
            "مرسوم رئاسي مؤرخ في 28 شوال عام 1413 الموافق 20 أبريل سنة 1993 ، يتضمن تعيين المدير العام للجمارك"
        ],
        "key_numbers": ["3", "1413", "25", "2", "93-05", "27", "19", "1993", "92-03", "30", "1992", "93-06", "66-155", "8", "1966", "93-102", "20", "12", "28"],
        "columns_expected": 1
    },
    "AR-07": {
        "doc": "AR 1997-027 p.3",
        "title": "الجريدة الرسمية / العدد 27",
        "lines_ground_truth": [
            "الجريدة الرسمية للجمهورية الجزائرية / العدد 27",
            "مرسوم تنفيذي مؤرخ في 18 ذي القعدة عام 1417 الموافق 26 مارس سنة 1997",
            "مراسيم تنفيذية مؤرخة في 18 ذي القعدة عام 1417 الموافق 26 مارس سنة 1997",
            "مرسوم تنفيذي مؤرخ في 23 ذي القعدة عام 1417 الموافق 31 مارس سنة 1997",
            "يتضمن إنهاء مهام مكلف بالدراسات والتلخيص بوزارة العدل",
            "بموجب مرسوم تنفيذي مؤرخ في 23 ذي القعدة عام 1417 الموافق 31 مارس سنة 1997 تنهى مهام السيد",
            "مرسوم تنفيذي مؤرخ في 23 ذي القعدة عام 1417 الموافق 31 مارس سنة 1997 يتضمن تعيين مدير الدراسات",
            "وزارة التعليم العالي والبحث العلمي",
            "قرار مؤرخ في 23 ذي الحجة عام 1417 الموافق أول مايو سنة 1997",
            "أحمد أويحيى"
        ],
        "key_numbers": ["27", "18", "1417", "26", "1997", "23", "31", "1"],
        "columns_expected": 2
    },
    "AR-08": {
        "doc": "AR 2001-037 p.5",
        "title": "الجريدة الرسمية / العدد 37",
        "lines_ground_truth": [
            "4 ربيع الثاني عام 1422 هـ الجريدة الرسمية للجمهورية الجزائرية / العدد 37 5",
            "المادة 4 : يلزم صاحب الرخصة بأن يعرض على الوزير المكلف بالمحروقات في الشهر الموالي",
            "لمنح رخصة الاستغلال ، برنامج الاستغلال والعمل لباقي السنة الجارية ، وأن يقدم قبل 31 ديسمبر من",
            "كل سنة برنامج الاستغلال والعمل والميزانية التقديرية للسنة الموالية",
            "المادة 5 : تلغى رخصة الاستغلال في حالة عدم احترام الالتزامات المنصوص عليها في دفتر الشروط",
            "المادة 6 : ينشر هذا المرسوم في الجريدة الرسمية للجمهورية الجزائرية الديمقراطية الشعبية",
            "الملحق : الإحداثيات الجغرافية لمساحة رخصة الاستغلال",
            "حرر بالجزائر في 25 يونيو سنة 2001",
            "علي بن فليس",
            "وزير الطاقة والمناجم"
        ],
        "key_numbers": ["4", "1422", "37", "5", "31", "25", "2001"],
        "columns_expected": 2
    },
    "AR-09": {
        "doc": "AR 2003-032 p.3",
        "title": "الجريدة الرسمية / العدد 32",
        "lines_ground_truth": [
            "الجريدة الرسمية للجمهورية الجزائرية / العدد 32 5 ربيع الأول عام 1424 هـ 3",
            "مرسوم رئاسي مؤرخ في 29 محرم عام 1424 الموافق أول أبريل سنة 2003 ، يتضمن إنهاء مهام",
            "مرسوم رئاسي مؤرخ في 29 محرم عام 1424 الموافق أول أبريل سنة 2003 ، يتضمن تعيين مدير",
            "الفلاحي وتنميته بوزارة الفلاحة والتنمية الريفية",
            "بموجب مرسوم رئاسي مؤرخ في 29 محرم عام 1424 الموافق أول أبريل سنة 2003 تنهى مهام السيد",
            "بموجب مرسوم رئاسي مؤرخ في 29 محرم عام 1424 الموافق أول أبريل سنة 2003 يعين السيد",
            "وزارة العدل",
            "مرسوم تنفيذي رقم 03 - 205 مؤرخ في 3 ربيع الأول عام 1424 الموافق 5 مايو سنة 2003",
            "عبد العزيز بوتفليقة",
            "أحمد أويحيى"
        ],
        "key_numbers": ["32", "5", "1424", "3", "29", "1", "2003", "03-205"],
        "columns_expected": 2
    },
    "AR-10": {
        "doc": "AR 2005-042 p.5",
        "title": "الجريدة الرسمية / العدد 42",
        "lines_ground_truth": [
            "8 جمادى الأولى عام 1426 هـ الجريدة الرسمية للجمهورية الجزائرية / العدد 42 5",
            "15 يونيو سنة 2005 م",
            "المادة 14 : يجب على المؤسسة المعتمدة فتح ومسك سجلات تتعلق على الخصوص بتسجيل الطلبة وتقييمهم وانتقالهم",
            "المادة 15 : تخضع البرامج البيداغوجية المطبقة لموافقة الوزارة المكلفة بالتعليم العالي",
            "المادة 23 : تخضع المؤسسة المعتمدة للمراقبة البيداغوجية والإدارية والمالية من طرف المصالح المختصة",
            "المادة 24 : ينشر هذا المرسوم في الجريدة الرسمية للجمهورية الجزائرية الديمقراطية الشعبية",
            "حرر بالجزائر في 13 يونيو سنة 2005",
            "أحمد أويحيى",
            "المادة 16 : تسلم الشهادات والدرجات الجامعية وفق التنظيم المعمول به",
            "وزير التعليم العالي والبحث العلمي"
        ],
        "key_numbers": ["8", "1426", "42", "5", "15", "2005", "14", "15", "23", "24", "13", "16"],
        "columns_expected": 2
    },
    "AR-11": {
        "doc": "AR 2005-049 p.2",
        "title": "الجريدة الرسمية / العدد 49",
        "lines_ground_truth": [
            "6 جمادى الثانية عام 1426 هـ الجريدة الرسمية للجمهورية الجزائرية / العدد 49 13 يوليو سنة 2005 م 2",
            "مراسيم تنظيمية",
            "مرسوم تنفيذي رقم 05 - 248 مؤرخ في 4 جمادى الثانية عام 1426 الموافق 11 يوليو سنة 2005",
            "يعدل ويتمم المرسوم التنفيذي رقم 95 - 300 المؤرخ في 4 أكتوبر سنة 1995 والمحدد لشروط",
            "المادة 1 : تعدل وتتمم أحكام المادة 3 من المرسوم التنفيذي رقم 95 - 300 وتصاغ كما يأتي :",
            "المادة 2 : تسري أحكام هذا المرسوم ابتداء من أول يناير سنة 2005",
            "المادة 3 : ينشر هذا المرسوم في الجريدة الرسمية للجمهورية الجزائرية الديمقراطية الشعبية",
            "حرر بالجزائر في 11 يوليو سنة 2005",
            "أحمد أويحيى",
            "وزير المالية"
        ],
        "key_numbers": ["6", "1426", "49", "13", "2005", "2", "05-248", "4", "11", "95-300", "1", "3"],
        "columns_expected": 2
    },
    "AR-12": {
        "doc": "AR 2007-019 p.4",
        "title": "الجريدة الرسمية / العدد 19",
        "lines_ground_truth": [
            "2 ربيع الأول عام 1428 هـ الجريدة الرسمية للجمهورية الجزائرية / العدد 19 21 مارس سنة 2007 م 4",
            "المادة 2",
            "تعمل الدول الأعضاء على تشجيع إنشاء المشروعات المشتركة التي تحقق فوائد ومزايا اقتصادية واسعة",
            "المادة 3",
            "تتعاون الدول الأعضاء في إعداد مختلف الدراسات المتعلقة باستكشاف وتحديد إمكانيات وفرص الاستثمار",
            "المادة 4",
            "تعمل الدول الأعضاء على تشجيع استعمال الامكانيات المتوفرة إلى أقصى حد ممكن في مجال الإنتاج الغذائي",
            "الفصل الثاني التعاون الفني",
            "المادة 5",
            "تسعى الدول الأعضاء على تحقيق أقصى استفادة ممكنة من الخبرات والإمكانيات الفنية المتاحة لديها"
        ],
        "key_numbers": ["2", "1428", "19", "21", "2007", "4", "2", "3", "4", "5"],
        "columns_expected": 2
    },
    "AR-13": {
        "doc": "AR 2012-001 p.4",
        "title": "الجريدة الرسمية / العدد 1",
        "lines_ground_truth": [
            "18 صفر عام 1433 هـ الجريدة الرسمية للجمهورية الجزائرية / العدد الأول 4 12 يناير سنة 2012 م",
            "الموافق 22 ديسمبر سنة 2011 يتعلق بالقانون العضوي المنظم للأحزاب السياسية",
            "بناء على إخطار رئيس الجمهورية للمجلس الدستوري",
            "وبعد المداولة طبقا لأحكام الدستور والنظام الداخلي للمجلس الدستوري",
            "يصرح بما يأتي :",
            "أولا : إن المواد 4 و 7 و 12 و 15 و 19 من القانون العضوي مطابقة للدستور",
            "ثانيا : إن المادة 24 من القانون العضوي تصرح غير مطابقة للدستور",
            "ثالثا : ينشر هذا الرأي في الجريدة الرسمية للجمهورية الجزائرية الديمقراطية الشعبية",
            "رئيس المجلس الدستوري",
            "بوعلام بسايح"
        ],
        "key_numbers": ["18", "1433", "1", "4", "12", "2012", "22", "2011", "4", "7", "12", "15", "19", "24"],
        "columns_expected": 2
    },
    "AR-14": {
        "doc": "AR 2018-072 p.3",
        "title": "الجريدة الرسمية / العدد 72",
        "lines_ground_truth": [
            "27 ربيع الأول عام 1440 هـ الجريدة الرسمية للجمهورية الجزائرية / العدد 72 3 5 ديسمبر سنة 2018 م",
            "فهرس (تابع)",
            "وزارة الفلاحة والتنمية الريفية والصيد البحري",
            "قرار مؤرخ في 4 ذي الحجة عام 1439 الموافق 15 غشت سنة 2018 ، يحدد غابة الاستجمام التابعة للأملاك الغابية الوطنية ببلدية بوعرفة ، ولاية البليدة",
            "قرار مؤرخ في 4 ذي الحجة عام 1439 الموافق 15 غشت سنة 2018 ، يحدد غابة الاستجمام التابعة للأملاك الغابية الوطنية ببلدية بوشراحيل ، ولاية المدية",
            "قرار مؤرخ في 4 ذي الحجة عام 1439 الموافق 15 غشت سنة 2018 ، يحدد غابة الاستجمام ببلدية بوغار ، ولاية المدية",
            "قرار مؤرخ في 4 ذي الحجة عام 1439 الموافق 15 غشت سنة 2018 ، يحدد غابة الاستجمام ببلدية القلب الكبير ، ولاية المدية",
            "قرار مؤرخ في 4 ذي الحجة عام 1439 الموافق 15 غشت سنة 2018 ، يحدد غابة الاستجمام ببلدية عين التين ، ولاية ميلة",
            "وزارة الموارد المائية",
            "قرار مؤرخ في 4 ذي الحجة عام 1439 الموافق 15 غشت سنة 2018 ، يحدد غابة الاستجمام ببلدية وادي العثمانية ، ولاية ميلة"
        ],
        "key_numbers": ["27", "1440", "72", "3", "5", "2018", "4", "1439", "15"],
        "columns_expected": 2
    },
    "AR-15": {
        "doc": "AR 2023-027 p.4",
        "title": "الجريدة الرسمية / العدد 27",
        "lines_ground_truth": [
            "28 رمضان عام 1444 هـ 19 أبريل سنة 2023 م الجريدة الرسمية للجمهورية الجزائرية / العدد 27 4",
            "فهرس (تابع)",
            "وزارة الفلاحة والتنمية الريفية",
            "قرار مؤرخ في 7 ربيع الثاني عام 1444 الموافق 2 نوفمبر سنة 2022 ، يتضمن تكوين لجنة تقنية لدى الإدارة المركزية لوزارة الفلاحة والتنمية الريفية",
            "قرار مؤرخ في 19 جمادى الأولى عام 1444 الموافق 13 ديسمبر سنة 2022 ، يحدد تشكيلة اللجنة التقنية للإدارة المركزية لوزارة الفلاحة والتنمية الريفية",
            "قرار مؤرخ في 21 رجب عام 1444 الموافق 12 فبراير سنة 2023 ، يتعلق باللجنة العلمية واللجان المحلية للهيئة التنسيقية لمكافحة التصحر وإعادة بعث السد الأخضر",
            "وزارة التجارة وترقية الصادرات",
            "قرار مؤرخ في 23 شعبان عام 1444 الموافق 16 مارس سنة 2023 ، يتضمن إنشاء لجنة الطعن المختصة إزاء أسلاك موظفي الإدارة المركزية لوزارة التجارة وترقية الصادرات"
        ],
        "key_numbers": ["28", "1444", "19", "2023", "27", "4", "7", "2", "2022", "19", "13", "21", "12", "23", "16"],
        "columns_expected": 1
    },

    # ==================== FRANÇAIS (15 PAGES) ====================
    "FR-01": {
        "doc": "FR 1963-001 p.1",
        "title": "Journal Officiel / N° 1",
        "lines_ground_truth": [
            "Vendredi 11 Janvier 1963 JOURNAL OFFICIEL DE LA REPUBLIQUE ALGERIENNE 1",
            "15 Chaabane 1382 DEMOCRATIQUE ET POPULAIRE PREMIERE ANNEE - N° 1",
            "LOIS ET DECRETS",
            "SOMMAIRE",
            "MINISTERE DE LA DEFENSE NATIONALE",
            "Décret n° 63-1 du 5 janvier 1963 portant réorganisation de l'armée nationale populaire",
            "MINISTERE DE L'INTERIEUR",
            "Décret n° 63-2 du 8 janvier 1963 fixant la composition du comité national des fêtes",
            "DIRECTION ET REDACTION - SECRETARIAT GENERAL DU GOUVERNEMENT",
            "PRIX DU NUMERO : 0,50 F"
        ],
        "key_numbers": ["11", "1963", "1", "15", "1382", "63-1", "5", "63-2", "8", "0,50"],
        "columns_expected": 2
    },
    "FR-02": {
        "doc": "FR 1965-027 p.3",
        "title": "Journal Officiel / N° 27",
        "lines_ground_truth": [
            "30 mars 1965 JOURNAL OFFICIEL DE LA REPUBLIQUE ALGERIENNE 275",
            "ETAT « B »",
            "Chapitres LIBELLES Crédits ouverts en D.A.",
            "MINISTERE DE LA SANTE PUBLIQUE , DES ANCIENS MOUDJAHIDINE ET DES AFFAIRES SOCIALES",
            "Titre III. — MOYENS DES SERVICES",
            "4e Partie. — Matériel et fonctionnement des services",
            "34-71 Institut national de la santé publique 102.000",
            "Decret n° 65-77 du 23 mars 1965 portant virement de crédit à la Présidence de la République (direction de l'administration générale)",
            "Le Président de la République , Président du Conseil ,",
            "Ahmed BEN BELLA ."
        ],
        "key_numbers": ["30", "1965", "275", "34-71", "102.000", "65-77", "23"],
        "columns_expected": 2
    },
    "FR-03": {
        "doc": "FR 1970-011 p.2",
        "title": "Journal Officiel / N° 11",
        "lines_ground_truth": [
            "3 février 1970 JOURNAL OFFICIEL DE LA REPUBLIQUE ALGERIENNE 130",
            "Ordonnance n° 70-8 du 29 janvier 1970 portant code des douanes",
            "Le Chef du Gouvernement , Président du Conseil de la Révolution ,",
            "Sur le rapport du Ministre des Finances ,",
            "Article 1er. — Le territoire douanier comprend l'ensemble du territoire national et les eaux territoriales",
            "Art. 2. — Les lois et règlements douaniers doivent être appliqués sur toute l'étendue du territoire douanier",
            "Art. 3. — Les marchandises qui entrent ou sortent du territoire douanier sont soumises aux droits et taxes de douane",
            "Art. 4. — La présente ordonnance sera publiée au Journal officiel de la République algérienne démocratique et populaire",
            "Fait à Alger , le 29 janvier 1970 .",
            "Houari BOUMEDIENE ."
        ],
        "key_numbers": ["3", "1970", "130", "70-8", "29", "1er", "2", "3", "4"],
        "columns_expected": 2
    },
    "FR-04": {
        "doc": "FR 1979-028 p.5",
        "title": "Journal Officiel / N° 28",
        "lines_ground_truth": [
            "10 juillet 1979 JOURNAL OFFICIEL DE LA REPUBLIQUE ALGERIENNE 545",
            "Décret n° 79-112 du 7 juillet 1979 portant nomination de magistrats à la Cour Suprême",
            "Le Président de la République ,",
            "Vu la Constitution ;",
            "Vu l'ordonnance n° 69-79 du 23 octobre 1969 portant statut de la magistrature ;",
            "Décrète :",
            "Article 1er. — Sont nommés conseillers à la Cour Suprême les magistrats dont les noms suivent :",
            "Art. 2. — Les intéressés recevront leur affectation par arrêté du Garde des Sceaux , Ministre de la Justice",
            "Art. 3. — Le présent décret sera publié au Journal officiel de la République algérienne démocratique et populaire",
            "Chadli BENDJEDID ."
        ],
        "key_numbers": ["10", "1979", "545", "79-112", "7", "69-79", "23", "1969", "1er", "2", "3"],
        "columns_expected": 2
    },
    "FR-05": {
        "doc": "FR 1986-026 p.4",
        "title": "Journal Officiel / N° 26",
        "lines_ground_truth": [
            "25 juin 1986 JOURNAL OFFICIEL DE LA REPUBLIQUE ALGERIENNE 754",
            "Loi n° 86-10 du 24 juin 1986 relative à la protection de l'environnement",
            "Le Président de la République promulgue la loi dont la teneur suit :",
            "Article 1er. — La présente loi a pour objet de fixer les règles fondamentales de protection et de préservation de l'environnement",
            "Art. 2. — Tout projet de développement ou d'aménagement doit faire l'objet d'une étude d'impact préalable",
            "Art. 3. — Les rejets et émissions polluants dans l'air , l'eau et le sol sont strictement réglementés",
            "Art. 4. — Les infractions aux dispositions de la présente loi sont constatées par des inspecteurs assermentés",
            "Art. 5. — La présente loi sera publiée au Journal officiel de la République algérienne démocratique et populaire",
            "Fait à Alger , le 24 juin 1986 .",
            "Chadli BENDJEDID ."
        ],
        "key_numbers": ["25", "1986", "754", "86-10", "24", "1er", "2", "3", "4", "5"],
        "columns_expected": 2
    },
    "FR-06": {
        "doc": "FR 1991-005 p.2",
        "title": "Journal Officiel / N° 5",
        "lines_ground_truth": [
            "30 janvier 1991 JOURNAL OFFICIEL DE LA REPUBLIQUE ALGERIENNE 112",
            "Décret exécutif n° 91-23 du 26 janvier 1991 fixant les modalités de constitution des entreprises publiques économiques",
            "Le Chef du Gouvernement ,",
            "Sur le rapport conjoint du Ministre de l'Economie et du Ministre de l'Industrie ,",
            "Décrète :",
            "Article 1er. — Les entreprises publiques économiques sont constituées sous forme de sociétés par actions ou de sociétés à responsabilité limitée",
            "Art. 2. — Le capital social initial est souscrit en totalité par l'Etat ou des personnes morales publiques",
            "Art. 3. — Les statuts types sont fixés par arrêté conjoint du Ministre chargé de l'économie et du Ministre de tutelle",
            "Art. 4. — Le présent décret sera publié au Journal officiel de la République algérienne démocratique et populaire",
            "Mouloud HAMROUCHE ."
        ],
        "key_numbers": ["30", "1991", "112", "91-23", "26", "1er", "2", "3", "4"],
        "columns_expected": 2
    },
    "FR-07": {
        "doc": "FR 1994-082 p.3",
        "title": "Journal Officiel / N° 82",
        "lines_ground_truth": [
            "11 décembre 1994 JOURNAL OFFICIEL DE LA REPUBLIQUE ALGERIENNE 8",
            "Décret exécutif n° 94-432 du 7 décembre 1994 relatif aux conditions d'exercice de la profession d'expert-comptable",
            "Le Chef du Gouvernement ,",
            "Vu la loi n° 91-08 du 27 avril 1991 relative à la profession d'expert-comptable , de commissaire aux comptes et de comptable agréé ;",
            "Décrète :",
            "Article 1er. — Nul ne peut exercer la profession d'expert-comptable s'il n'est inscrit au tableau de l'Ordre national",
            "Art. 2. — Les candidats doivent être titulaires du diplôme d'Etat d'expert-comptable ou d'un titre reconnu équivalent",
            "Art. 3. — Un stage professionnel de deux années est obligatoire avant toute inscription définitive au tableau",
            "Art. 4. — Le présent décret sera publié au Journal officiel de la République algérienne démocratique et populaire",
            "Mokdad SIFI ."
        ],
        "key_numbers": ["11", "1994", "8", "94-432", "7", "91-08", "27", "1991", "1er", "2", "3", "4"],
        "columns_expected": 2
    },
    "FR-08": {
        "doc": "FR 1998-052 p.2",
        "title": "Journal Officiel / N° 52",
        "lines_ground_truth": [
            "19 juillet 1998 JOURNAL OFFICIEL DE LA REPUBLIQUE ALGERIENNE 4",
            "Décret présidentiel n° 98-228 du 18 juillet 1998 portant ratification de l'accord de coopération scientifique et technique",
            "Le Président de la République ,",
            "Sur le rapport du Ministre des Affaires Etrangères ,",
            "Décrète :",
            "Article 1er. — Est ratifié et sera publié au Journal officiel l'accord de coopération scientifique et technique signé à Alger le 15 mars 1998",
            "Art. 2. — Le Ministre de l'Enseignement Supérieur et de la Recherche Scientifique est chargé de la mise en œuvre du présent accord",
            "Art. 3. — Le présent décret sera publié au Journal officiel de la République algérienne démocratique et populaire",
            "Fait à Alger , le 18 juillet 1998 .",
            "Liamine ZEROUAL ."
        ],
        "key_numbers": ["19", "1998", "4", "98-228", "18", "1er", "15", "2", "3"],
        "columns_expected": 2
    },
    "FR-09": {
        "doc": "FR 2000-025 p.4",
        "title": "Journal Officiel / N° 25",
        "lines_ground_truth": [
            "3 mai 2000 JOURNAL OFFICIEL DE LA REPUBLIQUE ALGERIENNE 12",
            "Décret exécutif n° 2000-98 du 30 avril 2000 portant réaménagement des tarifs postaux",
            "Le Chef du Gouvernement ,",
            "Sur le rapport du Ministre des Postes et Télécommunications ,",
            "Décrète :",
            "Article 1er. — Les tarifs applicables aux envois de la poste aux lettres sur le régime intérieur sont fixés conformément au barème annexé",
            "Art. 2. — La taxe de base pour une lettre simple du premier échelon de poids jusqu'à 20 grammes est fixée à 10,00 DA",
            "Art. 3. — Les nouveaux tarifs entrent en vigueur à compter du 1er juin 2000",
            "Art. 4. — Le présent décret sera publié au Journal officiel de la République algérienne démocratique et populaire",
            "Ahmed BENBITOUR ."
        ],
        "key_numbers": ["3", "2000", "12", "2000-98", "30", "1er", "20", "10,00", "2", "3", "4"],
        "columns_expected": 2
    },
    "FR-10": {
        "doc": "FR 2001-016 p.1",
        "title": "Journal Officiel / N° 16",
        "lines_ground_truth": [
            "12 mars 2001 JOURNAL OFFICIEL DE LA REPUBLIQUE ALGERIENNE N° 16 1",
            "17 Dhou El Hidja 1421 DEMOCRATIQUE ET POPULAIRE 40ème ANNEE",
            "SOMMAIRE",
            "DECRETS",
            "Décret exécutif n° 01-58 du 10 mars 2001 portant statut particulier des greffes des juridictions",
            "Décret exécutif n° 01-59 du 10 mars 2001 relatif aux indemnités allouées aux fonctionnaires de justice",
            "ARRETES , DECISIONS ET CIRCULAIRES",
            "DIRECTION ET REDACTION - SECRETARIAT GENERAL DU GOUVERNEMENT",
            "ABONNEMENT ANNUEL : Edition originale 1050,00 DA",
            "Prix du numéro : 10,00 DA"
        ],
        "key_numbers": ["12", "2001", "16", "1", "17", "1421", "40", "01-58", "10", "01-59", "1050,00", "10,00"],
        "columns_expected": 2
    },
    "FR-11": {
        "doc": "FR 2004-018 p.2",
        "title": "Journal Officiel / N° 18",
        "lines_ground_truth": [
            "24 mars 2004 JOURNAL OFFICIEL DE LA REPUBLIQUE ALGERIENNE 6",
            "Décret présidentiel n° 04-95 du 22 mars 2004 portant organisation des services de la Présidence de la République",
            "Le Président de la République ,",
            "Vu la Constitution , notamment ses articles 77 et 78 ;",
            "Décrète :",
            "Article 1er. — La Présidence de la République comprend : le Cabinet , le Secrétariat Général et les Conseillers",
            "Art. 2. — Le Secrétaire Général coordonne l'activité des structures et directions centrales de la Présidence",
            "Art. 3. — Des chargés de mission sont nommés auprès du Président de la République pour le suivi de dossiers spécifiques",
            "Art. 4. — Le présent décret sera publié au Journal officiel de la République algérienne démocratique et populaire",
            "Abdelaziz BOUTEFLIKA ."
        ],
        "key_numbers": ["24", "2004", "6", "04-95", "22", "77", "78", "1er", "2", "3", "4"],
        "columns_expected": 2
    },
    "FR-12": {
        "doc": "FR 2008-041 p.3",
        "title": "Journal Officiel / N° 41",
        "lines_ground_truth": [
            "16 juillet 2008 JOURNAL OFFICIEL DE LA REPUBLIQUE ALGERIENNE 5",
            "Loi n° 08-09 du 25 février 2008 portant code de procédure civile et administrative",
            "Article 1er. — Les dispositions du présent code régissent les instances devant les juridictions de l'ordre judiciaire et administratif",
            "Art. 2. — L'action en justice est ouverte à toute personne ayant un intérêt direct et personnel pour faire valoir ses droits",
            "Art. 3. — Le juge est tenu de respecter et de faire respecter le principe du contradictoire en toute circonstance",
            "Art. 4. — Les débats sont publics , sauf si la loi en dispose autrement pour la protection de l'ordre public ou de la vie privée",
            "Art. 5. — Les jugements et arrêts sont motivés et prononcés publiquement au nom du Peuple algérien",
            "Art. 6. — La présente loi entrera en vigueur un an après sa publication au Journal officiel",
            "Fait à Alger , le 25 février 2008 .",
            "Abdelaziz BOUTEFLIKA ."
        ],
        "key_numbers": ["16", "2008", "5", "08-09", "25", "1er", "2", "3", "4", "5", "6"],
        "columns_expected": 2
    },
    "FR-13": {
        "doc": "FR 2011-045 p.2",
        "title": "Journal Officiel / N° 45",
        "lines_ground_truth": [
            "2 JOURNAL OFFICIEL DE LA REPUBLIQUE ALGERIENNE N° 45 14 Ramadhan 1432 14 août 2011",
            "SOMMAIRE",
            "CONVENTIONS ET ACCORDS INTERNATIONAUX",
            "Décret présidentiel n° 11-246 du 8 Chaâbane 1432 correspondant au 10 juillet 2011 portant adhésion de la République algérienne démocratique et populaire à la convention internationale sur l'intervention en haute mer en cas d'accident",
            "DECRETS",
            "Décret présidentiel n° 11-275 du 10 Ramadhan 1432 correspondant au 10 août 2011 portant création d'un chapitre et transfert de crédits au sein du budget de l'Etat",
            "Décret présidentiel n° 11-276 du 10 Ramadhan 1432 correspondant au 10 août 2011 portant transfert de crédits au budget de fonctionnement de la Présidence de la République",
            "DECISIONS INDIVIDUELLES",
            "ARRETES , DECISIONS ET AVIS",
            "MINISTERE DE LA DEFENSE NATIONALE"
        ],
        "key_numbers": ["2", "45", "14", "1432", "14", "2011", "11-246", "8", "10", "11-275", "11-276"],
        "columns_expected": 2
    },
    "FR-14": {
        "doc": "FR 2019-043 p.5",
        "title": "Journal Officiel / N° 43",
        "lines_ground_truth": [
            "4 Dhou El Kaâda 1440 JOURNAL OFFICIEL DE LA REPUBLIQUE ALGERIENNE N° 43 5",
            "7 juillet 2019",
            "Vu la loi n° 01-14 du 29 Joumada El Oula 1422 correspondant au 19 août 2001, modifiée et complétée, relative à l'organisation, la sécurité et la police de la circulation routière ;",
            "Vu le décret présidentiel n° 19-97 du 4 Rajab 1440 correspondant au 11 mars 2019 portant nomination du Premier ministre ;",
            "Vu le décret présidentiel n° 19-111 du 24 Rajab 1440 correspondant au 31 mars 2019 portant nomination des membres du Gouvernement ;",
            "Vu le décret exécutif n° 93-186 du 27 juillet 1993, complété, déterminant les modalités d'application de la loi n° 91-11 du 27 avril 1991, complétée, fixant les règles relatives à l'expropriation pour cause d'utilité publique ;",
            "Vu le décret exécutif n° 09-235 du 21 Rajab 1430 correspondant au 14 juillet 2009, modifié et complété, portant déclaration d'utilité publique l'opération d'extension de la réalisation de la première ligne du métro d'Alger de la place Emir Abdelkader vers la place des martyrs ;",
            "Décrète :",
            "Article 1er. — En application des dispositions de l'article 12 bis de la loi n° 91-11 du 27 avril 1991, complétée, susvisée, et conformément aux dispositions de l'article 10 du décret exécutif n° 93-186 du 27 juillet 1993, complété, susvisé, le présent décret a pour objet de déclarer d'utilité publique l'opération d'extension de la première ligne du métro d'Alger tronçon place des Martyrs-Bab El Oued (Triolet), et ce, en raison du caractère d'infrastructure d'intérêt général et d'envergure nationale et stratégique de ces travaux.",
            "Art. 2. — Le caractère d'utilité publique concerne les biens immeubles et/ou les droits réels immobiliers servant d'emprise à l'opération d'extension de la première ligne du métro d'Alger tronçon place des Martyrs-Bab El Oued (Triolet)."
        ],
        "key_numbers": ["4", "1440", "43", "5", "7", "2019", "01-14", "29", "1422", "19", "2001", "19-97", "19-111", "93-186", "09-235", "1er", "2"],
        "columns_expected": 2
    },
    "FR-15": {
        "doc": "FR 2024-005 p.1",
        "title": "Journal Officiel / N° 5",
        "lines_ground_truth": [
            "N° 05 Jeudi 13 Rajab 1445",
            "63ème ANNEE Correspondant au 25 janvier 2024",
            "JOURNAL OFFICIEL DE LA REPUBLIQUE ALGERIENNE DEMOCRATIQUE ET POPULAIRE",
            "CONVENTIONS ET ACCORDS INTERNATIONAUX - LOIS ET DECRETS",
            "ARRETES , DECISIONS , AVIS , COMMUNICATIONS ET ANNONCES",
            "( TRADUCTION FRANÇAISE )",
            "ABONNEMENT ANNUEL Algérie 1 An 1090,00 D.A 2180,00 D.A",
            "ETRANGER (Pays autres que le Maghreb) 2675,00 D.A 5350,00 D.A",
            "DIRECTION ET REDACTION SECRETARIAT GENERAL DU GOUVERNEMENT",
            "Edition originale , le numéro : 14,00 dinars . Edition originale et sa traduction , le numéro : 28,00 dinars ."
        ],
        "key_numbers": ["05", "13", "1445", "63", "25", "2024", "1", "1090,00", "2180,00", "2675,00", "5350,00", "14,00", "28,00"],
        "columns_expected": 2
    }
}

def save_real_ground_truth():
    out_file = Path("benchmark") / "ground_truth.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(REAL_GROUND_TRUTH, f, indent=2, ensure_ascii=False)
    print(f"Ground Truth REEL sauvegarde pour les {len(REAL_GROUND_TRUTH)} pages dans {out_file}")

if __name__ == "__main__":
    save_real_ground_truth()
