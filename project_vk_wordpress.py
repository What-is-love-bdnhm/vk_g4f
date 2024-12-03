# мои токены из отдельного файла
from takenchik import TOKEN_VK

import json
import re
import base64
import zoneinfo
import datetime
import requests
from colorama import Fore
from g4f.client import Client as G4FClient


# функции для удобного написания цветного текста --------------------------------------------------


def default_print(txt):
    print(Fore.LIGHTWHITE_EX, txt)


def info_print(txt, inf=''):
    print(Fore.LIGHTBLUE_EX + '[INFO]' + Fore.BLUE + f'{txt} {inf}')


def status_print(txt, res=''):
    print(Fore.LIGHTGREEN_EX + "[STATUS]" + Fore.GREEN + txt + res)


def debug_print(txt, res=''):
    print(Fore.LIGHTWHITE_EX + '[DEBUG]' + Fore.WHITE + f"{txt} {res}")


def error_print(txt, e=''):
    print(Fore.LIGHTRED_EX + '[ERROR]' + Fore.RED + f"{txt} {e}")


# --------------------------------------------------------------------------------------------------

url = 'https://vk.com/wudiochan?w=wall-116181796_1249950'
VK_TOKEN = TOKEN_VK  # сюда вставить свой токен VK

DOMAIN_SITE = 'https://design-hope.ru/'
username = 'auto'
password = 'XjSrGW*EkLBxWppao2AO$y^p'

host_post = f'{DOMAIN_SITE}/wp-json/wp/v2/posts'
userpass = f'{username}:{password}'
encoded_u = base64.b64encode(userpass.encode()).decode()
headers_post = {'Authorization': f'Basic {encoded_u}'}


def get_post_vk_data(link: str) -> dict | None:
    if ('https://vk.com' in link) or ('https://m.vk.com' in link) and 'wall' in link:
        info_print('Попытка получения поста из VK по ссылке:', link)
        url_post = link.split('wall')[1]
        try:
            params = {
                'access_token': VK_TOKEN,
                'posts': url_post,
                'v': '5.199',
            }
            response = requests.get('https://api.vk.com/method/wall.getById', params=params)
            r = response.json()
            if 'error' in r:  # проверка ошибки со стороны вк
                r = r['error']
                error_print("Не удалось обработать пост:", r['error_code'])
                error_print('Подробности ошибки', r['error_msg'])
                return None
        except Exception as e:
            error_print('Не удалось получить пост из Vk:', e)
            return None

        post_data = {
            'date': [],
            'text': [],
            'photo': [],
            'video': [],
            'inner_data': {
                'text': [],
                'photo': [],
                'video': []
            }
        }
        try:
            last_item = r['response']['items'][-1]
            debug_print('Последний элемент поста:', last_item)

            if 'copy_history' in last_item and last_item['copy_history'][-1]['inner_type'] == 'wall_wallpost':
                post_data['inner_data']['text'].append(
                    last_item['copy_history'][-1]['text'].replace('\n', '<br>')
                )
                debug_print("Добавлен внутренний текст поста")

                for attachment in last_item['copy_history'][-1]['attachments']:
                    if attachment['type'] == 'photo':
                        max_size = max(attachment['photo']['sizes'], key=lambda x: x['width'] * x['height'])
                        post_data['inner_data']['photo'].append(max_size['url'])
                        debug_print('Добавлено внутреннее фото:', max_size['url'])

            text_post = last_item['text'].replace('\n', '<br>')
            post_data['text'].append(text_post)
            date_post = last_item['date']
            post_data['date'].append(datetime.datetime.fromtimestamp(date_post, tz=zoneinfo.ZoneInfo("Europe/Moscow")))
            debug_print('Текст поста:', text_post[:40])
            debug_print('Дата:', post_data['date'][0])

            for attachment in last_item['attachments']:
                if attachment['type'] == 'photo':
                    max_size = max(attachment['photo']['sizes'], key=lambda x: x['width'] * x['height'])
                    post_data['photo'].append(max_size['url'])
                    debug_print("Добавлено фото:", max_size['url'])

                elif attachment['type'] == 'video':
                    if attachment['video']['can_repost'] == 1:
                        own = attachment['video']['owner_id']
                        id_u = attachment['video']['id']
                        video_link = f'<iframe src="https://vk.com/video_ext.php?oid={own}&amp;id={id_u}&amp;hd=2" ' \
                                     f'width="807" height="500" allow="autoplay; encrypted-media; fullscreen; ' \
                                     f'picture-in-picture;" frameborder="0" allowfullscreen=""></iframe>'
                        post_data['video'].append(video_link)
                        debug_print("Добавлено видео:", video_link)
        except Exception as e:
            error_print('Ошибка при обработке данных поста:', e)
            return None
        debug_print("Полученный json VK: ", post_data)
        status_print("Данные обработаны и возвращены")
        return post_data
    else:
        error_print('Ошибка формата ссылки VK')
        return None


def gpt4_json(text: str, model: str = 'gpt-4o') -> str | None:
    info_print('Проверка длины текста перед подачей его g4f...')
    if len(text) >= 50:
        try:
            client = G4FClient()

            while True:
                info_print("Попытка получения заголовка, перефразированного текста и тэгов из материала...")
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "user",
                            "content": '''Напиши текст в официальном стиле, заголовок и хэштеги по следующему материалу 
                            в виде json в формате
                            {
                            "title": <заголовок для текста(если материал слишком короткий то сюда вставь текст)>
                            "text": <текст в официальном стиле без эмодзи(если материал слишком короткий оставь это поле пустым)>
                            "tags": <[тэги]>
                            }
                            
                            Материал:
                            ''' + text[0]
                        }
                    ]
                )

                res_title_tags = response.choices[0].message.content

                # получение json из ответа g4f
                while True:
                    try:
                        info_print('Попытка извлечения json из ответа g4f...')
                        match = re.search(r"\{.*\}", res_title_tags, re.DOTALL)
                        if match:
                            json_answer = json.loads(match.group(0))
                            debug_print("Полученный ответ:", json_answer)
                            status_print("Успешно получен json")
                        break
                    except Exception as e:
                        error_print('Ошибка при извлечении JSON:', e)

                    try:
                        info_print('Попытка построения json из ответа g4f...')
                        start_idx = res_title_tags.find("{")
                        if start_idx != -1:
                            # Сканируем строку начиная с первого символа '{'
                            text = []
                            for char in res_title_tags[start_idx:]:
                                text.append(char)
                                # Выход из цикла, когда находим закрывающую фигурную скобку
                                if char == '}':
                                    break
                            json_answer = json.loads("".join(text))
                            debug_print("Полученный ответ:", json_answer)
                            status_print("Успешно получен json")
                            break
                    except Exception as e:
                        error_print('Ошибка при построении JSON:', e)

                    error_print('Не удалось извлечь JSON.')
                    return None

                # проверка текста на соответствие официальному стилю
                try:
                    info_print('Проверка текста на официальный стиль...')
                    response_title_check = client.chat.completions.create(
                        model=model,
                        messages=[
                            {
                                "role": "user",
                                "content": 'Проверь текст на русский язык, соответствие официальному стилю, отсутствие \
                                эмодзи и напиши True если всё верно: ' +
                                           json_answer['text']
                            }
                        ]
                    )
                    res_check = response_title_check.choices[0].message.content
                    if 'True' in res_check:
                        status_print('Текст соответствует указанному стилю и написан на русском')
                        info_print('Проверка тэгов на наличие хэштегов и последующее исправление...')
                        for i in range(len(json_answer['tags'])):
                            if '#' not in json_answer['tags'][i]:
                                json_answer['tags'][i] = '#' + json_answer['tags'][i]
                        status_print('Проверка успешно завершена')
                        return json_answer
                except Exception as e:
                    error_print('Ошибка проверки, будет перезапущена генерация всего json!:', e)

        except Exception as e:
            error_print("Не удалось получить ответ от g4f:", e)
            return None
    else:
        status_print('Текст слишком короткий, был возвращён шаблон для подобных случаев')
        if text:
            return {
                "title": text[0],
                "text": '',
                "tags": ['#вкратце'],
            }
        else:
            return {
                "title": 'Без заголовка',
                "text": '',
                "tags": ['#вкратце'],
            }


def create_draft(post_data: dict, json_answer: dict) -> None:
    # загрузка фото на сайт
    try:
        if len(post_data['photo']) > 0:
            info_print('Попытка загрузки медиа на WordPress...')
            url_img = post_data['photo'][0]
            img_data = requests.get(url_img).content
            host_media = f'{DOMAIN_SITE}/wp-json/wp/v2/media'
            headers_media = {
                "Authorization": f'Basic {encoded_u}',
                'Content-Type': 'image/jpg',
                'Content-Disposition': f'attachment; filename=scvorcov.jpg'
            }
            response = requests.post(host_media, data=img_data, headers=headers_media)
            debug_print('Полученный ответ от WordPress: ', response.json())

            if response.status_code == 201:
                media_id = response.json()['id']
                status_print('Изображение загружено')
            else:
                error_print('Ошибка загрузки изображения:', f'{response.status_code}, {response.text}')
                return
        else:
            status_print('Изображения отсутствуют')
            media_id = None
    except Exception as e:
        error_print('Ошибка загрузки медиа:', e)
        return

    # проверка наличия тэга на сайте
    try:
        info_print('Проверка наличия тэгов на сайте...')
        tags = json_answer['tags']
        debug_print('Наши тэги: ', tags)
        host_tags = f"{DOMAIN_SITE}/wp-json/wp/v2/tags"
        tag_ids = {}
        response_tags = requests.get(host_tags, params={'per_page': '100'}, headers=headers_post)
        if response_tags.status_code != 200:
            print(Fore.RED)
            raise Exception(f"Ошибка получения тегов: {response_tags.status_code}, {response_tags.text}")
        tags_on_server = response_tags.json()

        # Создаем словарь {название тега: ID}
        tags_dict = {tag["name"]: tag["id"] for tag in tags_on_server}

        for given_tag in tags:
            if given_tag in tags_dict:
                debug_print(f'given tag: {given_tag}')
                # Если тег найден, добавляем его ID в результат
                tag_ids[given_tag] = tags_dict[given_tag]
            else:
                # Если тег не найден, создаем новый
                create_response = requests.post(
                    host_tags,
                    headers=headers_post,
                    json={"name": given_tag}
                )
                debug_print('ответ от сервера:', create_response.status_code)
                if create_response.status_code == 201:
                    new_tag = create_response.json()
                    tag_ids[given_tag] = new_tag["id"]
                else:
                    print(Fore.RED)
                    raise Exception(
                        f"Ошибка создания тега '{given_tag}': {create_response.status_code}, {create_response.text}")
            debug_print('Полученный словарь тэгов:', tag_ids)
    except Exception as e:
        error_print('Ошибка проверки наличия тэгов: ', e)
        return

    # загрузка поста
    if media_id != None:
        media_photo = '<br>'.join([
            f'<figure class="wp-block-image size-full"><img decoding="async" width="807" height="363" src="{i}" alt="" /></figure>'
            for i in post_data['photo']
        ])
        inner_media_photo = '<br>'.join([
            f'<figure class="wp-block-image size-full"><img decoding="async" width="807" height="363" src="{i}" alt="" /></figure>'
            for i in post_data['inner_data']['photo']
        ])
    else:
        media_photo, inner_media_photo = '', ''

    if len(post_data['video']) > 0:
        videos = '<br>'.join(post_data['video'])
    data = {
        'category': 1,
        'title': json_answer['title'],
        'content': json_answer['text'] + '<br>' + media_photo + inner_media_photo + '<br>' + videos,
        'status': 'draft',
        'categories': [7],
        'tags': [tag_ids[i] for i in tag_ids],
        "featured_media": media_id,
    }

    try:
        info_print('Попытка загрузки поста на WordPress')

        response = requests.post(host_post, json=data, headers=headers_post)

        debug_print('Получен ответ от сайта WordPress:', response)
        if response.status_code == 201:
            debug_print('Ответ от сайта:', response.json())
            status_print('Пост успешно создан')
        else:
            error_print('Ошибка создания поста:', f'{response.status_code}, {response.text}')
    except Exception as e:
        error_print('Ошибка при загрузке поста:', e)
        return None


def main():
    post_data = get_post_vk_data(url)
    json_gpt = gpt4_json(post_data['text'] + post_data['inner_data']['text'])
    create_draft(post_data, json_gpt)
    return


main()
