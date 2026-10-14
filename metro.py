"""香港地铁数据读取、路径比较与绘图；使用仓库内的 2023 年数据快照。"""

from math import isfinite
from pathlib import Path
import warnings

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
import networkx as nx


DATA_DIR = Path(__file__).resolve().parent


def _records(path, columns):
    """原始文件以 UTF-16 保存；忽略空行和允许前导空格的注释。"""
    with Path(path).open(encoding="utf-16") as stream:
        for number, raw in enumerate(stream, 1):
            text = raw.strip()
            if not text or text.startswith("#"):
                continue
            fields = text.split()
            if len(fields) != columns:
                raise ValueError(f"{Path(path).name}:{number}: 应有 {columns} 列")
            yield fields


def load_network(data_dir=DATA_DIR):
    """返回 MultiGraph；共享站名自然连通，每条平行边保留各自的线路。"""
    data_dir = Path(data_dir)
    lines = {}
    for code, name, color in _records(data_dir / "Hong_Kong_Metro_Lines_ZHCN.txt", 3):
        code = int(code)
        if code < 0 or code in lines:
            raise ValueError(f"线路编号无效或重复：{code}")
        lines[code] = {"name": name, "color": color}
    if not lines:
        raise ValueError("线路数据为空")

    graph = nx.MultiGraph(lines=lines, snapshot="2023-02-01")
    for _, source, target, distance, code in _records(
        data_dir / "Hong_Kong_Metro_Routes_ZHCN.txt", 5
    ):
        code, distance = int(code), float(distance)
        if code not in lines:
            raise ValueError(f"未知线路编号：{code}")
        if not isfinite(distance) or distance <= 0:
            raise ValueError(f"站间距离必须为有限正数：{source} → {target}")
        if source == target or graph.has_edge(source, target, key=code):
            raise ValueError(f"站间连接重复或为自环：{source} → {target}，线路 {code}")
        graph.add_edge(
            source, target, key=code, weight=distance,
            line_id=code, line_name=lines[code]["name"], color=lines[code]["color"],
        )
        for station in (source, target):
            graph.nodes[station].setdefault("lines", set()).add(code)
    if not graph:
        raise ValueError("站间连接数据为空")
    return graph


def get_transfer_stations(graph):
    """属于多条线路的站点；同一线路的分支节点不因此成为换乘站。"""
    return [station for station, data in graph.nodes(data=True) if len(data["lines"]) > 1]


def path_distance(graph, path):
    """给定节点路径，每段取平行边的最小距离，与 Dijkstra 的权重语义一致。"""
    return sum(
        min(edge["weight"] for edge in graph[source][target].values())
        for source, target in zip(path, path[1:])
    )


def compare_routes(graph, source, target):
    """比较 BFS 最少区间路径和 Dijkstra 最短距离路径，不计算换乘成本。"""
    missing = [station for station in dict.fromkeys((source, target)) if station not in graph]
    if missing:
        raise ValueError(f"未知站点：{'、'.join(missing)}")
    paths = [
        ("最少区间", nx.shortest_path(graph, source, target)),
        ("最短距离", nx.dijkstra_path(graph, source, target, weight="weight")),
    ]
    return [
        {"strategy": strategy, "path": path, "station_count": len(path),
         "segment_count": len(path) - 1, "distance": path_distance(graph, path)}
        for strategy, path in paths
    ]


def configure_plotting():
    """优先选择已安装的中文字体；缺少字体时给出明确提示。"""
    available = {font.name for font in font_manager.fontManager.ttflist}
    candidates = [
        "Noto Sans CJK SC", "Source Han Sans SC", "Microsoft YaHei",
        "PingFang SC", "Heiti SC", "Arial Unicode MS", "SimHei", "WenQuanYi Zen Hei",
    ]
    chosen = next((name for name in candidates if name in available), None)
    if chosen is None:
        warnings.warn("未找到中文字体，请安装 Noto Sans CJK SC 后重启内核。", stacklevel=2)
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": [chosen or "DejaVu Sans", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "figure.dpi": 110,
        "savefig.dpi": 160,
    })
    return chosen


def network_positions(graph):
    """固定种子的拓扑布局；位置和边长不代表地理坐标或实际距离。"""
    return nx.spring_layout(graph, seed=42, iterations=400, weight=None)


def _separate_labels(ax, labels, positions):
    """在显示坐标中轻移重叠标签；较远的标签用细线连接原站点。"""
    ax.figure.canvas.draw()
    renderer = ax.figure.canvas.get_renderer()
    names = list(labels)
    boxes = [labels[name].get_window_extent(renderer).expanded(1.1, 1.2) for name in names]
    centers = [(box.y0 + box.y1) / 2 for box in boxes]
    original = centers.copy()
    for _ in range(100):
        moved = False
        for i, first in enumerate(boxes):
            for j in range(i + 1, len(boxes)):
                second = boxes[j]
                if first.x0 >= second.x1 or second.x0 >= first.x1:
                    continue
                overlap = (first.height + second.height) / 2 - abs(centers[i] - centers[j])
                if overlap > 0:
                    direction = 1 if original[i] >= original[j] else -1
                    shift = overlap / 2 + 0.1
                    centers[i] += direction * shift
                    centers[j] -= direction * shift
                    moved = True
        if not moved:
            break
    for i, name in enumerate(names):
        shift = centers[i] - original[i]
        anchor = ax.transData.transform(labels[name].get_position())
        anchor[1] += shift
        location = ax.transData.inverted().transform(anchor)
        labels[name].set_position(location)
        if abs(shift) > 5:
            ax.annotate(
                "", xy=positions[name], xytext=location,
                arrowprops={"arrowstyle": "-", "color": "#888888", "lw": 0.5},
                zorder=1,
            )


def plot_network(graph, positions):
    """用平行弧线保留共线路段的各自颜色。"""
    fig, ax = plt.subplots(figsize=(19, 16), layout="constrained")
    edges = list(graph.edges(keys=True, data=True))
    nx.draw_networkx_edges(
        graph, positions, ax=ax,
        edgelist=[(u, v, key) for u, v, key, _ in edges],
        edge_color=[data["color"] for _, _, _, data in edges],
        width=2, node_size=65, arrows=True, arrowstyle="-",
        connectionstyle=["arc3,rad=0.10", "arc3,rad=-0.10"],
    )
    nx.draw_networkx_nodes(graph, positions, ax=ax, node_size=65, node_color="#e8edf2")
    nx.draw_networkx_nodes(
        graph, positions, ax=ax, nodelist=get_transfer_stations(graph),
        node_size=115, node_color="#f8ddd6", edgecolors="#ab5943", linewidths=0.7,
    )
    labels = nx.draw_networkx_labels(graph, positions, ax=ax, font_size=8, font_family=plt.rcParams["font.sans-serif"][0])
    legend = [
        Line2D([0], [0], color=line["color"], lw=3, label=line["name"])
        for line in graph.graph["lines"].values()
    ]
    legend.append(Line2D(
        [0], [0], marker="o", color="none", markerfacecolor="#f8ddd6",
        markeredgecolor="#ab5943", label="多线路换乘站",
    ))
    ax.legend(handles=legend, loc="upper left", frameon=False, fontsize=10)
    ax.set_title("香港地铁网络｜2023 年数据快照", fontsize=20, pad=18)
    ax.text(0.5, -0.015, "拓扑示意图 · 节点位置不代表地理坐标", transform=ax.transAxes, ha="center", color="#666666")
    ax.margins(0.13)
    ax.axis("off")
    _separate_labels(ax, labels, positions)
    return fig


def plot_route_comparison(graph, positions, results):
    """两种策略分别显示，避免重合路径互相覆盖。"""
    fig, axes = plt.subplots(1, 2, figsize=(22, 12), layout="constrained")
    simple_graph = nx.Graph(graph)
    route_stations = {station for result in results for station in result["path"]}
    xs, ys = zip(*(positions[station] for station in route_stations))
    x_padding = max(max(xs) - min(xs), 0.15) * 0.15
    y_padding = max(max(ys) - min(ys), 0.15) * 0.25
    label_groups = []
    for ax, result, color in zip(axes, results, ("#bd493b", "#226ea8")):
        path = result["path"]
        nx.draw_networkx_edges(simple_graph, positions, ax=ax, edge_color="#dfe3e8", width=1)
        nx.draw_networkx_nodes(simple_graph, positions, ax=ax, node_size=18, node_color="#dfe3e8")
        nx.draw_networkx_edges(
            simple_graph, positions, ax=ax, edgelist=list(zip(path, path[1:])),
            edge_color=color, width=3,
        )
        nx.draw_networkx_nodes(
            simple_graph, positions, ax=ax, nodelist=path, node_size=70, node_color=color,
        )
        label_positions = {station: (x, y + 0.025) for station, (x, y) in positions.items()}
        labels = nx.draw_networkx_labels(
            simple_graph, label_positions, ax=ax, labels={station: station for station in path},
            font_size=11, font_family=plt.rcParams["font.sans-serif"][0],
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8, "pad": 1},
        )
        ax.set_title(
            f"{result['strategy']}\n{result['segment_count']} 个区间 · "
            f"{result['station_count']} 个站点（含起终点） · 距离权重 {result['distance']:.2f}",
            fontsize=15, color=color, pad=12,
        )
        ax.set_xlim(min(xs) - x_padding, max(xs) + x_padding)
        ax.set_ylim(min(ys) - y_padding, max(ys) + y_padding)
        ax.axis("off")
        label_groups.append(labels)
    fig.suptitle(
        f"{results[0]['path'][0]} → {results[0]['path'][-1]}｜两种路径策略比较",
        fontsize=21,
    )
    for ax, labels in zip(axes, label_groups):
        _separate_labels(ax, labels, positions)
    return fig
