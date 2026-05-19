from webpilot.agent.tools import TOOL_SCHEMAS

EXPECTED_NAMES = {
    "web_search",
    "browser_goto",
    "browser_get_text",
    "browser_get_links",
    "browser_screenshot",
    "browser_back",
    "note",
    "cite",
    "finish",
}


def test_tool_schemas_count_and_names():
    assert len(TOOL_SCHEMAS) == 9
    assert {t["name"] for t in TOOL_SCHEMAS} == EXPECTED_NAMES


def test_each_schema_well_formed():
    for tool in TOOL_SCHEMAS:
        assert isinstance(tool["name"], str) and tool["name"]
        assert isinstance(tool["description"], str) and tool["description"]
        schema = tool["input_schema"]
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema and isinstance(schema["required"], list)


def test_required_fields_appear_in_properties():
    for tool in TOOL_SCHEMAS:
        props = tool["input_schema"]["properties"]
        for req in tool["input_schema"]["required"]:
            assert req in props, f"{tool['name']}: required field {req!r} not in properties"


def test_no_mutating_browser_tools_exposed():
    forbidden = {"browser_click", "browser_fill", "browser_submit", "browser_eval"}
    names = {t["name"] for t in TOOL_SCHEMAS}
    assert names & forbidden == set()
