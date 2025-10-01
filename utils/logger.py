import logging
import sys
import os


# Настройка кодировки для Windows
if sys.platform == "win32":
    try:
        import codecs
        # Пытаемся настроить stdout/stderr для UTF-8
        if sys.stdout.encoding != 'utf-8':
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        if sys.stderr.encoding != 'utf-8':
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except Exception as e:
        print(f"Warning: Could not set UTF-8 encoding: {e}")

# Создаем папку для логов если её нет
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'bot.log'), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('accountant_bot')

# Дополнительная настройка для обработки Unicode в Windows
class SafeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            # Заменяем проблемные символы для Windows
            msg = msg.encode('utf-8', errors='replace').decode('utf-8')
            stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)

# Заменяем стандартный handler на безопасный
for handler in logger.handlers[:]:
    if isinstance(handler, logging.StreamHandler):
        logger.removeHandler(handler)

logger.addHandler(SafeStreamHandler())