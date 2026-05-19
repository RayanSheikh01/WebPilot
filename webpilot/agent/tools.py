'''TOOL_SCHEMAS is a list of 9 dicts (web_search, browser_goto, browser_get_text, browser_get_links, browser_screenshot, browser_back, note, cite, finish).
Each has name, description, input_schema (a JSON schema with type: "object").
Each required param appears in input_schema.required.'''

from typing import List, Dict

TOOL_SCHEMAS: List[Dict] = [
    {
        "name": "web_search",
        "description": "Search the web for recent information. Use this tool when you need to find up-to-date information, or if you need to find information that might not be on the page you have open. Input should be a JSON object with a 'query' field containing the search query, and an optional 'k' field for the number of results (default 3).",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string"
                },
                "k": {
                    "type": "integer",
                    "default": 3
                }
            },
            "required": ["query"]
        },
    },
    {
        "name": "browser_goto",
        "description": "Navigate the browser to a URL. Use this tool to load a web page. Input should be a JSON object with a 'url' field containing the URL to navigate to.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string"
                }
            },
            "required": ["url"]
        },
    },
    {
        "name": "browser_get_text",
        "description": "Extract text content from the current page. Use this tool to read the text of the page. Input should be a JSON object with an optional 'max_chars' field to limit the number of characters returned (default 1000).",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_chars": {
                    "type": "integer",
                    "default": 1000
                }
            },
            "required": []
        },
    },
    {
        "name": "browser_get_links",
        "description": "Extract links from the current page. Use this tool to find links on the page. Input should be an empty JSON object ({}). Output will be a list of dicts with 'text' and 'href' fields.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        },
    },
    {
        "name": "browser_screenshot",
        "description": "Take a screenshot of the current page. Use this tool to capture the visual appearance of the page. Input should be an empty JSON object ({}). Output will be a base64-encoded PNG image.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        },
    },
    {
        "name": "browser_back",
        "description": "Go back in browser history. Use this tool to return to the previous page. Input should be an empty JSON object ({}).",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        },
    },
    {
        "name": "note",
        "description": "Record a note for later reference. Use this tool to save information you might want to recall later. Input should be a JSON object with a 'content' field containing the note text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string"
                }
            },
            "required": ["content"]
        },
    },
    {
        "name": "cite",
        "description": "Add a citation for a piece of information. Use this tool to keep track of sources for information you find. Input should be a JSON object with 'text' and 'url' fields.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string"
                },
                "url": {
                    "type": "string"
                }
            },
            "required": ["text", "url"]
        },
    },
    {
        "name": "finish",
        "description": "Finish the task and return the final answer. Use this tool when you have completed all necessary steps and are ready to provide the final answer. Input should be a JSON object with an 'answer' field containing the final answer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "answer": {
                    "type": "string"
                }
            },
            "required": ["answer"]
        },
    },
]