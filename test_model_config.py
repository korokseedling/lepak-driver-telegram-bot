import json

from chore_functions import TOOL_FUNCTIONS


def test_model_config_tools_match_chore_functions():
    with open('model_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)

    tool_names = {tool['function']['name'] for tool in config['tools']}
    assert tool_names == set(TOOL_FUNCTIONS.keys())


def test_model_config_has_no_lta_settings():
    with open('model_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)

    assert 'lta_api_settings' not in config


def test_system_prompt_enforces_html_only_formatting():
    with open('system_prompt.md', 'r', encoding='utf-8') as f:
        prompt = f.read()

    assert 'NO ASTERISKS' in prompt.upper()
    assert '<b>' in prompt


def test_system_prompt_uses_claptrap_persona():
    with open('system_prompt.md', 'r', encoding='utf-8') as f:
        prompt = f.read()

    assert 'Claptrap' in prompt
    assert 'minion' in prompt.lower()
