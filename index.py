import telebot
from telebot import types
from settings import *
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

##### Create connection with Google spreadsheet
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# # Adicione o caminho para o seu arquivo JSON da conta de serviço
creds = ServiceAccountCredentials.from_json_keyfile_name('googleKey.json', scope)

gc = gspread.authorize(creds)

sheet = gc.open_by_key('12JZ909ld7IO0aP-NFvfF56Tsbk9u6wBPbb0vVgrYyZo') # LINK: https://docs.google.com/spreadsheets/d/12JZ909ld7IO0aP-NFvfF56Tsbk9u6wBPbb0vVgrYyZo/edit#gid=240523302

worksheet = sheet.worksheet('BASE_NEW')

##### Create connection with telegram bot

TOKEN = telegram_API_KEY

bot = telebot.TeleBot(TOKEN)


# Gerenciamento de estado simplificado
user_state = {}

# Funções auxiliares
def get_categories_from_sheet(col_position):
    sheet = gc.open_by_key('12JZ909ld7IO0aP-NFvfF56Tsbk9u6wBPbb0vVgrYyZo')
    worksheet = sheet.worksheet('listas_categorias')
    lista_cat = worksheet.col_values(col_position)
    return lista_cat

def salvar_transacao(user_id, tipo, conta):
    sheet = gc.open_by_key('12JZ909ld7IO0aP-NFvfF56Tsbk9u6wBPbb0vVgrYyZo')
    worksheet = sheet.worksheet('BASE_NEW')
    proxima_linha = len(worksheet.col_values(1)) + 1
    dt_txn = datetime.now().strftime('%d/%m/%Y')
    worksheet.update(f'A{proxima_linha}', [[dt_txn, tipo, conta]])
    user_state[user_id] = {'step': None}  # Resetar o estado do usuário

# Handlers
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True)
    btn1 = types.KeyboardButton('Add transaction')
    btn2 = types.KeyboardButton('Leave')
    markup.add(btn1, btn2)
    bot.send_message(message.chat.id, "Choose an option:", reply_markup=markup)
    user_state[message.chat.id] = {'step': 'welcome'}

@bot.message_handler(func=lambda message: message.text == 'Leave')
def handle_leave(message):
    bot.send_message(message.chat.id, "See you soon!")
    user_state[message.chat.id] = {'step': None}

@bot.message_handler(func=lambda message: message.text == 'Add transaction' and user_state.get(message.chat.id, {}).get('step') == 'welcome')
def handle_add_transaction(message):
    lista_TIPO = get_categories_from_sheet(1)
    markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True)
    for tipo in lista_TIPO:
        markup.add(types.KeyboardButton(tipo))
    bot.send_message(message.chat.id, "What is the transaction TYPE?", reply_markup=markup)
    user_state[message.chat.id] = {'step': 'waiting_for_tipo'}

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get('step') == 'waiting_for_tipo')
def handle_tipo_response(message):
    tipo = message.text
    lista_CONTA = get_categories_from_sheet(2)
    markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True)
    for conta in lista_CONTA:
        markup.add(types.KeyboardButton(conta))
    bot.send_message(message.chat.id, "What is the ACCOUNT?", reply_markup=markup)
    user_state[message.chat.id] = {'step': 'waiting_for_conta', 'tipo': tipo}

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get('step') == 'waiting_for_conta')
def handle_conta_response(message):
    conta = message.text
    tipo = user_state[message.chat.id]['tipo']
    salvar_transacao(message.chat.id, tipo, conta)
    bot.send_message(message.chat.id, "Transaction successfully added!")

# Iniciar o bot
bot.polling()

## OTIMIZAR pegando dados de categoria apenas 1 vez