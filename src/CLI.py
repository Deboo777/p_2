import os
import sys


def load_config(config_path="config.yaml"):
    """Загружает и парсит конфигурационный файл YAML вручную."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"Критическая ошибка: Конфигурационный файл '{config_path}' не найден."
        )

    config = {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                if not line or line.startswith("#"):
                    continue

                if ":" not in line:
                    raise ValueError(f"Строка {line_num}: Неверный формат YAML.")

                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip()

                if (val.startswith('"') and val.endswith('"')) or (
                    val.startswith("'") and val.endswith("'")
                ):
                    val = val[1:-1]

                if val.lower() == "true":
                    val = True
                elif val.lower() == "false":
                    val = False
                elif val.isdigit():
                    val = int(val)

                config[key] = val
    except Exception as e:
        raise ValueError(
            f"Ошибка синтаксиса в конфигурационном файле YAML: {e}"
        )

    if not config:
        raise ValueError("Ошибка: Конфигурационный файл пуст.")

    return config


def validate_config(config):
    """Проверяет корректность типов и значений всех параметров конфигурации."""
    errors = []

    package_name = config.get("package_name")
    if not package_name or not isinstance(package_name, str):
        errors.append("Параметр 'package_name' должен быть непустой строкой.")

    repo_url = config.get("repository_url")
    if not repo_url or not isinstance(repo_url, str):
        errors.append(
            "Параметр 'repository_url' должен быть непустой строкой (URL или путь)."
        )

    test_mode = config.get("test_mode")
    if not isinstance(test_mode, bool):
        errors.append(
            "Параметр 'test_mode' должен быть логического типа (true/false)."
        )

    ascii_tree = config.get("ascii_tree_output")
    if not isinstance(ascii_tree, bool):
        errors.append(
            "Параметр 'ascii_tree_output' должен быть логического типа (true/false)."
        )

    max_depth = config.get("max_depth")
    if not isinstance(max_depth, int) or max_depth < 0:
        errors.append(
            "Параметр 'max_depth' должен быть целым неотрицательным числом."
        )

    filter_sub = config.get("filter_substring")
    if filter_sub is not None and not isinstance(filter_sub, str):
        errors.append("Параметр 'filter_substring' должен быть строкой.")

    if errors:
        error_msg = "Обнаружены ошибки валидации конфигурации:\n" + "\n".join(
            f"  - {err}" for err in errors
        )
        raise ValueError(error_msg)


def main():
    """Основная точка входа приложения для инициализации и вывода конфигурации."""
    config_file = "config.yaml"

    try:
        config = load_config(config_file)
        validate_config(config)

        print("Конфигурация приложения успешно загружена")
        for key, value in config.items():
            print(f"{key}: {value}")


    except (FileNotFoundError, ValueError) as err:
        print(err, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

