import os
import tempfile

import pytest

import app.prompts_config as pc
from app.prompts_config import GRAMMAR_REWRITE_DEFAULT, STUDY_MATERIAL_DEFAULT


@pytest.fixture(autouse=True)
def reset_prompts_cache():
    pc._prompts_cache = None
    yield
    pc._prompts_cache = None


def test_load_builtin_when_file_empty():
    result = pc.load_prompts("")
    assert result["grammar_rewrite_prompt"] == GRAMMAR_REWRITE_DEFAULT
    assert result["study_material_prompt"] == STUDY_MATERIAL_DEFAULT


def test_load_builtin_when_file_missing():
    result = pc.load_prompts("/nonexistent/prompts.yaml")
    assert result["grammar_rewrite_prompt"] == GRAMMAR_REWRITE_DEFAULT
    assert result["study_material_prompt"] == STUDY_MATERIAL_DEFAULT


def test_load_builtin_when_file_invalid():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("{invalid yaml [[[")
        tmp_path = f.name
    try:
        result = pc.load_prompts(tmp_path)
        assert result["grammar_rewrite_prompt"] == GRAMMAR_REWRITE_DEFAULT
        assert result["study_material_prompt"] == STUDY_MATERIAL_DEFAULT
    finally:
        os.unlink(tmp_path)


def test_load_from_yaml_overrides():
    custom_grammar = "Custom grammar rewrite prompt"
    custom_study = "Custom study material prompt"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(f"grammar_rewrite_prompt: |\n  {custom_grammar}\nstudy_material_prompt: |\n  {custom_study}\n")
        tmp_path = f.name
    try:
        result = pc.load_prompts(tmp_path)
        assert result["grammar_rewrite_prompt"] == custom_grammar
        assert result["study_material_prompt"] == custom_study
    finally:
        os.unlink(tmp_path)


def test_load_partial_yaml_falls_back():
    custom_study = "Custom study only"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(f"study_material_prompt: |\n  {custom_study}\n")
        tmp_path = f.name
    try:
        result = pc.load_prompts(tmp_path)
        assert result["grammar_rewrite_prompt"] == GRAMMAR_REWRITE_DEFAULT
        assert result["study_material_prompt"] == custom_study
    finally:
        os.unlink(tmp_path)


def test_cache_returns_same_instance():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("grammar_rewrite_prompt: |\n  hello\nstudy_material_prompt: |\n  world\n")
        tmp_path = f.name
    try:
        r1 = pc.load_prompts(tmp_path)
        r2 = pc.load_prompts(tmp_path)
        r3 = pc.load_prompts("")
        assert r1 is r2
        assert r1 is r3
        assert r1["grammar_rewrite_prompt"] == "hello"
    finally:
        os.unlink(tmp_path)


@pytest.mark.parametrize(
    "yaml_content,expected_grammar_key",
    [
        ("grammar_rewrite_prompt: ''\nstudy_material_prompt: |\n  study\n", "builtin"),
        ("grammar_rewrite_prompt: |\n  g\nstudy_material_prompt: ''\n", "custom"),
    ],
)
def test_empty_string_uses_builtin(yaml_content, expected_grammar_key):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        tmp_path = f.name
    try:
        result = pc.load_prompts(tmp_path)
        if expected_grammar_key == "builtin":
            assert result["grammar_rewrite_prompt"] == GRAMMAR_REWRITE_DEFAULT
        else:
            assert result["grammar_rewrite_prompt"] == "g"
    finally:
        os.unlink(tmp_path)
