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


class ToolExecutor:
    def __init__(self, browser, search, tracker, emit, screenshot_dir, notes_sink):
        self.browser = browser
        self.search = search
        self.tracker = tracker
        self.emit = emit
        self.screenshot_dir = screenshot_dir
        self.notes_sink = notes_sink
        self.tool_map = {
            "web_search": self._run_web_search,
            "browser_goto": self._run_browser_goto,
            "browser_get_text": self._run_browser_get_text,
            "browser_get_links": self._run_browser_get_links,
            "browser_screenshot": self._run_browser_screenshot,
            "browser_back": self._run_browser_back,
            "note": self._run_note,
            "cite": self._run_cite,
            "finish": self._run_finish,
        }

    async def run(self, name: str, input: Dict) -> Dict:
        if name not in self.tool_map:
            raise ValueError(f"Unknown tool: {name}")
        await self.tracker.check_before_call(name, input)
        result = await self.tool_map[name](input)
        tokens_used = 0  # In a real implementation, calculate tokens used based on input and output size.
        await self.tracker.record_call(name, input, result, tokens_used)
        return result

    # Placeholder implementations for each tool. In a real implementation, these would interact with the browser and search components.

    async def _run_web_search(self, input):
        query = input["query"]
        k = input.get("k", 3)
        return {"results": [f"Result {i+1} for {query}" for i in range(k)]}

    async def _run_browser_goto(self, input):
        url = input["url"]
        # Simulate browser navigation
        return {"status": f"Navigated to {url}"}

    async def _run_browser_get_text(self, input):
        max_chars = input.get("max_chars", 1000)
        # Simulate getting text from the page
        return {"text": "Some page text"[:max_chars]}

    async def _run_browser_get_links(self, input):
        # Simulate extracting links from the page
        return {"links": [{"text": "Example", "href": "http://example.com"}]}

    async def _run_browser_screenshot(self, input):
        # Simulate taking a screenshot
        return {"screenshot": "base64-encoded-image"}
    
    async def _run_browser_back(self, input):
        # Simulate going back in browser history
        return {"status": "Went back in history"}
    
    async def _run_note(self, input):
        content = input["content"]
        # Simulate saving a note
        self.notes_sink.save(content)
        return {"status": "Note saved"}
    
    async def _run_cite(self, input):
        text = input["text"]
        url = input["url"]
        # Simulate saving a citation
        self.notes_sink.save(f"Citation: {text} ({url})")
        return {"status": "Citation saved"}
    
    async def _run_finish(self, input):
        answer = input["answer"]
        # Simulate finishing the task
        return {"status": "Task finished", "answer": answer}
    
