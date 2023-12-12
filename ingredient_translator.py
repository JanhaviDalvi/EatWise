from googletrans import Translator


def trans(input_ingredient):
    translator = Translator()
    result = translator.translate(input_ingredient, dest='en')
    return result.text