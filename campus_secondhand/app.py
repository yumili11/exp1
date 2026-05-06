from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from functools import wraps
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = "campus_secondhand_secret_key"
DATABASE = "campus.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("请先登录后再访问。")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("请先登录后再访问。")
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("无权限访问该页面！普通用户只能查询数据。")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return wrapper

@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/index")
@login_required
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_id = request.form["user_id"].strip()
        password = request.form["password"].strip()

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM user WHERE user_id = ? AND password = ?",
            (user_id, password)
        ).fetchone()
        conn.close()

        if user:
            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            flash(f"登录成功，欢迎你：{user['username']}！")
            return redirect(url_for("index"))
        else:
            flash("账号或密码错误，请重新输入。")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("你已成功退出登录。")
    return redirect(url_for("login"))

@app.route("/users")
@admin_required
def users():
    conn = get_db_connection()
    users_data = conn.execute("""
        SELECT user_id, username, gender, phone, role
        FROM user
        ORDER BY user_id
    """).fetchall()
    conn.close()
    return render_template("users.html", users=users_data)

@app.route("/items")
@login_required
def items():
    keyword = request.args.get("keyword", "").strip()
    category = request.args.get("category", "").strip()
    seller_id = request.args.get("seller_id", "").strip()
    status = request.args.get("status", "").strip()
    min_price = request.args.get("min_price", "").strip()
    max_price = request.args.get("max_price", "").strip()
    sort_by = request.args.get("sort_by", "").strip()

    conn = get_db_connection()

    categories = conn.execute("SELECT DISTINCT category FROM item ORDER BY category").fetchall()
    sellers = conn.execute("SELECT user_id, username FROM user ORDER BY user_id").fetchall()

    sql = """
        SELECT item.*, user.username AS seller_name
        FROM item
        JOIN user ON item.seller_id = user.user_id
        WHERE 1=1
    """
    params = []

    if keyword:
        sql += " AND item.item_name LIKE ?"
        params.append(f"%{keyword}%")

    if category:
        sql += " AND item.category = ?"
        params.append(category)

    if seller_id:
        sql += " AND item.seller_id = ?"
        params.append(seller_id)

    if status != "":
        sql += " AND item.status = ?"
        params.append(int(status))

    if min_price:
        try:
            sql += " AND item.price >= ?"
            params.append(float(min_price))
        except ValueError:
            flash("最低价格格式不正确。")

    if max_price:
        try:
            sql += " AND item.price <= ?"
            params.append(float(max_price))
        except ValueError:
            flash("最高价格格式不正确。")

    if sort_by == "price_asc":
        sql += " ORDER BY item.price ASC"
    elif sort_by == "price_desc":
        sql += " ORDER BY item.price DESC"
    elif sort_by == "name_asc":
        sql += " ORDER BY item.item_name ASC"
    elif sort_by == "name_desc":
        sql += " ORDER BY item.item_name DESC"
    else:
        sql += " ORDER BY item.item_id ASC"

    items_data = conn.execute(sql, params).fetchall()
    conn.close()

    filters = {
        "keyword": keyword,
        "category": category,
        "seller_id": seller_id,
        "status": status,
        "min_price": min_price,
        "max_price": max_price,
        "sort_by": sort_by
    }

    return render_template(
        "items.html",
        items=items_data,
        categories=categories,
        sellers=sellers,
        filters=filters
    )

@app.route("/add_item", methods=["POST"])
@admin_required
def add_item():
    item_id = request.form["item_id"].strip()
    item_name = request.form["item_name"].strip()
    category = request.form["category"].strip()
    price = request.form["price"].strip()
    seller_id = request.form["seller_id"].strip()
    status = request.form["status"].strip()

    try:
        if not item_id or not item_name or not category or not price or not seller_id:
            raise Exception("所有字段都不能为空。")

        price_value = float(price)
        if price_value < 0:
            raise Exception("价格不能为负数。")

        conn = get_db_connection()
        conn.execute("""
            INSERT INTO item (item_id, item_name, category, price, seller_id, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (item_id, item_name, category, price_value, seller_id, int(status)))
        conn.commit()
        conn.close()
        flash("新商品添加成功！")
    except Exception as e:
        flash(f"添加商品失败：{str(e)}")

    return redirect(url_for("items"))

@app.route("/update_price", methods=["POST"])
@admin_required
def update_price():
    item_id = request.form["item_id"].strip()
    new_price = request.form["new_price"].strip()

    try:
        if not item_id or not new_price:
            raise Exception("商品编号和新价格不能为空。")

        price_value = float(new_price)
        if price_value < 0:
            raise Exception("价格不能为负数。")

        conn = get_db_connection()
        result = conn.execute(
            "UPDATE item SET price = ? WHERE item_id = ?",
            (price_value, item_id)
        )
        if result.rowcount == 0:
            raise Exception("商品不存在。")
        conn.commit()
        conn.close()
        flash("商品价格修改成功！")
    except Exception as e:
        flash(f"修改价格失败：{str(e)}")

    return redirect(url_for("items"))

@app.route("/delete_item/<item_id>")
@admin_required
def delete_item(item_id):
    try:
        conn = get_db_connection()
        item = conn.execute("SELECT * FROM item WHERE item_id = ?", (item_id,)).fetchone()

        if not item:
            conn.close()
            flash("商品不存在。")
            return redirect(url_for("items"))

        if item["status"] != 0:
            conn.close()
            flash("只能删除未售出的商品！")
            return redirect(url_for("items"))

        conn.execute("DELETE FROM item WHERE item_id = ?", (item_id,))
        conn.commit()
        conn.close()
        flash("未售出商品删除成功！")
    except Exception as e:
        flash(f"删除商品失败：{str(e)}")

    return redirect(url_for("items"))

@app.route("/buy_now/<item_id>", methods=["POST"])
@login_required
def buy_now(item_id):
    if session.get("role") != "user":
        flash("只有普通用户可以购买商品。")
        return redirect(url_for("items"))

    conn = get_db_connection()

    try:
        conn.execute("BEGIN")

        item = conn.execute("SELECT * FROM item WHERE item_id = ?", (item_id,)).fetchone()
        if item is None:
            raise Exception("商品不存在。")

        if item["status"] == 1:
            raise Exception("该商品已售出，不能重复购买。")

        order_exists = conn.execute("SELECT * FROM orders WHERE item_id = ?", (item_id,)).fetchone()
        if order_exists:
            raise Exception("该商品已有订单记录，不能重复购买。")

        order_id = "o" + uuid.uuid4().hex[:8]
        order_date = datetime.now().strftime("%Y-%m-%d")

        conn.execute("""
            INSERT INTO orders (order_id, buyer_id, item_id, order_date)
            VALUES (?, ?, ?, ?)
        """, (order_id, session["user_id"], item_id, order_date))

        conn.execute("UPDATE item SET status = 1 WHERE item_id = ?", (item_id,))
        conn.commit()
        flash("购买成功！订单已生成，商品状态已更新为已售出。")
    except Exception as e:
        conn.rollback()
        flash(f"购买失败：{str(e)}")
    finally:
        conn.close()

    return redirect(url_for("items"))

@app.route("/orders")
@login_required
def orders():
    conn = get_db_connection()

    if session.get("role") == "admin":
        orders_data = conn.execute("""
            SELECT orders.order_id, orders.order_date,
                   item.item_name,
                   buyer.username AS buyer_name
            FROM orders
            JOIN item ON orders.item_id = item.item_id
            JOIN user AS buyer ON orders.buyer_id = buyer.user_id
            ORDER BY orders.order_id
        """).fetchall()
    else:
        orders_data = conn.execute("""
            SELECT orders.order_id, orders.order_date,
                   item.item_name,
                   buyer.username AS buyer_name
            FROM orders
            JOIN item ON orders.item_id = item.item_id
            JOIN user AS buyer ON orders.buyer_id = buyer.user_id
            WHERE orders.buyer_id = ?
            ORDER BY orders.order_id
        """, (session["user_id"],)).fetchall()

    conn.close()
    return render_template("orders.html", orders=orders_data)

@app.route("/queries")
@login_required
def queries():
    conn = get_db_connection()

    # 基本查询
    unsold_items = conn.execute("SELECT * FROM item WHERE status = 0").fetchall()
    price_gt_30 = conn.execute("SELECT * FROM item WHERE price > 30").fetchall()
    daily_items = conn.execute("SELECT * FROM item WHERE category = '生活用品'").fetchall()
    u001_items = conn.execute("SELECT * FROM item WHERE seller_id = 'u001'").fetchall()

    # 连接查询
    sold_with_buyer = conn.execute("""
        SELECT item.item_name, user.username AS buyer_name
        FROM orders
        JOIN item ON orders.item_id = item.item_id
        JOIN user ON orders.buyer_id = user.user_id
        ORDER BY item.item_id
    """).fetchall()

    order_detail = conn.execute("""
        SELECT item.item_name, user.username AS buyer_name, orders.order_date
        FROM orders
        JOIN item ON orders.item_id = item.item_id
        JOIN user ON orders.buyer_id = user.user_id
        ORDER BY orders.order_id
    """).fetchall()

    seller_u001_purchase = conn.execute("""
        SELECT item.item_id, item.item_name,
               CASE
                   WHEN orders.item_id IS NOT NULL THEN '已购买'
                   ELSE '未购买'
               END AS purchase_status
        FROM item
        LEFT JOIN orders ON item.item_id = orders.item_id
        WHERE item.seller_id = 'u001'
        ORDER BY item.item_id
    """).fetchall()

    conn.close()

    return render_template(
        "queries.html",
        unsold_items=unsold_items,
        price_gt_30=price_gt_30,
        daily_items=daily_items,
        u001_items=u001_items,
        sold_with_buyer=sold_with_buyer,
        order_detail=order_detail,
        seller_u001_purchase=seller_u001_purchase
    )

@app.route("/stats")
@login_required
def stats():
    conn = get_db_connection()

    total_items = conn.execute("SELECT COUNT(*) AS cnt FROM item").fetchone()["cnt"]

    category_counts = conn.execute("""
        SELECT category, COUNT(*) AS cnt
        FROM item
        GROUP BY category
        ORDER BY cnt DESC
    """).fetchall()

    avg_price = conn.execute("SELECT AVG(price) AS avg_price FROM item").fetchone()["avg_price"]

    top_user = conn.execute("""
        SELECT user.username, COUNT(item.item_id) AS item_count
        FROM user
        LEFT JOIN item ON user.user_id = item.seller_id
        GROUP BY user.user_id, user.username
        ORDER BY item_count DESC
        LIMIT 1
    """).fetchone()

    conn.close()

    return render_template(
        "stats.html",
        total_items=total_items,
        category_counts=category_counts,
        avg_price=avg_price,
        top_user=top_user
    )

@app.route("/views")
@login_required
def views_page():
    conn = get_db_connection()

    sold_view = conn.execute("SELECT * FROM sold_items_view").fetchall()
    unsold_view = conn.execute("SELECT * FROM unsold_items_view").fetchall()

    conn.close()
    return render_template("views.html", sold_view=sold_view, unsold_view=unsold_view)

@app.route("/security")
@login_required
def security():
    return render_template("security.html")

@app.route("/concurrency")
@login_required
def concurrency():
    return render_template("concurrency.html")

if __name__ == "__main__":
    app.run(debug=True)
