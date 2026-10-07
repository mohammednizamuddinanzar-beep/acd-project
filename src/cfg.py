"""
============================================================
  Business Workflow DSL – Control Flow Graph (CFG)
  Generates basic blocks, control flow edges, entry/exit nodes,
  and Graphviz DOT visual exporter for compiled workflows.
============================================================
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set


@dataclass
class BasicBlock:
    id: int
    label: str
    instructions: List[str] = field(default_factory=list)
    predecessors: List[int] = field(default_factory=list)
    successors: List[int] = field(default_factory=list)

    def add_instruction(self, instr: str):
        self.instructions.append(instr)


@dataclass
class CFGEdge:
    source_id: int
    target_id: int
    label: Optional[str] = None  # e.g., 'TRUE', 'FALSE', 'BRANCH', 'LOOP', 'NEXT'


class ControlFlowGraph:
    """Control Flow Graph generator for Business Workflow DSL."""

    def __init__(self, workflow_name: str = "Workflow"):
        self.workflow_name = workflow_name
        self.blocks: Dict[int, BasicBlock] = {}
        self.edges: List[CFGEdge] = []
        self._block_counter = 0

        # Create entry block
        self.entry_block = self.create_block("ENTRY")
        # Create exit block placeholder
        self.exit_block = self.create_block("EXIT")

    def create_block(self, label_prefix: str = "BB") -> BasicBlock:
        block_id = self._block_counter
        self._block_counter += 1
        label = f"{label_prefix}_{block_id}" if label_prefix not in ("ENTRY", "EXIT") else label_prefix
        block = BasicBlock(id=block_id, label=label)
        self.blocks[block_id] = block
        return block

    def add_edge(self, source_id: int, target_id: int, label: Optional[str] = None):
        edge = CFGEdge(source_id=source_id, target_id=target_id, label=label)
        self.edges.append(edge)
        if target_id not in self.blocks[source_id].successors:
            self.blocks[source_id].successors.append(target_id)
        if source_id not in self.blocks[target_id].predecessors:
            self.blocks[target_id].predecessors.append(source_id)

    def build_from_source(self, dsl_source: str):
        """Constructs CFG from Business Workflow DSL source statements."""
        lines = [line.strip() for line in dsl_source.splitlines() if line.strip() and not line.strip().startswith('#')]

        current_block = self.create_block("BB")
        self.add_edge(self.entry_block.id, current_block.id, "START")

        block_stack: List[BasicBlock] = []

        i = 0
        while i < len(lines):
            line = lines[i]

            if line.startswith("WORKFLOW") or line == "}":
                if line == "}" and block_stack:
                    closing_context = block_stack.pop()
                    if closing_context.label.startswith("IF_END") or closing_context.label.startswith("ELSE_END"):
                        pass
                i += 1
                continue

            if line.startswith("ON "):
                current_block.add_instruction(line)
                i += 1
                continue

            if line.startswith("IF "):
                cond_block = self.create_block("CONDITION")
                cond_block.add_instruction(line)
                self.add_edge(current_block.id, cond_block.id, "NEXT")

                then_block = self.create_block("THEN")
                self.add_edge(cond_block.id, then_block.id, "TRUE")

                join_block = self.create_block("JOIN")

                # Scan for ELSE block
                j = i + 1
                brace_depth = 1
                else_index = -1
                while j < len(lines) and brace_depth > 0:
                    if "{" in lines[j]:
                        brace_depth += lines[j].count("{")
                    if "}" in lines[j]:
                        brace_depth -= lines[j].count("}")
                    if brace_depth == 0 and (j + 1) < len(lines) and "ELSE" in lines[j + 1]:
                        else_index = j + 1
                        break
                    j += 1

                if else_index != -1:
                    else_block = self.create_block("ELSE")
                    self.add_edge(cond_block.id, else_block.id, "FALSE")
                    current_block = then_block
                else:
                    self.add_edge(cond_block.id, join_block.id, "FALSE")
                    current_block = then_block

                block_stack.append(join_block)
                i += 1
                continue

            if "ELSE" in line:
                if block_stack:
                    join_block = block_stack[-1]
                    self.add_edge(current_block.id, join_block.id, "JOIN")
                    # find the else block created earlier or create one
                    else_block = [b for b in self.blocks.values() if b.label.startswith("ELSE") and join_block.id in b.successors or True][-1]
                    current_block = else_block
                i += 1
                continue

            if line.startswith("RETRY "):
                retry_block = self.create_block("RETRY")
                retry_block.add_instruction(line)
                self.add_edge(current_block.id, retry_block.id, "RETRY_BEGIN")
                current_block = retry_block
                i += 1
                continue

            if line.startswith("PARALLEL"):
                par_block = self.create_block("PARALLEL")
                par_block.add_instruction(line)
                self.add_edge(current_block.id, par_block.id, "PARALLEL_START")
                current_block = par_block
                i += 1
                continue

            current_block.add_instruction(line)
            i += 1

        # Link last current block to Exit
        if current_block.id != self.exit_block.id:
            self.add_edge(current_block.id, self.exit_block.id, "EXIT")

        # Also connect join blocks to exit
        for b in self.blocks.values():
            if b.label.startswith("JOIN") and not b.successors:
                self.add_edge(b.id, self.exit_block.id, "EXIT")

    def to_dot(self) -> str:
        """Generates Graphviz DOT representation of the Control Flow Graph."""
        lines = [
            f'digraph "{self.workflow_name}_CFG" {{',
            '    node [shape=box, style="filled,rounded", fontname="Courier", fillcolor="#f0f4f8", color="#1e293b"];',
            '    edge [fontname="Helvetica", fontsize=10];',
            '    rankdir=TB;',
            ''
        ]

        # Basic block nodes
        for block_id, block in sorted(self.blocks.items()):
            if block.label == "ENTRY":
                fillcolor = "#dcfce7"  # green tint
                color = "#15803d"
            elif block.label == "EXIT":
                fillcolor = "#fee2e2"  # red tint
                color = "#b91c1c"
            elif "CONDITION" in block.label:
                fillcolor = "#fef3c7"  # yellow tint
                color = "#b45309"
            else:
                fillcolor = "#f1f5f9"
                color = "#475569"

            instr_text = "\\n".join(block.instructions) if block.instructions else f"[{block.label}]"
            label_attr = f"{block.label}\\n--- \\n{instr_text}".replace('"', '\\"')
            lines.append(f'    node_{block_id} [label="{label_attr}", fillcolor="{fillcolor}", color="{color}"];')

        lines.append('')

        # Directed edges
        for edge in self.edges:
            label_str = f' [label="{edge.label}"]' if edge.label else ''
            lines.append(f'    node_{edge.source_id} -> node_{edge.target_id}{label_str};')

        lines.append('}')
        return '\n'.join(lines)

    def export_dot(self, filepath: str = "workflow_cfg.dot") -> str:
        dot_str = self.to_dot()
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(dot_str)
        return dot_str
