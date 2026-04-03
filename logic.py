import sqlite3
from datetime import datetime

class TaskDatabase:
    def __init__(self, db_name='tasks.db'):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                type TEXT,
                year INTEGER,
                month INTEGER,
                day INTEGER,
                hour INTEGER,
                minute INTEGER,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.cursor.execute("PRAGMA table_info(tasks)")
        columns = [column[1] for column in self.cursor.fetchall()]
    
        if 'notified' not in columns:
            try:
                self.cursor.execute('ALTER TABLE tasks ADD COLUMN notified BOOLEAN DEFAULT 0')
            except Exception as e:
                pass
            
            self.conn.commit()
    
    def add_task(self, user_id, name, task_type, date_list):
        """Добавление новой задачи"""
        try:
            self.cursor.execute('''
                INSERT INTO tasks (user_id, name, type, year, month, day, hour, minute)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, name, task_type, date_list[0], date_list[1], 
                  date_list[2], date_list[3], date_list[4]))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка при добавлении задачи: {e}")
            return False
    
    def get_active_tasks(self, user_id):
        """Получение активных задач пользователя"""
        self.cursor.execute('''
            SELECT id, name, type, year, month, day, hour, minute 
            FROM tasks 
            WHERE user_id = ? AND status = 'active'
            ORDER BY year, month, day, hour, minute
        ''', (user_id,))
        return self.cursor.fetchall()
    
    def get_completed_tasks(self, user_id):
        """Получение выполненных задач пользователя"""
        self.cursor.execute('''
            SELECT id, name, type, year, month, day, hour, minute 
            FROM tasks 
            WHERE user_id = ? AND status = 'completed'
            ORDER BY created_at DESC
            LIMIT 10
        ''', (user_id,))
        return self.cursor.fetchall()
    
    def get_tasks_for_reminder(self):
        """Получение задач, которые нужно напомнить (текущее время, не напомненные)"""
        now = datetime.now()
        self.cursor.execute('''
            SELECT id, user_id, name, type, year, month, day, hour, minute 
            FROM tasks 
            WHERE status = 'active' 
            AND notified = 0
            AND year = ? AND month = ? AND day = ? AND hour = ? AND minute = ?
        ''', (now.year, now.month, now.day, now.hour, now.minute))
        return self.cursor.fetchall()
    
    def mark_as_notified(self, task_id):
        """Отметить задачу как напомненную"""
        self.cursor.execute('UPDATE tasks SET notified = 1 WHERE id = ?', (task_id,))
        self.conn.commit()
    
    def complete_task(self, task_id):
        """Отметить задачу как выполненную"""
        self.cursor.execute('''
            UPDATE tasks SET status = 'completed' 
            WHERE id = ?
        ''', (task_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def delete_task(self, task_id):
        """Удаление задачи"""
        self.cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def format_task_for_display(self, task):
        """Форматирование задачи для вывода"""
        task_id, name, task_type, year, month, day, hour, minute = task
        return f"📝 {name}\n📌 Тип: {task_type}\n⏰ {day:02d}.{month:02d}.{year} {hour:02d}:{minute:02d}\nID: {task_id}"
    
    def close(self):
        """Закрытие соединения с БД"""
        self.conn.close()