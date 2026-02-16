import vk_api
from vk_api import VkUpload
from vk_api.utils import get_random_id
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkLongPoll, VkEventType
from PIL import Image, ImageDraw, ImageFont
from settings import VK_API
from database import init_db, save_certificate, get_stats
from export_excel import export_excel
from io import BytesIO

init_db()

vk_session = vk_api.VkApi(token=VK_API)
GROUP_ID = 235963490
vk = vk_session.get_api()
upload = VkUpload(vk_session)

longpoll = VkLongPoll(vk_session)

keyboard = VkKeyboard(one_time=True)
keyboard.add_button('Сертификат', color=VkKeyboardColor.SECONDARY)
subscribe_keyboard = VkKeyboard(one_time=True)
subscribe_keyboard.add_openlink_button("Подписаться", "https://vk.com/club235963490")
admin_keyboard = VkKeyboard(one_time=False)
admin_keyboard.add_button('Сертификат', color=VkKeyboardColor.SECONDARY)
admin_keyboard.add_line()
admin_keyboard.add_button('Статистика', color=VkKeyboardColor.PRIMARY)
admin_keyboard.add_button('Экспорт', color=VkKeyboardColor.POSITIVE)

waiting_fio = set()


def send_msg(peer_id, message, keyboard=None):
    vk.messages.send(
        peer_id=peer_id,
        message=message,
        random_id=get_random_id(),
        keyboard=keyboard if keyboard is None else keyboard.get_keyboard(),
    )


def draw_certificate(fio):
    img = Image.open("resources/picture.png").convert("RGB")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("font/CormorantGaramond-SemiBold.ttf", size=30)

    position = (300, 320)
    draw.text(position, fio, fill=(0, 0, 0), font=font)

    bio = BytesIO()
    img.save(bio, format="JPEG")
    bio.seek(0)
    return bio


def send_image(peer_id, image_bytes):
    photo = upload.photo_messages(photos=image_bytes)[0]
    attachment = f'photo{photo["owner_id"]}_{photo["id"]}'

    vk.messages.send(
        peer_id=peer_id,
        random_id=get_random_id(),
        attachment=attachment
    )

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
    ADMIN_IDS = {140345220}

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

        if text == "Сертификат":
            if not is_subscribed(user_id):
                send_msg(peer_id,
                         "❌ Для получения сертификата необходимо подписаться:",
                         keyboard=subscribe_keyboard)
                continue

            waiting_fio.add(user_id)
            send_msg(peer_id, "✍ Напишите ваши полные Фамилию Имя Отчество", keyboard=None)
            continue

        if user_id in waiting_fio:
            fio = text.title()
            waiting_fio.remove(user_id)

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
    listen_for_msg()
