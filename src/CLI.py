import gzip
import re
import tarfile
import urllib.request
from io import BytesIO

def parse_yaml_config(file_path):
    """
    Вручную парсит базовый конфигурационный файл формата YAML по указанному пути.
    """
    config = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if ':' in line:
                    key, val = line.split(':', 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if val.isdigit():
                        val = int(val)
                    elif val.lower() == 'true':
                        val = True
                    elif val.lower() == 'false':
                        val = False
                    config[key] = val
    except Exception as e:
        print(f"[ERROR] Ошибка при чтении конфигурации: {e}")
    return config

def clean_dependency_name(dep_string):
    """
    Очищает строку зависимости от ограничений версий и модификаторов.
    """
    match = re.match(r'^([^<=>~!]+)', dep_string)
    if match:
        return match.group(1).strip()
    return dep_string

def fetch_apk_index(repo_url):
    """
    Загружает и распаковывает файл APKINDEX.tar.gz по указанному URL.
    """
    index_url = repo_url.strip().strip('"').strip("'")
    
    try:
        req = urllib.request.Request(
            index_url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        response = urllib.request.urlopen(req)
        compressed_data = response.read()
    except Exception as e:
        print(f"[ERROR] Не удалось загрузить репозиторий: {e}")
        return {}

    try:
        with tarfile.open(fileobj=BytesIO(compressed_data), mode="r:gz") as tar:
            apkindex_file = tar.extractfile("APKINDEX")
            if not apkindex_file:
                print("[ERROR] Файл APKINDEX не найден внутри архива.")
                return {}
            content = apkindex_file.read().decode('utf-8')
        return parse_apk_index(content)
    except tarfile.ReadError:
        print(f"[ERROR] Файл по адресу не является валидным архивом GZIP.")
        return {}

def parse_apk_index(content):
    """
    Разбирает текстовое содержимое APKINDEX в словарь зависимостей пакетов.
    """
    packages_db = {}
    blocks = content.split('\n\n')
    
    for block in blocks:
        current_package = None
        dependencies = []
        
        for line in block.split('\n'):
            if line.startswith('P:'):
                current_package = line[2:].strip()
            elif line.startswith('D:'):
                raw_deps = line[2:].strip().split()
                dependencies = [clean_dependency_name(d) for d in raw_deps]
        
        if current_package:
            packages_db[current_package] = dependencies
            
    return packages_db

def main():
    """
    Основная функция выполнения Этапа 2 для демонстрации сбора прямых зависимостей.
    """
    config = parse_yaml_config("config.yaml")
    
    if not config:
        print("[ERROR] Конфигурация пуста или не найдена.")
        return
        
    print("Этап 2: Сбор данных")
    
    target_package = config.get("package_name")
    repo_url = config.get("repository_url")
    
    if not target_package or not repo_url:
        print("[ERROR] В конфигурации отсутствуют обязательные параметры.")
        return

    db = fetch_apk_index(repo_url)
    
    if target_package in db:
        direct_deps = db[target_package]
        print(f"\n[УСПЕХ] Пакет '{target_package}' найден.")
        print(f"Прямые зависимости пакета ({len(direct_deps)} шт.):")
        for dep in direct_deps:
            print(f"  - {dep}")
    else:
        print(f"\n[ОШИБКА] Пакет '{target_package}' не найден в выбранном репозитории.")

if __name__ == "__main__":
    main()
