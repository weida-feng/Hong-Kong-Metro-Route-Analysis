# Hong Kong Metro Route Analysis

English | [简体中文](README.zh-CN.md)

A Python project that models the Hong Kong metro as a multigraph using NetworkX and Matplotlib. It compares routes that minimize **the number of station-to-station segments** or **total distance weight**, and visualizes lines and interchange stations.

The project uses the original **2023-02-01 data snapshot**, covering 10 lines, 96 modeled nodes, and 112 connections. Node counts reflect modeling assumptions, including merged stations, rather than current MTR station totals.

## Route comparison: Yau Tong → Tsing Yi

![Comparison of routes with the fewest segments and the shortest distance](images/route_comparison.png)

| Strategy | Algorithm | Segments traveled | Stations, including both endpoints | Distance weight |
| --- | --- | ---: | ---: | ---: |
| Fewest segments | Unweighted shortest path / BFS | 10 | 11 | 20.89 |
| Shortest distance | Dijkstra | 17 | 18 | 19.00 |

With this dataset, the shortest-distance route takes 7 more segments than the example route with the fewest segments, but has a lower total distance weight. Different objectives lead to different routes.

Station names in the examples and figures retain the Chinese identifiers used in the original dataset. Yau Tong is `油塘`, and Tsing Yi is `青衣`.

- **Fewest segments:** 油塘 → 鲗鱼涌 → 北角 → 炮台山 → 天后 → 铜锣湾 → 湾仔 → 金钟 → 中环/香港 → 九龙 → 青衣
- **Shortest distance:** 油塘 → 蓝田 → 观塘 → 牛头角 → 九龙湾 → 彩虹 → 钻石山 → 黄大仙 → 乐富 → 九龙塘 → 石硖尾 → 太子 → 深水埗 → 长沙湾 → 荔枝角 → 美孚 → 荔景 → 青衣

The segment count equals the number of nodes in the path minus one. Distance is calculated from the data, taking the minimum weight among parallel edges for each segment, consistent with NetworkX's weighted shortest-path behavior. When multiple routes tie for the fewest segments, BFS returns one of them; it does not additionally minimize distance among those routes.

## Network model and visualization

![Hong Kong metro network topology](images/network.png)

- An undirected `MultiGraph` preserves parallel edges where different lines connect the same pair of stations.
- Stations with the same name share a node, naturally connecting their lines. Each edge stores its line ID, name, color, and distance weight; each node records its line memberships.
- Interchanges are identified by membership in multiple lines. Branch stations on a single line, such as `上水` and `将军澳`, are not mislabeled simply because they connect to multiple directions.
- Shared segments are drawn as separate colored arcs. Route strategies are shown in separate panels so overlapping paths remain visible.
- A topology layout with a fixed random seed removes the need for Graphviz. Node positions and drawn edge lengths do not represent geographic coordinates or actual distances.

## Getting started

Python 3.11 or later is recommended. From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m jupyterlab Hong_Kong_Metro_test.ipynb
```

On Windows, activate the environment with `.venv\Scripts\activate` instead.

In JupyterLab, select the Python kernel for this virtual environment and run all cells from the beginning. The notebook displays the analysis and saves both figures to `images/`. Its explanatory text is in Chinese.

Chinese labels require a Chinese font installed on your system. The plotting code automatically selects from common fonts. If a missing-font warning appears, install Noto Sans CJK SC and restart the kernel.

You can also query routes directly:

```python
from metro import compare_routes, load_network

graph = load_network()
for result in compare_routes(graph, "油塘", "青衣"):
    print(result["strategy"], result["segment_count"], result["distance"])
    print(" → ".join(result["path"]))
```

Run the checks:

```bash
python -m unittest discover -s tests -v
```

The checks cover line identity on shared segments, branch-station classification, example route metrics, distance selection among parallel edges, identical endpoints, unknown and unreachable stations, and invalid input data.

## Data and limitations

The original files retain their UTF-16 encoding:

| File | Contents | Source stated in the original file |
| --- | --- | --- |
| `Hong_Kong_Metro_Lines_ZHCN.txt` | Line IDs, names, and colors | MTR website |
| `Hong_Kong_Metro_Routes_ZHCN.txt` | Adjacent stations, distance weights, and line IDs | Wikipedia |

The original files do not record specific source pages or versions. This update preserves the snapshot without refreshing the network or independently verifying the distances. Distance weights retain their original numeric values and do not represent travel times.

The model retains the original project's simplifications:

- `中环/香港` and `尖沙咀/尖东` each merge two stations into one node, without accounting for walking distance within the interchange.
- High-speed rail and light rail are excluded. Airport Express is included, but its boarding and transfer restrictions are not modeled.
- Waiting times, running times, transfer costs, fares, directions, and timetables are not considered. All connections are treated as bidirectional.
- Connections adjacent to `马场` retain the original extra `0.001` weight. This heuristic does not replace modeling special service schedules.
- Interchange markers indicate that multiple lines meet in the model. Route queries do not calculate actual transfer counts or the fastest journey.

## Repository structure

```text
README.md                      English project overview
README.zh-CN.md                Chinese project overview
Hong_Kong_Metro_test.ipynb      Guided analysis, route comparison, and figure export
metro.py                       Data loading, graph construction, routing, and plotting
Hong_Kong_Metro_Lines_ZHCN.txt   Original line data
Hong_Kong_Metro_Routes_ZHCN.txt  Original station connection data
images/                        Example figures used in the README
tests/test_metro.py             Core behavior checks
requirements.txt               Runtime dependencies
```

The original exploration dates to 2023. This update preserves the data and both routing strategies, adds explicit line attributes, corrects interchange detection and result reporting, and improves setup and presentation.
