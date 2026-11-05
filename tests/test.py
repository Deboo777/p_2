import unittest
from unittest.mock import patch, mock_open

from src.CLI import (
    parse_yaml_config,
    clean_dependency_name,
    build_dependency_graph,
    generate_plantuml
)


class TestDependencyVisualizer(unittest.TestCase):

    def test_clean_dependency_name(self):
        """Тест очистки строк с версиями зависимостей."""
        self.assertEqual(clean_dependency_name("musl>=1.2.2"), "musl")
        self.assertEqual(clean_dependency_name("bash<5.0"), "bash")
        self.assertEqual(clean_dependency_name("zlib=1.2.11-r1"), "zlib")
        self.assertEqual(clean_dependency_name("so:libssl.so.3"), 
                        "so:libssl.so.3")

    def test_parse_yaml_config(self):
        """Тест ручного парсинга YAML с подменой файла (mock)."""
        yaml_content = """
        package_name: "curl"
        test_mode: true
        max_depth: 3
        repository_url: 'http://example.com'
        # это комментарий
        filter_substring: "so:"
        """
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            config = parse_yaml_config("dummy_path.yaml")
            
        self.assertEqual(config.get("package_name"), "curl")
        self.assertEqual(config.get("test_mode"), True)
        self.assertEqual(config.get("max_depth"), 3)
        self.assertEqual(config.get("repository_url"), "http://example.com")
        self.assertEqual(config.get("filter_substring"), "so:")

    def test_build_dependency_graph_filter(self):
        """Тест фильтрации по подстроке."""
        db = {
            "A": ["B", "so:libssl", "C"]
        }
        graph, _ = build_dependency_graph("A", db,
                         max_depth=5, filter_sub="so:")
        self.assertEqual(graph["A"], ["B", "C"])

    def test_generate_plantuml(self):
        """Тест генерации PlantUML кода."""
        graph = {
            "A": ["B"]
        }
        uml_code = generate_plantuml(graph)
        
        self.assertIn("@startuml", uml_code)
        self.assertIn('component "A"', uml_code)
        self.assertIn('component "B"', uml_code)
        self.assertIn('"A" --> "B"', uml_code)
        self.assertIn("@enduml", uml_code)


if __name__ == "__main__":
    unittest.main()