from flask import Flask, render_template, request, redirect, url_for, session
import os
import uuid
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = "super_secret_key"

# =========================
# CONFIG POSTGRESQL
# =========================

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.secret_key = os.getenv("SECRET_KEY")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# =========================
# MODELE DATABASE
# =========================

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100))
    matricule = db.Column(db.String(100))
    code = db.Column(db.String(20), unique=True)
    status = db.Column(db.String(20))
    expiration = db.Column(db.DateTime)
    date = db.Column(db.DateTime, default=datetime.utcnow)

# =========================
# CREATION TABLES
# =========================

with app.app_context():
    db.create_all()

# =========================
# FONCTION VERIFICATION
# =========================

def verifier_ticket(code):

    ticket = Ticket.query.filter_by(code=code).first()

    if ticket is None:
        return "introuvable"

    if ticket.status == "utilise":
        return "utilise"

    if datetime.now() > ticket.expiration:
        return "expire"

    ticket.status = "utilise"
    db.session.commit()

    return "valide"

# =========================
# ROUTES PUBLIQUES
# =========================

@app.route("/")
def home():
    return render_template("public/index.html")


@app.route("/achat", methods=["GET", "POST"])
def achat():

    if request.method == "POST":
        nom = request.form.get("nom")
        matricule = request.form.get("matricule")

        code = str(uuid.uuid4())[:8]

        heure_paiement = datetime.now()
        expiration = heure_paiement + timedelta(hours=4)

        new_ticket = Ticket(
            nom=nom,
            matricule=matricule,
            code=code,
            status="valide",
            expiration=expiration,
            date=heure_paiement
        )

        db.session.add(new_ticket)
        db.session.commit()

        return render_template(
            "public/ticket.html",
            nom=nom,
            matricule=matricule,
            code=code,
            heure_paiement=heure_paiement.strftime("%d/%m/%Y %H:%M"),
            expiration=expiration.strftime("%d/%m/%Y %H:%M")
        )

    return render_template("public/achat.html")


@app.route("/verification", methods=["GET", "POST"])
def verification():

    resultat = None

    if request.method == "POST":
        code = request.form.get("code")

        if code:
            resultat = verifier_ticket(code)

    return render_template(
        "public/verification.html",
        resultat=resultat
    )


@app.route("/ticket/<code>")
def ticket(code):

    ticket = Ticket.query.filter_by(code=code).first()

    if ticket:
        return render_template("public/ticket.html", ticket=ticket)
    else:
        return "Ticket introuvable"

# =========================
# ADMIN
# =========================

@app.route("/admin/connexion_admin", methods=["GET", "POST"])
def connexion_admin():

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == "admin" and password == "1234":
            session["admin"] = True
            return redirect(url_for("dashboard_admin"))
        else:
            return render_template("admin/connexion_admin.html", erreur="Identifiants incorrects")

    return render_template("admin/connexion_admin.html")


@app.route("/admin/dashboard_admin")
def dashboard_admin():
    if "admin" not in session:
        return redirect(url_for("connexion_admin"))

    total = Ticket.query.count()
    utilises = Ticket.query.filter_by(status="utilise").count()
    valides = Ticket.query.filter_by(status="valide").count()
    expires = Ticket.query.filter_by(status="expire").count()

    date_du_jour = datetime.now().strftime("%d %B %Y")

    return render_template(
        "admin/dashboard_admin.html",
        total=total,
        utilises=utilises,
        valides=valides,
        expires=expires,
        date_du_jour=date_du_jour
    )


@app.route("/admin/repertoire")
def repertoire():
    if "admin" not in session:
        return redirect(url_for("connexion_admin"))

    search = request.args.get("search")
    statut = request.args.get("statut")

    query = Ticket.query

    if search:
        query = query.filter(
            (Ticket.nom.ilike(f"%{search}%")) |
            (Ticket.matricule.ilike(f"%{search}%"))
        )

    if statut and statut != "tous":
        query = query.filter_by(status=statut)

    tickets = query.order_by(Ticket.date.desc()).all()

    return render_template(
        "admin/repertoire.html",
        tickets=tickets,
        search=search,
        statut=statut
    )


@app.route("/admin/verification", methods=["GET", "POST"])
def verification_admin():
    if "admin" not in session:
        return redirect(url_for("connexion_admin"))

    ticket = None
    message = None

    if request.method == "POST":
        code = request.form.get("code")

        if code:
            ticket = Ticket.query.filter_by(code=code).first()

            if not ticket:
                message = "introuvable"

    return render_template(
        "admin/verification_admin.html",
        ticket=ticket,
        message=message
    )


@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("connexion_admin"))


if __name__ == "__main__":
    app.run(debug=True)