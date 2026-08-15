"""
Top-level entry for the custom-opcode VM.

compile_to_lua(src) parses and compiles Lua source to a self-contained Lua
program that executes it via a custom bytecode interpreter -- the source is
never loadstring'd. Raises CompileError on unsupported input so the caller can
fall back to the source-level VM.
"""
from lvm_compiler import compile_source, CompileError  # noqa: F401
from lvm_runtime import emit_program


def compile_to_lua(src):
    protos, main_index = compile_source(src)
    return emit_program(protos, main_index)
