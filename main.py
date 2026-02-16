import vk_api
from vk_api import VkUpload
from vk_api.utils import get_random_id
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkLongPoll, VkEventType
from PIL import Image, ImageDraw, ImageFont
from settings import VK_API
from io import BytesIO

vk_session = vk_api.VkApi(token=VK_API)
vk = vk_session.get_api()
upload = VkUpload(vk_session)

longpoll = VkLongPoll(vk_session)

keyboard = VkKeyboard(one_time=True)
keyboard.add_button('Сертификат', color=VkKeyboardColor.SECONDARY)

waiting_fio = set()


def send_msg(user_id, message, keyboard=None):
    vk.messages.send(
        user_id=user_id,
        message=message,
        random_id=get_random_id(),
        keyboard=keyboard
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


def send_image(user_id, image_bytes):
    photo = upload.photo_messages(photos=image_bytes)[0]
    attachment = f'photo{photo["owner_id"]}_{photo["id"]}'

    vk.messages.send(
        user_id=user_id,
        random_id=get_random_id(),
        attachment=attachment
    )


def listen_for_msg():
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            user_id = event.user_id
            text = event.text.strip()

            print(f'Сообщение от {user_id}: {text}')

            if text == "Сертификат":
                waiting_fio.add(user_id)
                send_msg(user_id, "Напишите ваши полные Фамилию Имя Отчество")

            elif user_id in waiting_fio:
                fio = text.title()
                waiting_fio.remove(user_id)

                send_msg(user_id, "Генерирую сертификат...")

                img_bytes = draw_certificate(fio)
                send_image(user_id, img_bytes)

                send_msg(user_id, "Готово! Можете скачать и распечатать ☝️", keyboard=keyboard.get_keyboard())

            else:
                send_msg(user_id, "Привет! Для получения сертификата нажмите кнопку ниже 👇", keyboard=keyboard.get_keyboard())


if __name__ == '__main__':
    listen_for_msg()
