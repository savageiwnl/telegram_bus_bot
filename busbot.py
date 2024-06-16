import telebot
from bs4 import BeautifulSoup
import requests
from telebot import types
import threading
import time

# Ваш токен от BotFather
TOKEN = ''
bot = telebot.TeleBot(TOKEN)


# Функция для получения списка номеров автобусов с сайта
def get_bus_numbers():
    url = 'https://kudikina.ru/perm/bus/'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    bus_numbers = []
    for a in soup.find_all('a', class_='bus-item bus-icon'):
        title = a.get('title')  # Получаем значение атрибута title
        bus_number = title.split(',')[0].split()[1]  # Извлекаем номер автобуса
        bus_numbers.append(bus_number)

    return bus_numbers


# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = """
    Привет! Я ваш помощник в мире автобусного транспорта Перми. 🚌

    Меня зовут Транспортный Бот, и я здесь, чтобы сделать ваши поездки по городу максимально удобными и комфортными. С моей помощью вы сможете:

    🔹 Узнать актуальное расписание автобусов.

    Нажмите на кнопку снизу и я предоставлю вам всю необходимую информацию. 

    ☺ Пусть ваши поездки по Перми будут приятными и беззаботными! ☺
    """
    # Создаем клавиатуру
    markup = types.InlineKeyboardMarkup()
    # Создаем кнопку
    btn_help = types.InlineKeyboardButton('Помощь', callback_data='/help')
    # Добавляем кнопку на клавиатуру
    markup.add(btn_help)
    # Отправляем сообщение с клавиатурой
    bot.send_photo(message.chat.id, 'https://img.ttransport.ru/photo/21/94/219426.jpg', caption=welcome_text,
                   reply_markup=markup)


# Обработчик нажатий на кнопки
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "/help":
        send_help(call.message)


# Обработчик команды /help
@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """
    Вот список всех доступных команд и их описание:

    🔹 /start - Начать работу с ботом. Бот пришлет приветственное сообщение и предложит выбрать команду.

    🔹 /bus_numbers - Получить список номеров всех автобусов.

    🔹 /stops <номер автобуса> <буква маршрута> - Получить список остановок для указанного номера автобуса и буквы маршрута. Например: /stops 49 A

    🔹 /schedule <номер автобуса> <номер остановки> <буква маршрута> - Получить расписание автобуса на указанной остановке по указанному маршруту. Например: /schedule 49 2 A

    🔹 /help - Получить список всех доступных команд и их описание.
    """
    bot.send_message(message.chat.id, help_text)


# Обработчик команды /bus_numbers
@bot.message_handler(commands=['bus_numbers'])
def send_nums(message):
    bus_numbers = get_bus_numbers()
    bot.reply_to(message, 'Номера автобусов: ' + ', '.join(bus_numbers))


# Функция для получения списка остановок автобуса
def get_bus_stops(bus_number, route_letter):
    url = f'https://kudikina.ru/perm/bus/{bus_number}/{route_letter}'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Извлекаем название направления из HTML-кода
    direction = soup.find('a', href=f'/perm/bus/{bus_number}/{route_letter}').get_text(strip=True)
    bus_stops = []
    for div in soup.find_all('div', class_='bus-stop col-xs-12 col-sm-6 col-md-6'):
        bus_stop = div.get_text(strip=True)
        bus_stops.append(bus_stop)

    return direction, bus_stops


# Обработчик команды /stops
@bot.message_handler(commands=['stops'])
def send_stops(message):
    message_parts = message.text.split()
    if len(message_parts) < 3:
        bot.reply_to(message,
                     'Пожалуйста, укажите номер автобуса и букву маршрута после команды /stops. Например: /stops 49 A')
        return

    bus_number = message_parts[1]  # Извлекаем номер автобуса из сообщения
    test = get_bus_numbers()
    if bus_number not in test:
        bot.reply_to(message, 'Данного автобуса нет в расписании ')
        return
    route_letter = message_parts[2]  # Извлекаем букву маршрута из сообщения
    if route_letter == 'A' or route_letter == 'B':
        direction, bus_stops = get_bus_stops(bus_number, route_letter)
        bot.send_message(message.chat.id,
                         'Направление движения автобуса ' + bus_number + ' на маршруте ' + route_letter + ': ' + direction)
        bot.send_message(message.chat.id, 'Остановки: ' + ', '.join(bus_stops))
    else:
        bot.reply_to(message, 'Введите корректную букву маршрута')
        return


# Функция для получения расписания автобуса
def get_bus_schedule(bus_number, stop_number, route_letter):
    url = f'https://kudikina.ru/perm/bus/{bus_number}/{route_letter}'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    for row in soup.find_all('div', class_='row'):
        bus_stop_div = row.find('div', class_='bus-stop col-xs-12 col-sm-6 col-md-6')
        stop_times_div = row.find('div', class_='stop-times')

        if bus_stop_div is not None and stop_times_div is not None:
            bus_stop_name = bus_stop_div.get_text(strip=True)
            if bus_stop_name.startswith(
                    f'{stop_number}) '):  # Проверяем, начинается ли имя остановки с номера остановки
                schedule = []
                for span in stop_times_div.find_all('span', class_=['current showed', 'showed']):
                    time = span.get_text(strip=True)
                    schedule.append(time)
                return bus_stop_name, schedule  # Возвращаем полное имя остановки и расписание

    return None, None  # Возвращаем None, если не найдена остановка с указанным номером


# Обработчик команды /schedule
@bot.message_handler(commands=['schedule'])
def send_schedule(message):
    message_parts = message.text.split()
    if len(message_parts) < 4:
        bot.reply_to(message,
                     'Пожалуйста, укажите номер автобуса, номер остановки и букву маршрута после команды /schedule. Например: /schedule 49 2 A')
        return

    bus_number = message_parts[1]  # Извлекаем номер автобуса из сообщения
    test = get_bus_numbers()
    if bus_number not in test:
        bot.reply_to(message, 'Данного автобуса нет в расписании')
        return
    stop_number = message_parts[2]  # Извлекаем номер остановки из сообщения
    route_letter = message_parts[3]  # Извлекаем букву маршрута из сообщения
    if route_letter == 'A' or route_letter == 'B':
        bus_stop_name, schedule = get_bus_schedule(bus_number, stop_number,
                                                   route_letter)  # Получаем полное имя остановки и расписание
        if bus_stop_name is None:
            bot.reply_to(message, 'Остановка с указанным номером не найдена.')
        else:
            bot.reply_to(message,
                         'Расписание автобуса ' + bus_number + ' на остановке ' + bus_stop_name + ' по маршруту ' + route_letter + ': ' + ', '.join(
                             schedule))
    else:
        bot.reply_to(message, 'Введите корректную букву маршрута')
        return


# Функция, которая будет выполняться в фоновом режиме
def stay_awake():
    while True:
        print("Бот активен.")
        time.sleep(10 * 60)  # Пауза в 10 минут


# Запуск фонового потока
thread = threading.Thread(target=stay_awake)
thread.start()

bot.polling(none_stop=True)
