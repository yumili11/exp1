from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from contextlib import closing
from datetime import datetime

app = Flask(__name__)
app.secret_key = "campus_secondhand_secret_key"

DATABASE = "campus.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@app.route("/")
def index():
    return render_template("index.html")

# =========================
# 基础展示页面
# =========================
@app.route("/users")
def users():
    conn = get_db_connection()
    users_data = conn.execute("SELECT * FROM user ORDER BY user_id").fetchall()
    conn.close()
    return render_template("users.html", users=users_data)

@app.route("/items")
def items():
    conn = get_db_connection()
    items_data = conn.execute("""
        SELECT item.*, user.username AS seller_name
        FROM item
        JOIN user ON item.seller_id = user.user_id
        ORDER BY item.item_id
    """).fetchall()
    conn.close()
    return render_template("items.html", items=items_data)

@app.route("/orders")
def orders():
    conn = get_db_connection()
    orders_data = conn.execute("""
        SELECT orders.order_id, orders.order_date,
               item.item_name,
               buyer.username AS buyer_name
        FROM orders
        JOIN item ON orders.item_id = item.item_id
        JOIN user AS buyer ON orders.buyer_id = buyer.user_id
        ORDER BY orders.order_id
    """).fetchall()
    conn.close()
    return render_template("orders.html", orders=orders_data)

# =========================
# 数据操作
# =========================
@app.route("/add_item", methods=["POST"])
def add_item():
    item_id = request.form["item_id"]
    item_name = request.form["item_name"]
    category = request.form["category"]
    price = request.form["price"]
    seller_id = request.form["seller_id"]
    status = request.form["status"]

    try:
        conn = get_db_connection()
        conn.execute("""
            INSERT INTO item (item_id, item_name, category, price, seller_id, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (item_id, item_name, category, float(price), seller_id, int(status)))
        conn.commit()
        conn.close()
        flash("新商品添加成功！", "success")
    except Exception as e:
        flash(f"添加商品失败：{str(e)}", "danger")

    return redirect(url_for("items"))

@app.route("/update_price", methods=["POST"])
def update_price():
    item_id = request.form["item_id"]
    new_price = request.form["new_price"]

    try:
        conn = get_db_connection()
        conn.execute("UPDATE item SET price = ? WHERE item_id = ?", (float(new_price), item_id))
        conn.commit()
        conn.close()
        flash("商品价格修改成功！", "success")
    except Exception as e:
        flash(f"修改价格失败：{str(e)}", "danger")

    return redirect(url_for("items"))

@app.route("/delete_item/<item_id>")
def delete_item(item_id):
    try:
        conn = get_db_connection()
        item = conn.execute("SELECT * FROM item WHERE item_id = ?", (item_id,)).fetchone()
        if not item:
            flash("商品不存在！", "warning")
            conn.close()
            return redirect(url_for("items"))

        if item["status"] != 0:
            flash("只能删除未售出的商品！", "danger")
            conn.close()
            return redirect(url_for("items"))

        conn.execute("DELETE FROM item WHERE item_id = ?", (item_id,))
        conn.commit()
        conn.close()
        flash("未售出商品删除成功！", "success")
    except Exception as e:
        flash(f"删除商品失败：{str(e)}", "danger")

    return redirect(url_for("items"))

# =========================
# 基本查询
# =========================
@app.route("/queries")
def queries():
    conn = get_db_connection()

    unsold_items = conn.execute("SELECT * FROM item WHERE status = 0").fetchall()
    price_gt_30 = conn.execute("SELECT * FROM item WHERE price > 30").fetchall()
    daily_items = conn.execute("SELECT * FROM item WHERE category = '生活用品'").fetchall()
    u001_items = conn.execute("SELECT * FROM item WHERE seller_id = 'u001'").fetchall()

    sold_with_buyer = conn.execute("""
        SELECT item.item_name, user.username AS buyer_name
        FROM orders
        JOIN item ON orders.item_id = item.item_id
        JOIN user ON orders.buyer_id = user.user_id
    """).fetchall()

    order_detail = conn.execute("""
        SELECT item.item_name, user.username AS buyer_name, orders.order_date
        FROM orders
        JOIN item ON orders.item_id = item.item_id
        JOIN user ON orders.buyer_id = user.user_id
    """).fetchall()

    seller_u001_purchase = conn.execute("""
        SELECT item.item_id, item.item_name,
               CASE WHEN orders.item_id IS NOT NULL THEN '已购买' ELSE '未购买' END AS purchase_status
        FROM item
        LEFT JOIN orders ON item.item_id = orders.item_id
        WHERE item.seller_id = 'u001'
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

# =========================
# 聚合与分组
# =========================
@app.route("/stats")
def stats():
    conn = get_db_connection()

    total_items = conn.execute("SELECT COUNT(*) AS cnt FROM item").fetchone()["cnt"]
    category_counts = conn.execute("""
        SELECT category, COUNT(*) AS cnt
        FROM item
        GROUP BY category
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

# =========================
# 视图展示
# =========================
@app.route("/views")
def views_page():
    conn = get_db_connection()
    sold_view = conn.execute("SELECT * FROM sold_items_view").fetchall()
    unsold_view = conn.execute("SELECT * FROM unsold_items_view").fetchall()
    conn.close()
    return render_template("views.html", sold_view=sold_view, unsold_view=unsold_view)

# =========================
# 购买商品（事务）
# =========================
@app.route("/buy", methods=["GET", "POST"])
def buy():
    conn = get_db_connection()

    if request.method == "POST":
        order_id = request.form["order_id"]
        buyer_id = request.form["buyer_id"]
        item_id = request.form["item_id"]
        order_date = request.form["order_date"]

        try:
            conn.execute("BEGIN")

            item = conn.execute("SELECT * FROM item WHERE item_id = ?", (item_id,)).fetchone()
            if item is None:
                raise Exception("商品不存在")

            if item["status"] == 1:
                raise Exception("该商品已售出，不能重复购买")

            exists = conn.execute("SELECT * FROM orders WHERE item_id = ?", (item_id,)).fetchone()
            if exists:
                raise Exception("该商品已有订单记录，不能重复购买")

            conn.execute("""
                INSERT INTO orders (order_id, buyer_id, item_id, order_date)
                VALUES (?, ?, ?, ?)
            """, (order_id, buyer_id, item_id, order_date))

            conn.execute("UPDATE item SET status = 1 WHERE item_id = ?", (item_id,))

            conn.commit()
            flash("购买成功！订单已生成，商品状态已更新。", "success")
            conn.close()
            return redirect(url_for("orders"))

        except Exception as e:
            conn.rollback()
            flash(f"购买失败：{str(e)}", "danger")

    users_data = conn.execute("SELECT * FROM user ORDER BY user_id").fetchall()
    unsold_items = conn.execute("SELECT * FROM item WHERE status = 0 ORDER BY item_id").fetchall()
    conn.close()

    return render_template("buy.html", users=users_data, items=unsold_items, today=datetime.now().strftime("%Y-%m-%d"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
