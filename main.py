import os
import ast
import logging

from dotenv import load_dotenv

from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, TypeHandler


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMINS = ast.literal_eval(os.getenv("ADMINS"))
MESSAGES = {}

bot = Bot(token=BOT_TOKEN)


def message_is_from_admin(update):
    """Проверка, что боту пришло сообщение от админа."""
    return update.message.chat.id in ADMINS


def start_message(update, context):
    """Приветственное сообщение от бота при команде start."""
    if not message_is_from_admin(update):
        text = (
            "Привет! Здесь можно задать любой вопрос нашей команде."
            "Мы постараемся ответить как можно скорее."
        )
    else:
        text = (
            "Привет! Ты - администратор данного бота."
            "Сюда поступают вопросы от интересующихся проектом DevBrigde."
            "Отвечать на поступающие сообщения можно текстом и/или"
            "картинкой с помощью Reply. "
            "Это важно! Иначе ответ не увидит никто, кроме тебя."
            "Если кто-то из других администраторов ответит на поступившее ls"
            "сообщение - бот пришлет уведомление."
        )
    context.bot.send_message(chat_id=update.effective_chat.id, text=text)


def show_history(update, context):
    """
    Команда /show_history. Вывод содержимого MESSAGES
    при запросе от админов при команде /show_history.
    """
    if not message_is_from_admin(update):
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Это служебная команда."
        )
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text=MESSAGES
        )


def clear_history(update, context):
    """
    Команда /clear_history.
    Очищение словаря MESSAGES при запросе от админов.
    """
    if not message_is_from_admin(update):
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Это служебная команда."
        )
    else:
        MESSAGES.clear()


def router_for_incoming_messages(update, context):
    """
    Распределение входящих боту сообщений:
    ответы админов отправляются пользователям с помощью функции
    admin_reply_to_message, вопросы от пользователей пересылаются
    админам посредством forward_question_to_admin.
    При получении сообщения от пользователя его ID в паре с
    текстом сообщения сохраняются в словаре MESSAGES.
    """
    if not message_is_from_admin(update):
        MESSAGES[str(update.message.text)] = int(update.message.chat.id)
        forward_question_to_admin(update, context)

    else:
        admin_reply_to_question(update, context)


def forward_question_to_admin(update, context):
    """Пересылает админам сообщение, полученное ботом от пользователя."""
    for admin_id in ADMINS:
        context.bot.forward_message(
            chat_id=admin_id,
            from_chat_id=update.message.chat.id,
            message_id=update.message.message_id,
        )


def admin_reply_to_question(update, context):
    """
    Отправка сообщений от админов пользователям.
    Админ может отвечать тестом и/или картинкой.
    Админ делает reply на поступивший вопрос и сообщение уходит
    в чат бота с пользователем, задавшим вопрос.
    Остальный админы получают информационное сообщение о том,
    что вопрос обработан.
    Если админ не делает Reply при ответе, то получает информационное
    сообщение с напоминанием.
    """
    if update.message.reply_to_message:
        question = update.message.reply_to_message
        user_id = MESSAGES[str(question.text)]

        if update.message.text:
            context.bot.send_message(chat_id=user_id, text=update.message.text)

        if update.message.photo != []:
            context.bot.send_photo(
                chat_id=user_id, photo=update.message.photo[-1]
            )

        if update.message.caption:
            context.bot.send_message(
                chat_id=user_id, text=update.message.caption
            )

        other_admins = ADMINS.copy()
        del other_admins[update.message.chat.id]
        for admin_id in other_admins:
            context.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"{ADMINS[update.message.chat.id]} ответил на обращение"
                    f"{question.text}."
                    f"Содержание ответа: {update.message.text}"
                ),
            )
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Чтобы ответить, используй Reply на сообщение с вопросом",
        )


def main():
    updater = Updater(token=BOT_TOKEN)

    try:
        updater.dispatcher.add_handler(CommandHandler("start", start_message))
        updater.dispatcher.add_handler(
            CommandHandler("show_history", show_history)
            )
        updater.dispatcher.add_handler(
            CommandHandler("clear_history", clear_history)
            )
        updater.dispatcher.add_handler(
            TypeHandler(Update, router_for_incoming_messages)
        )

    except Exception as error:
        error_message = f"Сбой в работе бота: {error}"
        logging.error(error_message, exc_info=True)

    updater.start_polling()
    print("Бот запущен")
    updater.idle()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s, %(levelname)s, %(message)s, %(funcName)s, %(lineno)d"
        ),
        handlers=[
            logging.FileHandler(
                filename="main.log", mode="a", encoding="UTF-8"
                )
            ],
    )
    logger = logging.getLogger(__name__)
    main()
