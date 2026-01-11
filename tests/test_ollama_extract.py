import importlib.util
import unittest
from pathlib import Path

# Dynamically load the hello_ollama.py module to access extract_json_content without package import issues
module_path = Path(__file__).resolve().parents[1] / 'scripts' / 'hello_ollama.py'
spec = importlib.util.spec_from_file_location("ollama_module", module_path)
ollama_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ollama_module)

class TestExtractJsonContent(unittest.TestCase):
    def test_json_string_parsed(self):
        payload = {"message": {"content": '{"greeting":"hi","mood":"cheerful"}'}}
        self.assertEqual(ollama_module.extract_json_content(payload), {"greeting": "hi", "mood": "cheerful"})

    def test_non_json_string_returns_error(self):
        payload = {"message": {"content": "not json"}}
        res = ollama_module.extract_json_content(payload)
        self.assertEqual(res.get("error"), "Invalid JSON")

    def test_empty_content_returns_empty_content(self):
        payload = {"message": {"content": ""}}
        self.assertEqual(ollama_module.extract_json_content(payload), {"content": ""})

    def test_missing_message_returns_empty_content(self):
        payload = {}
        self.assertEqual(ollama_module.extract_json_content(payload), {"content": ""})

if __name__ == '__main__':
    unittest.main()
