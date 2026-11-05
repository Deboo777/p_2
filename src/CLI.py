import gzip
import re
import tarfile
import urllib.request
from io import BytesIO


def parse_yaml_config(file_path):
    """
    Вручную парсит базовый конфигурационный файл формата YAML
    по указанному пути.
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
    Загружает и распаковывает файл APKINDEX.tar.gz 
    по указанному URL.
    """
    index_url = repo_url.strip().strip('"').strip("'")
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    try:
        req = urllib.request.Request(
            index_url,
            headers={'User-Agent': user_agent}
        )
        response = urllib.request.urlopen(req)
        compressed_data = response.read()
    except Exception as e:
        print(f"[ERROR] Не удалось загрузить репозиторий: {e}")
        return {}
    try:
        with tarfile.open(
            fileobj=BytesIO(compressed_data), mode="r:gz"
        ) as tar:
            apkindex_file = tar.extractfile("APKINDEX")
            if not apkindex_file:
                print("[ERROR] Файл APKINDEX не найден в архиве.")
                return {}
            content = apkindex_file.read().decode('utf-8')
        return parse_apk_index(content)
    except tarfile.ReadError:
        print("[ERROR] Файл по " \
        "адресу не является валидным архивом GZIP.")
        return {}


def parse_apk_index(content):
    """
    Разбирает текстовое содержимое APKINDEX в словарь зависимостей.
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
                dependencies = [clean_dependency_name(d) 
                    for d in raw_deps]

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


def build_dependency_graph(package, db, max_depth, 
        filter_sub, current_depth=1, ctx=None):
    """
    Рекурсивно строит граф зависимостей методом DFS и 
    вычисляет порядок загрузки пакетов.
    """
    if ctx is None:
        ctx = ({}, [], [], set())  
    graph, path, order, visited_nodes = ctx
    def is_invalid():
        if filter_sub and filter_sub in package:
            return True
        if current_depth > max_depth:
            return True
        if package in path:
            return True
        return False
    if is_invalid():
        return graph, order
    path.append(package)
    filtered_deps = [d for d in db.get(package, 
            []) if not (filter_sub and filter_sub in d)]
    graph[package] = filtered_deps

    for dep in filtered_deps:
        build_dependency_graph(dep, db, max_depth, 
                    filter_sub, current_depth + 1, ctx)
    path.pop()
    if package not in visited_nodes:
        visited_nodes.add(package)
        order.append(package)
    return graph, order



def print_ascii_tree(package, graph, depth=0, visited=None):
    """
    Выводит зависимости пакета на экран в виде иерархического
    ASCII-дерева.
    """
    if visited is None:
        visited = set()

    indent = "    " * depth
    marker = "└── " if depth > 0 else ""

    if package in visited:
        print(f"{indent}{marker}{package} (повтор/цикл)")
        return

    print(f"{indent}{marker}{package}")
    visited.add(package)

    deps = graph.get(package, [])
    for dep in deps:
        print_ascii_tree(dep, graph, depth + 1, visited.copy())


def generate_plantuml(graph):
    """
    Формирует строку с описанием графа зависимостей на языке
    диаграмм PlantUML в виде компонентов.
    """
    lines = ["@startuml"]

    all_packages = set(graph.keys())
    for deps in graph.values():
        all_packages.update(deps)

    for pkg in sorted(all_packages):
        lines.append(f'  component "{pkg}"')

    lines.append("")

    for pkg, deps in graph.items():
        for dep in deps:
            safe_pkg = f'"{pkg}"'
            safe_dep = f'"{dep}"'
            lines.append(f"  {safe_pkg} --> {safe_dep}")

    lines.append("@enduml")
    return "\n".join(lines)


def main():
    """
    Основная функция выполнения Этапа 5 для визуализации графа зависимостей.
    """
    cfg = parse_yaml_config("config.yaml")
    if not cfg:
        print("[ERROR] Конфигурация пуста или не найдена.")
        return
    print("Этап 5: Визуализация графа зависимостей")
    tgt, url = cfg.get("package_name"), cfg.get("repository_url")
    if not tgt or not url:
        print("[ERROR] В конфигурации отсутствуют обязательные параметры.")
        return
    db = load_test_repository(url) if cfg.get("test_mode",
        False) else fetch_apk_index(url)
    if tgt not in db:
        print(f"[ERROR] Целевой пакет '{tgt}' не найден.")
        return
    graph, _ = build_dependency_graph(tgt, db, cfg.get("max_depth", 5),
     cfg.get("filter_substring", ""))
    if cfg.get("ascii_tree_output", False):
        print("\n[ВЫВОД] ASCII-дерево зависимостей:")
        print_ascii_tree(tgt, graph)
    print("\n[ВЫВОД] Код диаграммы PlantUML:\n" + generate_plantuml(graph))


if __name__ == "__main__":
    main()
