import unittest
from pathlib import Path
from tools.configure_lichess import build_config


class ConfigTests(unittest.TestCase):
    def test_resources_disabled_and_challengers_restricted(self):
        config = {"engine": {"online_moves": {"future_source": {"enabled": True}},
                             "lichess_bot_tbs": {"syzygy": {"enabled": True}},
                             "polyglot": {"enabled": True},
                             "uci_options": {"SyzygyPath": "/somewhere"},
                             "interpreter": "wrong"},
                  "challenge": {"online_block_list": ["https://example.invalid"], "min_rating": 2000}}
        result = build_config(config, Path("/project"), ["organiser", "opponent"], "knockout")
        self.assertFalse(result["engine"]["online_moves"]["future_source"]["enabled"])
        self.assertFalse(result["engine"]["lichess_bot_tbs"]["syzygy"]["enabled"])
        self.assertFalse(result["engine"]["polyglot"]["enabled"])
        self.assertNotIn("SyzygyPath", result["engine"]["uci_options"])
        self.assertNotIn("interpreter", result["engine"])
        self.assertFalse(result["matchmaking"]["allow_matchmaking"])
        self.assertEqual(result["challenge"]["allow_list"], ["organiser", "opponent"])
        self.assertEqual(result["challenge"]["min_base"], 180)
        self.assertEqual(result["challenge"]["max_base"], 180)
        self.assertEqual(result["challenge"]["min_increment"], 2)
        self.assertEqual(result["challenge"]["max_increment"], 2)
        self.assertEqual(result["challenge"]["modes"], ["casual"])
        self.assertTrue(all(not value for value in result["greeting"].values()))

    def test_final_stage_exact_time_control(self):
        result = build_config({}, Path("/project"), ["club-member"], "final")
        self.assertEqual(result["challenge"]["min_base"], 600)
        self.assertEqual(result["challenge"]["max_base"], 600)
        self.assertEqual(result["challenge"]["min_increment"], 5)
        self.assertEqual(result["challenge"]["max_increment"], 5)
        self.assertEqual(result["challenge"]["variants"], ["standard"])


if __name__ == "__main__":
    unittest.main()
