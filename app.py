from flask import Flask, request, render_template, redirect, url_for
import math
import json
import os
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
import numpy as np
from scipy.optimize import linear_sum_assignment

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

    # חלבי / בתי קפה
   "חלבי": "חלבי",
   "בית קפה": "חלבי",

# ברים
  "בר מסעדה": "בר-מסעדה",
  "בר-מסעדה": "בר-מסעדה"

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

        # ===== אסייתי =====
        { "name": "נאיה", "type": "אסייתי", "lat": 31.772836, "lon": 35.192510 },
        { "name": "מינאטו", "type": "אסייתי", "lat": 31.780541, "lon": 35.219102 },
        { "name": "שיסו", "type": "אסייתי", "lat": 31.780010, "lon": 35.214882 },
        { "name": "טטאמי", "type": "אסייתי", "lat": 31.770412, "lon": 35.215991 },
        { "name": "סושי רחביה", "type": "אסייתי", "lat": 31.774431, "lon": 35.212731 },
        { "name": "מנדרין", "type": "אסייתי", "lat": 31.782111, "lon": 35.216442 },
        { "name": "ג'וי", "type": "אסייתי", "lat": 31.776900, "lon": 35.214100 },
        { "name": "ריבר נודלס בר", "type": "אסייתי", "lat": 31.778800, "lon": 35.215300 },
        { "name": "יאקימונו", "type": "אסייתי", "lat": 31.781214, "lon": 35.216114 },
        { "name": "פאן אסיה", "type": "אסייתי", "lat": 31.777914, "lon": 35.214714 },
        { "name": "ווק רום", "type": "אסייתי", "lat": 31.776214, "lon": 35.213514 },
        { "name": "נודלה האוס", "type": "אסייתי", "lat": 31.779214, "lon": 35.215214 },

        # ===== איטלקי =====
        { "name": "לוצ'נה", "type": "איטלקי", "lat": 31.780904, "lon": 35.220143 },
        { "name": "רוזה", "type": "איטלקי", "lat": 31.782590, "lon": 35.219890 },
        { "name": "פיקולינו", "type": "איטלקי", "lat": 31.776900, "lon": 35.225200 },
        { "name": "פיאנו פקטורי", "type": "איטלקי", "lat": 31.771300, "lon": 35.219000 },
        { "name": "בלייז פיצה", "type": "איטלקי", "lat": 31.774912, "lon": 35.219411 },
        { "name": "פיצה פיציקטו", "type": "איטלקי", "lat": 31.783144, "lon": 35.213774 },
        { "name": "פיצה רומא", "type": "איטלקי", "lat": 31.779212, "lon": 35.222014 },
        { "name": "פיצה מייקל", "type": "איטלקי", "lat": 31.790114, "lon": 35.205881 },
        { "name": "פיצה ביג מאמא", "type": "איטלקי", "lat": 31.788211, "lon": 35.207114 },
        { "name": "קפה רימון", "type": "איטלקי", "lat": 31.776812, "lon": 35.224812 },
        { "name": "קפה קדוש", "type": "איטלקי", "lat": 31.778214, "lon": 35.216214 },
        { "name": "לחם ארז", "type": "איטלקי", "lat": 31.785114, "lon": 35.216114 },

        # ===== בשרים =====
        { "name": "מחניודה", "type": "בשרים", "lat": 31.785720, "lon": 35.212320 },
        { "name": "אנג'ליקה", "type": "בשרים", "lat": 31.776900, "lon": 35.222300 },
        { "name": "בירנבאום", "type": "בשרים", "lat": 31.778322, "lon": 35.221998 },
        { "name": "הדקל 3", "type": "בשרים", "lat": 31.783210, "lon": 35.218450 },
        { "name": "שירת הבשר", "type": "בשרים", "lat": 31.773884, "lon": 35.214913 },
        { "name": "אנטריקוטי", "type": "בשרים", "lat": 31.777114, "lon": 35.219903 },
        { "name": "חצות", "type": "בשרים", "lat": 31.785900, "lon": 35.211400 },
        { "name": "M25", "type": "בשרים", "lat": 31.785200, "lon": 35.212000 },
        { "name": "צדקיהו", "type": "בשרים", "lat": 31.751900, "lon": 35.215400 },
        { "name": "עזרא", "type": "בשרים", "lat": 31.789900, "lon": 35.213900 },
        { "name": "אנג'ליקה ביסטרו", "type": "בשרים", "lat": 31.776714, "lon": 35.222514 },
        { "name": "לחיים גריל", "type": "בשרים", "lat": 31.783811, "lon": 35.221701 },

        # ===== המבורגר =====
        { "name": "אגאדיר", "type": "המבורגר", "lat": 31.777420, "lon": 35.219870 },
        { "name": "בלאק ירושלים", "type": "המבורגר", "lat": 31.775650, "lon": 35.213980 },
        { "name": "גולדיס", "type": "המבורגר", "lat": 31.794412, "lon": 35.205411 },
        { "name": "סולומונס", "type": "המבורגר", "lat": 31.785212, "lon": 35.211932 },
        { "name": "BBB ירושלים", "type": "המבורגר", "lat": 31.776700, "lon": 35.214300 },
        { "name": "בורגר רום", "type": "המבורגר", "lat": 31.777114, "lon": 35.213114 },
        { "name": "המבורגר פריים", "type": "המבורגר", "lat": 31.781778, "lon": 35.219821 },
        { "name": "בורגר האוס", "type": "המבורגר", "lat": 31.782211, "lon": 35.218114 },

        # ===== מזרחי =====
        { "name": "עזורה", "type": "מזרחי", "lat": 31.785500, "lon": 35.212600 },
        { "name": "אימא", "type": "מזרחי", "lat": 31.785100, "lon": 35.212900 },
        { "name": "חומוס בן סירא", "type": "מזרחי", "lat": 31.777300, "lon": 35.213700 },
        { "name": "אבו שוקרי", "type": "מזרחי", "lat": 31.778900, "lon": 35.234400 },
        { "name": "פיירוז", "type": "מזרחי", "lat": 31.776300, "lon": 35.229200 },
        { "name": "אקליפטוס", "type": "מזרחי", "lat": 31.778612, "lon": 35.229714 },
        { "name": "מסעדת מימון", "type": "מזרחי", "lat": 31.786714, "lon": 35.213114 },
        { "name": "טלה", "type": "מזרחי", "lat": 31.779314, "lon": 35.212714 },
        { "name": "בולגורג'י", "type": "מזרחי", "lat": 31.779914, "lon": 35.213314 },

        # ===== בתי קפה / בר =====
        { "name": "תמול שלשום", "type": "חלבי", "lat": 31.778400, "lon": 35.215200 },
        { "name": "נוקטורנו", "type": "חלבי", "lat": 31.778000, "lon": 35.214400 },
        { "name": "מונה", "type": "בר-מסעדה", "lat": 31.779600, "lon": 35.217800 },
        { "name": "אדום", "type": "בר-מסעדה", "lat": 31.779200, "lon": 35.217300 },
        { "name": "Chakra", "type": "בר-מסעדה", "lat": 31.780200, "lon": 35.218200 },
        { "name": "Satya", "type": "בר-מסעדה", "lat": 31.780900, "lon": 35.217900 },
        { "name": "Sarwa", "type": "בר-מסעדה", "lat": 31.781114, "lon": 35.214914 },
        { "name": "Reshta", "type": "בר-מסעדה", "lat": 31.779914, "lon": 35.213714 },
        { "name": "Beer Bazaar", "type": "בר-מסעדה", "lat": 31.785214, "lon": 35.212914 },
        { "name": "Modern (מוזיאון ישראל)", "type": "בר-מסעדה", "lat": 31.772514, "lon": 35.204114 },
        { "name": "Happy Fish", "type": "בר-מסעדה", "lat": 31.776882, "lon": 35.224911 },

        # ===== תוספות =====
        { "name": "Seoul House", "type": "אסייתי", "lat": 31.777900, "lon": 35.214900 },
        { "name": "Asia Station", "type": "אסייתי", "lat": 31.781500, "lon": 35.217200 },
        { "name": "Tokyo Sushi Bar", "type": "אסייתי", "lat": 31.774900, "lon": 35.212900 },
        { "name": "Ninja Ramen", "type": "אסייתי", "lat": 31.778200, "lon": 35.215900 },
        { "name": "Pomo", "type": "איטלקי", "lat": 31.779800, "lon": 35.218200 },
        { "name": "Luciana Cafe", "type": "איטלקי", "lat": 31.780450, "lon": 35.220210 },
        { "name": "Pizza Toscana", "type": "איטלקי", "lat": 31.774211, "lon": 35.211914 },
        { "name": "Pizza Napoli", "type": "איטלקי", "lat": 31.778900, "lon": 35.214200 },
        { "name": "Cafe Greg Cinema City", "type": "איטלקי", "lat": 31.751900, "lon": 35.204800 },
        { "name": "לחיים בשר", "type": "בשרים", "lat": 31.783600, "lon": 35.221500 },
        { "name": "המעשנה הירושלמית", "type": "בשרים", "lat": 31.781900, "lon": 35.214500 },
        { "name": "שגב", "type": "בשרים", "lat": 31.779900, "lon": 35.216700 },
        { "name": "בשר בר", "type": "בשרים", "lat": 31.777400, "lon": 35.214400 },
        { "name": "האטליז", "type": "בשרים", "lat": 31.785400, "lon": 35.212100 },
        { "name": "גריל מרקט", "type": "בשרים", "lat": 31.785000, "lon": 35.211800 },
        { "name": "מוזס ירושלים", "type": "המבורגר", "lat": 31.776600, "lon": 35.214600 },
        { "name": "Burger Bar", "type": "המבורגר", "lat": 31.777800, "lon": 35.213900 },
        { "name": "Iwo’s Meatburger", "type": "המבורגר", "lat": 31.779900, "lon": 35.215100 },
        { "name": "Meat Point Burger", "type": "המבורגר", "lat": 31.781100, "lon": 35.219200 },
        { "name": "לינא", "type": "מזרחי", "lat": 31.778600, "lon": 35.234600 },
        { "name": "נאפורא", "type": "מזרחי", "lat": 31.779400, "lon": 35.233800 },
        { "name": "אבו עלי", "type": "מזרחי", "lat": 31.776800, "lon": 35.229900 },
        { "name": "Bulghourji", "type": "מזרחי", "lat": 31.779700, "lon": 35.213200 },
        { "name": "Khan Restaurant", "type": "מזרחי", "lat": 31.770600, "lon": 35.222200 },
        { "name": "Cafe Shelomo", "type": "בית קפה", "lat": 31.778900, "lon": 35.214900 },
        { "name": "Cafe Nadi", "type": "בית קפה", "lat": 31.779200, "lon": 35.215100 },
        { "name": "Fringe", "type": "בית קפה", "lat": 31.780100, "lon": 35.217100 },
        { "name": "Talbiya", "type": "בר-מסעדה", "lat": 31.779300, "lon": 35.217400 },
        { "name": "Greek Salon Jerusalem", "type": "בר-מסעדה", "lat": 31.780900, "lon": 35.217900 },
        { "name": "Touro", "type": "בר-מסעדה", "lat": 31.771200, "lon": 35.223400 },
        { "name": "David 16", "type": "בר-מסעדה", "lat": 31.777900, "lon": 35.224300 }
    ]

    
    for item in data:
       if Restaurant.query.filter_by(name=item["name"]).first():
          continue

       db.session.add(Restaurant(
         name=item["name"],
         type=normalize_type(item.get("type")),
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

MAX_DISTANCE = 10.0   # ק"מ – מרחק עירוני סביר
MAX_WAIT = 60.0       # דקות – זמן המתנה מקסימלי

def hungarian_top_k_restaurants_for_client(
    client_lat,
    client_lon,
    restaurants,
    k=5,
    distance_weight=3.0,
    wait_weight=1.0
):
    remaining = restaurants.copy()
    ranked = []

    for _ in range(min(k, len(remaining))):
        cost_matrix = np.zeros((1, len(remaining)))

        for j, r in enumerate(remaining):
            d = haversine(client_lat, client_lon, r["lat"], r["lon"])
            wait, _ = weighted_prediction_for_restaurant(r)

            distance_norm = d / MAX_DISTANCE
            wait_norm = wait / MAX_WAIT

            cost_matrix[0, j] = (
            0.7 * distance_norm +   # העדפה למרחק
            0.3 * wait_norm)


        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        best_index = col_ind[0]

        best_restaurant = remaining[best_index]
        ranked.append(best_restaurant)
        remaining.pop(best_index)

    return ranked


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
        return render_template(
            "results_search.html",
            results=[],
            error="לא התקבל מיקום. יש ללחוץ על 'אתר אותי'."
        )

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
        b["id"] = r["id"]                 # ← זו השורה החסרה
        b["distance_km"] = round(d, 2)
        b["lat"] = r["lat"]
        b["lon"] = r["lon"]

        results.append(b)

        

    # 🔥 האלגוריתם ההונגרי – מחוץ ללולאה
    ranked_results = hungarian_top_k_restaurants_for_client(
    client_lat=lat,
    client_lon=lon,
    restaurants=results,
    k=5
)


    return render_template(
        "results_search.html",
        results=ranked_results,
        error=None
    )

# ======================= דיווח עומס =======================
@app.route("/report", methods=["GET", "POST"])
def report_api():
    if request.method == "GET":
        preselected = request.args.get("restaurant_id", type=int)
        return render_template(
            "report_form.html",
            restaurants=load_restaurants(),
            preselected=preselected
        )

    data = request.form

    restaurant_id = data.get("restaurant_id", "").strip()
    restaurant_name = data.get("restaurant_name", "").strip()
    wait = int(data["wait_minutes"])

    restaurant = None

    # 1️⃣ נבחרה מסעדה מהרשימה
    if restaurant_id:
        restaurant = Restaurant.query.get(int(restaurant_id))

    # 2️⃣ לא נבחרה – הוזן שם ידני
    elif restaurant_name:
        restaurant = Restaurant.query.filter(
            Restaurant.name.ilike(restaurant_name)
        ).first()

        # 3️⃣ לא קיימת – יוצרים חדשה
        if not restaurant:
            restaurant = Restaurant(
                name=restaurant_name,
                available=True,
                wait_time=wait
            )
            db.session.add(restaurant)
            db.session.commit()

    if not restaurant:
        return "שגיאה: לא נבחרה מסעדה", 400

    reports = load_reports()
    reports.append({
        "id": len(reports) + 1,
        "restaurant_id": restaurant.id,
        "wait_minutes": wait,
        "created_at": now_utc().isoformat(),
    })
    save_reports(reports)

    restaurant.wait_time = wait
    db.session.commit()

    return render_template(
        "report_thanks.html",
        restaurant=restaurant,
        wait=wait
    )


# ======================= מסך ניהול =======================
@app.route("/admin", methods=["GET", "POST"])
def admin_page():
    if request.method == "POST":
        name = request.form["name"]
        type_ = normalize_type(request.form["type"])
        lat = float(request.form["lat"])
        lon = float(request.form["lon"])

        db.session.add(
            Restaurant(
                name=name,
                type=type_,
                lat=lat,
                lon=lon
            )
        )
        db.session.commit()
        return redirect(url_for("admin_page"))

    return render_template("admin.html", restaurants=Restaurant.query.all())

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        cleanup_types_in_db()   # ← זה קריטי

        if Restaurant.query.count() == 0:
            seed_restaurants()

    app.run(debug=True)


