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

def load_test_repository(file_path):
    """
    Загружает описание тестового графа из локального текстового файла.
    """
    packages_db = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if ':' in line:
                    pkg, deps = line.split(':', 1)
                    packages_db[pkg.strip()] = deps.strip().split()
    except Exception as e:
        print(f"[ERROR] Ошибка чтения тестового репозитория: {e}")
    return packages_db

def build_dependency_graph(package, db, max_depth, filter_sub, current_depth=1, graph=None, path=None, order=None, visited_nodes=None):
    """
    Рекурсивно строит граф зависимостей методом DFS и вычисляет порядок загрузки пакетов.
    """
    if graph is None:
        graph = {}
    if path is None:
        path = []
    if order is None:
        order = []
    if visited_nodes is None:
        visited_nodes = set()

    if filter_sub and filter_sub in package:
        return graph, order

    if current_depth > max_depth:
        return graph, order

    if package in path:
        print(f"[INFO] Обнаружен цикл зависимостей: {' -> '.join(path)} -> {package}")
        return graph, order

    path.append(package)
    
    direct_deps = db.get(package, [])
    filtered_deps = []
    
    for dep in direct_deps:
        if not (filter_sub and filter_sub in dep):
            filtered_deps.append(dep)
            
    graph[package] = filtered_deps

    for dep in filtered_deps:
        build_dependency_graph(dep, db, max_depth, filter_sub, current_depth + 1, graph, path, order, visited_nodes)

    path.pop()
    
    if package not in visited_nodes:
        visited_nodes.add(package)
        order.append(package)
        
    return graph, order

def main():
    """
    Основная функция выполнения Этапа 4 для демонстрации порядка загрузки зависимостей.
    """
    config = parse_yaml_config("config.yaml")
    
    if not config:
        print("[ERROR] Конфигурация пуста или не найдена.")
        return
        
    print("Этап 4: Дополнительные операции (Порядок загрузки)")
    
    target_package = config.get("package_name")
    test_mode = config.get("test_mode", False)
    repo_url = config.get("repository_url")
    max_depth = config.get("max_depth", 5)
    filter_substring = config.get("filter_substring", "")
    
    if not target_package or not repo_url:
        print("[ERROR] В конфигурации отсутствуют обязательные параметры.")
        return

    if test_mode:
        print(f"[MODE] Работа в тестовом режиме. Загрузка файла: {repo_url}")
        db = load_test_repository(repo_url)
    else:
        print(f"[MODE] Работа с реальным репозиторием Alpine.")
        db = fetch_apk_index(repo_url)
        
    if target_package not in db:
        print(f"[ERROR] Целевой пакет '{target_package}' не найден в базе данных.")
        return

    graph, order = build_dependency_graph(target_package, db, max_depth, filter_substring)
    
    print(f"\n[УСПЕХ] Порядок установки (загрузки) пакетов для '{target_package}':")
    for i, pkg in enumerate(order, 1):
        print(f"  {i}. {pkg}")

if __name__ == "__main__":
    main()
