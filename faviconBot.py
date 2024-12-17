import logging
import os 
import telebot
from commonregex import CommonRegex
from PIL import Image
from io import BytesIO
import requests
import tempfile 
import favicon
import cairosvg

API_KEY = os.getenv('API_KEY')
bot = telebot.TeleBot(API_KEY)    

@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, "Здравствуйте! Данный бот специализируется на анализе URL и возврате всех доступных Favicon. Принимает за раз только один URL. \n\nДля продолжения работы, пожалуйста, напишите или скопируйте и вставьте URL сайта.")

@bot.message_handler(content_types=["text"])
def get_favicon(message):
    user_message = CommonRegex(message.any_text)
    url = user_message.links #Регулярное выражение на проверку наличия ссылки в строке
    temp_dir = tempfile.mkdtemp() #Создание временной директории, где будут храниться PNG файлы
    
    if not url:
        bot.send_message(message.chat.id, "Данный бот принимает только URL.")
        return
    
    try:
        #Записываем в переменную icons лист из ссылок на favicons
        if "https://" not in url[0]:
            icons = favicon.get("https://" + url[0])
            
        else:
            icons = favicon.get(url[0])
            
    except Exception as e:
        logging.error(e)
        bot.send_message(message.chat.id, f"Ссылки {url[0]} не существует или доступ ограничен.")
        return
        
    if len(icons) > 0:
        try:
            
            for real_favicon in icons: 
                response = requests.get(real_favicon.url, stream=True)#Передаём заголовки URL в response
                response.raise_for_status()#Проверяем, не было ли ошибки при GET запросе
                
                if real_favicon.format != "svg":
                    #Открываем картинку и записываем её во временную директорию, изменяя формат на PNG
                    image = Image.open(BytesIO(response.content))
                    png_path = os.path.join(temp_dir, f"{real_favicon.format}.png")
                    image.save(png_path, format="PNG")
                    bot.send_document(message.chat.id, open(png_path, "rb"))
                
                #Поскольку Telegram не распознаёт SVG формат, то необходимо выловить в листе ссылок SVG, 
                #скачать его во временную директорию и изменить на PNG с помощью библиотеки cairosvg
                else:
                    #Создаём пустой PNG файл во временной директории
                    temp_png_path = os.path.join(temp_dir, f"{real_favicon.format}.png")
                    svgpng = Image.new("RGB", (100, 100), color="white")
                    svgpng.save(temp_png_path, format="PNG")
                    #Скачиваем во временную директорию в SVG файл картинку, которую мы выловили в response          
                    temp_svg_path = os.path.join(temp_dir, "temp_file.svg")
                    with open(temp_svg_path, "wb") as temp_svg:
                        for chunk in response.iter_content(1024):
                            temp_svg.write(chunk) 
                    #Перезаписываем содержимое из SVG файла в только что созданный PNG        
                    cairosvg.svg2png(url=temp_svg_path, write_to=temp_png_path)
                    
                    with open(temp_png_path, "rb") as png_file:
                        bot.send_document(message.chat.id, png_file) 
                
        except Exception as e:
            logging.error(e)
            bot.send_message(message.chat.id, "Ошибка при обработке Favicon (недопустимый формат).")
              
    else:
        bot.send_message(message.chat.id, "Favicon " + url[0] + " не найден")   
    
bot.polling()
