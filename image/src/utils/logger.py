import logging
import os

# 設定日誌紀錄的基本配置
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, "app.log")

logging.basicConfig(
    level=logging.DEBUG,  # 設置日誌級別，DEBUG 為最詳細級別
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),  # 日誌紀錄到文件
        logging.StreamHandler()         # 同時在控制台顯示
    ]
)

# 創建 logger
logger = logging.getLogger(__name__)

def log_error(message):
    """用於記錄錯誤訊息"""
    logger.error(message)

def log_info(message):
    """用於記錄普通訊息"""
    logger.info(message)

def log_debug(message):
    """用於記錄調試訊息"""
    logger.debug(message)