from flask import Flask, request, render_template, redirect, url_for
import math
import json
import os
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy

# ======================= הגדרות אפליקציה ו-DB =======================
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///foodi.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ======================= מודל מסעדות בבסיס הנתונים =======================
class Restaurant(db.Model):
    __tablename__ = 'restaurants'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    type = db.Column(db.String(100))
    lat = db.Column(db.Float, nullable=True)
    lon = db.Column(db.Float, nullable=True)
    contact = db.Column(db.String(50))
    available = db.Column(db.Boolean, default=True)
    wait_time = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "lat": self.lat,
            "lon": self.lon,
            "contact": self.contact,
            "available": self.available,
            "wait_time": self.wait_time
        }

# ======================= אחידות סוגים (נרמול) =======================
TYPE_CANONICAL = {
    # אסייתי
    "אסיאתי": "אסייתי",
    "אסייתית": "אסייתי",
    "אסייתי": "אסייתי",

    # בשרים
    "בשרי": "בשרים",
    "בשרית": "בשרים",
    "על האש": "בשרים",
    "גריל": "בשרים",
    "בשרים": "בשרים",

    # המבורגר
    "בורגר": "המבורגר",
    "המבורגר": "המבורגר",

    # מזרחי
    "מזרחית": "מזרחי",
    "מזרחי": "מזרחי",

    # איטלקי
    "איטלקית": "איטלקי",
    "איטלקי": "איטלקי",
}

def normalize_type(s: str) -> str:
    s = (s or "").strip()
    return TYPE_CANONICAL.get(s, s)

def cleanup_types_in_db():
    """מתקן ערכי type שכבר קיימים במסד (בלי למחוק DB)."""
    changed = 0
    for r in Restaurant.query.all():
        new_t = normalize_type(r.type)
        if r.type != new_t:
            r.type = new_t
            changed += 1
    db.session.commit()
    print(f"[cleanup_types_in_db] updated {changed} rows")

# ======================= Seed למסעדות =======================
def seed_restaurants():
    data = [
        { "name": "נאיה", "type": "אסייתי", "lat": 31.772836, "lon": 35.192510 },
        { "name": "לוצ'נה", "type": "איטלקי", "lat": 31.780904, "lon": 35.220143 },
        { "name": "הדקל 3", "type": "בשרים", "lat": 31.783210, "lon": 35.218450 },
        { "name": "רוזה", "type": "איטלקי", "lat": 31.782590, "lon": 35.219890 },
        { "name": "ממא איטליאנו", "type": "איטלקי", "lat": 31.781240, "lon": 35.217900 },
        { "name": "אנגליקה ביסטרו", "type": "בשרים", "lat": 31.776900, "lon": 35.222300 },
        { "name": "פיאנו פקטורי", "type": "איטלקי", "lat": 31.771300, "lon": 35.219000 },
        { "name": "ליבי", "type": "בשרים", "lat": 31.774530, "lon": 35.219330 },
        { "name": "בירנבאום", "type": "בשרים", "lat": 31.778322, "lon": 35.221998 },
        { "name": "אגאדיר הכשר", "type": "המבורגר", "lat": 31.777420, "lon": 35.219870 },

        { "name": "בלאק ירושלים", "type": "המבורגר", "lat": 31.775650, "lon": 35.213980 },
        { "name": "מרקש", "type": "מזרחי", "lat": 31.781132, "lon": 35.213441 },
        { "name": "המטבח של חלי", "type": "מזרחי", "lat": 31.790951, "lon": 35.205885 },
        { "name": "שגב קודש", "type": "בשרים", "lat": 31.779921, "lon": 35.216771 },
        { "name": "המוציא", "type": "מזרחי", "lat": 31.784812, "lon": 35.220781 },
        { "name": "מגדל דוד גריל", "type": "בשרים", "lat": 31.776880, "lon": 35.231210 },
        { "name": "בני הדייג", "type": "בשרים", "lat": 31.794335, "lon": 35.168771 },
        { "name": "אבולעפיה הכשר", "type": "מזרחי", "lat": 31.781777, "lon": 35.224777 },
        { "name": "גריל ברמות", "type": "בשרים", "lat": 31.828120, "lon": 35.208910 },
        { "name": "מינאטו הכשר", "type": "אסייתי", "lat": 31.780541, "lon": 35.219102 },

        { "name": "שיסו", "type": "אסייתי", "lat": 31.780010, "lon": 35.214882 },
        { "name": "טטאמי", "type": "אסייתי", "lat": 31.770412, "lon": 35.215991 },
        { "name": "סושי רחביה", "type": "אסייתי", "lat": 31.774431, "lon": 35.212731 },
        { "name": "ריבר הכשר ירושלים", "type": "אסייתי", "lat": 31.794450, "lon": 35.172311 },
        { "name": "מנדרין סושי", "type": "אסייתי", "lat": 31.782111, "lon": 35.216442 },
        { "name": "בשרי מהדרין מחנה יהודה", "type": "בשרים", "lat": 31.784631, "lon": 35.212124 },
        { "name": "הטאבון של סמי", "type": "מזרחי", "lat": 31.783502, "lon": 35.211545 },
        { "name": "אלום גריל", "type": "בשרים", "lat": 31.792452, "lon": 35.205991 },
        { "name": "סולומונס", "type": "המבורגר", "lat": 31.785212, "lon": 35.211932 },
        { "name": "בורגר סטיישן", "type": "המבורגר", "lat": 31.789213, "lon": 35.203002 },
        { "name": "בגריל שלנו", "type": "בשרים", "lat": 31.778911, "lon": 35.223312 },
        { "name": "גחלים גולן", "type": "בשרים", "lat": 31.807441, "lon": 35.214110 },
        { "name": "דוניא", "type": "מזרחי", "lat": 31.787214, "lon": 35.212134 },
        { "name": "גריל 443", "type": "בשרים", "lat": 31.857443, "lon": 35.239110 },
        { "name": "המושבה גריל בר", "type": "בשרים", "lat": 31.761242, "lon": 35.201994 },
        { "name": "אליהו פרגיות", "type": "בשרים", "lat": 31.799221, "lon": 35.199003 },
        { "name": "פרגיות המושבה", "type": "בשרים", "lat": 31.796221, "lon": 35.202114 },
        { "name": "אנטריקוטי", "type": "בשרים", "lat": 31.777114, "lon": 35.219903 },
        { "name": "סניף גריל רמות", "type": "בשרים", "lat": 31.825552, "lon": 35.208231 },
        { "name": "מזרח ומערב גריל", "type": "מזרחי", "lat": 31.774914, "lon": 35.212900 },

        { "name": "גולדיס", "type": "המבורגר", "lat": 31.794412, "lon": 35.205411 },
        { "name": "האמריקה", "type": "המבורגר", "lat": 31.781144, "lon": 35.214917 },
        { "name": "ברוני ביסטרו גריל", "type": "בשרים", "lat": 31.759114, "lon": 35.208311 },
        { "name": "שיפודיה טעמי המזרח", "type": "מזרחי", "lat": 31.787110, "lon": 35.213441 },
        { "name": "לחיים גריל", "type": "בשרים", "lat": 31.783811, "lon": 35.221701 },
        { "name": "המנגליסט", "type": "בשרים", "lat": 31.780311, "lon": 35.221402 },
        { "name": "דרום אמריקה גריל", "type": "בשרים", "lat": 31.799510, "lon": 35.202321 },
        { "name": "לבנדר גריל", "type": "בשרים", "lat": 31.767814, "lon": 35.207511 },
        { "name": "איליה גריל", "type": "בשרים", "lat": 31.782411, "lon": 35.217114 },
        { "name": "גריל גורמה ירושלים", "type": "בשרים", "lat": 31.778211, "lon": 35.217514 },

        { "name": "מגדל המנגל", "type": "בשרים", "lat": 31.794881, "lon": 35.173994 },
        { "name": "הגריל של איציק", "type": "בשרים", "lat": 31.782551, "lon": 35.220014 },
        { "name": "טעמי הכרם", "type": "מזרחי", "lat": 31.788114, "lon": 35.187911 },
        { "name": "שיפודי רוממה", "type": "בשרים", "lat": 31.806944, "lon": 35.192221 },
        { "name": "מסעדת לב הענבים", "type": "מזרחי", "lat": 31.782441, "lon": 35.224019 },
        { "name": "שירת הבשר", "type": "בשרים", "lat": 31.773884, "lon": 35.214913 },
        { "name": "שיפודי המושבה", "type": "בשרים", "lat": 31.762554, "lon": 35.203149 },
        { "name": "גריל אבו רמזי", "type": "בשרים", "lat": 31.794114, "lon": 35.219331 },
        { "name": "סולטן גריל", "type": "מזרחי", "lat": 31.799144, "lon": 35.207773 },
        { "name": "מנגלי ישראל", "type": "בשרים", "lat": 31.784610, "lon": 35.217441 },

        { "name": "סמיר גריל", "type": "בשרים", "lat": 31.785104, "lon": 35.211908 },
        { "name": "המברגר פריים", "type": "המבורגר", "lat": 31.781778, "lon": 35.219821 },
        { "name": "בורגר מירון", "type": "המבורגר", "lat": 31.788212, "lon": 35.212114 },
        { "name": "בורגר קינג הכשר", "type": "המבורגר", "lat": 31.776114, "lon": 35.218144 },
        { "name": "מודרן גריל", "type": "בשרים", "lat": 31.774412, "lon": 35.231019 },
        { "name": "אמבטיה גריל בר", "type": "בשרים", "lat": 31.770014, "lon": 35.214992 },
        { "name": "השיפוד המהיר", "type": "בשרים", "lat": 31.785441, "lon": 35.212510 },
        { "name": "הטחנה", "type": "מזרחי", "lat": 31.757812, "lon": 35.204412 },
        { "name": "פרגיות הכנסת", "type": "בשרים", "lat": 31.777911, "lon": 35.205992 },
        { "name": "גריל גולן", "type": "בשרים", "lat": 31.804112, "lon": 35.213114 },
        { "name": "הבשר הלבן (כשר)", "type": "בשרים", "lat": 31.779712, "lon": 35.217810 },
        { "name": "המבורגריית טוסטי", "type": "המבורגר", "lat": 31.782011, "lon": 35.220611 },
        { "name": "בשרים השלום", "type": "בשרים", "lat": 31.781221, "lon": 35.205991 },
        { "name": "מזרחי טעים", "type": "מזרחי", "lat": 31.785902, "lon": 35.214223 },
        { "name": "האריה השואג גריל", "type": "בשרים", "lat": 31.796541, "lon": 35.205410 },
        { "name": "שאפו גריל", "type": "בשרים", "lat": 31.790314, "lon": 35.217112 },
        { "name": "גריל 2000", "type": "בשרים", "lat": 31.774014, "lon": 35.213114 },
        { "name": "אל גאוצ'ו ירושלים (כשר)", "type": "בשרים", "lat": 31.790221, "lon": 35.216671 },
        { "name": "בורגרז", "type": "המבורגר", "lat": 31.782214, "lon": 35.221994 },
        { "name": "הביסטרו של אבו שאקר", "type": "מזרחי", "lat": 31.789914, "lon": 35.203211 },

        { "name": "טבע הבשר", "type": "בשרים", "lat": 31.783012, "lon": 35.216512 },
        { "name": "מסעדת גולן", "type": "בשרים", "lat": 31.804911, "lon": 35.213991 },
        { "name": "אש וארומה", "type": "בשרים", "lat": 31.778412, "lon": 35.211514 },
        { "name": "בשר הרים", "type": "בשרים", "lat": 31.787712, "lon": 35.206314 },
        { "name": "המסעדה הירושלמית", "type": "מזרחי", "lat": 31.777512, "lon": 35.219114 },
        { "name": "שיפודי רמות פלוס", "type": "בשרים", "lat": 31.827811, "lon": 35.209002 },
        { "name": "הגריל הדתי", "type": "בשרים", "lat": 31.782910, "lon": 35.207890 },
        { "name": "שיפודי קסטל", "type": "בשרים", "lat": 31.775522, "lon": 35.184211 },
        { "name": "בשרים העמק", "type": "בשרים", "lat": 31.783512, "lon": 35.214781 },
        { "name": "הכפרי גריל", "type": "בשרים", "lat": 31.771512, "lon": 35.215221 },

        { "name": "הביסטרו של עודד", "type": "בשרים", "lat": 31.785314, "lon": 35.211114 },
        { "name": "שיפוד אנדור", "type": "בשרים", "lat": 31.759882, "lon": 35.205014 },
        { "name": "אגדת הבשר", "type": "בשרים", "lat": 31.782212, "lon": 35.219711 },
        { "name": "הפלא של הבשר", "type": "בשרים", "lat": 31.785114, "lon": 35.211311 },
        { "name": "גריל הבירה", "type": "בשרים", "lat": 31.774114, "lon": 35.218321 },
        { "name": "בורגר האוס מהדרין", "type": "המבורגר", "lat": 31.782211, "lon": 35.218114 },
        { "name": "קצבים ושות׳", "type": "בשרים", "lat": 31.783114, "lon": 35.217214 },
        { "name": "הטעמים של רומי", "type": "מזרחי", "lat": 31.787219, "lon": 35.214509 },
        { "name": "אצל חנניה", "type": "מזרחי", "lat": 31.781214, "lon": 35.220114 },
        { "name": "אלפרדו בשרים", "type": "בשרים", "lat": 31.778411, "lon": 35.213501 },

        { "name": "גריל המלכים", "type": "בשרים", "lat": 31.784912, "lon": 35.218711 },
        { "name": "טעמי הרובע", "type": "מזרחי", "lat": 31.774211, "lon": 35.235114 },
        { "name": "מנגל השכונה", "type": "בשרים", "lat": 31.792214, "lon": 35.205112 },
        { "name": "בית הבשר", "type": "בשרים", "lat": 31.788514, "lon": 35.212411 },
        { "name": "שיפודי בוכרים", "type": "בשרים", "lat": 31.793411, "lon": 35.219114 },
        { "name": "סניף 71 גריל", "type": "בשרים", "lat": 31.795011, "lon": 35.207881 },
        { "name": "מאכלי המזרח", "type": "מזרחי", "lat": 31.785119, "lon": 35.214991 },
        { "name": "גריל ישראל", "type": "בשרים", "lat": 31.781514, "lon": 35.220814 },
        { "name": "מסעדת מימון", "type": "מזרחי", "lat": 31.786714, "lon": 35.213114 },
        { "name": "אש וליבו", "type": "בשרים", "lat": 31.781114, "lon": 35.215514 },

        { "name": "גריל השוק", "type": "בשרים", "lat": 31.784014, "lon": 35.212114 },
        { "name": "הגריל המהיר", "type": "בשרים", "lat": 31.783912, "lon": 35.219114 },
        { "name": "המנגל של תומר", "type": "בשרים", "lat": 31.781214, "lon": 35.207714 },
        { "name": "שיפודי המכרז", "type": "בשרים", "lat": 31.782511, "lon": 35.213714 },
        { "name": "בשרים גולן מערב", "type": "בשרים", "lat": 31.804712, "lon": 35.210912 },
        { "name": "המקור הבשרי", "type": "בשרים", "lat": 31.780114, "lon": 35.217114 },
        { "name": "גריל האלה", "type": "בשרים", "lat": 31.783412, "lon": 35.212711 },
        { "name": "אש התבור", "type": "בשרים", "lat": 31.789214, "lon": 35.217314 },
        { "name": "מזרחית טובה", "type": "מזרחי", "lat": 31.786114, "lon": 35.209914 },
        { "name": "בשרים וים", "type": "בשרים", "lat": 31.778914, "lon": 35.215214 },

        { "name": "הדר הבשרים", "type": "בשרים", "lat": 31.777214, "lon": 35.212514 },
        { "name": "הטעם השביעי", "type": "מזרחי", "lat": 31.781714, "lon": 35.219814 },
        { "name": "תמשיח בשרים", "type": "בשרים", "lat": 31.785214, "lon": 35.210614 },
        { "name": "שיפודי הלל", "type": "בשרים", "lat": 31.780414, "lon": 35.220214 },
        { "name": "בשרים פרימיום", "type": "בשרים", "lat": 31.782514, "lon": 35.214214 },
        { "name": "אש הגבעה", "type": "בשרים", "lat": 31.792014, "lon": 35.214714 },
        { "name": "מזרחי הממלכה", "type": "מזרחי", "lat": 31.785714, "lon": 35.214114 },
        { "name": "שיפודי קינג", "type": "בשרים", "lat": 31.784114, "lon": 35.207714 },
        { "name": "המסעדה העממית", "type": "מזרחי", "lat": 31.782114, "lon": 35.222214 },
        { "name": "שיפוד העיר", "type": "בשרים", "lat": 31.774914, "lon": 35.212114 },

        { "name": "טעם ירושלים", "type": "מזרחי", "lat": 31.786514, "lon": 35.208914 },
        { "name": "גריל האומה", "type": "בשרים", "lat": 31.793114, "lon": 35.212514 },
        { "name": "גחלים 28", "type": "בשרים", "lat": 31.783714, "lon": 35.220114 },
        { "name": "בשרים בכיכר", "type": "בשרים", "lat": 31.776314, "lon": 35.214214 },
        { "name": "הטאבון והגריל", "type": "בשרים", "lat": 31.777214, "lon": 35.216514 },
        { "name": "מנגל ישראלי", "type": "בשרים", "lat": 31.781514, "lon": 35.218414 },
        { "name": "הבשרים של איתי", "type": "בשרים", "lat": 31.788414, "lon": 35.215114 },
        { "name": "חגיגת בשרים", "type": "בשרים", "lat": 31.783814, "lon": 35.211114 },
        { "name": "גריל של פעם", "type": "בשרים", "lat": 31.784214, "lon": 35.218114 },
        { "name": "מזרחית באווירה", "type": "מזרחי", "lat": 31.784114, "lon": 35.212914 },

        { "name": "אש הסולטן", "type": "בשרים", "lat": 31.781914, "lon": 35.214414 },
        { "name": "מסעדת עזרא", "type": "מזרחי", "lat": 31.786114, "lon": 35.209214 },
        { "name": "הגריל המשפחתי", "type": "בשרים", "lat": 31.781314, "lon": 35.213314 },
        { "name": "בשרים הטובים", "type": "בשרים", "lat": 31.780914, "lon": 35.215614 },
        { "name": "אמפריית המנגל", "type": "בשרים", "lat": 31.787214, "lon": 35.212214 },
        { "name": "מזרחי הנביאים", "type": "מזרחי", "lat": 31.782314, "lon": 35.219714 },
        { "name": "גריל הגבעה", "type": "בשרים", "lat": 31.792914, "lon": 35.209714 },
        { "name": "שיפודי משה", "type": "בשרים", "lat": 31.777014, "lon": 35.217314 },
        { "name": "מנגל ישראלי בית הכרם", "type": "בשרים", "lat": 31.793014, "lon": 35.187414 },
        { "name": "בשרים הנשיא", "type": "בשרים", "lat": 31.776814, "lon": 35.214114 },

        { "name": "גריל מאה שערים", "type": "בשרים", "lat": 31.788912, "lon": 35.219114 },
        { "name": "הטאבון של אבו שאקר", "type": "מזרחי", "lat": 31.786211, "lon": 35.215411 },
        { "name": "ממלכת הבשרים", "type": "בשרים", "lat": 31.782912, "lon": 35.217112 },
        { "name": "המסעדה הירושלמית", "type": "מזרחי", "lat": 31.780714, "lon": 35.212214 },
        { "name": "שיפודי רחביה", "type": "בשרים", "lat": 31.772914, "lon": 35.214012 },
        { "name": "מזרחי אותנטי", "type": "מזרחי", "lat": 31.776214, "lon": 35.218714 },
        { "name": "גריל שומרי", "type": "בשרים", "lat": 31.779614, "lon": 35.210114 },
        { "name": "המנגל החם", "type": "בשרים", "lat": 31.783214, "lon": 35.223114 },
        { "name": "מזרחית הכותל", "type": "מזרחי", "lat": 31.775114, "lon": 35.234214 },
        { "name": "שיפודי ארזים", "type": "בשרים", "lat": 31.789714, "lon": 35.216314 },

        { "name": "גריל המלכות", "type": "בשרים", "lat": 31.784514, "lon": 35.211114 },
        { "name": "הטאבון והמנגל", "type": "בשרים", "lat": 31.782914, "lon": 35.209814 },
        { "name": "מזרחי אותנטי טעמי ירושלים", "type": "מזרחי", "lat": 31.777914, "lon": 35.213714 },
        { "name": "בשרים גולן דרום", "type": "בשרים", "lat": 31.802114, "lon": 35.213214 },
        { "name": "אש הגלבוע", "type": "בשרים", "lat": 31.781114, "lon": 35.222214 },
        { "name": "שיפודי התחנה", "type": "בשרים", "lat": 31.764814, "lon": 35.212514 },
        { "name": "המזרחית של שלומי", "type": "מזרחי", "lat": 31.784114, "lon": 35.205814 },
        { "name": "גריל טעמי הכפר", "type": "בשרים", "lat": 31.793214, "lon": 35.199414 },
        { "name": "ברביקיו ירושלים", "type": "בשרים", "lat": 31.788914, "lon": 35.214914 },
        { "name": "שיפודי מרכז העיר", "type": "בשרים", "lat": 31.781314, "lon": 35.221114 },

        { "name": "מנגולד בשרים", "type": "בשרים", "lat": 31.787714, "lon": 35.209114 },
        { "name": "שיפודי השדרה", "type": "בשרים", "lat": 31.772114, "lon": 35.217914 },
        { "name": "הבשרים של אדיר", "type": "בשרים", "lat": 31.789214, "lon": 35.205314 },
        { "name": "מזרחית אבן ישראל", "type": "מזרחי", "lat": 31.779014, "lon": 35.212214 },
        { "name": "גריל השלושה", "type": "בשרים", "lat": 31.783114, "lon": 35.219114 },
        { "name": "מסעדת ברכת שלום", "type": "מזרחי", "lat": 31.775514, "lon": 35.211214 },
        { "name": "שיפודי הקסטל", "type": "בשרים", "lat": 31.804114, "lon": 35.177114 },
        { "name": "גריל אורנים", "type": "בשרים", "lat": 31.792214, "lon": 35.209614 },
        { "name": "המעשנה הירושלמית", "type": "בשרים", "lat": 31.781914, "lon": 35.214514 },
        { "name": "בשרים על האש", "type": "בשרים", "lat": 31.786814, "lon": 35.216914 },

        { "name": "הגריל הציוני", "type": "בשרים", "lat": 31.782714, "lon": 35.218114 },
        { "name": "אמנות הבשר", "type": "בשרים", "lat": 31.777414, "lon": 35.214414 },
        { "name": "האש של רחמים", "type": "בשרים", "lat": 31.784814, "lon": 35.221814 },
        { "name": "בשרים הדור הבא", "type": "בשרים", "lat": 31.783214, "lon": 35.211714 },
        { "name": "מזרחית הבירה", "type": "מזרחי", "lat": 31.781414, "lon": 35.216214 },
        { "name": "הגריל השוקק", "type": "בשרים", "lat": 31.788014, "lon": 35.214114 },
        { "name": "שיפודי עמק רפאים", "type": "בשרים", "lat": 31.769514, "lon": 35.215914 },
        { "name": "בשרים גבעת מרדכי", "type": "בשרים", "lat": 31.776514, "lon": 35.203114 },
        { "name": "הבשר של ניסים", "type": "בשרים", "lat": 31.785214, "lon": 35.212214 },
        { "name": "שיפודי דוד המלך", "type": "בשרים", "lat": 31.775014, "lon": 35.229214 },

        { "name": "בשרים הסנהדרין", "type": "בשרים", "lat": 31.792814, "lon": 35.210314 },
        { "name": "הגריל של הצפון", "type": "בשרים", "lat": 31.801314, "lon": 35.210914 },
        { "name": "האש המזרחית", "type": "מזרחי", "lat": 31.782114, "lon": 35.213214 },
        { "name": "מנגל גן הפעמון", "type": "בשרים", "lat": 31.769214, "lon": 35.217714 },
        { "name": "המסעדה הבוכרית", "type": "מזרחי", "lat": 31.793014, "lon": 35.221114 },
        { "name": "שיפודי קרן היסוד", "type": "בשרים", "lat": 31.772314, "lon": 35.219714 },
        { "name": "מזרחית רמות", "type": "מזרחי", "lat": 31.825514, "lon": 35.197214 },
        { "name": "הבשרים של רועי", "type": "בשרים", "lat": 31.782514, "lon": 35.205814 },
        { "name": "מנגל ירושלים", "type": "בשרים", "lat": 31.781014, "lon": 35.215014 },
        { "name": "גריל חברון", "type": "בשרים", "lat": 31.770714, "lon": 35.229114 },

        { "name": "בלייז פיצה", "type": "איטלקי", "lat": 31.774912, "lon": 35.219411 },
        { "name": "פיצה פיציקטו", "type": "איטלקי", "lat": 31.783144, "lon": 35.213774 },
        { "name": "פיצה טוקיו", "type": "איטלקי", "lat": 31.770441, "lon": 35.215901 },
        { "name": "פיצה רומא", "type": "איטלקי", "lat": 31.779212, "lon": 35.222014 },
        { "name": "פיצה מייקל", "type": "איטלקי", "lat": 31.790114, "lon": 35.205881 },
        { "name": "טוסקנה פיצה", "type": "איטלקי", "lat": 31.774211, "lon": 35.211914 },
        { "name": "פיצה פילגרם", "type": "איטלקי", "lat": 31.777512, "lon": 35.214812 },
        { "name": "פיצה ברכת שמים", "type": "איטלקי", "lat": 31.792411, "lon": 35.207114 },
        { "name": "פיצה קסטל", "type": "איטלקי", "lat": 31.762114, "lon": 35.203411 },
        { "name": "פיצה רפאל", "type": "איטלקי", "lat": 31.776114, "lon": 35.216214 },

        { "name": "קפה לוצ'נה", "type": "איטלקי", "lat": 31.780450, "lon": 35.220210 },
        { "name": "קפה גרג ממילא", "type": "איטלקי", "lat": 31.776882, "lon": 35.224911 },
        { "name": "קפית הסינמטק", "type": "איטלקי", "lat": 31.768914, "lon": 35.219412 },
        { "name": "קפה ברנז'ה", "type": "איטלקי", "lat": 31.781914, "lon": 35.213512 },
        { "name": "לחם ארז", "type": "איטלקי", "lat": 31.785114, "lon": 35.216114 },
        { "name": "קפה לנדוור מלחה", "type": "איטלקי", "lat": 31.751412, "lon": 35.204314 },
        { "name": "קפה לנדוור רמות", "type": "איטלקי", "lat": 31.825212, "lon": 35.208992 },

        { "name": "פיצה בריגה", "type": "איטלקי", "lat": 31.781501, "lon": 35.213901 },
        { "name": "פיצה אגד שמאי", "type": "איטלקי", "lat": 31.780412, "lon": 35.221112 },
        { "name": "פיצה רומא מהדרין", "type": "איטלקי", "lat": 31.783781, "lon": 35.213439 },
        { "name": "פיצה ביג מאמא", "type": "איטלקי", "lat": 31.788211, "lon": 35.207114 },
        { "name": "פיצה גולדה", "type": "איטלקי", "lat": 31.783014, "lon": 35.219114 }
    ]

    for item in data:
        if Restaurant.query.filter_by(name=item["name"]).first():
            continue
        db.session.add(Restaurant(
            name=item["name"],
            type=normalize_type(item.get("type")),  # ✅ תיקון
            lat=item.get("lat"),
            lon=item.get("lon"),
        ))
    db.session.commit()

# ======================= קבצי JSON =======================
RESVJSON = "reservations.json"
REPORTS = "reports.json"
USERS = "users.json"
VOTES = "votes.json"

def _load(path, default):
    if os.path.exists(path):
        try:
            return json.load(open(path, encoding="utf-8"))
        except:
            return default
    return default

def _save(path, obj):
    json.dump(obj, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def load_restaurants():
    return [r.to_dict() for r in Restaurant.query.filter_by(available=True).all()]

def load_reports():
    return _load(REPORTS, [])

def save_reports(x):
    _save(REPORTS, x)

def now_utc():
    return datetime.utcnow()

# ======================= Utils =======================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))

# ======================= Predictor =======================
DEFAULT_WAIT = 25
HALF_LIFE_MIN = 30.0
LAMBDA = math.log(2.0) / HALF_LIFE_MIN
RECENT_WINDOW_MIN = 120

def reports_for_restaurant(rid, within_min=RECENT_WINDOW_MIN):
    reports = load_reports()
    cutoff = now_utc() - timedelta(minutes=within_min)
    return [
        r for r in reports
        if r["restaurant_id"] == rid and datetime.fromisoformat(r["created_at"]) >= cutoff
    ]

def weighted_prediction_for_restaurant(rest):
    recents = reports_for_restaurant(rest["id"])
    if not recents:
        return DEFAULT_WAIT, 0

    weights = []
    waits = []
    now = now_utc()

    for rep in recents:
        minutes_ago = (now - datetime.fromisoformat(rep["created_at"])).total_seconds() / 60
        w = math.exp(-LAMBDA * minutes_ago)
        weights.append(w)
        waits.append(rep["wait_minutes"])

    pred = sum(w*m for w, m in zip(weights, waits)) / sum(weights)
    return round(pred, 1), len(recents)

def predicted_wait_bundle(rest):
    pred, n = weighted_prediction_for_restaurant(rest)
    return {
        "restaurant_id": rest["id"],
        "name": rest["name"],
        "predicted_wait": pred,
        "n_reports_used": n
    }

# ======================= עמוד הבית =======================
@app.route("/")
def home():
    return render_template("index.html")

# ======================= תוצאות כלליות =======================
@app.route("/results")
def results_page():
    restaurants = load_restaurants()
    enriched = [predicted_wait_bundle(r) for r in restaurants]
    return render_template("results.html", predictions=enriched)

# ======================= חיפוש מסעדה לפי מיקום =======================
@app.route("/find")
def find_restaurant():
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    cuisine = request.args.get("type", type=str)

    # ✅ מנרמלים את מה שהמשתמש הזין
    cuisine = normalize_type(cuisine)

    if lat is None or lon is None:
        return render_template("results_search.html", results=[], error="לא התקבל מיקום. יש ללחוץ על 'אתר אותי'.")

    restaurants = load_restaurants()
    results = []

    for r in restaurants:
        if r["lat"] is None or r["lon"] is None:
            continue

        # ✅ משווים על בסיס נרמול
        if cuisine and normalize_type(r["type"]) != cuisine:
            continue

        d = haversine(lat, lon, r["lat"], r["lon"])

        b = predicted_wait_bundle(r)
        b["distance_km"] = round(d, 2)
        b["lat"] = r["lat"]
        b["lon"] = r["lon"]

        results.append(b)

    results.sort(key=lambda x: x["distance_km"])
    return render_template("results_search.html", results=results, error=None)

# ======================= דיווח עומס =======================
@app.route("/report", methods=["GET", "POST"])
def report_api():
    if request.method == "GET":
        preselected = request.args.get("restaurant_id", type=int)
        return render_template("report_form.html", restaurants=load_restaurants(), preselected=preselected)

    data = request.form
    rid = int(data["restaurant_id"])
    wait = int(data["wait_minutes"])

    reports = load_reports()
    reports.append({
        "id": len(reports) + 1,
        "restaurant_id": rid,
        "wait_minutes": wait,
        "created_at": now_utc().isoformat(),
    })
    save_reports(reports)

    restaurant = Restaurant.query.get(rid)
    if restaurant:
        restaurant.wait_time = wait
        db.session.commit()

    return render_template("report_thanks.html", restaurant=restaurant, wait=wait)

# ======================= מסך ניהול =======================
@app.route("/admin", methods=["GET", "POST"])
def admin_page():
    if request.method == "POST":
        name = request.form["name"]
        type_ = normalize_type(request.form["type"])  # ✅ תיקון
        lat = float(request.form["lat"])
        lon = float(request.form["lon"])
        contact = request.form["contact"]

        db.session.add(Restaurant(name=name, type=type_, lat=lat, lon=lon, contact=contact))
        db.session.commit()
        return redirect(url_for("admin_page"))

    return render_template("admin.html", restaurants=Restaurant.query.all())

@app.route("/admin/restaurant/<int:rid>/toggle", methods=["POST"])
def toggle_restaurant(rid):
    r = Restaurant.query.get_or_404(rid)
    r.available = not r.available
    db.session.commit()
    return redirect(url_for("admin_page"))

# ======================= הרצה =======================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_restaurants()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

