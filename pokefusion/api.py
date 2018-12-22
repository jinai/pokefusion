import logging
import os

from selenium import webdriver
from selenium.common.exceptions import UnexpectedAlertPresentException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.remote_connection import LOGGER

import utils

LOGGER.setLevel(logging.WARNING)
chrome_bin = os.environ['GOOGLE_CHROME_SHIM']
chrome_options = Options()
chrome_options.binary_location = chrome_bin
chrome_options.add_argument("--headless")
chrome_options.add_argument("--log-level=3")
chrome = webdriver.Chrome(chrome_options=chrome_options, executable_path="chromedriver")


class PokeFusion():
    BASE_URL_FUSION = "http://pokefusion.japeal.com/PKMColourV5.php?ver=3.2&p1={head_id}&p2={body_id}&c={color_id}"
    BASE_URL_SPRITE = "http://pokefusion.japeal.com/sprMenuImgGEN{gen}_{rel_id}.png"
    GENERATIONS = {
        "1": range(1, 152),
        "2": range(152, 252),
        "3": range(252, 387),
        "4": range(387, 495),
        "5": range(495, 650)
    }

    @staticmethod
    def get_fusion_as_file(*, head_id, body_id, color_id):
        try:
            chrome.get(PokeFusion.BASE_URL_FUSION.format(head_id=head_id, body_id=body_id, color_id=color_id))
            data = chrome.find_element_by_id("image1").get_attribute("src").split(",", 1)[1]
            return utils.base64_to_file(data)
        except UnexpectedAlertPresentException:
            chrome.switch_to.alert.dismiss()

    @staticmethod
    def get_sprite_as_file(*, pkmn_id):
        pkmn_id = int(pkmn_id)
        for gen in PokeFusion.GENERATIONS:
            _range = PokeFusion.GENERATIONS[gen]
            if pkmn_id in _range:
                url = PokeFusion.BASE_URL_SPRITE.format(gen=gen, rel_id=pkmn_id - _range.start)
                return utils.zoom_image(utils.url_to_file(url), factor=3)
