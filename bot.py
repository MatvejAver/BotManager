import telebot
import threading
import time
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from logic import TaskDatabase 
from config import TOKEN

bot = telebot.TeleBot(TOKEN)
db = TaskDatabase()


user_states = {}

class ReminderThread(threading.Thread):
    def __init__(self, bot, db, check_interval=60):
        threading.Thread.__init__(self)
        self.bot = bot
        self.db = db
        self.check_interval = check_interval
        self.daemon = True
        self.running = True
    
    def run(self):
        """Запуск потока с проверкой напоминаний"""
        print("🕒 Поток напоминаний запущен...")
        while self.running:
            try:
                self.check_reminders()
            except Exception as e:
                print(f"Ошибка в потоке напоминаний: {e}")
            time.sleep(self.check_interval)
    
    def check_reminders(self):
        """Проверка и отправка напоминаний"""
        tasks_to_remind = self.db.get_tasks_for_reminder()
        
        for task in tasks_to_remind:
            task_id, user_id, name, task_type, year, month, day, hour, minute = task

            markup = InlineKeyboardMarkup()
            complete_btn = InlineKeyboardButton(
                text="✅ Выполнено", 
                callback_data=f"complete_{task_id}"
            )
            markup.add(complete_btn)
            
            try:
                self.bot.send_message(
                    user_id,
                    f"⏰ **НАПОМИНАНИЕ!** ⏰\n\n"
                    f"📝 Задача: {name}\n"
                    f"📌 Тип: {task_type}\n"
                    f"⏱ Время: {day:02d}.{month:02d}.{year} {hour:02d}:{minute:02d}\n\n"
                    f"Нажмите кнопку ниже, когда выполните задачу:",
                    reply_markup=markup
                )

                self.db.mark_as_notified(task_id)
                print(f"✅ Напоминание отправлено для задачи {task_id} пользователю {user_id}")
                
            except Exception as e:
                print(f"❌ Ошибка при отправке напоминания для задачи {task_id}: {e}")
    
    def stop(self):
        """Остановка потока"""
        self.running = False

reminder_thread = ReminderThread(bot, db)
reminder_thread.start()

def create_inline_keyboard():
    markup = InlineKeyboardMarkup()
    work_today = InlineKeyboardButton(text="📋 Задачи", callback_data="work_today")
    work_last = InlineKeyboardButton(text="✅ Сделанные", callback_data="work_last")
    create_work = InlineKeyboardButton(text="➕ Создать", callback_data="create_work")
    del_work = InlineKeyboardButton(text="❌ Удалить", callback_data="del_work")
    markup.row(work_today, work_last)
    markup.row(create_work, del_work)
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id, 
        '''Привет!
Я бот-ежедневник с напоминаниями!

📋 Список задач
✅ Сделанные задачи
➕ Создать задачу
❌ Удалить задачу

Я напомню о задаче в указанное время!''', 
        reply_markup=create_inline_keyboard()
    )

@bot.message_handler(commands=['reminders'])
def check_reminders_command(message):
    """Команда для проверки статуса напоминаний"""
    bot.send_message(
        message.chat.id,
        "🕒 Система напоминаний активна!\n"
        "Я проверяю задачи каждую минуту."
    )

@bot.message_handler(content_types=['text'])
def text(message):
    user_id = message.from_user.id
    
    if user_id in user_states:
        state = user_states[user_id]
        
        if state['step'] == 1:
            state['name'] = message.text
            state['step'] = 2
            bot.send_message(message.chat.id, '''Введите дату задачи:
ГГГГ ММ ДД ЧЧ ММ
Например: 2026 03 15 14 30''')
            
        elif state['step'] == 2:
            date_parts = message.text.split()
            error = validate_date(date_parts)
            
            if error is None:
                state['date'] = [int(x) for x in date_parts]
                state['step'] = 3
                bot.send_message(message.chat.id, "Введите тип задачи (работа/учеба/личное/другое):")
            else:
                bot.send_message(message.chat.id, f"{error}\nПопробуйте еще раз:")
                
        elif state['step'] == 3:
            task_type = message.text
            state['type'] = task_type
            
            success = db.add_task(
                user_id=user_id,
                name=state['name'],
                task_type=task_type,
                date_list=state['date']
            )
            
            if success:
                d = state['date']
                date_str = f"{d[2]:02d}.{d[1]:02d}.{d[0]} {d[3]:02d}:{d[4]:02d}"
                bot.send_message(
                    message.chat.id, 
                    f"✅ Задача создана!\n\n"
                    f"📝 {state['name']}\n"
                    f"📌 Тип: {task_type}\n"
                    f"⏰ {date_str}\n\n"
                    f"⏱ Я напомню об этой задаче!"
                )
            else:
                bot.send_message(message.chat.id, "❌ Ошибка при создании задачи")
            
            del user_states[user_id]

def validate_date(date_parts):
    """Проверка корректности даты"""
    if len(date_parts) != 5:
        return "❌ Нужно ввести 5 чисел: год месяц день час минуты"
    
    try:
        numbers = [int(x) for x in date_parts]
    except ValueError:
        return "❌ Все значения должны быть числами"
    
    year, month, day, hour, minute = numbers

    now = datetime.now()
    try:
        task_time = datetime(year, month, day, hour, minute)
        if task_time < now:
            return "❌ Нельзя создать задачу на прошедшее время!"
    except ValueError:
        return "❌ Некорректная дата"
    
    if not (2026 <= year <= 2100):
        return "❌ Год должен быть от 2026 до 2100"
    if not (1 <= month <= 12):
        return "❌ Месяц должен быть от 1 до 12"
    if not (1 <= day <= 31):
        return "❌ День должен быть от 1 до 31"
    if not (0 <= hour <= 23):
        return "❌ Час должен быть от 0 до 23"
    if not (0 <= minute <= 59):
        return "❌ Минуты должны быть от 0 до 59"
    
    return None

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    user_id = call.from_user.id
    
    if call.data == "work_today":
        tasks = db.get_active_tasks(user_id)
        if tasks:
            response = "📋 **Активные задачи:**\n\n"
            for task in tasks:
                response += db.format_task_for_display(task) + "\n\n"
        else:
            response = "✅ Нет активных задач!"
        bot.send_message(call.message.chat.id, response)
        
    elif call.data == "work_last":
        tasks = db.get_completed_tasks(user_id)
        if tasks:
            response = "✅ **Выполненные задачи:**\n\n"
            for task in tasks:
                response += db.format_task_for_display(task) + "\n\n"
        else:
            response = "📭 Нет выполненных задач"
        bot.send_message(call.message.chat.id, response)
        
    elif call.data == "create_work":
        user_states[user_id] = {'step': 1}
        bot.send_message(call.message.chat.id, "Введите название задачи:")
        
    elif call.data == "del_work":
        tasks = db.get_active_tasks(user_id)
        if tasks:
            markup = InlineKeyboardMarkup()
            for task in tasks[:5]:
                btn = InlineKeyboardButton(
                    text=f"❌ {task[1][:20]}...", 
                    callback_data=f"delete_{task[0]}"
                )
                markup.add(btn)
            markup.add(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu"))
            bot.send_message(
                call.message.chat.id, 
                "Выберите задачу для удаления:",
                reply_markup=markup
            )
        else:
            bot.send_message(call.message.chat.id, "📭 Нет задач для удаления")
            
    elif call.data.startswith("delete_"):
        task_id = int(call.data.split("_")[1])
        if db.delete_task(task_id):
            bot.send_message(call.message.chat.id, "✅ Задача удалена!")
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка при удалении")
    
    elif call.data.startswith("complete_"):
        task_id = int(call.data.split("_")[1])
        if db.complete_task(task_id):
            try:
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=call.message.text + "\n\n✅ **Задача выполнена!**",
                    reply_markup=None
                )
            except:
                bot.send_message(call.message.chat.id, "✅ Задача выполнена!")
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка")
            
    elif call.data == "back_to_menu":
        bot.send_message(
            call.message.chat.id, 
            "Главное меню:", 
            reply_markup=create_inline_keyboard()
        )

if __name__ == "__main__":
    try:
        print("🚀 Бот запущен...")
        print("🕒 Напоминания активны")
        print("📁 База данных: tasks.db")
        bot.polling(none_stop=True)
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
    finally:
        reminder_thread.stop()
        db.close()
        print("👋 Все ресурсы освобождены")