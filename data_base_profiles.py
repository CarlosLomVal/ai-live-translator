# -*- coding: utf-8 -*-
"""
Created on Tue Nov  4 09:39:24 2025

@author: sebas
"""

import sqlite3

DB_PATH = "profiles.db"

def get_conn():
    return sqlite3.connect(DB_PATH) #we create a connection to de database

def create_table():
    conn = get_conn()
    cur = conn.cursor() #we create a cursor 
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY,
            source_language TEXT NOT NULL,
            target_language TEXT NOT NULL,
            voice_gen TEXT NOT NULL,
            register TEXT NOT NULL,
            max_latency_ms INTEGER NOT NULL
        );
    """)
    conn.commit() #we save changes
    conn.close()

def upsert_profile(user_id, source_language, target_language,voice_gen, register, max_latency_ms): #insert or update a user
    create_table() 
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO user_profiles (user_id, source_language, target_language, voice_gen, register, max_latency_ms)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            source_language=excluded.source_language,
            target_language=excluded.target_language,
            voice_gen=excluded.voice_gen,
            register=excluded.register,
            max_latency_ms=excluded.max_latency_ms;
    """, (user_id, source_language, target_language, voice_gen, register, max_latency_ms))
    conn.commit()
    conn.close()

def load_profile(user_id): #we read a certain profile for the use in the user_profile agent 
    create_table() 
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id, source_language, target_language, voice_gen, register, max_latency_ms FROM user_profiles WHERE user_id = ?;", (user_id,)) #here the SQL consult is done, we really dont want the whole table just the info of the profile 
    row = cur.fetchone() #we get the row of the profile
    conn.close()
    if row:
        return {
            "user_id": row[0],
            "source_language": row[1],
            "target_language": row[2],
            "voice_gen": row[3],
            "register": row[4],
            "max_latency_ms": row[5],
        }
    return None

def list_profiles() -> list:
    create_table()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM user_profiles ORDER BY user_id;")
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]