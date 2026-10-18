"""Ponto de entrada: python main.py"""
import logging

from assessor.bot import criar_aplicacao

logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)

if __name__ == "__main__":
    criar_aplicacao().run_polling()
