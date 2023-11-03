# -*- coding: utf-8 -*-

# Created by: Raf

# 这个文件用来辅助调整截图区域坐标。运行游戏，全屏截图，放上路径，就可以查看截图区域。

import cv2

# Modify the region parameters and the image path
capture_pos = [(300, 790, 1250, 75),    # 玩家区域
               (450, 380, 530, 210),    # 玩家上家区域
               (970, 380, 530, 210),   # 玩家下家区域
               (90, 310, 190, 100),   # 地主标志区域(玩家上家)
               (15, 875, 270, 100),    # 地主标志区域(玩家)
               (1640, 310, 190, 100),    # 地主标志区域(玩家下家)
               (817, 36, 287, 136),     # 地主底牌区域
               (680, 570, 530, 160)     #玩家出牌区域
               ]
img_path = 'D:/screenshot/6.jpg'


img = cv2.imread(img_path)
for pos in capture_pos:
    img = cv2.rectangle(img, pos[0:2], (pos[0] + pos[2], pos[1] + pos[3]), (0, 0, 255), 3)
cv2.namedWindow("test", 0)
cv2.imshow("test", img)
cv2.waitKey(0)
cv2.destroyAllWindows()
