from functools import wraps

from flask import Flask, abort, jsonify, redirect, render_template, request, session, url_for, flash
from werkzeug.security import check_password_hash

from inventory import (
    adjust_stock,
    ensure_database,
    get_alerts,
    get_dashboard_counts,
    get_inventory_rows,
    get_logs,
    register_product,
    resolve_product_id,
)
from database import get_user
from scanner import scan_product_id_from_bytes


app = Flask(__name__)
app.secret_key = "inventory-prototype-secret"


PUBLIC_ENDPOINTS = {"login", "static"}


def login_required(view_function):
    @wraps(view_function)
    def wrapper(*args, **kwargs):
        if not session.get("username"):
            return redirect(url_for("login", next=request.path))
        return view_function(*args, **kwargs)

    return wrapper


def role_required(*allowed_roles):
    def decorator(view_function):
        @wraps(view_function)
        def wrapper(*args, **kwargs):
            if session.get("role") not in allowed_roles:
                abort(403)
            return view_function(*args, **kwargs)

        return wrapper

    return decorator


@app.before_request
def initialize_database() -> None:
    ensure_database()
    if request.endpoint in PUBLIC_ENDPOINTS or request.endpoint is None:
        return
    if not session.get("username"):
        return redirect(url_for("login", next=request.path))


@app.context_processor
def inject_session_context():
    return {
        "current_username": session.get("username"),
        "current_role": session.get("role"),
    }


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("username"):
        return redirect(url_for("index"))

    if request.method == "POST":
        username = str(request.form.get("username", "")).strip()
        password = str(request.form.get("password", ""))
        user = get_user(username)

        if user and check_password_hash(user["password_hash"], password):
            session["username"] = user["username"]
            session["role"] = user["role"]
            flash(f"{user['username']} 계정으로 로그인했습니다.", "success")
            return redirect(request.form.get("next") or url_for("index"))

        flash("아이디 또는 비밀번호가 올바르지 않습니다.", "danger")

    return render_template("login.html")


@app.get("/logout")
def logout():
    session.clear()
    flash("로그아웃되었습니다.", "success")
    return redirect(url_for("login"))


@app.get("/")
@login_required
def index():
    counts = get_dashboard_counts()
    return render_template("index.html", counts=counts)


@app.route("/products", methods=["GET", "POST"])
@login_required
@role_required("admin")
def products():
    if request.method == "POST":
        result = register_product(
            product_id=request.form.get("product_id", ""),
            name=request.form.get("name", ""),
            min_quantity=request.form.get("min_quantity", 0),
        )
        flash(result["message"], "success" if result["ok"] else "danger")
        return redirect(url_for("products"))

    return render_template(
        "products.html",
        products=get_inventory_rows(),
    )


@app.route("/inventory", methods=["GET", "POST"])
@login_required
def inventory():
    if request.method == "POST":
        product_id = resolve_product_id(request.form.get("product_id", ""))
        uploaded_image = request.files.get("scan_image")
        if uploaded_image and uploaded_image.filename:
            scanned_value = scan_product_id_from_bytes(uploaded_image.read())
            product_id = resolve_product_id(scanned_value)
            if not product_id:
                flash("업로드된 이미지에서 QR/바코드를 인식하지 못했습니다.", "danger")
                return redirect(url_for("inventory"))

        action = request.form.get("action", "in")
        quantity = request.form.get("quantity", 1)

        result = adjust_stock(
            product_id=product_id,
            action=action,
            quantity=quantity,
            username=session.get("username", "system"),
        )
        flash(result["message"], "success" if result["ok"] else "danger")
        return redirect(url_for("inventory"))

    return render_template(
        "inventory.html",
        products=get_inventory_rows(),
    )


@app.get("/logs")
@login_required
def logs():
    return render_template("logs.html", logs=get_logs())


@app.get("/alerts")
@login_required
def alerts():
    return render_template("alerts.html", alerts=get_alerts())


@app.post("/api/scan")
@login_required
def api_scan():
    payload = request.get_json(silent=True) or request.form
    product_id = resolve_product_id(payload.get("product_id", ""))
    action = payload.get("action", "in")
    quantity = payload.get("quantity", 1)

    result = adjust_stock(
        product_id=product_id,
        action=action,
        quantity=quantity,
        username=session.get("username", "system"),
    )
    status_code = 200 if result["ok"] else 400
    return jsonify(result), status_code


@app.get("/api/inventory")
@login_required
def api_inventory():
    return jsonify(get_inventory_rows())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)