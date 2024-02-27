import telebot
from telebot import types
from settings import *
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd
import time

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

sheet = gc.open_by_key('12JZ909ld7IO0aP-NFvfF56Tsbk9u6wBPbb0vVgrYyZo')
worksheet = sheet.worksheet('listas_categorias')
data = worksheet.get_all_values()
df_list_cat = pd.DataFrame(data[1:], columns=['TIPO', 'CONTA', 'CATEGORIA', 'CATEGORIA_DETALHADA'])

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

def salvar_transacao(user_id, tipo, conta, nome_txn, categoria, categoria_detalhada, valor):
    sheet = gc.open_by_key('12JZ909ld7IO0aP-NFvfF56Tsbk9u6wBPbb0vVgrYyZo')
    worksheet = sheet.worksheet('BASE_NEW')
    proxima_linha = len(worksheet.col_values(1)) + 1
    dt_txn = datetime.now().strftime('%d/%m/%Y')
    dt_payment=f'=IF(D{proxima_linha}="Cartão Azul Família";EOMONTH(A{proxima_linha};0)+6;IF(D{proxima_linha}="Cartão XP";EOMONTH(A{proxima_linha};0)+5;A{proxima_linha}))'
    family_divided=f'=IF(D{proxima_linha}="Cartão Azul Família";1;0)'
    dt_for_calc= '=EOMONTH(B:B;-1)+1'
    worksheet.update(f'A{proxima_linha}:J{proxima_linha}', [[dt_txn, dt_payment, tipo, conta, nome_txn, categoria, categoria_detalhada, valor, family_divided, dt_for_calc]], value_input_option='USER_ENTERED')

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
    lista_TIPO = df_list_cat.loc[df_list_cat['TIPO'] != '', 'TIPO'].dropna().unique().tolist()
    markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True)
    for tipo in lista_TIPO:
        markup.add(types.KeyboardButton(tipo))
    bot.send_message(message.chat.id, "What is the transaction TYPE?", reply_markup=markup)
    user_state[message.chat.id] = {'step': 'waiting_for_tipo'}

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get('step') == 'waiting_for_tipo')
def handle_tipo_response(message):
    tipo = message.text
    lista_CONTA = df_list_cat.loc[df_list_cat['CONTA'] != '', 'CONTA'].dropna().unique().tolist()
    markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True)
    for conta in lista_CONTA:
        markup.add(types.KeyboardButton(conta))
    bot.send_message(message.chat.id, "What is the ACCOUNT?", reply_markup=markup)
    user_state[message.chat.id] = {'step': 'waiting_for_conta', 'tipo': tipo}

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get('step') == 'waiting_for_conta')
def handle_conta_response(message):
    conta = message.text
    bot.send_message(message.chat.id, "What is the VALUE of the transaction?")
    user_state[message.chat.id] = {'step': 'waiting_for_valor', 'tipo': user_state[message.chat.id]['tipo'], 'conta': conta}

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get('step') == 'waiting_for_valor')
def handle_valor_response(message):
    valor = message.text
    bot.send_message(message.chat.id, "What is the NAME of the transaction?")
    user_state[message.chat.id].update({'step': 'waiting_for_nome_txn', 'valor': valor})

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get('step') == 'waiting_for_nome_txn')
def handle_nome_txn_response(message):
    nome_txn = message.text
    lista_CATEGORIA = df_list_cat.loc[df_list_cat['CATEGORIA'] != '', 'CATEGORIA'].dropna().unique().tolist()
    markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True)
    for categoria in lista_CATEGORIA:
        markup.add(types.KeyboardButton(categoria))
    bot.send_message(message.chat.id, "What is the CATEGORY of the transaction?", reply_markup=markup)
    user_state[message.chat.id].update({'step': 'waiting_for_categoria', 'nome_txn': nome_txn})

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get('step') == 'waiting_for_categoria')
def handle_categoria_response(message):
    categoria = message.text
    lista_CATEGORIA_DETALHADA = df_list_cat.loc[(df_list_cat['CATEGORIA'] == categoria) & (df_list_cat['CATEGORIA_DETALHADA'] != ''), 'CATEGORIA_DETALHADA'].dropna().unique().tolist()
    markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True)
    for categoria_detalhada in lista_CATEGORIA_DETALHADA:
        markup.add(types.KeyboardButton(categoria_detalhada))
    bot.send_message(message.chat.id, "What is the DETAILED CATEGORY of the transaction?", reply_markup=markup)
    user_state[message.chat.id].update({'step': 'waiting_for_categoria_detalhada', 'categoria': categoria})

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get('step') == 'waiting_for_categoria_detalhada')
def handle_last_response(message):
    categoria_detalhada = message.text
    user_data = user_state[message.chat.id]
    salvar_transacao(message.chat.id, user_data['tipo'], user_data['conta'], user_data['nome_txn'], user_data['categoria'], categoria_detalhada, user_data['valor'])
    bot.send_message(message.chat.id, "Transaction successfully added!")

@bot.message_handler(func=lambda message: True)  # Catch-all para mensagens não reconhecidas
def handle_unknown(message):
    bot.send_message(message.chat.id, "I didn't understand that. Please try again.")

# Main loop
def main():
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"Error: {e}")
            bot.stop_polling()
            time.sleep(5)

if __name__ == "__main__":
    main()

# Iniciar o bot
bot.polling()