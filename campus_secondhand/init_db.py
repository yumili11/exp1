import sqlite3
import os

DATABASE = "campus.db"

if os.path.exists(DATABASE):
    os.remove(DATABASE)

conn = sqlite3.connect(DATABASE)
conn.execute("PRAGMA foreign_keys = ON")
cursor = conn.cursor()

# 创建 user 表
cursor.execute("""
CREATE TABLE user (
    user_id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    gender TEXT NOT NULL,
    phone TEXT NOT NULL
)
""")

# 创建 item 表
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

# 创建 orders 表
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

# 触发器：插入订单后自动更新商品为已售出
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

# 插入初始用户数据
users = [
    ("u001", "张三", "男", "13800000001"),
    ("u002", "李四", "女", "13800000002"),
    ("u003", "王五", "男", "13800000003"),
    ("u004", "赵六", "女", "13800000004")
]
cursor.executemany("INSERT INTO user VALUES (?, ?, ?, ?)", users)

# 注意：这里把有订单的商品初始状态先设为0
items = [
    ("i001", "高等数学教材", "学习用品", 25.0, "u001", 0),
    ("i002", "电风扇", "生活用品", 45.0, "u002", 0),
    ("i003", "羽毛球拍", "体育用品", 60.0, "u003", 0),
    ("i004", "台灯", "生活用品", 35.0, "u001", 0),
    ("i005", "Python程序设计", "学习用品", 30.0, "u004", 0)
]
cursor.executemany("INSERT INTO item VALUES (?, ?, ?, ?, ?, ?)", items)

# 插入订单后，触发器会把 i002 和 i004 自动改成已售出
orders = [
    ("o001", "u003", "i002", "2025-04-10"),
    ("o002", "u002", "i004", "2025-04-11")
]
cursor.executemany("INSERT INTO orders VALUES (?, ?, ?, ?)", orders)

# 创建视图
cursor.execute("""
CREATE VIEW sold_items_view AS
SELECT item.item_name, orders.buyer_id
FROM item
JOIN orders ON item.item_id = orders.item_id
WHERE item.status = 1
""")

cursor.execute("""
CREATE VIEW unsold_items_view AS
SELECT *
FROM item
WHERE status = 0
""")

conn.commit()
conn.close()

print("数据库初始化完成：campus.db")
