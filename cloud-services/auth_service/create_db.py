import sqlite3

db_path="users.db"

create_tables_sql="""
CREATE TABLE IF NOT EXISTS USER(
	User_ID INTEGER PRIMARY KEY,
	First_Name VARCHAR(255),
	Last_Name VARCHAR(255),
	Email VARCHAR(255) UNIQUE NOT NULL,
	Password VARCHAR(255) UNIQUE NOT NULL,
	Storage_ID INTEGER REFERENCES STORAGE (Storage_ID)
);
"""

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.executescript(create_tables_sql)
conn.commit()
conn.close()

print("Database created successfully!")
