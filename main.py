# -*- coding: utf-8 -*-
# Created by: Raf
import os
import sys
import cv2
import numpy as np
import pyautogui
from PJYSDK import *
from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import QTime, QEventLoop
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMessageBox
import BidModel
from MainWindowUI import Ui_Form
from douzero.env.game import GameEnv
from douzero.evaluation.deep_agent import DeepAgent

EnvCard2RealCard = {3: '3', 4: '4', 5: '5', 6: '6', 7: '7',
                    8: '8', 9: '9', 10: 'T', 11: 'J', 12: 'Q',
                    13: 'K', 14: 'A', 17: '2', 20: 'X', 30: 'D'}

RealCard2EnvCard = {'3': 3, '4': 4, '5': 5, '6': 6, '7': 7,
                    '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12,
                    'K': 13, 'A': 14, '2': 17, 'X': 20, 'D': 30}

AllEnvCard = [3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 6, 6, 7, 7, 7, 7,
              8, 8, 8, 8, 9, 9, 9, 9, 10, 10, 10, 10, 11, 11, 11, 11, 12,
              12, 12, 12, 13, 13, 13, 13, 14, 14, 14, 14, 17, 17, 17, 17, 20, 30]

AllCards = ['rD', 'bX', 'b2', 'r2', 'bA', 'rA', 'bK', 'rK', 'bQ', 'rQ', 'bJ', 'rJ', 'bT', 'rT',
            'b9', 'r9', 'b8', 'r8', 'b7', 'r7', 'b6', 'r6', 'b5', 'r5', 'b4', 'r4', 'b3', 'r3']

class MyPyQT_Form(QtWidgets.QWidget, Ui_Form):
    def __init__(self):
        super(MyPyQT_Form, self).__init__()
        self.setupUi(self)
        self.setWindowFlags(QtCore.Qt.WindowMinimizeButtonHint |    # 使能最小化按钮
                            QtCore.Qt.WindowCloseButtonHint |       # 使能关闭按钮
                            QtCore.Qt.WindowStaysOnTopHint)         # 窗体总在最前端
        self.setFixedSize(self.width(), self.height())              # 固定窗体大小
        self.setWindowIcon(QIcon('pics/favicon.ico'))
        window_pale = QtGui.QPalette()
        self.setPalette(window_pale)

        self.Players = [self.RPlayer, self.Player, self.LPlayer]
        self.counter = QTime()

        # 参数
        self.MyConfidence = 0.9  # 我的牌的置信度
        self.OutConfidence = 0.9 # 我的出牌置信度
        self.OtherConfidence = 0.9  # 别人的牌的置信度
        self.WhiteConfidence = 0.9  # 检测白块的置信度
        self.LandlordFlagConfidence = 0.8     # # 检测地主标志的置信度
        self.ThreeLandlordCardsConfidence = 0.85  # 检测地主底牌的置信度
        self.WaitTime = 1  # 等待状态稳定延时
        self.MyFilter = 40  # 我的牌检测结果过滤参数
        self.OtherFilter = 25  # 别人的牌检测结果过滤参数
        self.SleepTime = 0.1  # 循环中睡眠时间

        # 坐标
        self.MyHandCardsPos = (300, 790, 1250, 75)  # 我的截图区域
        self.LPlayedCardsPos = (450, 380, 530, 210)  # 左边截图区域
        self.RPlayedCardsPos = (970, 380, 530, 210)  # 右边截图区域
        self.LandlordFlagPos = [(1640, 310, 190, 100), (15, 875, 270, 100), (90, 310, 190, 100)]  # 地主标志截图区域(右-我-左)
        self.ThreeLandlordCardsPos = (817, 36, 287, 136)      # 地主底牌截图区域，resize成349x168
        self.outPos = (680, 570, 530, 160)

        # 信号量
        self.shouldExit = 0  # 通知上一轮记牌结束
        self.canRecord = threading.Lock()  # 开始记牌

        # 模型路径
        self.card_play_model_path_dict = {
            'landlord': "baselines/douzero_WP/landlord.ckpt",
            'landlord_up': "baselines/douzero_WP/landlord_up.ckpt",
            'landlord_down': "baselines/douzero_WP/landlord_down.ckpt"
        }

    def init_display(self):
        self.WinRate.setText("预估胜率")
        self.InitCard.setText("开始")
        self.UserHandCards.setText("手牌")
        self.LPlayedCard.setText("上家出牌区域")
        self.RPlayedCard.setText("下家出牌区域")
        self.PredictedCard.setText("AI出牌区域")
        self.ThreeLandlordCards.setText("三张底牌")
        self.BidWinrate.setText("叫牌推荐")
        for player in self.Players:
            player.setStyleSheet('background-color: rgba(255, 0, 0, 0);')

    def init_cards(self):
        # 玩家手牌
        self.user_hand_cards_real = ""
        self.user_hand_cards_env = []
        # 其他玩家出牌
        self.other_played_cards_real = ""
        self.other_played_cards_env = []
        # 其他玩家手牌（整副牌减去玩家手牌，后续再减掉历史出牌）
        self.other_hand_cards = []
        # 三张底牌
        self.three_landlord_cards_real = ""
        self.three_landlord_cards_env = []
        #玩家出牌
        self.out_cards_real = None
        # 玩家角色代码：0-地主上家, 1-地主, 2-地主下家
        self.user_position_code = None
        self.user_position = ""
        # 开局时三个玩家的手牌
        self.card_play_data_list = {}
        # 出牌顺序：0-玩家出牌, 1-玩家下家出牌, 2-玩家上家出牌
        self.play_order = 0

        self.env = None

        while len(self.user_hand_cards_real) < 17 or \
            len(self.three_landlord_cards_real) != 3:
            self.counter.restart()
            while self.counter.elapsed() < 1000:
                QtWidgets.QApplication.processEvents(QEventLoop.AllEvents, 50)
            # 识别玩家手牌
            self.other_hand_cards = []
            self.user_hand_cards_real = self.find_my_cards(self.MyHandCardsPos)
            print("识别玩家手牌")
            self.UserHandCards.setText(self.user_hand_cards_real)
            self.user_hand_cards_env = [RealCard2EnvCard[c] for c in list(self.user_hand_cards_real)]
            print(len(self.user_hand_cards_real))
            if len(self.user_hand_cards_real) == 17:
                win_rate = BidModel.predict(self.user_hand_cards_real)
                print("预计叫地主胜率：", win_rate)
                self.WinRate.setText("预估胜率：" + str(round(win_rate, 2)) + "%")
                if win_rate > 75:
                    self.BidWinrate.setText("抢地主")
                elif win_rate > 65:
                    self.BidWinrate.setText("叫地主")
                else:
                    self.BidWinrate.setText("不叫")
            # 识别三张底牌
            self.three_landlord_cards_real = self.find_three_landlord_cards(self.ThreeLandlordCardsPos)
            print("识别三张底牌")
            self.ThreeLandlordCards.setText("底牌：" + self.three_landlord_cards_real)
            self.three_landlord_cards_env = [RealCard2EnvCard[c] for c in list(self.three_landlord_cards_real)]

        while self.user_position_code is None:
            self.counter.restart()
            while self.counter.elapsed() < 1000:
                QtWidgets.QApplication.processEvents(QEventLoop.AllEvents, 50)
            # 识别玩家的角色
            self.user_position_code = self.find_landlord(self.LandlordFlagPos)
            print("识别玩家角色")
        self.user_position = ['landlord_up', 'landlord', 'landlord_down'][self.user_position_code]
        for player in self.Players:
            player.setStyleSheet('background-color: rgba(255, 0, 0, 0);')
        self.Players[self.user_position_code].setStyleSheet('background-color: rgba(255, 0, 0, 0.1);')

        # 整副牌减去玩家手上的牌，就是其他人的手牌,再分配给另外两个角色（如何分配对AI判断没有影响）
        for i in set(AllEnvCard):
            self.other_hand_cards.extend([i] * (AllEnvCard.count(i) - self.user_hand_cards_env.count(i)))
        self.card_play_data_list.update({
            'three_landlord_cards': self.three_landlord_cards_env,
            ['landlord_up', 'landlord', 'landlord_down'][(self.user_position_code + 0) % 3]:
                self.user_hand_cards_env,
            ['landlord_up', 'landlord', 'landlord_down'][(self.user_position_code + 1) % 3]:
                self.other_hand_cards[0:17] if (self.user_position_code + 1) % 3 != 1 else self.other_hand_cards[17:],
            ['landlord_up', 'landlord', 'landlord_down'][(self.user_position_code + 2) % 3]:
                self.other_hand_cards[0:17] if (self.user_position_code + 1) % 3 == 1 else self.other_hand_cards[17:]
        })

        while len(self.card_play_data_list["landlord_up"]) != 17 or \
            len(self.card_play_data_list["landlord_down"]) != 17 or \
            len(self.card_play_data_list["landlord"]) != 20:
            #print(len(self.card_play_data_list["landlord_up"]))
            # QMessageBox.critical(self, "手牌识别出错", "初始手牌数目有误", QMessageBox.Yes, QMessageBox.Yes)
            # self.init_display()
            # return
            self.counter.restart()
            while self.counter.elapsed() < 1000:
                QtWidgets.QApplication.processEvents(QEventLoop.AllEvents, 50)
            # 识别玩家手牌
            self.other_hand_cards = []
            self.user_hand_cards_real = self.find_my_cards(self.MyHandCardsPos)
            print("识别玩家手牌")
            self.UserHandCards.setText(self.user_hand_cards_real)
            self.user_hand_cards_env = [RealCard2EnvCard[c] for c in list(self.user_hand_cards_real)]

            # 整副牌减去玩家手上的牌，就是其他人的手牌,再分配给另外两个角色（如何分配对AI判断没有影响）
            for i in set(AllEnvCard):
                self.other_hand_cards.extend([i] * (AllEnvCard.count(i) - self.user_hand_cards_env.count(i)))
            self.card_play_data_list.update({
                'three_landlord_cards': self.three_landlord_cards_env,
                'landlord_up': [],
                ['landlord_up', 'landlord', 'landlord_down'][(self.user_position_code + 0) % 3]:
                    self.user_hand_cards_env,
                ['landlord_up', 'landlord', 'landlord_down'][(self.user_position_code + 1) % 3]:
                    self.other_hand_cards[0:17] if (self.user_position_code + 1) % 3 != 1 else self.other_hand_cards[
                                                                                               17:],
                ['landlord_up', 'landlord', 'landlord_down'][(self.user_position_code + 2) % 3]:
                    self.other_hand_cards[0:17] if (self.user_position_code + 1) % 3 == 1 else self.other_hand_cards[
                                                                                               17:]
            })

        # 得到出牌顺序
        self.play_order = 0 if self.user_position == "landlord" else 1 if self.user_position == "landlord_up" else 2

        # 创建一个代表玩家的AI
        ai_players = [0, 0]
        ai_players[0] = self.user_position
        ai_players[1] = DeepAgent(self.user_position, self.card_play_model_path_dict[self.user_position])

        self.env = GameEnv(ai_players)

        self.start()

    def start(self):
        self.env.card_play_init(self.card_play_data_list)
        print("开始出牌\n")
        while not self.env.game_over:
            # 玩家出牌时就通过智能体获取action，否则通过识别获取其他玩家出牌
            if self.play_order == 0:
                self.PredictedCard.setText("出牌中...")
                action_message = self.env.step(self.user_position)
                # 更新界面
                self.UserHandCards.setText("手牌：" + str(''.join(
                    [EnvCard2RealCard[c] for c in self.env.info_sets[self.user_position].player_hand_cards]))[::-1])

                self.PredictedCard.setText(action_message["action"] if action_message["action"] else "不出")
                self.WinRate.setText("胜率：" + action_message["win_rate"])
                print("\n手牌：", str(''.join(
                        [EnvCard2RealCard[c] for c in self.env.info_sets[self.user_position].player_hand_cards])))
                print("出牌：", action_message["action"] if action_message["action"] else "不出", "， 胜率：",
                      action_message["win_rate"])

                while self.find_out(self.outPos) == 0 and \
                          not pyautogui.locateOnScreen('pics/opass.png',
                                                 region=self.outPos,
                                                 confidence=self.OutConfidence):
                    if self.env.game_over:
                        break
                    print("等待玩家出牌")
                    self.counter.restart()
                    while self.counter.elapsed() < 1200:
                        QtWidgets.QApplication.processEvents(QEventLoop.AllEvents, 50)

                self.play_order = 1
            elif self.play_order == 1:
                self.other_played_cards_real = ""
                self.RPlayedCard.setText("出牌中...")
                pass_flag = None
                self.counter.restart()
                while self.counter.elapsed() < 500:
                    QtWidgets.QApplication.processEvents(QEventLoop.AllEvents, 50)
                # 不出
                pass_flag = pyautogui.locateOnScreen('pics/pass.png',
                                                     region=self.RPlayedCardsPos,
                                                     confidence=0.85)

                while self.other_played_cards_real == "" and \
                        not pyautogui.locateOnScreen('pics/pass.png',
                                                     region=self.RPlayedCardsPos,
                                                     confidence=0.85):
                    if self.env.game_over:
                        break
                    print("等待下家出牌")
                    # 未找到"不出"
                    if pass_flag is None:
                        self.counter.restart()
                        while self.counter.elapsed() < 1200:
                            QtWidgets.QApplication.processEvents(QEventLoop.AllEvents, 50)
                        # 识别下家出牌
                        self.other_played_cards_real = self.find_other_cards(self.RPlayedCardsPos)
                    # 找到"不出"
                    else:
                        self.other_played_cards_real = ""
                print("\n下家出牌：", self.other_played_cards_real)
                self.other_played_cards_env = [RealCard2EnvCard[c] for c in list(self.other_played_cards_real)]
                self.env.step(self.user_position, self.other_played_cards_env)
                # 更新界面
                self.RPlayedCard.setText(self.other_played_cards_real if self.other_played_cards_real else "不出")
                self.play_order = 2
            elif self.play_order == 2:
                self.other_played_cards_real = ""
                self.LPlayedCard.setText("出牌中...")
                self.counter.restart()
                while self.counter.elapsed() < 500:
                    QtWidgets.QApplication.processEvents(QEventLoop.AllEvents, 50)
                # 不出
                pass_flag = pyautogui.locateOnScreen('pics/lpass.png',
                                                     region=self.LPlayedCardsPos,
                                                     confidence=0.85)

                while self.other_played_cards_real == "" and \
                        not pyautogui.locateOnScreen('pics/lpass.png',
                                                    region=self.LPlayedCardsPos,
                                                    confidence=0.85):
                    if self.env.game_over:
                        break
                    print("等待上家出牌")
                    # 未找到"不出"
                    if pass_flag is None:
                        self.counter.restart()
                        while self.counter.elapsed() < 1200:
                            QtWidgets.QApplication.processEvents(QEventLoop.AllEvents, 50)
                        # 识别上家出牌
                        self.other_played_cards_real = self.find_other_cards(self.LPlayedCardsPos)
                    # 找到"不出"
                    else:
                        self.other_played_cards_real = ""
                    QtWidgets.QApplication.processEvents(QEventLoop.AllEvents, 50)
                print("\n上家出牌：", self.other_played_cards_real)
                self.other_played_cards_env = [RealCard2EnvCard[c] for c in list(self.other_played_cards_real)]
                self.env.step(self.user_position, self.other_played_cards_env)
                self.play_order = 0
                # 更新界面
                self.LPlayedCard.setText(self.other_played_cards_real if self.other_played_cards_real else "不出")
            else:
                pass

            self.counter.restart()
            while self.counter.elapsed() < 100:
                QtWidgets.QApplication.processEvents(QEventLoop.AllEvents, 50)

        print("{}胜，本局结束，开始下一局请点开始!\n".format("农民" if self.env.winner == "farmer" else "地主"))
        QMessageBox.information(self, "本局结束!", "{}胜！开始下一局请点开始".format("农民" if self.env.winner == "farmer" else "地主"),
                                QMessageBox.Yes, QMessageBox.Yes)
        self.env.reset()
        self.init_display()

    def find_landlord(self, landlord_flag_pos):
        self.counter.restart()
        while self.counter.elapsed() < 1000:
            QtWidgets.QApplication.processEvents(QEventLoop.AllEvents, 50)
        for pos in landlord_flag_pos:
            result = pyautogui.locateOnScreen('pics/landlord_words.png', region=pos, confidence=self.LandlordFlagConfidence)
            result1 = pyautogui.locateOnScreen('pics/landlord.png', region=pos, confidence=self.LandlordFlagConfidence)
            if result is not None or result1 is not None:
                return landlord_flag_pos.index(pos)
        return None

    def find_out(self, pos): #是否有不出
        result = pyautogui.locateOnScreen('pics/white.png', region=pos, confidence=self.OutConfidence)
        result1 = pyautogui.locateOnScreen('pics/obX.png', region=pos, confidence=self.OutConfidence)
        result2 = pyautogui.locateOnScreen('pics/orD.png', region=pos, confidence=self.OutConfidence)
        if result is None and result1 is None and result2 is None:
            return 0
        else:
            return 1

    def find_three_landlord_cards(self, pos):
        three_landlord_cards_real = ""
        img = pyautogui.screenshot(region=pos)
        img = img.resize((349, 168))
        img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        # 创建一个列表来存储找到的位置
        found_locations = []
        for card in AllCards:
            # 加载卡片图像
            card_image = cv2.imread('pics/o' + card + '.png')
            # 使用模板匹配来查找卡片匹配项
            result = cv2.matchTemplate(img, card_image, cv2.TM_CCOEFF_NORMED)
            threshold = self.ThreeLandlordCardsConfidence  # 设置匹配置信度阈值
            # 获取匹配结果的位置
            loc = np.where(result >= threshold)
            # 遍历匹配位置并将卡片添加到结果中
            for pt in zip(*loc[::-1]):
                # 检查是否是重复位置
                is_duplicate = False
                for prev_loc in found_locations:
                    distance = self.calculate_distance(pt, prev_loc)
                    if distance < 15:
                        is_duplicate = True
                        break
                if not is_duplicate:
                    # 在图像上绘制矩形标记匹配位置，避免重复匹配
                    cv2.rectangle(img, pt, (pt[0] + card_image.shape[1], pt[1] + card_image.shape[0]), (0, 0, 255),
                                  2)
                    # 将卡片追加到结果中
                    three_landlord_cards_real += card[1]
                    # 将当前位置添加到已找到的位置列表中
                    found_locations.append(pt)

        #print(three_landlord_cards_real)
        return three_landlord_cards_real

    def calculate_distance(self, pt1, pt2):
        # 计算两个点之间的欧氏距离
        return np.sqrt((pt1[0] - pt2[0]) ** 2 + (pt1[1] - pt2[1]) ** 2)

    def find_my_cards(self, pos):
        user_hand_cards_real = ""
        img = pyautogui.screenshot(region=pos)
        img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        # 存储已找到的匹配位置
        found_locations = []
        for card in AllCards:
            # 读取卡片图像
            card_image = cv2.imread('pics/m' + card + '.png')
            # 使用OpenCV的模板匹配方法
            result = cv2.matchTemplate(img, card_image, cv2.TM_CCOEFF_NORMED)
            # 获取匹配结果的位置
            loc = np.where(result >= self.MyConfidence)
            # 如果找到匹配的图像，则将卡片信息添加到结果中
            if loc[0].any():
                for pt in zip(*loc[::-1]):
                    # 检查当前匹配位置与之前找到的位置的距离
                    is_duplicate = False
                    for prev_loc in found_locations:
                        distance = self.calculate_distance(pt, prev_loc)
                        if distance < self.MyFilter:
                            is_duplicate = True
                            break
                    if not is_duplicate:
                        # 在图像上绘制矩形标记匹配位置，避免重复匹配
                        cv2.rectangle(img, pt, (pt[0] + card_image.shape[1], pt[1] + card_image.shape[0]), (0, 0, 255),
                                      2)
                        # 将卡片信息添加到结果中
                        user_hand_cards_real += card[1]
                        # 将当前匹配位置添加到已找到的位置列表中
                        found_locations.append(pt)
        #print(user_hand_cards_real)
        return user_hand_cards_real

    def find_other_cards(self, pos):
        other_played_cards_real = ""
        self.counter.restart()
        while self.counter.elapsed() < 1000:
            QtWidgets.QApplication.processEvents(QEventLoop.AllEvents, 50)
        img = pyautogui.screenshot(region=pos)
        img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        # 存储已找到的匹配位置
        found_locations = []
        for card in AllCards:
            # 读取卡片图像
            card_image = cv2.imread('pics/o' + card + '.png')
            # 使用OpenCV的模板匹配方法
            result = cv2.matchTemplate(img, card_image, cv2.TM_CCOEFF_NORMED)
            threshold = self.OtherConfidence  # 设置匹配阈值，可以根据需要调整
            # 获取匹配结果的位置
            loc = np.where(result >= threshold)
            # 如果找到匹配的图像，则将卡片信息添加到结果中
            if loc[0].any():
                for pt in zip(*loc[::-1]):
                    # 检查当前匹配位置与之前找到的位置的距离
                    is_duplicate = False
                    for prev_loc in found_locations:
                        distance = self.calculate_distance(pt, prev_loc)
                        if distance < self.OtherFilter:  # Use self.OtherFilter without the extra "self."
                            is_duplicate = True
                            break
                    if not is_duplicate:
                        # 将卡片信息添加到结果中
                        other_played_cards_real += card[1]
                        # 将当前匹配位置添加到已找到的位置列表中
                        found_locations.append(pt)
        #print(other_played_cards_real)
        return other_played_cards_real

    def stop(self):
        try:
            self.env.game_over = True
        except AttributeError as e:
            pass


if __name__ == '__main__':
    # os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
    # os.environ["CUDA_VISIBLE_DEVICES"] = '0'
    os.environ["GIT_PYTHON_REFRESH"] = 'quiet'

    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet("""
        QPushButton {
            background-color: #3498db;
            border: 2px solid #2980b9;
            border-radius: 5px;
            color: white;
            font-weight: bold;
            padding: 8px 16px;
        }

        QPushButton:hover {
            background-color: #2980b9;
            border: 2px solid #3498db;
        }

        QComboBox {
            background-color: white;
            border: 2px solid #3498db;
            border-radius: 5px;
            padding: 4px;
            font-weight: bold;
        }

        QComboBox:drop-down {
            border: 0;
        }

        QComboBox QAbstractItemView:item {
            height: 30px;
            font-weight: normal;
        }

        QLabel {
            color: #3498db;
        }
    """)

    my_pyqt_form = MyPyQT_Form()
    my_pyqt_form.show()
    sys.exit(app.exec_())