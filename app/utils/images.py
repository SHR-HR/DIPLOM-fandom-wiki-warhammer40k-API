# Модуль утилит для работы с изображениями
# Отвечает за определение локальных путей файлов и безопасное удаление загруженных изображений

from pathlib import Path
from urllib.parse import urlparse

# Корень API-проекта = папка API-SOLO-PROJECT
# parents[2] поднимается на 2 уровня вверх от текущего файла:
# J:\MAIN_DIP-М\API\app\utils\images.py → J:\MAIN_DIP-М\API\
BASE_DIR = Path(__file__).resolve().parents[2]

# Директория данных проекта (J:\MAIN_DIP-М\API\data)
DATA_DIR = BASE_DIR / "data"

# Директория для загруженных файлов (J:\MAIN_DIP-М\API\data\uploads)
UPLOADS_DIR = DATA_DIR / "uploads"

def _is_subpath(p: Path, parent: Path) -> bool:
    """
    Безопасная проверка что путь p находится внутри директории parent.
    
    Args:
        p (Path): Проверяемый путь
        parent (Path): Родительская директория
        
    Returns:
        bool: True если p находится внутри parent, False если нет
        
    Безопасность:
        - Предотвращает path traversal атаки (например, ../../../etc/passwd)
        - Использует resolve() для нормализации путей
        - relative_to() генерирует исключение если пути не связаны
        
    Пример:
        _is_subpath(Path("/data/uploads/image.jpg"), Path("/data/uploads")) → True
        _is_subpath(Path("/data/uploads/../etc/passwd"), Path("/data/uploads")) → False
    """
    try:
        # Пытаемся получить относительный путь p относительно parent
        # Если это удается - p находится внутри parent
        p.resolve().relative_to(parent.resolve())
        return True
    except Exception:
        # Если возникает исключение - пути не связаны (p вне parent)
        return False

def _strip_slashes(s: str) -> str:
    """
    Удаляет начальные слеши и обратные слеши из строки.
    
    Args:
        s (str): Входная строка (например, "/uploads/image.jpg")
        
    Returns:
        str: Строка без начальных слешей (например, "uploads/image.jpg")
        
    Зачем нужно:
        - Предотвращает создание абсолютных путей при объединении
        - Обеспечивает корректную работу с относительными путями
        - Обрабатывает разные стили слешей (Unix/Windows)
    """
    return s.lstrip("/\\") if isinstance(s, str) else s

def local_upload_path_from_url(url: str) -> Path | None:
    """
    Преобразует URL в абсолютный путь к локальному файлу в директории uploads.
    
    Args:
        url (str): URL для анализа (может быть относительным или абсолютным)
        
    Returns:
        Path | None: Абсолютный путь к файлу или None если URL не указывает на локальный файл
        
    Поддерживаемые форматы URL:
        - Относительные: "/uploads/xxx.jpg"
        - Абсолютные: "http(s)://<домен>/uploads/xxx.jpg"
        - Локальные: "http://127.0.0.1:8000/uploads/xxx.jpg"
        
    Безопасность:
        - Проверяет что результирующий путь находится внутри UPLOADS_DIR
        - Игнорирует внешние домены и data: URL
        - Обрабатывает попытки path traversal
    """
    if not url or not isinstance(url, str):
        return None

    u = url.strip()

    # ОБРАБОТКА ОТНОСИТЕЛЬНЫХ URL: /uploads/...
    if u.startswith("/uploads/"):
        # Убираем префикс "/uploads/" и начальные слеши
        relative_path = _strip_slashes(u.removeprefix("/uploads/"))
        # Создаем абсолютный путь
        p = UPLOADS_DIR / relative_path
        # Проверяем безопасность пути
        return p if _is_subpath(p, UPLOADS_DIR) else None

    # ОБРАБОТКА АБСОЛЮТНЫХ URL: http://...
    try:
        # Парсим URL для извлечения пути
        uu = urlparse(u)
        # Нормализуем путь: заменяем обратные слеши и обрабатываем двойные слеши
        path = (uu.path or "").replace("\\", "/")
        
        if path.startswith("/uploads/"):
            # Извлекаем относительную часть пути
            relative_path = _strip_slashes(path.removeprefix("/uploads/"))
            p = UPLOADS_DIR / relative_path
            return p if _is_subpath(p, UPLOADS_DIR) else None
    except Exception:
        # Если парсинг URL не удался (некорректный URL) - игнорируем
        pass

    # data: URL, внешние домены и неподдерживаемые форматы - игнорируем
    return None

def delete_local_uploads(urls: list[str]) -> tuple[list[str], list[str]]:
    """
    Безопасное удаление локальных файлов изображений по их URL.
    
    Args:
        urls (list[str]): Список URL для удаления
        
    Returns:
        tuple[list[str], list[str]]: Кортеж из двух списков:
            - removed_paths: Пути к фактически удаленным файлам
            - resolved_candidates: Все распознанные локальные пути (для отладки)
            
    Процесс работы:
        1. Убираем дубликаты и нестроковые значения
        2. Для каждого URL определяем локальный путь
        3. Если путь валиден и файл существует - удаляем его
        4. Возвращаем результаты для отладки и подтверждения
        
    Особенности:
        - Не падает при ошибках удаления отдельных файлов
        - Возвращает подробную информацию для отладки
        - Работает только с локальными файлами (игнорирует внешние URL)
    """
    removed: list[str] = []    # Список успешно удаленных файлов
    candidates: list[str] = [] # Список всех распознанных путей (для отладки)
    
    # Обрабатываем только уникальные строковые URL
    unique_urls = set([x for x in urls if isinstance(x, str) and x.strip()])
    
    for u in unique_urls:
        # Пытаемся преобразовать URL в локальный путь
        p = local_upload_path_from_url(u)
        if not p:
            continue  # Пропускаем если не локальный файл
            
        # Добавляем путь в кандидаты (даже если файла нет)
        candidates.append(str(p))
        
        try:
            # Проверяем существование файла и удаляем
            if p.exists():
                p.unlink(missing_ok=True)  # missing_ok=True для защиты от race condition
                removed.append(str(p))
        except Exception:
            # Игнорируем ошибки удаления (нет прав, файл занят и т.д.)
            # Не прерываем выполнение из-за проблем с одним файлом
            pass
            
    return removed, candidates


# Подробное объяснение системы работы с изображениями:

# Определение путей:

# BASE_DIR и производные:

# # Иерархия путей:
# BASE_DIR = J:\MAIN_DIP-М\API\                    # parents[2] от images.py
# DATA_DIR = J:\MAIN_DIP-М\API\data\              # Базовая директория данных
# UPLOADS_DIR = J:\MAIN_DIP-М\API\data\uploads\   # Директория загрузок

# Зачем нужно parents[2]:

# images.py находится в: J:\MAIN_DIP-М\API\app\utils\images.py
# - parents[0] → J:\MAIN_DIP-М\API\app\utils\
# - parents[1] → J:\MAIN_DIP-М\API\app\  
# - parents[2] → J:\MAIN_DIP-М\API\  (нужный уровень)

# Функция _is_subpath - безопасность:

# Защита от Path Traversal:

# Без этой проверки злоумышленник мог бы использовать URL вроде:

# /uploads/../../etc/passwd

# /uploads/../data/users.json


# Как работает защита:

# # Злонамеренный URL: "/uploads/../../etc/passwd"
# relative_path = "etc/passwd"  # после removeprefix и strip
# p = UPLOADS_DIR / "etc/passwd"  # J:\MAIN_DIP-М\API\data\uploads\etc\passwd

# # Проверка: находится ли J:\...\uploads\etc\passwd внутри J:\...\uploads?
# _is_subpath(p, UPLOADS_DIR) → False  # etc/passwd выходит за пределы uploads!

# Функция local_upload_path_from_url:

# Поддержка разных форматов URL:

# Относительные URL:

# Вход: "/uploads/my_image.jpg"
# → relative_path = "my_image.jpg"
# → p = J:\MAIN_DIP-М\API\data\uploads\my_image.jpg

# Абсолютные URL:

# Вход: "https://example.com/uploads/avatar.png"
# → uu.path = "/uploads/avatar.png"  
# → relative_path = "avatar.png"
# → p = J:\MAIN_DIP-М\API\data\uploads\avatar.png

# Локальные серверы:

# Вход: "http://localhost:8000/uploads/photo.jpg"
# → uu.path = "/uploads/photo.jpg"
# → relative_path = "photo.jpg"  
# → p = J:\MAIN_DIP-М\API\data\uploads\photo.jpg

# Игнорируемые URL:
# data: URL - "data:image/png;base64,iVBORw0KGgo..."

# Внешние домены - "https://external-site.com/image.jpg"

# Некорректные форматы - "invalid_url"


# Функция delete_local_uploads:

# Процесс удаления:
# Дeduпликация - set() убирает повторяющиеся URL

# Фильтрация - оставляем только непустые строки

# Преобразование - URL → локальный путь

# Проверка существования - только существующие файлы удаляем

# Безопасное удаление - с обработкой исключений


# Возвращаемые данные:

# # Пример результата:
# removed = [
#     "J:\\MAIN_DIP-М\\API\\data\\uploads\\image1.jpg",
#     "J:\\MAIN_DIP-М\\API\\data\\uploads\\avatar.png"
# ]
# candidates = [
#     "J:\\MAIN_DIP-М\\API\\data\\uploads\\image1.jpg", 
#     "J:\\MAIN_DIP-М\\API\\data\\uploads\\avatar.png",
#     "J:\\MAIN_DIP-М\\API\\data\\uploads\\nonexistent.jpg"  # даже если файла нет
# ]

# Обработка ошибок:
# Файл занят - другим процессом

# Нет прав - недостаточно прав для удаления

# Файл уже удален - missing_ok=True предотвращает исключение

# Поврежденный путь - некорректные символы в имени


# Интеграция с системой Warhammer 40,000 вики:

# Сценарии использования:

# Удаление статьи:

# # При удалении статьи собираем все URL изображений и удаляем файлы
# urls = [
#     "/uploads/space_marine.jpg",
#     "http://localhost:8000/uploads/imperial_logo.png",
#     "https://external.com/warhammer.jpg"  # этот URL будет проигнорирован
# ]

# removed, candidates = delete_local_uploads(urls)
# # removed: ['J:\\...\\uploads\\space_marine.jpg', 'J:\\...\\uploads\\imperial_logo.png']
# # candidates: ['J:\\...\\uploads\\space_marine.jpg', 'J:\\...\\uploads\\imperial_logo.png']

# Очистка неиспользуемых изображений:

# # Можно создать скрипт для поиска и удаления изображений не связанных со статьями
# all_uploaded_files = set(p.name for p in UPLOADS_DIR.iterdir())
# used_images = extract_image_urls_from_articles()  # из всех статей

# unused_files = all_uploaded_files - used_images
# removed, candidates = delete_local_uploads([f"/uploads/{f}" for f in unused_files])

# Безопасность для вики-проекта:
# Защита контента - случайное удаление только локальных файлов

# Сохранение внешних ресурсов - изображения с официальных сайтов не затрагиваются

# Целостность данных - проверки предотвращают удаление системных файлов

# Этот модуль обеспечивает надежное и безопасное управление файлами изображений
# в проекте вики по Warhammer 40,000, предоставляя инструменты для корректного определения путей
# и очистки неиспользуемых ресурсов.




