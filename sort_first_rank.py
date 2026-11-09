#!/usr/bin/env python3
"""Sort the top rank of a DOT digraph alphabetically by node label."""

from __future__ import annotations

import argparse
from pathlib import Path

import pygraphviz as pgv


def node_label(node: pgv.Node) -> str:
    """Return the node's explicit label, or its name when no label is set."""
    label = node.attr.get("label")
    if not label or label == r"\N":
        return str(node)
    return str(label)


def first_rank_node_names(graph: pgv.AGraph, tolerance: float = 0.01) -> list[str]:
    """Find nodes on the first rank for the graph's rank direction."""
    # Layout a copy so Graphviz's pos/width/height attributes do not leak into
    # the output graph.
    graph = graph.copy()
    graph.layout(prog="dot")
    positioned: list[tuple[pgv.Node, float, float]] = []

    for node in graph.nodes():
        position = node.attr.get("pos")
        if not position:
            continue
        try:
            x, y = position.rstrip("!").split(",", maxsplit=1)
            positioned.append((node, float(x), float(y)))
        except ValueError as error:
            raise ValueError(
                f"Graphviz returned an invalid position for node {node!s}: {position!r}"
            ) from error

    if not positioned:
        return []

    rankdir = (graph.graph_attr.get("rankdir") or "TB").upper()
    if rankdir == "TB":
        coordinate = lambda item: -item[2]  # highest Y
    elif rankdir == "BT":
        coordinate = lambda item: item[2]   # lowest Y
    elif rankdir == "LR":
        coordinate = lambda item: item[1]   # lowest X
    elif rankdir == "RL":
        coordinate = lambda item: -item[1]  # highest X
    else:
        raise ValueError(f"Unsupported rankdir: {rankdir!r}")

    first_coordinate = min(coordinate(item) for item in positioned)
    return [
        str(node)
        for node, x, y in positioned
        if abs(coordinate((node, x, y)) - first_coordinate) <= tolerance
    ]


def sort_first_rank(input_path: Path, output_path: Path) -> list[str]:
    graph = pgv.AGraph(str(input_path))
    if not graph.is_directed():
        raise ValueError("The input must be a DOT digraph, not an undirected graph")

    first_rank_names = first_rank_node_names(graph)
    first_rank = sorted(
        (graph.get_node(name) for name in first_rank_names),
        key=lambda node: (node_label(node).casefold(), node_label(node), str(node)),
    )

    if first_rank:
        rank = graph.add_subgraph(
            [str(node) for node in first_rank],
            name="sorted_first_rank",
            rank="same",
        )
        # dot uses these high-weight invisible edges as left-to-right ordering
        # constraints without drawing anything in the rendered graph.
        for left, right in zip(first_rank, first_rank[1:]):
            rank.add_edge(left, right, style="invis", weight="1000")

    graph.write(str(output_path))
    return [str(node) for node in first_rank]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Parse a DOT digraph and constrain its top rank to alphabetical "
            "left-to-right order by label."
        )
    )
    parser.add_argument("input", type=Path, help="input DOT file")
    parser.add_argument("output", type=Path, help="output DOT file")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sorted_nodes = sort_first_rank(args.input, args.output)
    print(
        f"Wrote {args.output}; sorted first-rank nodes: "
        + (", ".join(sorted_nodes) if sorted_nodes else "(none)")
    )


if __name__ == "__main__":
    main()
