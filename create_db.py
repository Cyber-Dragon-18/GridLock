import pandas as pd
import sqlite3

from fontTools.subset import subset

file_path = '67676767667.xlsx'
db_path = "67676767676.db"

# Criar as tabelas do modelo relacional
create_tables_sql = """
CREATE TABLE IF NOT EXISTS STORAGE (
    Storage_ID INTEGER PRIMARY KEY,
    Storage_Plan INTEGER
);

CREATE TABLE IF NOT EXISTS USER (
    User_ID INTEGER PRIMARY KEY,
    First_Name VARCHAR(255),
    Last_Name VARCHAR(255),
    Email VARCHAR(255),
    Password VARCHAR(255),
    Storage_ID INTEGER REFERENCES STORAGE (Storage_ID)
);

CREATE TABLE IF NOT EXISTS FILE (
    File_ID INTEGER PRIMARY KEY,
    User_ID INTEGER REFERENCES USER (User_ID),
    File_Name VARCHAR(255),
    Status VARCHAR(255),
    File_Size FLOAT,
    File_Type VARCHAR(255),
    Date_Added TIMESTAMP,
);

CREATE TABLE IF NOT EXISTS FILE_TYPE (
    FileJ_Type_ID INTEGER PRIMARY KEY,
    File_Type VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS JOBS (
    Job_ID INTEGER PRIMARY KEY,
    User_ID INTEGER REFERENCES USER (User_ID),
    File_Job VARCHAR(255),
    FileJ_Type_ID INTEGER REFERENCES FILE_TYPE (FileJ_Type_ID),
    Status VARCHAR(255),
    Job_Size INTEGRER,
);
"""