import vk_api
import vk_api.exceptions
import requests
import re
import threading
import queue
from config import *
from vk_api import VkUpload
from vk_api.utils import get_random_id
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkLongPoll, VkEventType
from PIL import Image, ImageDraw, ImageFont
from database import init_db, save_certificate, get_stats
from export_excel import export_excel
from io import BytesIO
import time

init_db()

send_queue = queue.Queue()
vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
upload = VkUpload(vk_session)

longpoll = VkLongPoll(vk_session)

keyboard = VkKeyboard(one_time=True)
keyboard.add_button('Сертификат', color=VkKeyboardColor.SECONDARY)
subscribe_keyboard = VkKeyboard(one_time=True)
subscribe_keyboard.add_openlink_button("Подписаться", "https://vk.com/club115581151")
admin_keyboard = VkKeyboard(one_time=True)
admin_keyboard.add_button('Сертификат', color=VkKeyboardColor.SECONDARY)
admin_keyboard.add_line()
admin_keyboard.add_button('Статистика', color=VkKeyboardColor.PRIMARY)
admin_keyboard.add_button('Экспорт', color=VkKeyboardColor.POSITIVE)

waiting_fio = dict()

def sender_worker():
    while True:
        try:
            func, args = send_queue.get()
            func(*args)
            time.sleep(0.35)
        except Exception as e:
            print("Sender fatal error:", e)
            time.sleep(2)
        finally:
            send_queue.task_done()

threading.Thread(target=sender_worker, daemon=True).start()

def validate_fio(text: str):
    text = text.strip()

    if len(text) < MIN_FIO_LENGTH:
        return False, "❌ Слишком короткое ФИО"

    if len(text) > MAX_FIO_LENGTH:
        return False, "❌ Слишком длинное ФИО"

    if not FIO_REGEX.match(text):
        return False, "❌ Используйте только буквы, пробелы и дефис"

    if any(ch.isdigit() for ch in text):
        return False, "❌ В ФИО не должно быть цифр"

    low = text.lower()
    for word in BAD_WORDS:
        if word in low:
            return False, "❌ Недопустимые слова в ФИО"

    if len(text.split()) < 2:
        return False, "❌ Введите Фамилию и Имя (и Отчество при наличии)"

    return True, text.title()

def send_msg(peer_id, text, keyboard=None):
    send_queue.put((_send_msg, (peer_id, text, keyboard)))

def _send_msg(peer_id, message, keyboard=None):
    retries = 0
    max_retries = 5

    while retries < max_retries:
        try:
            vk.messages.send(
                peer_id=peer_id,
                message=message,
                random_id=get_random_id(),
                keyboard=keyboard if keyboard is None else keyboard.get_keyboard(),
            )
            return
        except vk_api.exceptions.ApiError as e:
            code = e.error.get("error_code")

            if code in (6, 10, 14, 29):
                delay = min(2 ** retries, 30)
                print(f"VK API error {code}. Retry in {delay}s")
                time.sleep(delay)
                retries += 1
            else:
                print("VK API fatal error:", e)
                return
        except (requests.exceptions.ReadTimeout,
                requests.exceptions.ConnectionError) as e:

            delay = min(2 ** retries, 30)
            print(f"Connection error: {e}. Retry in {delay}s")
            time.sleep(delay)
            retries += 1


    print("Message send failed after retries")


def draw_certificate(fio):
    img = Image.open("resources/certificate.jpg").convert("RGB")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("font/CormorantGaramond-SemiBoldItalic.ttf", size=40)

    position = (400, 360)
    draw.text(position, fio, fill=(0, 0, 0), font=font)

    bio = BytesIO()
    img.save(bio, format="JPEG")
    bio.seek(0)
    return bio

def send_image(peer_id, img_bytes):
    send_queue.put((_send_image, (peer_id, img_bytes)))


def _send_image(peer_id, image_bytes):
    retries = 0
    max_retries = 5

    while retries < max_retries:
        try:
            photo = upload.photo_messages(photos=image_bytes)[0]
            attachment = f'photo{photo["owner_id"]}_{photo["id"]}'

            vk.messages.send(
                peer_id=peer_id,
                random_id=get_random_id(),
                attachment=attachment
            )
            return
        except vk_api.exceptions.ApiError as e:
            code = e.error.get("error_code")
            delay = min(2 ** retries, 30)
            print(f"VK image error {code}. Retry in {delay}s")
            time.sleep(delay)
            retries += 1

        except Exception as e:
            delay = min(2 ** retries, 30)
            print(f"Upload error: {e}. Retry in {delay}s")
            time.sleep(delay)
            retries += 1

        print("Image send failed after retries")

def is_subscribed(user_id):
    result = vk.groups.isMember(group_id=GROUP_ID, user_id=user_id)
    return bool(result)

def send_excel(peer_id, filename):
    doc = upload.document_message(filename, peer_id=peer_id)
    attachment = f"doc{doc['doc']['owner_id']}_{doc['doc']['id']}"

    vk.messages.send(
        peer_id=peer_id,
        random_id=0,
        attachment=attachment
    )

def listen_for_msg():
    ADMIN_IDS = {140345220, 203184728, 354900973}

    for event in longpoll.listen():
        if event.type != VkEventType.MESSAGE_NEW or not event.to_me:
            continue

        user_id = event.user_id
        peer_id = event.peer_id
        text = event.text.strip()

        print(f'Сообщение от {user_id}: {text}')

        if user_id in ADMIN_IDS:
            kb = admin_keyboard
        elif user_id in waiting_fio:
            kb = None
        else:
            kb = keyboard

        if user_id in ADMIN_IDS:
            if text == "Статистика":
                total, users = get_stats()
                send_msg(peer_id, f"📊 Статистика:\nВсего сертификатов: {total}\nПользователей: {users}", keyboard=kb)
                continue

            if text == "Экспорт":
                filename = export_excel()
                send_excel(peer_id, filename)
                continue

            if text == "/test":
                for i in range(20):
                    send_msg(peer_id, f"test {i}")
                send_msg(peer_id, "Тест очереди завершён")
                continue

        if text == "Сертификат":
            if not is_subscribed(user_id):
                send_msg(peer_id,
                         "❌ Для получения сертификата необходимо подписаться:",
                         keyboard=subscribe_keyboard)
                continue

            waiting_fio[user_id] = time.time()
            send_msg(peer_id, "✍ Напишите ваши полные Фамилию Имя Отчество", keyboard=None)
            continue

        if user_id in waiting_fio:
            if time.time() - waiting_fio[user_id] > 300:
                del waiting_fio[user_id]
                send_msg(peer_id, "⏳ Время ожидания истекло, нажмите «Сертификат» снова")
                continue
            ok, result = validate_fio(text)
            if not ok:
                send_msg(peer_id, result)
                continue

            fio = result
            del waiting_fio[user_id]

            send_msg(peer_id, "Генерирую сертификат...", keyboard=None)
            img_bytes = draw_certificate(fio)
            send_image(peer_id, img_bytes)
            save_certificate(user_id, fio)

            send_msg(peer_id, "✅ Готово! Можете скачать и распечатать 👇", keyboard=keyboard)
            continue

        if kb is not None:
            send_msg(peer_id,
                     "Привет! Для получения сертификата нажмите кнопку ниже 👇",
                     keyboard=kb)

if __name__ == '__main__':
    while True:
        try:
            listen_for_msg()
        except Exception as e:
            print("Ошибка:", e)
            time.sleep(5)
