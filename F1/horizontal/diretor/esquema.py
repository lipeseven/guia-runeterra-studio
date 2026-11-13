"""Validador mínimo de JSON Schema (subconjunto do draft 2020-12), sem dependências.

O `.venv` não tem `jsonschema` e nada é instalado só para isso. Os arquivos em `esquemas/` são JSON Schema padrão:
se um dia o `jsonschema` entrar, ele lê os mesmos arquivos. Palavras suportadas: type, enum, const, required,
properties, additionalProperties (bool ou esquema), items, minItems, maxItems, minimum, maximum, exclusiveMinimum,
minLength, pattern, anyOf, oneOf, $ref (#/$defs/...).
"""
from __future__ import annotations

import re
from pathlib import Path

from comum import ESQUEMAS, ler_json

_TIPOS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def carregar(nome: str) -> dict:
    p = ESQUEMAS / (nome if nome.endswith(".json") else f"{nome}.schema.json")
    return ler_json(p)


def _ref(raiz: dict, ref: str) -> dict:
    if not ref.startswith("#/"):
        raise ValueError(f"$ref não suportado: {ref}")
    no = raiz
    for parte in ref[2:].split("/"):
        no = no[parte]
    return no


def validar(dados, esquema: dict | str, raiz: dict | None = None, caminho: str = "$") -> list[str]:
    """Lista de erros ("$.cenas[2].motor: valor 'blender' fora de [...]"). Vazia = válido."""
    if isinstance(esquema, str):
        esquema = carregar(esquema)
    raiz = raiz or esquema
    if "$ref" in esquema:
        return validar(dados, _ref(raiz, esquema["$ref"]), raiz, caminho)
    erros: list[str] = []
    t = esquema.get("type")
    if t is not None:
        tipos = t if isinstance(t, list) else [t]
        if not any(_TIPOS[x](dados) for x in tipos):
            return [f"{caminho}: esperado {'/'.join(tipos)}, veio {type(dados).__name__}"]
    if "const" in esquema and dados != esquema["const"]:
        erros.append(f"{caminho}: esperado {esquema['const']!r}")
    if "enum" in esquema and dados not in esquema["enum"]:
        erros.append(f"{caminho}: valor {dados!r} fora de {esquema['enum']}")
    if isinstance(dados, (int, float)) and not isinstance(dados, bool):
        if "minimum" in esquema and dados < esquema["minimum"]:
            erros.append(f"{caminho}: {dados} < mínimo {esquema['minimum']}")
        if "maximum" in esquema and dados > esquema["maximum"]:
            erros.append(f"{caminho}: {dados} > máximo {esquema['maximum']}")
        if "exclusiveMinimum" in esquema and dados <= esquema["exclusiveMinimum"]:
            erros.append(f"{caminho}: {dados} ≤ {esquema['exclusiveMinimum']}")
    if isinstance(dados, str):
        if "minLength" in esquema and len(dados) < esquema["minLength"]:
            erros.append(f"{caminho}: texto vazio/curto demais")
        if "pattern" in esquema and not re.search(esquema["pattern"], dados):
            erros.append(f"{caminho}: {dados!r} não segue o padrão {esquema['pattern']}")
    if isinstance(dados, list):
        if "minItems" in esquema and len(dados) < esquema["minItems"]:
            erros.append(f"{caminho}: {len(dados)} itens < mínimo {esquema['minItems']}")
        if "maxItems" in esquema and len(dados) > esquema["maxItems"]:
            erros.append(f"{caminho}: {len(dados)} itens > máximo {esquema['maxItems']}")
        if "items" in esquema:
            for k, v in enumerate(dados):
                erros += validar(v, esquema["items"], raiz, f"{caminho}[{k}]")
    if isinstance(dados, dict):
        for r in esquema.get("required", []):
            if r not in dados:
                erros.append(f"{caminho}: falta o campo '{r}'")
        props = esquema.get("properties", {})
        extra = esquema.get("additionalProperties", True)
        for k, v in dados.items():
            if k in props:
                erros += validar(v, props[k], raiz, f"{caminho}.{k}")
            elif extra is False:
                erros.append(f"{caminho}: campo desconhecido '{k}'")
            elif isinstance(extra, dict):
                erros += validar(v, extra, raiz, f"{caminho}.{k}")
    for chave in ("anyOf", "oneOf"):
        if chave in esquema:
            oks = [not validar(dados, s, raiz, caminho) for s in esquema[chave]]
            n = sum(oks)
            if n == 0 or (chave == "oneOf" and n > 1):
                erros.append(f"{caminho}: não casa com {'nenhuma' if n == 0 else 'mais de uma'} das opções de {chave}")
    return erros


def exigir(dados, nome: str) -> None:
    erros = validar(dados, nome)
    if erros:
        raise ValueError(f"{nome} inválido:\n  " + "\n  ".join(erros[:30]))
