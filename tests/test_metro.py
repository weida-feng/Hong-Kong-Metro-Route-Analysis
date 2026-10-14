"""覆盖多重边、分支站误判和输入边界；不依赖 Notebook 的旧输出。"""

from pathlib import Path
import tempfile
import unittest

import networkx as nx

from metro import compare_routes, get_transfer_stations, load_network, path_distance


class MetroTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = load_network()

    def test_snapshot_counts_and_connectivity(self):
        self.assertEqual(len(self.graph.graph["lines"]), 10)
        self.assertEqual(self.graph.number_of_nodes(), 96)
        self.assertEqual(self.graph.number_of_edges(), 112)
        self.assertTrue(nx.is_connected(self.graph))

    def test_parallel_edges_keep_line_identity(self):
        edges = self.graph["油麻地"]["旺角"]
        self.assertEqual({edge["line_name"] for edge in edges.values()}, {"荃湾线", "观塘线"})
        self.assertEqual(self.graph.nodes["旺角"]["lines"], {0, 1})

    def test_branches_are_not_transfer_stations(self):
        transfers = set(get_transfer_stations(self.graph))
        self.assertTrue({"金钟", "旺角", "北角", "欣澳"}.issubset(transfers))
        self.assertTrue(transfers.isdisjoint({"将军澳", "上水", "大学", "沙田"}))

    def test_example_metrics_are_computed_from_data(self):
        fewest, shortest = compare_routes(self.graph, "油塘", "青衣")
        self.assertEqual((fewest["segment_count"], fewest["station_count"]), (10, 11))
        self.assertAlmostEqual(fewest["distance"], 20.89)
        self.assertEqual((shortest["segment_count"], shortest["station_count"]), (17, 18))
        self.assertAlmostEqual(shortest["distance"], 19.0)

    def test_distance_uses_minimum_parallel_edge(self):
        self.assertAlmostEqual(path_distance(self.graph, ["北角", "鲗鱼涌"]), 0.94)

    def test_same_station_has_zero_segments_and_distance(self):
        for result in compare_routes(self.graph, "金钟", "金钟"):
            self.assertEqual(result["path"], ["金钟"])
            self.assertEqual(result["segment_count"], 0)
            self.assertEqual(result["distance"], 0)

    def test_unknown_and_unreachable_stations(self):
        with self.assertRaisesRegex(ValueError, "未知站点"):
            compare_routes(self.graph, "不存在", "金钟")
        disconnected = self.graph.copy()
        disconnected.remove_edges_from(list(disconnected.edges("青衣", keys=True)))
        with self.assertRaises(nx.NetworkXNoPath):
            compare_routes(disconnected, "金钟", "青衣")

    def test_parser_handles_blank_lines_and_rejects_invalid_routes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Hong_Kong_Metro_Lines_ZHCN.txt").write_text(
                "\n  # 注释\n3 示例线 #123456\n", encoding="utf-16"
            )
            route_file = root / "Hong_Kong_Metro_Routes_ZHCN.txt"
            route_file.write_text("\n  # 注释\n0 甲 乙 1.5 3\n", encoding="utf-16")
            self.assertEqual(load_network(root).number_of_edges(), 1)
            for record in [
                "0 甲 乙 -1 3", "0 甲 乙 nan 3", "0 甲 乙 inf 3",
                "0 甲 乙 1 9", "0 甲 甲 1 3", "0 甲 乙 1", "0 甲 乙 1+2 3",
                "0 甲 乙 1 3\n1 乙 甲 1 3",
            ]:
                with self.subTest(record=record):
                    route_file.write_text(record, encoding="utf-16")
                    with self.assertRaises(ValueError):
                        load_network(root)


if __name__ == "__main__":
    unittest.main()
