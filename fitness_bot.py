from dotenv import load_dotenv
import os
from flask import Flask
from threading import Thread
import sqlite3
import matplotlib.pyplot as plt
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from datetime import datetime
import random  # Добавлен для случайного выбора тренировки

app_flask = Flask(__name__)


@app_flask.route("/")
def home():
    return "Bot is running!"


def run_flask():
    app_flask.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))


# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("Ошибка: переменная окружения BOT_TOKEN не найдена.")
    exit(1)

# Константы состояний для ConversationHandler
WEIGHT, HEIGHT, WAIST, CALORIES_SPENT, CALORIES_EATEN, STEPS = range(6)

# Инициализация базы данных SQLite
conn = sqlite3.connect("fitness_data.db", check_same_thread=False)
c = conn.cursor()

# Создание таблицы, если её нет
c.execute(
    """CREATE TABLE IF NOT EXISTS user_parameters (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    date TEXT,
    weight REAL,
    height REAL,
    waist REAL,
    activity_level TEXT,
    calories_spent INTEGER,
    calories_eaten INTEGER,
    steps INTEGER,
    bmi REAL
)"""
)
conn.commit()

# Словарь с тренировками
WORKOUTS = {
    "Руки": [
        "1. Подъем гантелей на бицепс 3x15\n2. Отжимания на трицепс 3x12\n3. Молотковые сгибания 4x10",
        "1. Французский жим 4x12\n2. Концентрированный подъем на бицепс 3x15\n3. Разгибания в кроссовере 3x20",
        "1. Подтягивания обратным хватом 4x8\n2. Жим гантелей сидя 3x10\n3. Сгибания Зоттмана 3x12",
    ],
    "Ноги-Ягодицы": [
        "1. Приседания с весом 4x15\n2. Выпады с гантелями 3x12\n3. Ягодичный мостик 4x20",
        "1. Румынская тяга 4x12\n2. Болгарские сплит-приседы 3x10\n3. Подъемы на носки 4x25",
        "1. Становая тяга сумо 4x8\n2. Махи гирей 3x15\n3. Боковые выпады 4x12",
    ],
    "Спина": [
        "1. Тяга верхнего блока 4x12\n2. Тяга гантели в наклоне 3x10\n3. Гиперэкстензия 4x15",
        "1. Подтягивания широким хватом 4x8\n2. Тяга Т-грифа 3x12\n3. Пуловер с гантелью 3x15",
        "1. Становая тяга 4x6\n2. Тяга нижнего блока 3x12\n3. Шраги с гантелями 4x20",
    ],
    "Пресс": [
        "1. Скручивания 4x25\n2. Планка 3x1 минута\n3. Подъем ног в висе 3x15",
        "1. Русские скручивания 4x20\n2. Боковая планка 3x40 сек\n3. Велосипед 4x30",
        "1. Дровосек с гантелью 3x15\n2. Альпинист 4x30\n3. Вакуум живота 5x20 сек",
    ],
}

# Клавиатура с основными кнопками
main_keyboard = ReplyKeyboardMarkup(
    [
        [
            "/add_parameters Ввод параметров",
            "/quick_workout Быстрая тренировка",
        ],  # Добавлена кнопка "Быстрая тренировка"
        ["/progress_chart График веса", "/waist_chart График изменения талии"],
        ["/calories_chart График ккал", "/steps_chart График шагов"],
        ["/export_data Получить таблицу"],
    ],
    resize_keyboard=True,
)


# Команда для старта
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я твой фитнес-бот. Готов помочь тебе отслеживать тренировки и параметры!",
        reply_markup=main_keyboard,
    )


# Команда для добавления параметров
async def add_parameters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Давай начнем с твоего веса. Введи свой вес в килограммах:"
    )
    return WEIGHT


async def get_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    weight = update.message.text
    context.user_data["weight"] = float(weight)
    await update.message.reply_text("Отлично! Теперь введи свой рост в сантиметрах:")
    return HEIGHT


async def get_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    height = update.message.text
    context.user_data["height"] = float(height)
    await update.message.reply_text("Хорошо! Теперь введи обхват талии в сантиметрах:")
    return WAIST


async def get_waist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    waist = update.message.text
    context.user_data["waist"] = float(waist)
    await update.message.reply_text("Сколько калорий ты потратил за день?")
    return CALORIES_SPENT


async def get_calories_spent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    calories_spent = update.message.text
    context.user_data["calories_spent"] = int(calories_spent)
    await update.message.reply_text("Сколько калорий ты съел за день?")
    return CALORIES_EATEN


async def get_calories_eaten(update: Update, context: ContextTypes.DEFAULT_TYPE):
    calories_eaten = update.message.text
    context.user_data["calories_eaten"] = int(calories_eaten)
    await update.message.reply_text("Сколько шагов ты прошел за день?")
    return STEPS


async def get_steps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    steps = update.message.text
    context.user_data["steps"] = int(steps)

    # Вычисление и вывод BMI
    weight = context.user_data["weight"]
    height = context.user_data["height"] / 100  # Перевод роста в метры
    bmi = round(weight / (height**2), 2)

    # Сохранение параметров в базу данных
    user_id = update.effective_user.id
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute(
        """INSERT INTO user_parameters (user_id, date, weight, height, waist, bmi, calories_spent, calories_eaten, steps) 
                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            date,
            weight,
            context.user_data["height"],
            context.user_data["waist"],
            bmi,
            context.user_data["calories_spent"],
            context.user_data["calories_eaten"],
            context.user_data["steps"],
        ),
    )
    conn.commit()

    response = (
        f"Отлично! Вот твои параметры:\n"
        f"Вес: {weight} кг\n"
        f"Рост: {context.user_data['height']} см\n"
        f"Обхват талии: {context.user_data['waist']} см\n"
        f"Индекс массы тела (BMI): {bmi}\n"
        f"Калории потрачено: {context.user_data['calories_spent']} ккал\n"
        f"Калории съедено: {context.user_data['calories_eaten']} ккал\n"
        f"Шагов пройдено: {context.user_data['steps']}"
    )

    await update.message.reply_text(response, reply_markup=main_keyboard)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Ввод параметров отменен.", reply_markup=main_keyboard
    )
    return ConversationHandler.END


# Команда для отображения графика веса
async def progress_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    c.execute(
        """SELECT date, weight FROM user_parameters WHERE user_id = ? ORDER BY date""",
        (user_id,),
    )
    data = c.fetchall()

    if not data:
        await update.message.reply_text("Данных для построения графика пока нет.")
        return

    # Построение графика
    dates = [datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S") for row in data]
    weights = [row[1] for row in data]

    plt.figure(figsize=(10, 5))
    plt.plot(dates, weights, marker="o", color="blue")
    plt.title("График изменения веса")
    plt.xlabel("Дата")
    plt.ylabel("Вес (кг)")
    plt.grid(True)

    # Сохранение графика и отправка пользователю
    chart_path = "progress_chart.png"
    plt.savefig(chart_path)
    plt.close()

    await update.message.reply_photo(photo=open(chart_path, "rb"))


# График изменения обхвата талии
async def waist_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    c.execute(
        """SELECT date, waist FROM user_parameters WHERE user_id = ? ORDER BY date""",
        (user_id,),
    )
    data = c.fetchall()

    if not data:
        await update.message.reply_text(
            "Данных для построения графика обхвата талии пока нет."
        )
        return

    dates = [datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S") for row in data]
    waists = [row[1] for row in data]

    plt.figure(figsize=(10, 5))
    plt.plot(dates, waists, marker="o", color="green")
    plt.title("График изменения обхвата талии")
    plt.xlabel("Дата")
    plt.ylabel("Обхват талии (см)")
    plt.grid(True)

    chart_path = "waist_chart.png"
    plt.savefig(chart_path)
    plt.close()

    await update.message.reply_photo(photo=open(chart_path, "rb"))


# График изменения калорий
async def calories_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    c.execute(
        """SELECT date, calories_spent FROM user_parameters WHERE user_id = ? AND calories_spent IS NOT NULL ORDER BY date""",
        (user_id,),
    )
    data = c.fetchall()

    if not data:
        await update.message.reply_text(
            "Данных для построения графика калорий пока нет."
        )
        return

    dates = [datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S") for row in data]
    calories = [row[1] for row in data]

    plt.figure(figsize=(10, 5))
    plt.plot(dates, calories, marker="o", color="orange")
    plt.title("График изменения калорий")
    plt.xlabel("Дата")
    plt.ylabel("Калории (ккал)")
    plt.grid(True)

    chart_path = "calories_chart.png"
    plt.savefig(chart_path)
    plt.close()

    await update.message.reply_photo(photo=open(chart_path, "rb"))


# График изменения шагов
async def steps_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    c.execute(
        """SELECT date, steps FROM user_parameters WHERE user_id = ? AND steps IS NOT NULL ORDER BY date""",
        (user_id,),
    )
    data = c.fetchall()

    if not data:
        await update.message.reply_text("Данных для построения графика шагов пока нет.")
        return

    dates = [datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S") for row in data]
    steps = [row[1] for row in data]

    plt.figure(figsize=(10, 5))
    plt.plot(dates, steps, marker="o", color="purple")
    plt.title("График изменения шагов")
    plt.xlabel("Дата")
    plt.ylabel("Шаги (кол-во)")
    plt.grid(True)

    chart_path = "steps_chart.png"
    plt.savefig(chart_path)
    plt.close()

    await update.message.reply_photo(photo=open(chart_path, "rb"))


# Экспорт данных в файл
async def export_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    c.execute("""SELECT * FROM user_parameters WHERE user_id = ?""", (user_id,))
    data = c.fetchall()

    if not data:
        await update.message.reply_text("Нет данных для экспорта.")
        return

    file_path = "fitness_data.csv"
    with open(file_path, "w") as f:
        f.write(
            "ID,User ID,Date,Weight,Height,Waist,Activity Level,Calories Spent,Calories Eaten,Steps,BMI\n"
        )
        for row in data:
            f.write(",".join(map(str, row)) + "\n")

    await update.message.reply_document(document=open(file_path, "rb"))


# Обработчики для быстрой тренировки
async def quick_workout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = ReplyKeyboardMarkup(
        [["Руки", "Ноги-Ягодицы"], ["Спина", "Пресс"], ["Вернуться домой"]],
        resize_keyboard=True,
    )
    await update.message.reply_text(
        "Выбери часть тела, которую ты хочешь потренировать:", reply_markup=keyboard
    )
    return "SELECTED_BODY_PART"


async def send_workout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    body_part = update.message.text
    if body_part in WORKOUTS:
        workout = random.choice(WORKOUTS[body_part])
        await update.message.reply_text(
            f"Твоя тренировка на {body_part}:\n\n{workout}", reply_markup=main_keyboard
        )
    else:
        await update.message.reply_text(
            "Пожалуйста, выбери часть тела из предложенных вариантов",
            reply_markup=main_keyboard,
        )
    return ConversationHandler.END


async def cancel_workout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Возвращаемся в главное меню!", reply_markup=main_keyboard
    )
    return ConversationHandler.END


# Основной блок запуска бота
if __name__ == "__main__":
    # Загрузка токена из переменной окружения
    import os
    from dotenv import load_dotenv

    load_dotenv()
    TOKEN = os.getenv("BOT_TOKEN")

    if not TOKEN:
        print("Ошибка: переменная окружения BOT_TOKEN не найдена.")
        exit(1)

    # Создаем приложение и добавляем обработчики команд
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("progress_chart", progress_chart))
    app.add_handler(CommandHandler("waist_chart", waist_chart))
    app.add_handler(CommandHandler("calories_chart", calories_chart))
    app.add_handler(CommandHandler("steps_chart", steps_chart))
    app.add_handler(CommandHandler("export_data", export_data))

    # ConversationHandler для ввода параметров
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add_parameters", add_parameters)],
        states={
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weight)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_height)],
            WAIST: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_waist)],
            CALORIES_SPENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_calories_spent)
            ],
            CALORIES_EATEN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_calories_eaten)
            ],
            STEPS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_steps)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # ConversationHandler для быстрой тренировки
    conv_workout = ConversationHandler(
        entry_points=[CommandHandler("quick_workout", quick_workout)],
        states={
            "SELECTED_BODY_PART": [
                MessageHandler(
                    filters.Regex("^(Руки|Ноги-Ягодицы|Спина|Пресс)$"), send_workout
                ),
                MessageHandler(filters.Regex("^Вернуться домой$"), cancel_workout),
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_workout)],
    )

    app.add_handler(conv_handler)
    app.add_handler(conv_workout)

app_flask = Flask(__name__)


@app_flask.route("/")
def home():
    return "Bot is running!"


def run_flask():
    app_flask.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))


if __name__ == "__main__":
    # Запуск Flask сервера в отдельном потоке
    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    # Запуск бота
    print("Бот запущен. Ожидание команд...")
    app.run_polling()
