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


def message_is_from_admin(message):
    """Проверка, что боту пришло сообщение от админа."""
    return message.chat.id in ADMINS


def start_message(update, context):
    """Приветственное сообщение от бота при команде start."""
    message = update.message
    if not message_is_from_admin(message):
        text = (
            "Привет! Здесь можно задать любой вопрос нашей команде."
            "Мы постараемся ответить как можно скорее."
        )
    else:
        text = (
            "Привет! Ты - администратор данного бота."
            "Отвечать на поступающие сообщения можно текстом и/или "
            "картинкой с помощью Reply. "
            "Это важно! Иначе ответ не увидит никто, кроме тебя."
            "Если кто-то из других администраторов ответит на поступившее "
            "сообщение - бот пришлет тебе уведомление."
        )
    context.bot.send_message(chat_id=message.chat.id, text=text)


def show_history(update, context):
    """
    Команда /show_history. Вывод содержимого MESSAGES
    при запросе от админов при команде /show_history.
    """
    message = update.message
    if not message_is_from_admin(message):
        context.bot.send_message(
            chat_id=message.chat.id, text="Это служебная команда."
        )
    else:
        context.bot.send_message(
            chat_id=message.chat.id, text=MESSAGES
        )


def clear_history(update, context):
    """
    Команда /clear_history.
    Очищение словаря MESSAGES при запросе от админов.
    """
    message = update.message
    if not message_is_from_admin(message):
        context.bot.send_message(
            chat_id=message.chat.id, text="Это служебная команда."
        )
    else:
        MESSAGES.clear()


def message_content(message):
    """Содержимое сообщение в зависимости от того, что было отправлено:
    текст, картинка, фото, документ, аудио. Используется для связи с id
    автора сообщения."""

    content = ""

    if message.text:
        content = str(message.text)

    elif message.photo != []:
        content = message.photo[-1].file_unique_id

    elif message.document != {}:
        content = message.document.file_unique_id

    elif message.audio != {}:
        content = message.audio.file_unique_id

    return content


def router_for_incoming_messages(update, context):
    """
    Распределение входящих боту сообщений:
    ответы админов отправляются пользователям с помощью функции
    admin_reply_to_message, вопросы от пользователей пересылаются
    админам посредством forward_question_to_admin.
    При получении сообщения от пользователя его ID в паре с
    текстом сообщения сохраняются в словаре MESSAGES.
    """
    message = update.message
    if not message_is_from_admin(message):
        MESSAGES[message_content(message)] = int(message.chat.id)
        forward_question_to_admin(message, context)
    else:
        admin_reply_to_question(message, context)


def forward_question_to_admin(message, context):
    """Пересылает админам сообщение, полученное ботом от пользователя."""
    for admin_id in ADMINS:
        context.bot.forward_message(
            chat_id=admin_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )


def admin_reply_to_question(message, context):
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
    if message.reply_to_message:
        question = message.reply_to_message
        user_id = MESSAGES[message_content(question)]

        if message.text:
            context.bot.send_message(chat_id=user_id, text=message.text)
            answer = str(message.text)
        if message.photo != []:
            context.bot.send_photo(
                chat_id=user_id, photo=message.photo[-1]
            )
            answer = " ответ содержит картинку"
        if message.caption:
            context.bot.send_message(
                chat_id=user_id, text=message.caption
            )
            answer = (
                f"Ответ содержит картинку с подписью "
                f"{message.caption}"
            )
        if message.document:
            context.bot.send_document(
                chat_id=user_id, document=message.document
            )
            answer = " ответ содержит документ"

        other_admins = ADMINS.copy()
        del other_admins[message.chat.id]
        for admin_id in other_admins:
            context.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"{ADMINS[message.chat.id]} ответил на обращение "
                    f"{question.text}. "
                    f"Содержание ответа: {answer}"
                ),
            )
    
    else:
        context.bot.send_message(
            chat_id=message.chat.id,
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
