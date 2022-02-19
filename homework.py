import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

import exceptions

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s (%(name)s) [%(levelname)s] - %(message)s'
)
handler.setFormatter(formatter)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# 10 минут
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Функция отправляет сообщение о новом статусе в чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logger.error(
            f'Ошибка при попытке отправить сообщение в телеграмм: {error}'
        )
    else:
        logger.info(f'Бот отправил сообщение: {message}')


def get_api_answer(current_timestamp):
    """Функция делает запрос в API-сервису Яндекс.Домашка."""
    timestamp = current_timestamp or int(time.time())
    logger.info(f'Время запроса: {timestamp}')
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != 200:
            raise exceptions.EndpointHomeworkError
    except exceptions.EndpointHomeworkError:
        message = f'Эндпоинт {ENDPOINT} недоступен. Статус кода не "ОК".'
        logger.error(message)
        raise exceptions.EndpointHomeworkError(message)
    except exceptions.ApiHomeworkError as error:
        message = f'Ошибка при запросе к API Яндекс.Домашка: {error}'
        logger.error(message)
        raise exceptions.ApiHomeworkError(message)
    else:
        return(response.json())


def check_response(response):
    """Функция проверяет ответ API на корректность."""
    response_keys = ['homeworks', 'current_date']
    for key in response_keys:
        try:
            response[key]
        except KeyError as error:
            message = (f'В ответе API отсутствует ожидаемый ключ словаря {key}'
                       f': {error}')
            logger.error(message)
            raise KeyError(message)
        else:
            type_homeworks = type(response['homeworks'])
            if type_homeworks == list:
                return response['homeworks']
            else:
                message = ('Значение словаря API-ответа от Яндекс.Домашка под '
                           'ключом "homeworks" не соответствует ожидаемому '
                           f'типу данных: {type_homeworks}')
                logger.error(message)
                raise exceptions.TypeValueError(message)


def parse_status(homework):
    """Функция проверяет корректность полученных статусов от API."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    try:
        HOMEWORK_STATUSES[homework_status]
    except KeyError:
        message = (f'В ответе неопознанный статус домашней работы: '
                   f'{homework_status}')
        logger.error(message)
        raise KeyError(message)
    else:
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Функция проверяет доступность всех необходимых переменных окружения."""
    variable_env = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    count = 0
    for i in variable_env:
        try:
            if i is None:
                raise exceptions.VariableNoneError
        except exceptions.VariableNoneError:
            logger.critical(
                f'Отсутсвует переменная окружения: {i}.'
                'Программа принудительно остановлена.'
            )
        else:
            count += 1
    if len(variable_env) == count:
        logger.info('Все переменные окружения доступны')
        return True
    return False


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        return
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    message = ''
    id_homework = 0
    status_homework = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            check_answer = check_response(response)
            status_message = parse_status(check_answer[0])
        except IndexError:
            logger.debug('Отсутствует обновлённый статус в API-ответе')
            current_timestamp = response['current_date']
        except Exception as error:
            new_message = f'Сбой в работе программы: {error}'
            logger.error(new_message)
            if message != new_message:
                send_message(bot, new_message)
                message = new_message
        else:
            if (check_answer[0]['id'] == id_homework
                    and check_answer[0]['status'] == status_homework):
                current_timestamp = response['current_date']
            else:
                send_message(bot, status_message)
                logger.info(f'Статус домашней работы {check_answer[0]["id"]} '
                            f'изменился на {check_answer[0]["status"]}')
                current_timestamp = response['current_date']
                id_homework = check_answer[0]['id']
                status_homework = check_answer[0]['status']
        finally:
            time.sleep(RETRY_TIME)


# Функция main при импорт-ии homework.py в другой файл не будет исполняться
if __name__ == '__main__':
    main()