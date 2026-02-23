import sqlite3
c = sqlite3.connect(":memory:")
c.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
c.execute("INSERT INTO users (name) VALUES ('User 1')")
c.execute("INSERT INTO users (name) VALUES ('User 2')")
print("Integer array:", c.execute("SELECT * FROM users WHERE id IN (1)").fetchall())
print("String array:", c.execute("SELECT * FROM users WHERE id IN ('1')").fetchall())
