import sqlite3
import os

DATABASE = "campus.db"

# 如果数据库已存在，先删除，避免旧数据和旧结构干扰
if os.path.exists(DATABASE):
    os.remove(DATABASE)

conn = sqlite3.connect(DATABASE)
conn.execute("PRAGMA foreign_keys = ON")
cursor = conn.cursor()

# =========================
# 1. 创建 user 表
# =========================
cursor.execute("""
CREATE TABLE user (
    user_id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    password TEXT NOT NULL,
    gender TEXT NOT NULL,
    phone TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'user'))
)
""")

# =========================
# 2. 创建 item 表
# status: 0=未售出, 1=已售出
# =========================
cursor.execute("""
CREATE TABLE item (
    item_id TEXT PRIMARY KEY,
    item_name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL CHECK(price >= 0),
    seller_id TEXT NOT NULL,
    status INTEGER NOT NULL CHECK(status IN (0, 1)),
    FOREIGN KEY (seller_id) REFERENCES user(user_id)
)
""")

# =========================
# 3. 创建 orders 表
# 每个商品最多只能交易一次，所以 item_id 唯一
# =========================
cursor.execute("""
CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,
    buyer_id TEXT NOT NULL,
    item_id TEXT NOT NULL UNIQUE,
    order_date TEXT NOT NULL,
    FOREIGN KEY (buyer_id) REFERENCES user(user_id),
    FOREIGN KEY (item_id) REFERENCES item(item_id)
)
""")

# =========================
# 4. 插入初始用户数据
# =========================
users = [
    ("u001", "张三", "123456", "男", "13800000001", "admin"),
    ("u002", "李四", "123456", "女", "13800000002", "user"),
    ("u003", "王五", "123456", "男", "13800000003", "user"),
    ("u004", "赵六", "123456", "女", "13800000004", "user")
]
cursor.executemany("INSERT INTO user VALUES (?, ?, ?, ?, ?, ?)", users)

# =========================
# 5. 插入初始商品数据
# 注意：这里全部先设为未售出 status=0
# 这样才能先插入订单，再更新状态
# =========================
items = [
    ("i001", "高等数学教材", "学习用品", 25.0, "u001", 0),
    ("i002", "电风扇", "生活用品", 45.0, "u002", 0),
    ("i003", "羽毛球拍", "体育用品", 60.0, "u003", 0),
    ("i004", "台灯", "生活用品", 35.0, "u001", 0),
    ("i005", "Python程序设计", "学习用品", 30.0, "u004", 0)
]
cursor.executemany("INSERT INTO item VALUES (?, ?, ?, ?, ?, ?)", items)

# =========================
# 6. 插入初始订单数据
# 先插入订单，再更新对应商品状态
# =========================
orders = [
    ("o001", "u003", "i002", "2025-04-10"),
    ("o002", "u002", "i004", "2025-04-11")
]
cursor.executemany("INSERT INTO orders VALUES (?, ?, ?, ?)", orders)

# 把已有订单的商品状态更新为已售出
cursor.execute("""
UPDATE item
SET status = 1
WHERE item_id IN (SELECT item_id FROM orders)
""")

# =========================
# 7. 创建触发器
# 现在放在初始化数据之后创建，避免影响初始导入
# =========================

# 插入订单前检查商品是否未售出
cursor.execute("""
CREATE TRIGGER check_order_insert
BEFORE INSERT ON orders
FOR EACH ROW
BEGIN
    SELECT CASE
        WHEN (SELECT COUNT(*) FROM item WHERE item_id = NEW.item_id) = 0
        THEN RAISE(ABORT, '商品不存在')
    END;

    SELECT CASE
        WHEN (SELECT status FROM item WHERE item_id = NEW.item_id) != 0
        THEN RAISE(ABORT, '商品已售出，不能重复购买')
    END;
END;
""")

# 插入订单后，自动把商品改为已售出
cursor.execute("""
CREATE TRIGGER update_item_status_after_order
AFTER INSERT ON orders
FOR EACH ROW
BEGIN
    UPDATE item
    SET status = 1
    WHERE item_id = NEW.item_id;
END;
""")

# 防止把已有订单的商品改回未售出
cursor.execute("""
CREATE TRIGGER prevent_invalid_status_update
BEFORE UPDATE OF status ON item
FOR EACH ROW
BEGIN
    SELECT CASE
        WHEN NEW.status = 0 AND EXISTS (
            SELECT 1 FROM orders WHERE item_id = NEW.item_id
        )
        THEN RAISE(ABORT, '该商品已有订单，不能改回未售出')
    END;
END;
""")

# =========================
# 8. 创建视图
# =========================

# 已售商品视图（商品名 + 买家ID）
cursor.execute("""
CREATE VIEW sold_items_view AS
SELECT item.item_name, orders.buyer_id
FROM item
JOIN orders ON item.item_id = orders.item_id
WHERE item.status = 1
""")

# 未售商品视图
cursor.execute("""
CREATE VIEW unsold_items_view AS
SELECT item_id, item_name, category, price, seller_id
FROM item
WHERE status = 0
""")

conn.commit()
conn.close()

print("数据库初始化完成：campus.db")
print("管理员：u001 / 123456")
print("普通用户：u002 / 123456, u003 / 123456, u004 / 123456")
