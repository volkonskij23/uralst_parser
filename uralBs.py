from bs4                       import BeautifulSoup
from requests_futures.sessions import FuturesSession
import json
import requests
import pandas as pd


"""
    Функция чтения json-файла

    :param     filename: Название файла
    :type      filename: str.
    
    :returns: dict или list
"""
def json_load(filename):
    with open(filename, "r", encoding="utf8") as read_file:
        result = json.load(read_file)
    return result

"""
    Функция записи в json-файл

    :param     filename: Название файла
    :type      filename: str.
    :param     data: Записываемые данные
    :type      data: list or dict.
  
"""
def json_dump(filename, data):
    with open(filename, "w", encoding="utf8") as write_file:
        json.dump(data, write_file, ensure_ascii=False)

"""
    Функция добавления записи в json-файл

    :param     filename: Название файла
    :type      filename: str.
    :param     data: Добавляемые данные
    :type      data: list or dict.
  
"""
def json_add(filename, data):
    res = json_load(filename)

    y = res | data

    json_dump(filename, y)

"""
    Функция дробления списка на заданное количество частей
"""
def chunks(lst, n):

    for i in range(0, len(lst), n):
        yield lst[i : i + n]

"""
    Функция записи результата парсинга в excel
"""
def res_to_excel():
    result = json_load("result.json")
    df_list = []

    for link in result.keys():

        try:
            df_list.append(
                [
                    link,
                    result[link]["product_name"],
                    result[link]["code"],
                    result[link]["short_desc"],
                    result[link]["price"],
                    "| ".join(result[link]["imgs"]),
                    result[link]["props_text"],
                    result[link]["desc_text"],
                    result[link]["stock"],
                    result[link]["expected"],
                    result[link]["status"],
                ]
            )
        except:
            df_list.append([link, "", "", "", "", "", "", "", "", "", ""])

    df = pd.DataFrame(
        df_list,
        columns=[
            "Ссылка на товар",
            "Название",
            "Код",
            "Краткое описание",
            "Цена",
            "Ссылки на картинки",
            "Характеристики",
            "Описание",
            "В наличии",
            "Ожидается",
            "Статус",
        ],
    )
    df.to_excel(r"result.xlsx", index=False)


url        = "https://www.uralst.ru/in-stock#all"
old_result = json_load("result.json")
result     = {}
catalog    = []
response   = requests.get("https://www.uralst.ru/in-stock#all")
soup       = BeautifulSoup(response.text, "html.parser")
urls       = soup.find_all("div", class_="technique-in-stock__name")

for item_url in urls:
    url = item_url.find("a", href=True)
    if url not in catalog:
        catalog.append("https://www.uralst.ru" + url["href"])


chunks_list = chunks(catalog, 10)

for chunk in chunks_list:

    session = FuturesSession(max_workers=10)

    futures = [session.get(i) for i in chunk]

    for future in futures:
        try:
            page = future.result()

            soup = BeautifulSoup(page.text, "html.parser")
            link = chunk[futures.index(future)]

            print(str(catalog.index(link)) + "/" + str(len(catalog)))
            result[link] = {}

            result[link]["product_name"] = soup.find(
                "h1", class_="catalogunit-title"
            ).text
            products = soup.find_all("div", class_="product-1__item")

            for product in products:
                name = product.find("div", class_="product-1__name").find("a").text

                if result[link]["product_name"].upper() == name.upper():
                    try:
                        result[link]["code"] = product.find(
                            "span", class_="model-code__code"
                        ).text
                    except:
                        result[link]["code"] = product.find(
                            "div", class_="product-1__model-code"
                        ).text.replace("Код:", "")
                    result[link]["short_desc"] = product.find(
                        "div", class_="product-1__body"
                    ).text.strip()

                    if "not-made" not in link:
                        try:
                            result[link]["price"] = product.find(
                                "div", class_="product-1__price prices__price"
                            ).text.strip()
                        except Exception as e:

                            result[link]["price"] = product.find(
                                "div",
                                class_="product-1__price prices__price prices__price_spec",
                            ).text.strip()
                    else:
                        result[link]["price"] = "Модель не производится"

                    try:
                        result[link]["stock"] = product.find(
                            "div", class_="units-in-stock"
                        ).text.strip()
                    except:
                        result[link]["stock"] = ""

                    try:
                        result[link]["expected"] = product.find(
                            "div", class_="expected-units-in-stock"
                        ).text.strip()
                    except:
                        try:
                            result[link]["expected"] = product.find(
                                "div", class_="expected-units"
                            ).text.strip()
                        except:
                            result[link]["expected"] = ""
                    break

            print(result[link]["price"])
            img_block = soup.find("div", class_="product-card-images__thumbnail")
            imgs_urls = img_block.find_all("div")

            result[link]["imgs"] = []
            for img_url in imgs_urls:
                try:
                    url = img_url.find("a", href=True)
                    if url not in result[link]["imgs"]:
                        result[link]["imgs"].append(url["href"].split("?")[0])
                except:
                    continue

            try:
                props = soup.find("table", class_="model-props-table")
                result[link]["props_text"] = props.text.strip()
            except:
                result[link]["props_text"] = ""

            try:
                desc = soup.find("div", class_="description_container").text
            except:
                desc = ""

            try:
                desc_spec = (
                    "\n"
                    + soup.find_all("div", class_="specifications_container")[1].text
                )
            except:
                desc_spec = ""

            result[link]["desc_text"] = (desc + desc_spec).strip()

            if link not in old_result.keys():
                result[link]["status"] = "Новое"
            elif old_result[link]["price"] == result[link]["price"]:
                result[link]["status"] = "Активное"
            elif old_result[link]["price"] <= result[link]["price"]:
                result[link]["status"] = "Цена выросла"
            elif old_result[link]["price"] >= result[link]["price"]:
                result[link]["status"] = "Цена снизилась"
        except Exception as e:
            print(e)
            continue


for link in old_result.keys():
    if link not in result.keys():
        result[link] = {}
        result[link] = old_result[link]
        result[link]["status"] = "Неактивно"

json_add("result.json", result)


res_to_excel()
