import os
import psycopg2
from faker import Faker
import random
from datetime import datetime, timedelta

# Настройки подключения к твоей бд NestJS
DB_HOST = "localhost"
DB_PORT = "5433"
DB_NAME = "kanban"
DB_USER = "postgres"
DB_PASSWORD = "mysecretpassword"

fake = Faker(['ru_RU', 'en_US'])


def connect_db():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


def clear_and_seed_data():
    conn = connect_db()
    cursor = conn.cursor()

    print("Проверка и создание изолированных аналитических таблиц...")
    
    # Создаем таблицы со специальным префиксом analytics_, чтобы не конфликтовать с NestJS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analytics_boards (
            board_id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analytics_columns (
            column_id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            position INT NOT NULL,
            board_id INT REFERENCES analytics_boards(board_id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analytics_tasks (
            task_id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            priority VARCHAR(50) NOT NULL,
            column_id INT REFERENCES analytics_columns(column_id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            completed_at TIMESTAMP
        );
    """)

    print("Очистка аналитических данных...")
    cursor.execute("TRUNCATE TABLE analytics_tasks, analytics_columns, analytics_boards RESTART IDENTITY CASCADE;")

    print("Генерация тестовых досок и колонок...")
    cursor.execute(
        "INSERT INTO analytics_boards (title, created_at, updated_at) VALUES (%s, NOW(), NOW()) RETURNING board_id;",
        ("Основной IT-Продукт (Разработка)",))
    board_id = cursor.fetchone()

    statuses = ['ToDo', 'In Progress', 'Done']
    column_ids = {}
    for pos, status in enumerate(statuses):
        cursor.execute(
            "INSERT INTO analytics_columns (title, position, board_id, created_at, updated_at) VALUES (%s, %s, %s, NOW(), NOW()) RETURNING column_id;",
            (status, pos, board_id))
        column_ids[status] = cursor.fetchone()

    print("Генерация 300 реалистичных задач для аналитики...")
    now = datetime.now()
    start_date = now - timedelta(days=90)

    priorities = ['Low', 'Medium', 'High', 'Blocker']
    types = ['Feature', 'Bug', 'Task']

    for _ in range(300):
        created_at = fake.date_time_between(start_date=start_date, end_date=now)
        rand = random.random()

        if rand < 0.10:
            current_column_id = column_ids['ToDo']
            updated_at = created_at
            completed_at = None
        elif rand < 0.30:
            current_column_id = column_ids['In Progress']
            updated_at = created_at + timedelta(hours=random.randint(1, 48))
            completed_at = None
        else:
            current_column_id = column_ids['Done']
            updated_at = created_at + timedelta(hours=random.randint(1, 48))
            completed_at = updated_at + timedelta(days=random.randint(1, 7), hours=random.randint(1, 23))

        title = f"[{random.choice(types)}] {fake.sentence(nb_words=4)}"
        description = fake.paragraph(nb_sentences=2)
        priority = random.choice(priorities)

        cursor.execute(
            """
            INSERT INTO analytics_tasks (title, description, priority, column_id, created_at, updated_at, completed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
            """,
            (title, description, priority, current_column_id, created_at, updated_at, completed_at)
        )

    conn.commit()
    cursor.close()
    conn.close()
    print("База данных успешно наполнена аналитическими данными!")


if __name__ == "__main__":
    clear_and_seed_data()