import asyncio
import requests
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
from xml.etree import ElementTree as ET  # ElementTree необходим для работы с XML
from config import TOKEN, POLYGON_API_KEY

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# URL для инфо о стране
COUNTRY_URL = "https://countries.trevorblades.com"
# URL для акций
BASE_URL = 'https://api.polygon.io/v2/aggs/ticker'

# Получение инфо о стране
def get_country_info(country_code):
    json = {'query': f'''
    {{
      country(code: "{country_code}") {{
        name
        native
        emoji
        currency
        languages {{
          code
          name
        }}
      }}
    }}
    '''}
    response = requests.post(COUNTRY_URL, json=json)
    return response.json()

# Получение котировок валют ЦБ РФ
def get_currency_rates(date):
    url = f"http://www.cbr.ru/scripts/XML_daily.asp?date_req={date}"
    response = requests.get(url)

    if response.status_code == 200:
        root = ET.fromstring(response.content)
        rates = {}
        for valute in root.findall('Valute'):
            name = valute.find('Name').text
            value = valute.find('Value').text
            rates[name] = value
        return rates
    else:
        return None

# Получение котировок акций
def get_stock_data(ticker, from_date, to_date):
    url = f"{BASE_URL}/{ticker}/range/1/day/{from_date}/{to_date}"
    params = {
        'adjusted': 'true',
        'sort': 'asc',
        'apiKey': POLYGON_API_KEY
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Ошибка: {response.status_code}, {response.text}")
        return None

@router.message(CommandStart())
async def start_command(message: Message):
    welcome_text = "Привет! Используйте команды для получения информации:\n" \
                   "/country [код страны] - получить информацию о стране\n" \
                   "/currency [дата в формате dd/mm/yyyy] - получить котировки валют на заданную дату\n" \
                   "/stock [тикер] [дата_начала] [дата_конца] - получить котировки акций\n" \
                   "/info - узнать доступные команды"
    await message.answer(welcome_text)

@router.message(Command("info"))
async def info_command(message: Message):
    info_text = "Доступные команды:\n" \
                "/country [код страны] - получить информацию о стране\n" \
                "/currency [дата в формате dd/mm/yyyy] - получить котировки валют на заданную дату\n" \
                "/stock [тикер] [дата_начала] [дата_конца] - получить котировки акций\n"
    await message.answer(info_text)

 # Вывод инфо для пользователя
@router.message()
async def handle_user_message(message: Message):
    user_message = message.text.strip().split()

    # Информация о стране
    if user_message[0].lower() == "/country" and len(user_message) == 2:
        country_code = user_message[1].strip().upper()
        country_info = get_country_info(country_code)

        if 'data' in country_info and country_info['data']['country']:
            country = country_info['data']['country']
            info = (
                f"Страна: {country['name']}\n"
                f"Название на родном языке: {country['native']}\n"
                f"Эмодзи: {country['emoji']}\n"
                f"Валюта: {country['currency']}\n"
                f"Языки:\n"
            )

            for language in country['languages']:
                info += f"- {language['name']} (код: {language['code']})\n"

            await message.answer(info)
        else:
            await message.answer("Страна не найдена. Попробуйте еще раз.")

    # Котировка валют
    elif user_message[0].lower() == "/currency" and len(user_message) == 2:
        date = user_message[1]
        rates = get_currency_rates(date)

        if rates:
            response_message = "Котировки валют на {}:\n".format(date)
            for name, value in rates.items():
                response_message += f"{name}: {value}\n"
            await message.answer(response_message)
        else:
            await message.answer("Не удалось получить котировки. Проверьте дату.")

    #  Получение котировок акций
    elif user_message[0].lower() == "/stock" and len(user_message) == 4:
        ticker = user_message[1]
        from_date = user_message[2]
        to_date = user_message[3]
        stock_data = get_stock_data(ticker, from_date, to_date)

        if stock_data and 'results' in stock_data:
            response_message = f"Котировки акций {ticker} с {from_date} по {to_date}:\n"
            for result in stock_data['results']:
                response_message += (f"Дата: {result['t']} - Открытие: {result['o']}, "
                                     f"Закрытие: {result['c']}, "
                                     f"Максимум: {result['h']}, "
                                     f"Минимум: {result['l']}, "
                                     f"Объем: {result['v']}\n")
            await message.answer(response_message)
        else:
            await message.answer("Не удалось получить данные о котировках. Проверьте тикер и даты.")

    else:
        await message.answer("Неверная команда. Используйте /info для получения списка команд.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())